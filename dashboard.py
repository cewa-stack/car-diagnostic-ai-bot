import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA ---
API_URL_LATEST = "http://127.0.0.1:8000/latest"
API_URL_HISTORY = "http://127.0.0.1:8000/history"
REFRESH_RATE = 3

# --- USTAWIENIA STRONY ---
st.set_page_config(
    page_title="CewAI Diagnostics Pro",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PROFESSIONAL CSS THEME ---
st.markdown("""
    <style>
    /* 1. Główne tło */
    .stApp { background-color: #0e1117; }

    /* 2. WYMUSZENIE BIAŁEGO TEKSTU */
    p, .stMarkdown, .stText, li, h1, h2, h3, h4, h5, h6 { color: #e0e0e0 !important; }
    
    /* 3. Karty */
    .css-card {
        background-color: #1a1c24;
        border: 1px solid #2b2d35;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 15px;
    }
    
    /* 4. Metryki */
    div[data-testid="stMetric"] {
        background-color: #1a1c24;
        border: 1px solid #2b2d35;
        border-radius: 6px;
    }
    div[data-testid="stMetricLabel"] { color: #9ca3af !important; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }

    /* 5. Alerty DTC */
    .dtc-tag {
        display: inline-block;
        background-color: #371b1b;
        color: #f87171 !important;
        border: 1px solid #7f1d1d;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-right: 8px;
        margin-bottom: 4px;
    }
    .status-ok {
        background-color: #064e3b;
        color: #34d399 !important;
        border: 1px solid #065f46;
        padding: 10px;
        border-radius: 6px;
        text-align: center;
        font-weight: 600;
    }

    /* 6. AI Box */
    .ai-container {
        border-left: 4px solid #4f8bf9;
        background-color: #1a1c24;
        padding: 15px 20px;
        border-radius: 0 8px 8px 0;
    }
    
    /* 7. Linie podziału */
    hr { margin-top: 1em; margin-bottom: 1em; border-color: #333; }
    
    div[data-testid="stSidebar"] button { width: 100%; }
    
    /* 8. Podświetlenie wybranego wiersza w tabeli */
    [data-testid="stDataFrame"] { border: 1px solid #333; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJE API ---
def get_live_data():
    try:
        response = requests.get(API_URL_LATEST, timeout=5)
        return response.json() if response.status_code == 200 else None
    except: return None

def get_history_data():
    try:
        response = requests.get(API_URL_HISTORY, params={"limit": 50}, timeout=5)
        return response.json().get("history", []) if response.status_code == 200 else []
    except: return []

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2316/2316086.png", width=70)
    st.markdown("### Diagnostic AI")
    st.caption("Professional Solution by CewAI")
    st.divider()

    api_status = get_live_data()
    if api_status:
        st.markdown("✅ **System Online**")
        device_id = api_status.get("live_data", {}).get("device_id", "N/A")
        st.code(f"ID: {device_id}", language="text")
    else:
        st.markdown("🔴 **System Offline**")
        st.caption("Brak połączenia z backendem")

    st.divider()
    st.markdown("**Panel Sterowania**")
    if st.button("⚡ AKTUALIZUJ TERAZ", type="primary"):
        st.rerun()

    st.markdown("")
    auto_refresh = st.toggle("Auto-odświeżanie (Live)", value=True)
    refresh_rate = st.slider("Częstotliwość (s)", 1, 10, 3)

# --- GŁÓWNY WIDOK ---
st.markdown('<div style="font-size: 1.8rem; font-weight: 700; color: white;">CewAI Vehicle Diagnostics</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size: 1rem; color: #888; margin-bottom: 2rem;">Zaawansowana analiza parametrów pojazdu w czasie rzeczywistym</div>', unsafe_allow_html=True)

tab_live, tab_history = st.tabs(["📊 LIVE DATA MONITOR", "🗃️ HISTORIA DIAGNOZ"])

# ==========================================
# ZAKŁADKA 1: LIVE MONITOR
# ==========================================
with tab_live:
    if not api_status:
        st.info("📡 Oczekiwanie na dane z pojazdu...")
    else:
        live = api_status.get("live_data", {})
        analysis = api_status.get("ai_analysis", {})
        timestamp = api_status.get("timestamp", 0)
        dtc_list = live.get("dtc", [])
        
        with st.container():
            col_car, col_time, col_stat = st.columns([2, 1, 1])
            with col_car:
                st.subheader(f"🚗 {live.get('name', 'Nieznany pojazd')}")
            with col_time:
                st.caption("Ostatni odczyt")
                st.write(datetime.fromtimestamp(timestamp).strftime('%H:%M:%S'))
            with col_stat:
                if dtc_list:
                    st.markdown(f":red[**Wykryto usterek: {len(dtc_list)}**]")
                else:
                    st.markdown(":green[**Status: OK**]")
        
        st.markdown("---")
        c_left, c_right = st.columns([2, 1])

        with c_left:
            st.markdown("#### ⚙️ Parametry Silnika")
            pids = live.get("pids", {})
            if pids:
                pid_items = list(pids.items())
                rows = len(pid_items) // 3 + 1
                for i in range(rows):
                    cols = st.columns(3)
                    for j in range(3):
                        idx = i * 3 + j
                        if idx < len(pid_items):
                            k, v = pid_items[idx]
                            cols[j].metric(k, str(v))
            else:
                st.warning("Brak aktywnych parametrów PID")

        with c_right:
            st.markdown("#### ⚠️ Kody DTC")
            if dtc_list:
                with st.container(border=True):
                    for code in dtc_list:
                        st.markdown(f'<div class="dtc-tag">{code}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-ok">BRAK BŁĘDÓW</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🧠 Analiza Sztucznej Inteligencji")
        
        if analysis and "analysis_summary" in analysis:
            st.markdown('<div class="ai-container">', unsafe_allow_html=True)
            st.markdown('<div style="color: #4f8bf9; font-weight: bold; font-size: 1.1rem; margin-bottom: 10px;">🔎 DIAGNOZA GEMINI</div>', unsafe_allow_html=True)
            st.write(analysis.get("analysis_summary"))
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**🔧 Zalecane działanie**")
                st.write(analysis.get("recommended_action"))
            with c2:
                st.markdown("**💰 Szacowany koszt**")
                st.write(f"**{analysis.get('estimated_repair_cost_pln')}**")
            with c3:
                st.markdown("**📊 Poziom pewności**")
                conf = analysis.get("confidence_level", "Low")
                if conf == "High" or conf == "Wysoki": st.progress(0.9)
                elif conf == "Medium": st.progress(0.5)
                else: st.progress(0.2)
                st.caption(f"Confidence: {conf}")

            with st.expander("Zobacz możliwe przyczyny techniczne"):
                for cause in analysis.get("possible_causes", []):
                    st.markdown(f"- {cause}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("AI analizuje napływające dane...")

# ==========================================
# ZAKŁADKA 2: HISTORIA (ZMODYFIKOWANA)
# ==========================================
with tab_history:
    col_h1, col_h2 = st.columns([1, 5])
    with col_h1:
        if st.button("🔄 Odśwież tabelę"):
            st.rerun()
    
    history = get_history_data()

    if history:
        # Przygotowanie danych
        table_data = []
        for r in history:
            raw_cost = r.get('full_analysis', {}).get('estimated_repair_cost_pln', 'N/A')
            cost = str(raw_cost) 
            
            table_data.append({
                "ID": r['id'],
                "Data": datetime.fromisoformat(r['timestamp']).strftime('%d.%m.%Y %H:%M'),
                "Pojazd": r['car_name'],
                "Błędy": ", ".join(r['dtc']) if r['dtc'] else "System OK",
                "Kosztorys": cost
            })
        
        df = pd.DataFrame(table_data)
        if not df.empty:
             df["Kosztorys"] = df["Kosztorys"].astype(str)

        # 1. INTERAKTYWNA TABELA
        st.markdown("👉 **Kliknij w wiersz tabeli, aby zobaczyć szczegóły poniżej**")
        
        event = st.dataframe(
            df,
            hide_index=True,
            selection_mode="single-row", # Pozwala wybrać tylko jeden wiersz
            on_select="rerun",           # Odświeża stronę po kliknięciu
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "Błędy": st.column_config.TextColumn(width="medium"),
            }
        )
        
        # 2. LOGIKA WYBORU REKORDU
        selected_record = None
        
        # Sprawdzamy, czy użytkownik coś kliknął
        if len(event.selection.rows) > 0:
            # Pobieramy index wybranego wiersza
            selected_index = event.selection.rows[0]
            # Pobieramy ID z DataFrame
            selected_db_id = df.iloc[selected_index]["ID"]
            # Szukamy pełnego obiektu w historii
            selected_record = next((item for item in history if item["id"] == selected_db_id), None)
        elif history:
            # Domyślnie pokaż najnowszy (pierwszy z góry)
            selected_record = history[0]

        st.divider()
        
        # 3. WYŚWIETLANIE SZCZEGÓŁÓW (KARTA DIAGNOSTYCZNA)
        if selected_record:
            st.subheader(f"📋 Karta Diagnostyczna (Raport #{selected_record['id']})")
            
            # Rozpakowanie danych
            raw_data = selected_record.get('full_data', {})
            ai_data = selected_record.get('full_analysis', {})
            
            with st.container(border=True):
                c_car, c_ai = st.columns([1, 1.5])
                
                # --- DANE Z AUTA ---
                with c_car:
                    st.markdown("#### 📡 Dane Pomiarowe")
                    st.write(f"**Pojazd:** {raw_data.get('name', 'N/A')}")
                    st.write(f"**Device ID:** `{raw_data.get('device_id', 'N/A')}`")
                    st.markdown("---")
                    
                    st.write("**Wykryte Kody DTC:**")
                    dtcs = raw_data.get('dtc', [])
                    if dtcs:
                        for code in dtcs:
                            st.markdown(f'<div class="dtc-tag">{code}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(":green[Brak błędów]")
                    
                    st.markdown("---")
                    st.write("**Parametry Live:**")
                    pids = raw_data.get('pids', {})
                    if pids:
                        for k, v in pids.items():
                            st.markdown(f"**{k}:** {v}")
                    else:
                        st.caption("Brak parametrów.")

                # --- RAPORT AI ---
                with c_ai:
                    st.markdown("#### 🧠 Raport Techniczny (Gemini)")
                    
                    st.info(ai_data.get('analysis_summary', 'Brak analizy'))
                    
                    st.markdown("**🔍 Możliwe przyczyny usterki:**")
                    causes = ai_data.get('possible_causes', [])
                    for cause in causes:
                        st.markdown(f"- {cause}")
                    
                    st.markdown("---")
                    st.markdown("**🔧 Zalecane działania naprawcze:**")
                    st.write(ai_data.get('recommended_action', '---'))
                    
                    st.markdown("---")
                    col_cost, col_conf = st.columns(2)
                    with col_cost:
                        st.metric("Szacowany Koszt", str(ai_data.get('estimated_repair_cost_pln', '---')))
                    with col_conf:
                        st.metric("Pewność Diagnozy", ai_data.get('confidence_level', '---'))
        else:
            st.info("Wybierz rekord z tabeli.")

    else:
        st.info("Brak historii. Podłącz urządzenie, aby zebrać dane.")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()