import os
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, RootModel, field_validator
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- ŁADOWANIE ZMIENNYCH ---
load_dotenv() 

# --- BAZA DANYCH ---
from sqlalchemy.orm import Session
from database import init_db, get_db, DiagnosticRecord

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CarDiagnosticAI")

# --- CONFIGURATION ---
API_KEY = os.getenv("GEMINI_API_KEY", "")
CACHE_DURATION_MINUTES = 30
RATE_LIMIT_DELAY = 4.0 

# --- DATA MODELS ---
class PIDData(RootModel[Dict[str, Any]]):
    pass

class DiagnosticData(BaseModel):
    device_id: str = Field(..., min_length=1)
    name: str = Field("Live Data from Car")
    dtc: List[str] = Field(default_factory=list)
    pids: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('dtc', mode='before')
    @classmethod
    def validate_dtc(cls, v):
        if not v: return []
        if isinstance(v, str): return [v]
        return [str(code).strip().upper() for code in v if code]

class AnalysisResult(BaseModel):
    analysis_summary: str = "Oczekiwanie na dane..."
    dtc_explanations: List[Dict[str, str]] = Field(default_factory=list)
    possible_causes: List[str] = Field(default_factory=list)
    estimated_repair_cost_pln: str = "---"
    recommended_action: str = "---"
    confidence_level: str = "Low"

    # Walidator 1: Naprawia DTC (lista słowników)
    @field_validator('dtc_explanations', mode='before')
    @classmethod
    def fix_dtc_structure(cls, v):
        if isinstance(v, list):
            cleaned = []
            for item in v:
                if isinstance(item, dict): cleaned.append(item)
                elif isinstance(item, str): cleaned.append({"code": "INFO", "explanation": item})
            return cleaned
        return []

    # Walidator 2: Naprawia Przyczyny (lista stringów)
    @field_validator('possible_causes', mode='before')
    @classmethod
    def fix_list_structure(cls, v):
        if isinstance(v, str): return [v]
        if isinstance(v, list): return [str(i) for i in v]
        return []

    # Walidator 3: Naprawia liczby na napisy (np. cenę)
    @field_validator('estimated_repair_cost_pln', 'recommended_action', 'analysis_summary', 'confidence_level', mode='before')
    @classmethod
    def force_string(cls, v):
        if v is None: return "---"
        return str(v)

class DiagnosticResponse(BaseModel):
    live_data: DiagnosticData
    ai_analysis: AnalysisResult
    timestamp: float
    cache_hit: bool

