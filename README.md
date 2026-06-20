# ⚙️ CityPulse AI Backend — Smart Governance Engine

FastAPI-powered REST API gateway and autonomous AI grievance router for the CityPulse AI platform. It automatically classifies civic complaints, performs predictive analytics, and handles the multi-lingual Voice AI assistant chat loops.

---

## 🚀 Live API Endpoints
* **Base URL**: [https://citypluse-ai-backend.onrender.com](https://citypluse-ai-backend.onrender.com)
* **Interactive Docs (Swagger)**: [https://citypluse-ai-backend.onrender.com/docs](https://citypluse-ai-backend.onrender.com/docs)
* **Redoc alternative**: [https://citypluse-ai-backend.onrender.com/redoc](https://citypluse-ai-backend.onrender.com/redoc)

---

## 🛠️ API Routing Ledger

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/classify` | Classifies raw complaint text, extracts category, priority score, and assigned department. |
| **GET** | `/complaints` | Returns a list of all complaints in the registry. |
| **POST** | `/complaints` | Registers a new civic complaint into the SQLite database. |
| **GET** | `/complaints/{id}` | Fetches individual ticket details. |
| **PATCH** | `/complaints/{id}` | Updates ticket status (*Submitted $\rightarrow$ In Progress $\rightarrow$ Resolved*) or reassigns departments. |
| **GET** | `/analytics/summary` | Aggregates operational KPIs (Average SLA, Active loads, SLA breach ratios). |
| **GET** | `/analytics/predictive` | Performs workload forecasting and Llama-based proactive advisory recommendations. |
| **POST** | `/assistant/chat` | Chat gateway for the Voice AI widget. Returns text synthesis and structured complaint data. |

---

## 🧠 AI & Fallback Mechanisms
* **Primary Classifier**: Uses Meta Llama 3.1 LLM models (via Groq Cloud) to parse inputs, match Udaipur wards, compute public safety scores, and output clean JSON structures validated by Pydantic.
* **Keyword Fallback**: If the Groq API key is missing or hits free-tier rate limits, the backend automatically falls back to a regex keyword-matching engine so the live app never crashes during demo slides.

---

## 🏃 Local Setup & Run

1. **Activate virtual environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .\.venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment**:
   Create a `.env` file containing your `GROQ_API_KEY`:
   ```env
   GROQ_API_KEY=gsk_your_key_here
   ```
4. **Seed database with 200 mock complaints**:
   ```bash
   python seed.py
   ```
5. **Start server**:
   ```bash
   python -m uvicorn main:app --reload
   ```
