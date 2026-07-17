# Medical Bill / Insurance Claim Fighter Agent
## Full Technical Architecture & Build Plan

---

## 1. Product Scope (v1)

**Input:** User uploads an EOB (Explanation of Benefits), denial letter, or itemized hospital bill (PDF/image).
**Output:** A structured risk/error report + a ready-to-send appeal letter, with the agent tracking the case until resolution.

**v1 boundaries (don't over-scope):**
- US healthcare system only (CPT/ICD codes, ERISA/state insurance law)
- One insurer, one claim per case initially
- Human sends the final letter (no auto-mailing yet) — agent drafts, user approves/sends
- Support the 3 most common denial reasons first (medical necessity, billing code mismatch, out-of-network miscoding), expand later

---

## 2. Tech Stack

### Frontend
- **Next.js 14 (App Router) + TypeScript** — file upload UI, case dashboard, appeal letter editor
- **Tailwind + shadcn/ui** — fast, clean UI
- **React Query** — case status polling/updates

### Backend / Orchestration
- **Python (FastAPI)** — API layer; Python has the best ecosystem for document parsing + agent frameworks
- **LangGraph** (preferred over plain LangChain) — for the actual agent loop, since this needs a stateful, multi-step, cyclical workflow (parse → research → draft → wait for response → re-plan), not a linear chain
- Alternative: build the state machine yourself with a simple **Celery + Postgres**-backed task queue if you want less framework lock-in — totally reasonable for a portfolio project and easier to explain in an interview

### LLM Layer
- **Claude (Sonnet-class model)** via Anthropic API — primary reasoning engine (document understanding, drafting, policy interpretation)
- Use **tool use / function calling** for: OCR trigger, policy database lookup, web search, letter generation
- Keep a **separate, cheaper model call** (or a smaller Claude model) for simple sub-tasks like classification (denial reason type) to control cost

### Document Processing
- **AWS Textract** or **Azure Document Intelligence** — OCR + structured field extraction from scanned bills/EOBs (these forms are messy; don't rely on LLM vision alone for structured field extraction)
- **PyMuPDF / pdfplumber** — for text-based PDFs (many EOBs are digital, not scanned)
- **Claude vision** (image/PDF input) — as a fallback/cross-check reasoning layer on top of OCR output, especially for handwritten annotations or ambiguous layouts

### Knowledge Base / RAG
- **Vector DB: Pgvector (inside Postgres) or Qdrant** — store:
  - CPT/ICD code reference data
  - No Surprises Act + ERISA appeal rules
  - State-specific insurance commissioner processes (50-state matrix)
  - Insurer-specific policy documents (when available)
- **Embeddings:** Voyage AI or OpenAI text-embedding-3 for the RAG index
- Precompute a **billing-error pattern library** (rule-based, not LLM) — e.g. duplicate charges, unbundling violations, balance billing under No Surprises Act — this should be deterministic code, not model guesswork, since it's checkable fact-matching

### Database
- **PostgreSQL** — cases, documents, appeal history, users
- **S3 (or equivalent)** — raw uploaded documents

### Agent Memory / State
- Each "case" is a persistent object with:
  - Case status (intake → analyzed → drafted → sent → awaiting response → resolved/escalated)
  - Full history of what was argued, what evidence was cited, what the insurer replied
  - This is stored relationally in Postgres, **not** just stuffed into an LLM context window — retrieve the relevant history per step instead of replaying everything

### Background Jobs / Monitoring
- **Celery + Redis** (or AWS Step Functions if you want managed orchestration) — for:
  - Scheduled follow-up reminders (insurers have response deadlines, e.g. 30/60 days)
  - Re-checking case status
  - Nudging user when a round of action is needed

### Auth / Compliance
- **Clerk or Auth0** for auth
- **HIPAA consideration:** this touches PHI (protected health information). For a portfolio project you can caveat this clearly and use synthetic/anonymized test data. For anything real-world, you'd need a BAA with your cloud provider (AWS/Azure both offer HIPAA-eligible services) and encryption at rest/in transit — worth mentioning in your writeup even if you don't fully implement it, it shows maturity.

### Deployment
- **Vercel** (frontend) + **Railway/Render/Fly.io** (backend) for a fast portfolio deploy, or **AWS ECS/Fargate** if you want to show cloud-native chops

---

## 3. End-to-End Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INTAKE                                                        │
│   User uploads denial letter / EOB / bill (PDF or photo)        │
│   → Textract/PyMuPDF extracts raw text + structured fields       │
│   → Claude classifies document type + extracts:                  │
│       patient info, CPT/ICD codes, dates of service,             │
│       denial reason code, dollar amounts, insurer name           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. ANALYSIS (Agent Planning Step)                                │
│   Agent decides which sub-checks apply, runs them in parallel:   │
│    a) Rule-engine check: duplicate billing, unbundling,          │
│       balance billing violations (deterministic code)            │
│    b) RAG lookup: relevant No Surprises Act / ERISA / state law  │
│    c) RAG lookup: insurer's own published policy (if available)  │
│    d) Web search tool: precedent cases / similar successful      │
│       appeals for this denial code                                │
│   → Agent synthesizes findings into a Risk Report:               │
│       - Likely error type(s) found                                │
│       - Confidence level per finding                              │
│       - Estimated dollar amount recoverable                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. DRAFTING                                                       │
│   Agent generates:                                                │
│    - Formal appeal letter, citing specific policy clause/law     │
│    - Checklist of supporting documents patient should attach     │
│    - Editable in UI before the user sends it                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. USER REVIEW & SEND                                             │
│   User edits/approves → marks as "sent" (or integrates with      │
│   email/fax API to actually send)                                │
│   → Case status = "awaiting response", deadline computed          │
│   and stored (insurer response window, e.g. 30 days)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. FOLLOW-UP LOOP (this is the core "agentic" part)              │
│   Scheduled job checks deadline                                  │
│   → If insurer responds: user uploads response                  │
│      → Agent re-analyzes: did they concede, partially concede,  │
│        or deny again with new reasoning?                         │
│      → If second denial: agent drafts round-2 appeal referencing│
│        what was already argued (retrieved from case memory)      │
│   → If no response by deadline: agent flags this as itself a    │
│     compliance violation (many states require timely response)  │
│     and drafts an escalation                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. ESCALATION (if 2 rounds fail)                                  │
│   Agent generates:                                                │
│    - State insurance commissioner complaint (state-specific       │
│      form/process pulled from knowledge base)                     │
│    - Or: recommendation to consult a patient advocate/attorney   │
│    - Summary packet of the full case history for handoff          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. RESOLUTION                                                     │
│   Case marked resolved (won/partial/lost)                        │
│   → Outcome logged and (optionally) fed back into the rule       │
│     engine / RAG store to improve future case pattern matching   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Agent Architecture Detail (LangGraph state machine)