# --- SERVICE LAYER ---
class DiagnosticService:
    def __init__(self):
        self.latest_response_cache: Optional[DiagnosticResponse] = None
        self.analysis_cache: Dict[str, Dict] = {}
        self.last_api_call_time = 0.0

    def get_cache_key(self, dtc_list: List[str], pids: Dict) -> str:
        dtc_str = "|".join(sorted(dtc_list))
        pids_str = "|".join(f"{k}:{v}" for k, v in sorted(pids.items()))
        return f"{dtc_str}_{pids_str}".replace(" ", "")

    def is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self.analysis_cache:
            return False
        timestamp = self.analysis_cache[cache_key]["timestamp"]
        return (time.time() - timestamp) < (CACHE_DURATION_MINUTES * 60)

    async def enforce_rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_api_call_time
        if time_since_last < RATE_LIMIT_DELAY:
            wait_time = RATE_LIMIT_DELAY - time_since_last
            logger.info(f"Rate limiting: sleeping {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self.last_api_call_time = time.time()

    def clean_json_string(self, text: str) -> str:
        """Usuwa znaczniki Markdown ```json ... ```"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def get_fallback_analysis(self, dtc_codes: List[str], error_msg: str = "") -> dict:
        msg = f"Błąd analizy AI. {error_msg}" if API_KEY else "Brak klucza API"
        return {
            "analysis_summary": msg,
            "dtc_explanations": [{"code": str(c), "explanation": "Błąd"} for c in dtc_codes] or [{"code": "INFO", "explanation": "System OK"}],
            "possible_causes": ["Błąd parsowania JSON", "Problem z siecią"],
            "estimated_repair_cost_pln": "Nieznany",
            "recommended_action": "Sprawdź logi w konsoli backendu",
            "confidence_level": "Low"
        }

    async def clean_cache(self):
        current_time = time.time()
        keys_to_delete = [
            k for k, v in self.analysis_cache.items()
            if (current_time - v["timestamp"]) > (CACHE_DURATION_MINUTES * 60)
        ]
        for k in keys_to_delete:
            del self.analysis_cache[k]

    async def process_data(self, data: DiagnosticData) -> tuple[dict, bool]:
        cache_key = self.get_cache_key(data.dtc, data.pids)
        
        if self.is_cache_valid(cache_key):
            logger.info(f"Cache HIT for {data.device_id}")
            return self.analysis_cache[cache_key]["data"], True

        if not API_KEY:
            logger.warning("BRAK KLUCZA API!")
            return self.get_fallback_analysis(data.dtc), False

        await self.enforce_rate_limit()

        system_prompt = (
            "Jesteś Głównym Technikiem Diagnostą. Analizuj dane OBD2. "
            "Odpowiedz WYŁĄCZNIE czystym JSON (bez znaczników markdown). Pola: "
            "analysis_summary, dtc_explanations (lista), possible_causes (lista), "
            "estimated_repair_cost_pln (string), recommended_action, confidence_level."
        )
        user_prompt = (
            f"Pojazd: {data.name}\nKody: {data.dtc}\nPID: {json.dumps(data.pids)}\nAnaliza PL."
        )

        try:
            logger.info("Calling Gemini AI...")
            client = genai.Client(api_key=API_KEY)
            response = await asyncio.to_thread(
                client.models.generate_content,
                model='gemini-2.0-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            
            raw_text = response.text
            # --- DEBUG LOG ---
            logger.info(f"[DEBUG] SUROWA ODPOWIEDŹ GEMINI: {raw_text[:200]}...") # Pokaż pierwsze 200 znaków
            
            # Czyszczenie i parsowanie
            clean_text = self.clean_json_string(raw_text)
            
            try:
                analysis_data = json.loads(clean_text)
                # Obsługa listy jako głównego obiektu
                if isinstance(analysis_data, list): 
                    analysis_data = analysis_data[0] if analysis_data else {}
            except json.JSONDecodeError as e:
                logger.error(f"JSON Parse Error: {e}")
                logger.error(f"Failed Text: {clean_text}")
                return self.get_fallback_analysis(data.dtc, "Błąd struktury JSON"), False

            self.analysis_cache[cache_key] = {"data": analysis_data, "timestamp": time.time()}
            return analysis_data, False

        except Exception as e:
            logger.error(f"AI Critical Fail: {e}")
            return self.get_fallback_analysis(data.dtc, str(e)), False

# --- APP SETUP ---
app = FastAPI(title="Car Diagnostic AI Bot", version="3.4.0")
service = DiagnosticService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()
    # Pusty stan początkowy
    service.latest_response_cache = DiagnosticResponse(
        live_data=DiagnosticData(device_id="INIT"),
        ai_analysis=AnalysisResult(),
        timestamp=time.time(),
        cache_hit=False
    )
    logger.info("System ready.")

# --- ENDPOINTS ---

@app.post("/analyze", response_model=DiagnosticResponse, tags=["Diagnostics"])
async def analyze_endpoint(
    data: DiagnosticData, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    analysis_result, cache_hit = await service.process_data(data)
    
    response = DiagnosticResponse(
        live_data=data,
        ai_analysis=analysis_result,
        timestamp=time.time(),
        cache_hit=cache_hit
    )
    
    service.latest_response_cache = response
    
    try:
        new_record = DiagnosticRecord(
            device_id=data.device_id,
            car_name=data.name,
            raw_data=data.model_dump(),
            ai_analysis=analysis_result
        )
        db.add(new_record)
        db.commit()
    except Exception as e:
        logger.error(f"DB Error: {e}")

    background_tasks.add_task(service.clean_cache)
    return response

@app.get("/latest", response_model=DiagnosticResponse, tags=["Diagnostics"])
async def get_latest():
    if service.latest_response_cache:
        return service.latest_response_cache
    raise HTTPException(status_code=404, detail="No data yet")

@app.get("/history", tags=["Diagnostics"])
async def get_history(limit: int = 50, db: Session = Depends(get_db)):
    records = db.query(DiagnosticRecord).order_by(DiagnosticRecord.timestamp.desc()).limit(limit).all()
    history_list = []
    for r in records:
        ai_data = r.ai_analysis
        if isinstance(ai_data, list): ai_data = ai_data[0] if ai_data else {}
        if not isinstance(ai_data, dict): ai_data = {}
        
        history_list.append({
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "car_name": r.car_name,
            "dtc": r.raw_data.get("dtc", []),
            "full_analysis": ai_data,
            "full_data": r.raw_data  # <--- TEGO BRAKOWAŁO!
        })
    return {"history": history_list}

if __name__ == "__main__":
    import uvicorn
    if not API_KEY:
        logger.warning("⚠️ OSTRZEŻENIE: Zmienna GEMINI_API_KEY nie jest ustawiona!")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)