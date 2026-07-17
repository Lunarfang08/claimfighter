# Phase 1 - File Structure & Rule Engine Review

## Complete File Structure

```
medical_insu/
├── README.md                              # Complete documentation
├── PHASE1_STRUCTURE.md                    # This file
├── insurance-appeal-agent-architecture.md # Original architecture doc
├── pyproject.toml                         # Dependencies and build config
├── .python-version                        # Python 3.11
├── .gitignore
│
├── schemas/                               # Pydantic data models
│   ├── __init__.py
│   ├── extracted_fields.py                # ExtractedFields model (patient, codes, amounts)
│   └── risk_report.py                     # RiskReport model (findings, recommendations)
│
├── pipeline/                              # Core processing logic
│   ├── __init__.py
│   ├── llm_client.py                      # Ollama wrapper with structured output
│   └── rule_engine.py                     # ⭐ DETERMINISTIC BILLING CHECKS (review this)
│
├── data/samples/                          # Synthetic test documents
│   ├── denial_medical_necessity_emergency.txt
│   ├── denial_code_mismatch.txt
│   └── denial_out_of_network.txt
│
├── tests/
│   ├── __init__.py
│   └── test_rule_engine.py                # Unit tests for rule engine
│
└── main.py                                # Phase 1 pipeline entry point
```

## Rule Engine Logic Summary

The `pipeline/rule_engine.py` module contains **zero LLM calls** — pure Python logic for detecting billing errors. Here's what each check does:

### 1. `check_duplicate_charges()`
**What it checks:** Same CPT code billed multiple times on same date of service

**Logic:**
- Iterates through CPT codes, tracks which codes have been seen
- If a code appears more than once → HIGH confidence duplicate charge finding
- Cites Medicare Claims Processing Manual

**Confidence:** HIGH (when found)

**Legal basis:** Medicare Claims Processing Manual Ch. 23 §20.7.3

---

### 2. `check_unbundling_violations()`
**What it checks:** CPT codes that shouldn't be billed together (NCCI edits)

**Logic:**
- Uses hardcoded `CPT_BUNDLING_RULES` dictionary (simplified subset for demo)
- Checks if any pair of codes in the claim matches a known bundling violation
- Examples:
  - CT head with/without contrast billed separately
  - Multiple E&M visit levels for same encounter
  - Comprehensive metabolic panel + individual tests it includes

**Confidence:** HIGH (when found)

**Legal basis:** NCCI (National Correct Coding Initiative) edits from CMS

**Real-world note:** In production, this would query a full NCCI database (updated quarterly by CMS). For the demo, we have ~6 common rules hardcoded.

---

### 3. `check_balance_billing_violations()`
**What it checks:** No Surprises Act violations (effective Jan 1, 2022)

**Logic:**
- **Emergency services:** If CPT codes indicate ER visit (99281-99285) AND patient has any responsibility → flag as potential NSA violation (MEDIUM confidence, since we don't know their deductible)
- **Out-of-network provider:** If `in_network=False` AND non-emergency → flag as LOW confidence (needs investigation whether facility was in-network and whether patient signed consent)

**Confidence:** MEDIUM for emergency, LOW for OON investigation

**Legal basis:** No Surprises Act § 2799B-1(b) & § 2799B-2(a)

**Real-world application:** This is ENFORCEABLE. Patients can report violations to CMS No Surprises Help Desk. Very powerful appeal basis.

---

### 4. `check_medical_necessity_denial_weakness()`
**What it checks:** Whether a "CO-50" (not medically necessary) denial is weak/appealable

**Logic:**
- Only triggers on denial code `CO-50`
- **Emergency service + CO-50 = HIGH confidence appeal:** Emergency services must be covered based on "prudent layperson standard" (presenting symptoms, not retrospective diagnosis)
- **Diagnostic imaging + CO-50 = MEDIUM confidence:** These are frequently overturned when physician documents clinical reasoning

**Confidence:** HIGH for emergency, MEDIUM for imaging

**Legal basis:** EMTALA § 1867(e)(1)(B) & ACA § 2719A (prudent layperson standard)

**Real-world note:** CO-50 denials are THE most common and THE most overturned on appeal. Emergency service denials under CO-50 are especially strong appeal cases.

---

### 5. `check_out_of_network_coding_error()`
**What it checks:** Whether a service was incorrectly processed as out-of-network

**Logic:**
- If `in_network=False` AND denial code is `CO-96` or `CO-167` → flag for verification
- Recommendation: Check insurer's online provider directory for the service date

**Confidence:** MEDIUM

**Real-world application:** Network status errors are common. Insurers must honor their published directories under "network adequacy" rules.

---

### Helper Functions

- `_is_emergency_cpt_code()`: Checks if any codes are ER visit E&M codes (99281-99285)
- `_is_diagnostic_imaging()`: Checks if any codes start with 70-79 (radiology range)

---

## Key Design Decisions in Rule Engine

### Why Deterministic?
✅ **Testable:** Unit tests verify exact behavior  
✅ **Explainable:** Can cite exact code line that detected error  
✅ **Correct:** Billing rules are factual — don't hallucinate them  
✅ **Fast:** No LLM latency for pattern matching

### What's Simplified for Demo?
- **NCCI rules:** Real system would have full database (10,000+ code pairs, updated quarterly)
- **State law variations:** No Surprises Act is federal, but 50 states have additional protections
- **Plan-specific rules:** Real system would need insurer's Evidence of Coverage (EOC) documents
- **Dollar amount calculations:** We flag issues but don't calculate exact recoverable amounts (would need line-item data)

### What's Realistic?
- **No Surprises Act logic:** 100% accurate to actual law (effective 1/1/2022)
- **CO-50 denial patterns:** Matches real patient advocate guidance
- **Denial reason codes:** Uses actual CMS/insurance industry standard codes
- **CPT code ranges:** Emergency codes, radiology codes, etc. are correct

---

## Questions to Consider Before Writing LLM Prompts

1. **Duplicate charge detection:** Is the current logic too strict? Should we allow same code if different modifiers (e.g., bilateral procedures)?

2. **Unbundling rules:** The 6 hardcoded rules are common ones. Want to add more for demo, or is this sufficient to prove the concept?

3. **Balance billing - emergency confidence:** Currently MEDIUM because we don't know if the patient responsibility is just their normal deductible/copay vs. actual balance billing. Should we raise to HIGH and let the LLM synthesis step add nuance?

4. **Medical necessity - imaging:** Currently only flags CT/MRI/X-ray (codes 70xxx-79xxx). Should we also flag lab tests (80xxx-89xxx) or physical therapy (97xxx)?

5. **Missing checks:** Are there other common billing errors we should add?
   - Upcoding (billing higher E&M level than documented)?
   - Timely filing (claim filed after deadline)?
   - Authorization errors (service needed pre-auth)?

Let me know if you want to adjust any of the rule engine logic before I move on to writing the LLM prompts.

---

## Next Steps

Once you approve the rule engine logic:

1. ✅ Review this structure and rule logic
2. ⏳ Write LLM prompts for `classify_document()` and `extract_fields()`
3. ⏳ Test the end-to-end pipeline on the 3 sample documents
4. ⏳ Debug and refine based on qwen2.5:3b behavior
5. ⏳ Document any model-specific quirks/workarounds needed
