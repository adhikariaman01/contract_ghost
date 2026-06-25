# 👻 Contract Ghost

> AI-powered multi-agent system that detects **ghost clauses** — contract provisions that are legally present but unenforceable, void, or contradictory in a specific jurisdiction.

---

## What it does

Contract Ghost uses a two-agent LangGraph pipeline to analyze legal documents:

1. **Extractor Agent** — Parses the raw contract into structured, typed clauses using Gemini
2. **Evaluator Agent** — Cross-references each clause against jurisdiction-specific enforceability rules via RAG (ChromaDB)
3. **Human-in-the-Loop** — Flags low-confidence or critical findings for your review before finalizing
4. **Final Report** — Generates a risk-scored report with plain-language explanations and suggested revisions

### Supported jurisdictions
California · New York · Texas · Federal · EU

### Supported contract types
Lease · Employment · Terms of Service · NDA · Other

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Google Gemini API key](https://aistudio.google.com/apikey)

### 1. Clone and run

```bash
git clone <repo>
cd contract_ghost
python run.py
```

The launcher will:
- Prompt you for your `GEMINI_API_KEY` and create `backend/.env`
- Install Python dependencies (`pip install -r requirements.txt`)
- Install npm dependencies (`npm install`)
- Start both servers in parallel with color-coded output

### 2. Open the app

```
http://localhost:5173
```

### 3. Manual setup (alternative)

```bash
# Backend
cd backend
echo "GEMINI_API_KEY=your_key_here" > .env
pip install -r requirements.txt
python run.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Architecture

```
contract_ghost/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point + lifespan
│   │   ├── config.py            # Pydantic Settings
│   │   ├── models/
│   │   │   ├── schemas.py       # Pydantic v2 models
│   │   │   └── state.py         # LangGraph TypedDict state
│   │   ├── agents/
│   │   │   ├── extractor_agent.py   # Clause extraction
│   │   │   ├── evaluator_agent.py   # Enforceability evaluation
│   │   │   ├── finalizer.py         # Report assembly
│   │   │   └── graph.py             # LangGraph state machine
│   │   ├── services/
│   │   │   ├── vector_store.py      # ChromaDB setup + retrieval
│   │   │   ├── rules_loader.py      # JSON rules loader
│   │   │   └── session_store.py     # In-memory session state
│   │   ├── routers/
│   │   │   └── contract.py          # REST API endpoints
│   │   └── data/
│   │       ├── legal_rules/
│   │       │   └── unenforceability_rules.json  # 25 curated rules
│   │       └── sample_contracts/
│   │           └── sample_lease_ca.txt
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Home.tsx             # Upload panel
│       │   ├── AnalysisPage.tsx     # Live pipeline monitor
│       │   └── ReportPage.tsx       # Final report view
│       ├── components/
│       │   ├── AgentChainVisualizer.tsx
│       │   └── HitlReview.tsx       # HITL modal
│       ├── services/api.ts
│       ├── hooks/usePolling.ts
│       └── types/index.ts
└── run.py                           # Master launcher
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/contract/analyze` | Start analysis pipeline |
| `GET` | `/api/contract/status/{id}` | Poll pipeline state |
| `GET` | `/api/contract/reports/{id}` | Get clause reports |
| `POST` | `/api/contract/hitl/{id}` | Submit HITL verdict |
| `GET` | `/api/contract/report/{id}` | Get final report |
| `GET` | `/api/contract/chain/{id}` | Get agent chain log |
| `GET` | `/api/contract/sample` | Load demo contract |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + TypeScript |
| Styling | CSS Modules (no framework) |
| Backend | FastAPI + Uvicorn |
| Validation | Pydantic v2 |
| LLM | Google Gemini 1.5 Flash |
| Agent Framework | LangChain + LangGraph |
| Vector Store | ChromaDB (in-memory) |
| State | In-memory session store |

---

## Environment Variables

```bash
# backend/.env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash          # optional
GEMINI_EMBEDDING_MODEL=models/embedding-001  # optional
BACKEND_PORT=8000                      # optional
```

---

## Disclaimer

Contract Ghost is for **informational purposes only** and does not constitute legal advice.
The analysis reflects general enforceability principles and may not account for specific factual circumstances, recent case law, or local ordinances. Always consult a qualified attorney before relying on these findings.
