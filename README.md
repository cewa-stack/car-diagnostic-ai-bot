#  Car Diagnostic AI Bot - System Diagnostyki Pojazdów OBD2

## AI Diagnostic System | Real-Time OBD2 Analysis with Gemini API

System umożliwia zaawansowaną diagnostykę pojazdów w czasie rzeczywistym, wykorzystując dane z modułu ESP32/OBD2, backend FastAPI oraz analityczny model Gemini do interpretacji kodów DTC i parametrów PID.

** Szybka i precyzyjna diagnoza usterek samochodowych, minimalizująca koszty i czas postoju.
** Wykorzystuje model Gemini do generowania profesjonalnych raportów, obejmujących możliwe przyczyny, zalecane działania i szacowany koszt naprawy.
** Idealne rozwiązanie dla warsztatów samochodowych i entuzjastów motoryzacji, do monitorowania stanu technicznego w czasie rzeczywistym.

---

###  Funkcjonalności

* **Real-Time Data Flow:** Odbiór danych (kody DTC, parametry Live PID) z urządzenia zewnętrznego (ESP32/OBD2).
* **AI-Powered Analysis:** Wykorzystanie Google Gemini (model `gemini-2.0-flash`) do zaawansowanej interpretacji diagnostycznej w języku polskim.
* **Persistent Data Storage:** Przechowywanie historii diagnoz w bazie danych SQLite (za pomocą SQLAlchemy).
* **Interactive Dashboard:** Intuicyjny interfejs użytkownika oparty na Streamlit do monitorowania danych na żywo i przeglądania historii.
* **Caching Mechanism:** Wbudowany mechanizm buforowania w FastAPI, minimalizujący opóźnienia i koszty API.

###  Stos Technologiczny

* **Backend:** Python, FastAPI, Uvicorn, SQLAlchemy (SQLite)
* **AI/ML:** Google Gemini API (`gemini-2.0-flash`), Pydantic (walidacja danych)
* **Frontend:** Python, Streamlit (Dashboard)
* **Inne:** Python-dotenv, CORS Middleware


###  Instrukcja Uruchomienia (Lokalnie)

#### Krok 1: Klonowanie Repozytorium

```bash
git clone [https://github.com/TwojaNazwa/car-diagnostic-ai-bot.git](https://github.com/TwojaNazwa/car-diagnostic-ai-bot.git)
cd car-diagnostic-ai-bot
Krok 2: Konfiguracja Środowiska
Utwórz Środowisko Wirtualne:

Bash

python -m venv venv
source venv/bin/activate  # lub .\venv\Scripts\activate dla Windows
Instalacja Zależności:

Bash

pip install -r requirements.txt
Krok 3: Konfiguracja Klucza API
Utwórz plik .env w głównym katalogu i wklej swój klucz API:

# Plik .env
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
Krok 4: Uruchomienie Serwerów
Uruchom Backend (w terminalu #1):

Bash

uvicorn backend_server:app --host 0.0.0.0 --port 8000
Uruchom Frontend (w terminalu #2):

Bash

streamlit run dashboard.py
Po uruchomieniu, otwórz w przeglądarce adres podany przez Streamlit (zwykle http://localhost:8501).

 Jak Przetestować
Możesz przetestować system, wysyłając symulowane dane POST do serwera. Adres API to http://127.0.0.1:8000/analyze.

Przykład użycia curl (Symulacja awarii zapłonu):

Bash

curl -X POST [http://127.0.0.1:8000/analyze](http://127.0.0.1:8000/analyze) \
-H "Content-Type: application/json" \
-d '{
    "device_id": "SIM_TEST_01",
    "dtc": ["P0300", "P0302"],
    "pids": {
        "Obroty silnika (RPM)": "850",
        "Temperatura płynu (°C)": "95",
        "Obciążenie silnika (%)": "40"
    }
}'
Cechy AI Diagnosty:
✔️ Szybka interpretacja kodów DTC i parametrów Live PID. ✔️ Szacowanie kosztów naprawy (w PLN) jako cenny wskaźnik. ✔️ Zapewnienie poziomu pewności diagnozy (Confidence Level).