Think of it as a graph of nodes, not a single prompt:

- **`classify_document`** node → determines doc type & routes accordingly
- **`extract_fields`** node → structured extraction (codes, amounts, dates)
- **`rule_engine_check`** node → deterministic Python checks (NOT LLM — keep this separate and testable)
- **`policy_rag_lookup`** node → retrieves relevant law/policy chunks
- **`precedent_search`** node → web search tool call for similar cases
- **`synthesize_findings`** node → LLM combines all of the above into the Risk Report
- **`draft_letter`** node → LLM generates the appeal letter using findings + templates
- **`await_human_review`** node → pauses graph execution until user approves (LangGraph supports human-in-the-loop interrupts natively — use this)
- **`monitor_deadline`** node → background/scheduled re-entry point
- **`process_response`** node → re-enters analysis when new insurer response is uploaded
- **`escalate`** node → terminal branch generating regulator complaint

This separation matters for your build **and** for explaining it in an interview: it shows you understand that "agentic" doesn't mean "one giant prompt" — it means a controlled state machine where the LLM makes local decisions but the *structure* is deterministic and inspectable.

---

## 5. Why This Architecture Is Genuinely "Agentic" (not a wrapper)

- **Multi-step planning:** the agent decides which checks apply per case (not every denial needs every check)
- **Tool use:** OCR, rule engine, RAG, web search, letter generation are distinct tools the agent orchestrates
- **Persistent state across a long timeline:** appeals unfold over weeks/months — this is not a single-turn interaction
- **Human-in-the-loop by design:** the agent doesn't act autonomously in the world (doesn't send the letter itself in v1) — a well-scoped safety boundary that's also easier to build
- **Self-correction:** round 2 drafting explicitly references what was already argued and why it didn't work

---

## 6. Suggested Build Order (MVP → full system)

1. **Static pipeline first:** upload → OCR → LLM extraction → rule engine → risk report (no agent framework yet, just a linear script). Prove the core value prop works on 10-20 real sample EOBs.
2. **Add drafting:** generate the appeal letter from the risk report.
3. **Add persistence:** move from a script to a real case object in Postgres.
4. **Add the follow-up loop:** this is where you introduce LangGraph/state machine + scheduled jobs.
5. **Add escalation path.**
6. **Polish UI + auth + deploy.**

Building it in this order means you have a demoable product after step 2, and you add the "hard agent" parts once the core value is proven.

---

## 7. Data You'll Need to Bootstrap

- Sample EOBs/denial letters (many are shared anonymized online for patient advocacy purposes, or generate realistic synthetic ones with Claude for testing)
- No Surprises Act text + a handful of state insurance appeal statutes (public, scrapeable)
- A small curated list of common denial reason codes (CO-11, CO-16, CO-50, etc.) and what they mean — this becomes your rule engine's backbone

---

## 8. Portfolio/Demo Framing

When you present this, lead with the workflow diagram above and one concrete example: "Here's a real denial, here's the risk report the agent generated, here's the letter, here's what happens when the insurer responds again." A live walkthrough of the follow-up loop is the most impressive part — it's the piece that proves this isn't just a document summarizer.
