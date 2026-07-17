# Medical Claim Fighter

AI-powered assistant for analyzing medical bills, EOBs, and insurance denial letters — with deterministic billing-error detection, legal-backed findings, and a full appeal letter workflow.

Upload a document, get a structured risk report in seconds, review an editable appeal letter, and track the case through approval, sending, and insurer follow-up.

> **Portfolio / demo project.** Not intended for production use with real patient data without proper HIPAA compliance, authentication, and a BAA with your cloud provider.

---

## Features

### Document analysis
- Upload **TXT, PDF, PNG, or JPG** files (up to 10 MB)
- Automatic document classification (EOB, denial letter, itemized bill)
- LLM-powered field extraction: patient info, CPT/ICD codes, amounts, denial reasons
- Deterministic rule engine for billing errors — no LLM guesswork on factual checks

### Risk report
- Findings with confidence levels, evidence, legal citations, and recommended actions
- Supports common denial types: medical necessity (CO-50), code mismatch (CO-16), out-of-network (CO-96), balance billing (No Surprises Act)
- Extracted fields view and processing step timeline

### Appeal letter workflow
- Auto-generated appeal letter draft from risk report findings
- Editable letter interface with version history (draft → approved → sent)
- Supporting document checklist tailored to finding types
- Insurer response upload with Round 2 draft generation
- Follow-up deadline tracking after a letter is marked sent

### Case management
- Web dashboard to list, view, and delete cases
- Real-time processing status polling
- File-based persistence (JSON + local uploads) for local development

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend — Next.js 16 (App Router) + TypeScript                │
│  Upload UI · Case dashboard · Risk report · Appeal letter editor│
└────────────────────────────┬────────────────────────────────────┘
                             │ REST (axios + React Query)
┌────────────────────────────▼────────────────────────────────────┐
│  Backend — FastAPI (Python)                                     │
│  Upload · Process · Cases · Appeal letter lifecycle             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Analysis Pipeline (Python)                                     │
│  document_loader → Ollama LLM → rule_engine → risk_report       │
│  → appeal_letter_builder                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     Ollama (local LLM)              File storage
     qwen2.5:3b                      cases.json + uploads/
```

**Design principle:** The LLM handles narrow extraction/classification tasks. All billing-error detection runs as pure Python logic in the rule engine so results are testable, explainable, and non-hallucinated.

See [`insurance-appeal-agent-architecture.md`](./insurance-appeal-agent-architecture.md) for the full long-term plan (PostgreSQL, RAG, LangGraph agent loop).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui, React Query |
| Backend | FastAPI, Uvicorn, Pydantic v2 |
| LLM | [Ollama](https://ollama.com) (`qwen2.5:3b`) via OpenAI-compatible API |
| Document parsing | pdfplumber, PyMuPDF, Pillow |
| Storage | Local JSON file + filesystem uploads (dev/demo) |
| Testing | pytest |

---

## Prerequisites

- **Python 3.11+**
- **Node.js 20+** and npm
- **Ollama** with the `qwen2.5:3b` model

### Install Ollama and pull the model

```bash
# macOS
brew install ollama

# Start the Ollama server (keep this running)
ollama serve

# In another terminal, pull the model
ollama pull qwen2.5:3b
```

Verify Ollama is running:

```bash
curl http://localhost:11434/v1/models
```

---

## Getting Started

### 1. Clone and set up Python

```bash
git clone <your-repo-url>
cd medical_insu

python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install pipeline + schemas package
pip install -e ".[dev]"

# Install backend API dependencies
pip install -r backend/requirements.txt
```

### 2. Start the backend

```bash
cd backend
uvicorn api.main:app --reload --port 8000
```

- API: http://localhost:8000  
- Interactive docs: http://localhost:8000/docs

### 3. Start the frontend

In a new terminal:

```bash
cd frontend
npm install

# Optional — defaults to http://localhost:8000 if unset
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
```

- App: http://localhost:3000

### 4. Try it

1. Open http://localhost:3000 and click **Analyze a Document**
2. Upload a sample file from `data/samples/`
3. Click **Start Analysis** and wait for processing to finish
4. Review the risk report and appeal letter on the case detail page

---

## CLI Usage

You can also run the analysis pipeline directly from the command line (no web UI):

```bash
# Activate venv first
source .venv/bin/activate

# Emergency service denied as "not medically necessary"
python main.py data/samples/denial_medical_necessity_emergency.txt

# Diagnosis code mismatch
python main.py data/samples/denial_code_mismatch.txt

