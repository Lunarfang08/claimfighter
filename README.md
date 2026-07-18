# Medical Claim Fighter

**AI-powered medical insurance claim appeal assistant — Phases 1-4 Complete**

A full-stack application that analyzes medical billing documents, detects errors, generates appeal letters, and manages the complete follow-up lifecycle through an agentic state machine.

## 🎯 Features Complete

### ✅ Phase 1 — Document Analysis & Risk Report
- **Multi-format upload**: PDF, TXT, PNG/JPG with OCR support (Tesseract)
- **AI field extraction**: Ollama/OpenAI-compatible LLM extracts structured data (patient, insurer, codes, amounts, denial reasons)
- **Rule engine**: 5 deterministic checks for common billing errors (duplicate charges, unbundling, No Surprises Act violations, medical necessity weaknesses)
- **Risk report**: Prioritized findings with legal citations, estimated impact, and actionable recommendations
- **Real-time status tracking**: Processing pipeline with live updates

### ✅ Phase 2 — AI Appeal Letters & PDF Export
- **AI-enhanced letters**: LLM generates persuasive opening/closing paragraphs while keeping structure auditable
- **Deterministic citations**: Legal references and policy citations derived from rule engine (no hallucination)
- **PDF generation**: Professional, printable PDFs with reportlab
- **Editable interface**: Draft → Approve → Send workflow with version control
- **Supporting docs checklist**: Dynamic checklist based on finding types

### ✅ Phase 3 — PostgreSQL Persistence & Search
- **Database layer**: SQLAlchemy async ORM with PostgreSQL + SQLite fallback for local dev
- **Full-text search**: Search cases by filename, patient name, insurer, denial text
- **Advanced filtering**: Filter by status, insurer, date range
- **Case timeline**: Unified audit log showing all events (processing, approval, sending, responses, escalation)
- **Pagination & sorting**: Handle thousands of cases efficiently

### ✅ Phase 4 — LangGraph Follow-up State Machine
- **Agentic follow-up loop**: Durable state machine tracks Round 1 → Round 2 → Escalation
- **Deadline tracking**: Auto-generates escalation packet when insurer response deadline passes
- **Insurer response handling**: Upload response → auto-generate Round 2 draft
- **Manual controls**: Manual escalation and case resolution with outcome tracking
- **Persistent state**: Graph state stored in DB, survives restarts (no in-memory timers)

---

## 🏗️ Architecture

### Backend (Python + FastAPI)
```
backend/
├── api/
│   └── main.py              # FastAPI app — 19 endpoints (Phases 1-4)
├── database/
│   ├── models.py            # SQLAlchemy ORM models (10 tables)
│   ├── engine.py            # Async DB engine + session factory
│   └── crud.py              # All database operations
├── config.py                # Environment configuration
└── requirements.txt         # Python dependencies

pipeline/
├── document_loader.py       # PDF/image OCR extraction
├── llm_client.py            # Ollama/OpenAI LLM wrapper
├── rule_engine.py           # 5 deterministic billing checks
├── appeal_letter_builder.py # Deterministic letter generation
├── llm_appeal_enhancer.py   # AI prose enhancement (Phase 2)
├── pdf_export.py            # PDF generation with reportlab
└── follow_up_agent.py       # LangGraph state machine (Phase 4)

schemas/
├── extracted_fields.py      # ExtractedFields model
├── risk_report.py           # RiskReport + ErrorFinding models
└── appeal_letter.py         # AppealLetterDraft + Version models
```

### Frontend (Next.js 16 + React 19 + TypeScript)
```
frontend/
├── app/
│   ├── page.tsx                  # Landing page
│   ├── upload/page.tsx           # File upload + processing trigger
│   ├── cases/page.tsx            # Case dashboard with search (Phase 3)
│   └── cases/[id]/page.tsx       # Case detail with 5 tabs
├── components/
│   ├── upload/                   # FileUploader + ProcessingStatus
│   ├── report/                   # RiskReportView + ExtractedFieldsView + FindingCard
│   ├── appeal/                   # AppealLetterEditor (Phase 2)
│   ├── timeline/                 # CaseTimeline (Phase 3)
│   ├── followup/                 # FollowUpStatus (Phase 4)
│   └── ui/                       # shadcn/ui components
├── hooks/
│   ├── useCases.ts               # React Query hooks for CRUD + search
│   └── useAppealLetter.ts        # Letter workflow hooks
└── lib/
    ├── api.ts                    # Axios API client
    ├── types.ts                  # TypeScript types matching backend
    └── utils.ts                  # Utilities
```

