from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Konfiguracja SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./car_logs.db"

# check_same_thread=False jest potrzebne dla SQLite w FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- MODEL TABELI ---
class DiagnosticRecord(Base):
    __tablename__ = "diagnostics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    device_id = Column(String, index=True)
    car_name = Column(String)
    
    # Przechowujemy pełne JSONy, żeby nic nie stracić
    raw_data = Column(JSON)      # To co przyszło z ESP32 (DTC + PID)
    ai_analysis = Column(JSON)   # To co odpisało Gemini

def init_db():
    """Tworzy tabele w bazie danych"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Zależność do pobierania sesji bazy"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()