# Out-of-network provider at in-network facility
python main.py data/samples/denial_out_of_network.txt
```

---

## Project Structure

```
medical_insu/
├── frontend/                    # Next.js web app
│   ├── app/                     # Pages (home, upload, cases)
│   ├── components/              # UI, upload, report, appeal letter
│   ├── hooks/                   # React Query hooks
│   └── lib/                     # API client and types
├── backend/
│   ├── api/main.py              # FastAPI application
│   ├── storage/cases.json       # Case metadata (gitignored in prod)
│   └── uploads/                 # Uploaded documents
├── pipeline/
│   ├── document_loader.py       # TXT / PDF / image text extraction
│   ├── llm_client.py            # Ollama wrapper with structured JSON output
│   ├── rule_engine.py           # Deterministic billing error checks
│   └── appeal_letter_builder.py # Appeal letter draft generation
├── schemas/                     # Pydantic models (extracted fields, risk report, letters)
├── data/samples/                # Synthetic test documents
├── tests/                       # Unit tests (rule engine)
├── main.py                      # CLI pipeline entry point
└── insurance-appeal-agent-architecture.md
```

---

## API Overview

Full endpoint documentation is available at http://localhost:8000/docs when the backend is running.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/api/upload` | Upload a document, create a case |
| `POST` | `/api/process/{case_id}` | Run the analysis pipeline |
| `GET` | `/api/cases` | List all cases |
| `GET` | `/api/cases/{case_id}` | Get case details + risk report |
| `GET` | `/api/cases/{case_id}/status` | Poll processing status |
| `GET` | `/api/cases/{case_id}/appeal-letter` | Get appeal letter versions |
| `POST` | `/api/cases/{case_id}/appeal-letter/approve` | Approve a letter version |
| `POST` | `/api/cases/{case_id}/appeal-letter/send` | Mark letter as sent |
| `POST` | `/api/cases/{case_id}/insurer-response` | Upload insurer reply, generate Round 2 draft |
| `POST` | `/api/cases/{case_id}/resolve` | Mark case resolved |
| `DELETE` | `/api/cases/{case_id}` | Delete a case |

Example with curl:

```bash
# Upload
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@data/samples/denial_medical_necessity_emergency.txt"

# Process (use case_id from upload response)
curl -X POST "http://localhost:8000/api/process/<case_id>"

# Get results
curl "http://localhost:8000/api/cases/<case_id>"
```

---

## Rule Engine Checks

All checks are deterministic Python — no LLM involved:

| Check | What it detects |
|---|---|
| Duplicate charges | Same CPT code billed multiple times on the same date |
| Unbundling violations | Separately billed services that should be bundled (NCCI rules) |
| Balance billing (NSA) | No Surprises Act violations for emergency / OON-at-in-network-facility |
| Medical necessity weakness | CO-50 denials on emergency services (high overturn rate) |
| Out-of-network miscoding | Potential incorrect network status processing |

---

## Testing

```bash
source .venv/bin/activate
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ --cov=pipeline --cov-report=term-missing
```

---

## Deployment (Fly.io)

This repo includes Fly.io configs for a **two-app deployment**:

| App | Config | What it runs |
|---|---|---|
| `medical-insu-api` | `fly.backend.toml` | FastAPI + Ollama + persistent volume |
| `medical-insu-web` | `fly.frontend.toml` | Next.js standalone server |

**Quick start** (from repo root):

```bash
fly auth login
fly apps create medical-insu-api
fly volumes create medical_insu_data --region iad --size 3 -a medical-insu-api
fly deploy -c fly.backend.toml

# Update NEXT_PUBLIC_API_URL in fly.frontend.toml, then:
fly apps create medical-insu-web
fly deploy -c fly.frontend.toml

fly secrets set ALLOWED_ORIGINS="https://medical-insu-web.fly.dev,http://localhost:3000" -a medical-insu-api
```

Full step-by-step guide: **[DEPLOY_FLY.md](./DEPLOY_FLY.md)**

### Environment variables

| Variable | Service | Description |
|---|---|---|
| `ALLOWED_ORIGINS` | Backend | Comma-separated CORS origins |
| `NEXT_PUBLIC_API_URL` | Frontend (build) | Backend URL, e.g. `https://medical-insu-api.fly.dev` |
| `OLLAMA_MODEL` | Backend | Default: `qwen2.5:3b` |

The backend uses a **4 GB Fly machine** and a **3 GB volume** for case data, uploads, and cached Ollama models.

> **Note:** File-based JSON storage is fine for demos. For production, migrate to PostgreSQL + object storage (see roadmap).

---

## Roadmap

| Phase | Status | Scope |
|---|---|---|
| **Phase 1** — Static analysis pipeline | ✅ Done | Upload, extraction, rule engine, risk report |
| **Phase 2** — Letter drafting + documents | ✅ Mostly done | Appeal letters, PDF/image upload, editable UI |
| **Phase 3** — Persistence | 🔲 Planned | PostgreSQL, case timeline, search |
| **Phase 4** — Follow-up loop | 🔲 Planned | LangGraph state machine, durable job queue, Round N automation |
| **Phase 5+** — RAG + auth | 🔲 Planned | Policy knowledge base, user accounts, HIPAA-ready infra |

---

## Design Decisions

**Why Ollama instead of a cloud LLM?**
Zero inference cost during development, no PHI sent to external APIs, and demonstrates working with resource-constrained local models. Trade-off: less reliable than Claude/GPT, which is why LLM calls are kept narrow (classify + extract only).

**Why separate the rule engine from the LLM?**
Billing rules are factual and checkable. Pure Python functions are unit-testable, explainable ("this line of code flagged it"), and cannot hallucinate legal violations.

**Why deterministic appeal letters instead of LLM-generated?**
Letter content is auditable against the same findings shown in the UI. Legal citations in the letter come directly from the rule engine output, not a second model pass that could drift.

---

## Disclaimer

This project uses **synthetic sample data** for demonstration. It is **not HIPAA-compliant** as shipped (no auth, no encryption guarantees, no BAA). Do not upload real patient health information unless you have implemented proper security controls and legal agreements.

---

## License

MIT — portfolio project, not for production medical use without proper compliance review.