### Database Schema (Phase 3)
```
cases                       # Core case record
├── processing_steps        # Ordered pipeline log
├── extracted_fields        # LLM-extracted data (1:1)
├── risk_reports            # Risk analysis (1:1)
│   └── findings            # Individual errors (1:many)
├── appeal_letter_versions  # Versioned letters (1:many)
├── follow_up_states        # LangGraph state (1:1)
└── case_timeline_events    # Unified audit log (1:many)
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (with pip)
- **Node.js 20+** (with npm)
- **Ollama** (for local LLM) — [install guide](https://ollama.ai)
- *Optional:* **Tesseract OCR** (for image/scanned PDF support) — `brew install tesseract` (macOS)
- *Optional:* **PostgreSQL 15+** (for production; SQLite used by default for local dev)

### 1. Clone & Setup Backend

```bash
cd medical_insu

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env file and configure
cp .env.example .env
# Edit .env — set OLLAMA_BASE_URL, model, etc.

# Pull Ollama model (if using Ollama)
ollama pull qwen2.5:3b
```

### 2. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy env file
cp .env.example .env.local
# Edit .env.local — set NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run the Application

**Terminal 1 — Backend:**
```bash
cd medical_insu
source venv/bin/activate
python backend/api/main.py
# Backend runs on http://localhost:8000
```

**Terminal 2 — Frontend:**
```bash
cd medical_insu/frontend
npm run dev
# Frontend runs on http://localhost:3000
```

**Open browser:** http://localhost:3000

---

## 📖 Usage Flow

### 1. Upload Document
- Go to **Upload** page
- Drop or select a medical document (PDF, TXT, image)
- Click **Start Analysis**
- Processing runs in background (~30-60s depending on LLM speed)

### 2. Review Risk Report
- Navigate to **Cases** → select your case
- **Report** tab shows findings, estimated recovery, appeal likelihood
- **Data** tab shows extracted fields (patient, insurer, codes, amounts)

### 3. Approve & Send Letter (Phase 2)
- **Appeal Letter** tab shows AI-enhanced draft
- Edit the letter if needed
- Click **Approve Letter** → creates immutable approved version
- Download PDF for printing
- Click **Mark as Sent** → set response deadline (default 30 days)

### 4. Follow-up Loop (Phase 4)
- Case status → `sent` and deadline tracking begins
- **Timeline** tab shows all events
- **Follow-Up Loop** card shows deadline countdown
- When insurer responds:
  - Upload response file → auto-generates Round 2 draft
- If deadline passes with no response:
  - System auto-generates escalation packet
  - Or click **Escalate Case** manually

### 5. Resolution
- Click **Resolve Case** button
- Select outcome: **Won** / **Partial** / **Lost**
- Add notes (amount recovered, final outcome)
- Case marked as `resolved`

---

## 🔧 Configuration

### Environment Variables

**Backend** (`.env`):
```bash
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:3b

# Database (optional — defaults to SQLite)
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/medical_claim_fighter

# CORS
ALLOWED_ORIGINS=http://localhost:3000

# Storage
STORAGE_DIR=backend/storage
UPLOADS_DIR=backend/uploads
```

**Frontend** (`.env.local`):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Using a Different LLM

**Ollama** (default):
```bash
ollama pull qwen2.5:3b  # or mistral, llama3, etc.
```

**Groq** (cloud, faster):
```bash
OLLAMA_BASE_URL=https://api.groq.com/openai/v1
OLLAMA_MODEL=llama-3.3-70b-versatile
OPENAI_API_KEY=gsk_...  # Your Groq API key
```

**OpenAI**:
```bash
OLLAMA_BASE_URL=https://api.openai.com/v1
OLLAMA_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

### PostgreSQL Setup (Production)

```bash
# Create database
createdb medical_claim_fighter

# Set DATABASE_URL
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/medical_claim_fighter

# Tables auto-create on first run
python backend/api/main.py
```

---

## 🧪 Testing

### Backend Tests
```bash
source venv/bin/activate

# Test database models
python -c "
from backend.database.models import Base, Case
print('✓ Models imported')
"

# Test full CRUD cycle
python -c "
import asyncio
from backend.database.crud import create_case, get_case
# ... (see internal test script)
"

# Test state machine
python -c "
from pipeline.follow_up_agent import FollowUpAgent
agent = FollowUpAgent('test-case')
state = agent.initial_state()
print('✓ Agent works')
"
```

