# Medical Claim Fighter - Phase 1

AI-powered medical bill and insurance claim appeal assistant.

## What This Does (Phase 1)

Takes a medical bill, EOB (Explanation of Benefits), or denial letter and:
1. Extracts structured information (patient, codes, amounts, denial reasons)
2. Runs deterministic rule-based checks for billing errors and legal violations
3. Generates a risk report with findings, confidence levels, and recommended actions

**Phase 1 Scope:** Static pipeline only. No database, no web UI, no LangGraph yet.

## Architecture Highlights

- **Local LLM:** Uses Ollama (qwen2.5:3b) via OpenAI-compatible API instead of cloud APIs
- **Deterministic Rule Engine:** Billing error detection is pure Python logic, NOT LLM guesswork
- **Structured Output:** Every LLM call returns validated Pydantic models with retry-on-failure
- **Real Legal Logic:** Implements actual No Surprises Act balance billing rules and NCCI unbundling checks

## Prerequisites

1. **Python 3.11+** (uses modern type hints)
2. **Ollama** with `qwen2.5:3b` model

### Installing Ollama & Model

```bash
# Install Ollama (if not already installed)
# macOS:
brew install ollama

# Start Ollama service
ollama serve

# Pull the model (in another terminal)
ollama pull qwen2.5:3b
```

Verify Ollama is running:
```bash
curl http://localhost:11434/v1/models
```

## Installation

```bash
# Clone/navigate to project directory
cd medical_insu

# Create virtual environment and install dependencies
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Or with uv (faster):
uv pip install -e .
```

## Usage

Run the pipeline on a sample document:

```bash
python main.py data/samples/denial_medical_necessity_emergency.txt
```

Try all three test cases:

```bash
# Case 1: Emergency service denied as "not medically necessary"
python main.py data/samples/denial_medical_necessity_emergency.txt

# Case 2: Diagnosis code mismatch (x-ray for soft tissue injury)
python main.py data/samples/denial_code_mismatch.txt

# Case 3: Out-of-network provider at in-network facility
python main.py data/samples/denial_out_of_network.txt
```

## Project Structure

```
medical_insu/
├── main.py                    # Phase 1 pipeline entry point
├── schemas/
│   ├── extracted_fields.py    # Pydantic model for extracted data
│   └── risk_report.py         # Pydantic model for analysis output
├── pipeline/
│   ├── llm_client.py          # Ollama wrapper with structured output
│   └── rule_engine.py         # Deterministic billing error checks
├── data/samples/              # Synthetic test documents
│   ├── denial_medical_necessity_emergency.txt
│   ├── denial_code_mismatch.txt
│   └── denial_out_of_network.txt
├── tests/                     # Unit tests
│   └── test_rule_engine.py
└── README.md
```

## Rule Engine Checks (Phase 1)

All deterministic, no LLM involved:

1. **Duplicate Charges:** Same CPT code billed multiple times on same date
2. **Unbundling Violations:** Separately billing services that should be bundled (NCCI rules)
3. **Balance Billing Violations:** No Surprises Act checks for emergency services and OON providers at in-network facilities
4. **Medical Necessity Denial Weakness:** CO-50 denials on emergency services (high overturn rate)
5. **Out-of-Network Miscoding:** Flags potential incorrect network status processing

## Testing

Run unit tests:

```bash
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ --cov=pipeline --cov-report=term-missing
```

## What's NOT in Phase 1

- ❌ PDF/image upload (uses plain text files)
- ❌ OCR (pdfplumber/PyMuPDF integration comes later)
- ❌ RAG lookups (policy/law knowledge base)
- ❌ Letter drafting
- ❌ Database persistence
- ❌ LangGraph state machine
- ❌ Web UI
- ❌ Follow-up loop

These come in Phases 2-6 per the architecture doc.

## Sample Output

```json
{
  "case_summary": "Denial Letter from Blue Cross Blue Shield for Jane M. Doe. Total patient responsibility: $2100. 1 potential issue(s) detected.",
  "findings": [
    {
      "error_type": "medical_necessity_dispute",
      "confidence": "high",
      "description": "Medical necessity denial for emergency service. Emergency services must be covered based on 'prudent layperson' standard...",
      "evidence": [
        "Denial code: CO-50 (Non-covered service / Not medically necessary)",
        "Emergency service codes detected",
        "Prudent layperson standard applies"
      ],
      "legal_citation": "EMTALA § 1867(e)(1)(B) & ACA § 2719A: Emergency services covered based on presenting symptoms...",
      "estimated_impact": "2100.00",
      "recommendation": "File appeal immediately. Cite prudent layperson standard..."
    }
  ],
  "total_disputed_amount": "2100.00",
  "total_billed_amount": "3500.00",
  "appeal_likelihood": "high",
  "next_steps": [
    "File appeal immediately. Cite prudent layperson standard. Attach: ER admission notes..."
  ]
}
```

## Design Decisions (for Interviews)

### Why Ollama instead of Claude?
- **Portfolio constraint:** Demonstrates ability to work with resource-constrained local models
- **Cost:** Zero inference cost during development
- **Privacy:** No PHI sent to external APIs (HIPAA consideration)
- **Trade-off:** Less reliable than Claude, hence the heavy defensive parsing and narrow single-purpose LLM calls

### Why NOT give the LLM "tool use" autonomy?
- 8B models are unreliable at tool selection and multi-step planning
- Better to run ALL checks unconditionally in Python and let the LLM only do narrow extraction/classification tasks
- The "agentic" behavior comes from the state machine (LangGraph in Phase 4), not from the LLM deciding which functions to call

### Why separate rule engine from LLM?
- **Testability:** Pure Python functions have deterministic, unit-testable behavior
- **Explainability:** Can cite exact line of code that detected an error
- **Correctness:** Billing rules are factual, checkable logic — don't hallucinate them
- **Performance:** No LLM latency for simple pattern matching

## Next Steps (Phase 2)

1. Add letter drafting (LLM generates appeal letter from risk report)
2. Add PDF text extraction (pdfplumber for digital PDFs)
3. Improve LLM prompts based on real-world testing

## License

MIT (portfolio project — not for production medical use without proper HIPAA compliance)
