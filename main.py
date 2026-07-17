#!/usr/bin/env python3
"""Phase 1 Pipeline: Static end-to-end processing.

Usage:
    python main.py data/samples/denial_medical_necessity_emergency.txt
"""

import sys
from pathlib import Path
from decimal import Decimal

from pipeline.llm_client import OllamaClient
from pipeline.rule_engine import run_all_rule_checks
from schemas import RiskReport, ConfidenceLevel


def load_document_text(filepath: str) -> str:
    """Load text from a file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {filepath}")
    return path.read_text()


def synthesize_risk_report(
    extracted_fields,
    rule_findings: list,
) -> RiskReport:
    """Synthesize a RiskReport from extracted fields and rule findings.
    
    In later phases, this will be an LLM call that combines rule findings
    with RAG lookups and web search. For Phase 1, we keep it simple.
    """
    # Calculate totals
    total_disputed = sum(
        f.estimated_impact or Decimal(0)
        for f in rule_findings
    )
    
    # Generate case summary
    doc_type = extracted_fields.document_type.value.replace("_", " ").title()
    patient = extracted_fields.patient_name or "Patient"
    insurer = extracted_fields.insurer_name or "insurance company"
    
    if rule_findings:
        finding_summary = f"{len(rule_findings)} potential issue(s) detected"
    else:
        finding_summary = "No obvious billing errors detected in initial rule-based check"
    
    case_summary = (
        f"{doc_type} from {insurer} for {patient}. "
        f"Total patient responsibility: ${extracted_fields.patient_responsibility or 0}. "
        f"{finding_summary}."
    )
    
    # Determine overall appeal likelihood
    if not rule_findings:
        appeal_likelihood = ConfidenceLevel.LOW
    else:
        # Use highest confidence finding
        highest_confidence = rule_findings[0].confidence
        appeal_likelihood = highest_confidence
    
    # Generate next steps
    next_steps = []
    if rule_findings:
        # Group by recommendation
        recs = list(set(f.recommendation for f in rule_findings))
        next_steps.extend(recs[:3])  # Top 3 unique recommendations
    else:
        next_steps.append(
            "Review itemized bill carefully for any charges that seem incorrect or duplicate"
        )
        next_steps.append(
            "Request complete medical records to verify services were actually provided"
        )
    
    return RiskReport(
        case_summary=case_summary,
        findings=rule_findings,
        total_disputed_amount=total_disputed,
        total_billed_amount=extracted_fields.billed_amount or Decimal(0),
        appeal_likelihood=appeal_likelihood,
        next_steps=next_steps,
    )


def main():
    """Run Phase 1 pipeline on a document."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <path-to-document.txt>")
        print("\nExample:")
        print("  python main.py data/samples/denial_medical_necessity_emergency.txt")
        sys.exit(1)
    
    document_path = sys.argv[1]
    
    print("=" * 70)
    print("MEDICAL CLAIM FIGHTER - PHASE 1 PIPELINE")
    print("=" * 70)
    print(f"\nProcessing: {document_path}\n")
    
    # Step 1: Load document text
    print("Step 1: Loading document...")
    text = load_document_text(document_path)
    print(f"  ✓ Loaded {len(text)} characters\n")
    
    # Step 2: Initialize LLM client
    print("Step 2: Initializing LLM client (Ollama)...")
    llm = OllamaClient(model="qwen2.5:3b")
    print("  ✓ Connected to Ollama at http://localhost:11434/v1\n")
    
    # Step 3: Classify document
    print("Step 3: Classifying document type...")
    doc_type = llm.classify_document(text)
    print(f"  ✓ Document type: {doc_type.value}\n")
    
    # Step 4: Extract structured fields
    print("Step 4: Extracting structured fields...")
    fields = llm.extract_fields(text, doc_type)
    print(f"  ✓ Extracted fields:")
    print(f"     Patient: {fields.patient_name}")
    print(f"     Insurer: {fields.insurer_name}")
    print(f"     Service Date: {fields.service_date}")
    print(f"     CPT Codes: {', '.join(fields.cpt_codes) if fields.cpt_codes else 'None'}")
    print(f"     ICD Codes: {', '.join(fields.icd_codes) if fields.icd_codes else 'None'}")
    print(f"     Billed: ${fields.billed_amount or 0}")
    print(f"     Patient Responsibility: ${fields.patient_responsibility or 0}")
    print(f"     Denial Code: {fields.denial_reason_code or 'N/A'}")
    print(f"     In-Network: {fields.in_network}\n")
    
    # Step 5: Run rule engine checks
    print("Step 5: Running rule engine checks...")
    findings = run_all_rule_checks(fields)
    print(f"  ✓ Found {len(findings)} potential issues\n")
    
    # Step 6: Synthesize risk report
    print("Step 6: Synthesizing risk report...")
    report = synthesize_risk_report(fields, findings)
    print("  ✓ Risk report generated\n")
    
    # Output results
    print("=" * 70)
    print("RISK REPORT")
    print("=" * 70)
    print(report.model_dump_json(indent=2))
    print("\n")
    
    print("=" * 70)
    print("PHASE 1 COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