### Frontend Tests
```bash
cd frontend

# TypeScript check
npx tsc --noEmit

# Build check
npm run build
```

---

## 📊 API Endpoints

### Phase 1 — Core
- `POST /api/upload` — Upload document
- `POST /api/process/{case_id}` — Trigger pipeline
- `GET /api/cases` — List cases (with filters, search, pagination)
- `GET /api/cases/{case_id}` — Get full case
- `GET /api/cases/{case_id}/status` — Lightweight status poll
- `DELETE /api/cases/{case_id}` — Delete case

### Phase 2 — Appeal Letters
- `GET /api/cases/{case_id}/appeal-letter` — Get letter + versions
- `POST /api/cases/{case_id}/appeal-letter/approve` — Approve draft
- `POST /api/cases/{case_id}/appeal-letter/send` — Mark as sent
- `GET /api/cases/{case_id}/appeal-letter/{version_id}/pdf` — Download PDF

### Phase 3 — Timeline
- `GET /api/cases/{case_id}/timeline` — Get all events

### Phase 4 — Follow-up
- `POST /api/cases/{case_id}/insurer-response` — Upload response → Round 2
- `POST /api/cases/{case_id}/escalate` — Manual escalation
- `POST /api/cases/{case_id}/resolve` — Mark resolved

---

## 🔐 Security Notes

- **No authentication** in current version — add JWT/OAuth before exposing publicly
- **CORS** configured via `ALLOWED_ORIGINS` env var
- **File uploads** validated by extension (no executable files)
- **SQL injection** prevented via SQLAlchemy parameterized queries
- **Secrets** — never commit `.env` files; use `.env.example` as template

---

## 🚢 Deployment

### Backend (Fly.io / Railway / Render)
```bash
# Set environment variables in platform dashboard
# Ensure PostgreSQL add-on is provisioned
# Push code — auto-deploys with Dockerfile.backend
```

### Frontend (Vercel / Netlify)
```bash
# Connect GitHub repo
# Set NEXT_PUBLIC_API_URL to your backend URL
# Auto-deploys on push
```

### All-in-One (Docker Compose)
```bash
docker-compose up -d
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Postgres: localhost:5432
```

---

## 📚 Project Structure Details

### LLM Integration Strategy
- **Only 2 LLM calls** in the entire pipeline:
  1. `classify_document(text)` → document type
  2. `extract_fields(text, doc_type)` → 16 structured fields
- **Zero LLM calls** in:
  - Rule engine (pure Python logic)
  - Risk report synthesis (deterministic)
  - Appeal letter generation (template-based)
  - Follow-up state machine (FSM logic)
- **Optional AI enhancement** (Phase 2):
  - LLM writes opening/closing prose for letters
  - All citations still come from rule engine (no hallucination)

### State Machine (Phase 4)
```
idle → letter_sent → [response_received → draft_round2] or [deadline_exceeded → draft_escalation] → resolved
```
- State stored as JSON in `follow_up_states.graph_state_json`
- Transitions validated by `_TRANSITIONS` table
- Side effects in `_apply_effects()` update payload fields
- Audit trail in `events` array

### Database Design Choices
- **SQLite** for local dev (zero config, single file)
- **PostgreSQL** for production (concurrent writes, full-text search)
- **Async everywhere** — SQLAlchemy async, FastAPI async, React Query
- **Cascade deletes** — deleting a case removes all related records
- **Denormalized fields** — `case_id` copied to `findings` for fast filtering

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes, test locally
4. Run `npx tsc --noEmit` (frontend) and backend tests
5. Commit with clear messages
6. Push and open a PR

---

## 📄 License

MIT License — see LICENSE file

---

## 🙏 Acknowledgments

- **FastAPI** — blazing-fast Python web framework
- **Next.js** — React framework with App Router
- **Ollama** — local LLM inference
- **LangGraph** — state machine framework
- **shadcn/ui** — beautiful UI components
- **Tailwind CSS** — utility-first styling
- **SQLAlchemy** — Python ORM
- **TanStack Query** — React data fetching
- **reportlab** — PDF generation
- **Tesseract OCR** — image text extraction

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/medical-claim-fighter/issues)
- **Docs**: This README + inline code comments
- **Community**: [Discussions](https://github.com/yourusername/medical-claim-fighter/discussions)

---

**Built with ❤️ to help patients fight unfair medical billing.**
