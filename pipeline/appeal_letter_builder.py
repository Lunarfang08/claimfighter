"""Build a formal, ready-to-print appeal letter from findings.

This is intentionally deterministic (no additional LLM calls) so that:
- the output is auditable against the `risk_report` findings
- legal citations used in the letter come from the same place as the UI
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from schemas import ErrorType, ExtractedFields, RiskReport

from schemas.appeal_letter import AppealLetterDraft


def _format_money(value: Any) -> str:
    if value is None:
        return "0.00"
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_supporting_checklist(fields: ExtractedFields, report: RiskReport) -> list[str]:
    base = [
        "Copy of the insurer denial letter (including denial reason/code).",
        "Explanation of Benefits (EOB) and/or claim statement for the denied service.",
        "Itemized bill from the provider showing CPT/HCPCS and dates of service.",
        "Proof of payment and/or amount already paid (if any).",
        "A clear copy of this appeal letter (signed) and any attachments.",
        "Patient identification information (member ID / patient ID).",
    ]

    # Add targeted items based on detected finding types.
    by_type: list[str] = []
    error_types = {f.error_type for f in report.findings}

    if ErrorType.MEDICAL_NECESSITY_DISPUTE in error_types:
        by_type.extend(
            [
                "Clinical notes supporting medical necessity (e.g., admitting notes, triage notes, physician assessment).",
                "Orders/referral documentation for the denied service.",
                "Any documentation of symptoms and why the test/procedure was medically required at the time.",
            ]
        )

    if ErrorType.NO_SURPRISES_ACT_VIOLATION in error_types:
        by_type.extend(
            [
                "Documentation that the services were emergency services (presenting symptoms / ER triage records).",
                "Or documentation identifying the facility setting and that in-network rate rules apply (where applicable).",
                "A copy of the relevant plan benefit language regarding cost-sharing and network status.",
            ]
        )

    if ErrorType.DUPLICATE_CHARGE in error_types:
        by_type.extend(
            [
                "Itemized line-item breakdown showing duplicate/overlapping charges (or receipts showing amounts).",
            ]
        )

    if ErrorType.UNBUNDLING_VIOLATION in error_types:
        by_type.extend(
            [
                "Documentation showing the correct comprehensive code(s) / bundle explanation (as reflected in standard coding practice).",
            ]
        )

    if ErrorType.OUT_OF_NETWORK_MISCODING in error_types:
        by_type.extend(
            [
                "Evidence of provider network status for the date of service (insurer directory printout or correspondence).",
            ]
        )

    return base + by_type


def build_policy_references(report: RiskReport) -> list[str]:
    # Keep these high-signal and non-hallucinatory: base them on the finding types + citations when present.
    refs: list[str] = []
    for f in report.findings:
        if f.legal_citation:
            continue

        # Fallback policy text when we don't have a specific citation from the findings.
        if f.error_type == ErrorType.NO_SURPRISES_ACT_VIOLATION:
            refs.append("No Surprises Act: limits on balance billing for eligible services and required coverage rules.")
        elif f.error_type == ErrorType.MEDICAL_NECESSITY_DISPUTE:
            refs.append("Emergency/medical necessity standards: appeal based on presenting symptoms and clinical documentation.")
        elif f.error_type == ErrorType.DUPLICATE_CHARGE:
            refs.append("Claims processing rules: duplicate claim recovery/dispute procedure.")
        elif f.error_type == ErrorType.UNBUNDLING_VIOLATION:
            refs.append("Correct coding/bundling standards: NCCI-style edit logic and comprehensive code selection.")
        elif f.error_type == ErrorType.OUT_OF_NETWORK_MISCODING:
            refs.append("Network status/coding accuracy: use insurer directory and network adequacy rules.")
        else:
            refs.append("Applicable insurer contract and state/federal appeal rights.")

    return _unique_preserve_order(refs)


def build_legal_citations(report: RiskReport) -> list[str]:
    citations = [f.legal_citation for f in report.findings if f.legal_citation]
    return _unique_preserve_order(citations)


def build_appeal_letter_text(fields: ExtractedFields, report: RiskReport) -> str:
    patient_name = fields.patient_name or "Patient"
    patient_id = fields.patient_id or "N/A"
    insurer_name = fields.insurer_name or "Insurance Company"
    provider_name = fields.provider_name or "Provider"
    service_date = str(fields.service_date) if fields.service_date else "N/A"

    denial_code = fields.denial_reason_code or "N/A"
    denial_reason_text = fields.denial_reason_text or "N/A"

    disputed_amount = _format_money(report.total_disputed_amount)
    billed_amount = _format_money(report.total_billed_amount)

    finding_lines: list[str] = []
    for i, f in enumerate(report.findings, start=1):
        parts = [f"{i}. {f.description}"]
        if f.legal_citation:
            parts.append(f"   Legal basis: {f.legal_citation}")
        if f.recommendation:
            parts.append(f"   Requested remedy: {f.recommendation}")
        finding_lines.append("\n".join(parts))
    findings_block = "\n\n".join(finding_lines) if finding_lines else "No specific issues were identified by the initial review."

    checklist_preview = "\n".join(f"   - {item}" for item in build_supporting_checklist(fields, report)[:12])
    checklist_tail = (
        f"\n   ...and additional documents listed in the attached checklist. "
        if len(build_supporting_checklist(fields, report)) > 12
        else ""
    )

    return f"""[Date]

To: Appeals Department
{insurer_name}

Re: Appeal of denial / request for reconsideration
Patient: {patient_name}
Member ID / Patient ID: {patient_id}
Provider: {provider_name}
Date of Service: {service_date}
Denial reason code (if provided): {denial_code}
Denial reason (if provided): {denial_reason_text}

Claim summary:
- Total amount billed: ${billed_amount}
- Amount disputed / requested for review: ${disputed_amount}

Dear Appeals Department,

I am writing to appeal the decision regarding the above-referenced claim/service. The initial denial states: “{denial_reason_text}”.
Based on the information available in the EOB/denial/itemized bill and the documented review findings summarized in this packet, I respectfully request that {insurer_name} reverse or modify the decision and provide payment at the appropriate rate, or otherwise correct the claim processing error(s).

Findings supporting this appeal (summary):
{findings_block}

Requested remedy:
I request that {insurer_name} reconsider the claim and correct the identified issue(s), including any related cost-sharing or payment amounts, and provide a written response addressing each point raised in this appeal.

Supporting documents checklist (high-level):
{checklist_preview}{checklist_tail}

I certify that the information provided is accurate to the best of my knowledge.
Please contact me if additional documentation is required to process this appeal.

Sincerely,

______________________________
Signature
{patient_name}
Patient / Member ID: {patient_id}
Phone: ______________________
Email: _______________________
"""


def build_appeal_letter_draft(fields: ExtractedFields, report: RiskReport) -> AppealLetterDraft:
    legal_citations = build_legal_citations(report)
    policy_references = build_policy_references(report)
    checklist = build_supporting_checklist(fields, report)

    # Subject line should be short (email/fax) and stable.
    patient_name = fields.patient_name or "Patient"
    insurer_name = fields.insurer_name or "Insurer"
    suggested_subject_line = f"Appeal Request - {patient_name} - {insurer_name}"

    letter_text = build_appeal_letter_text(fields, report)

    return AppealLetterDraft(
        letter_text=letter_text,
        legal_citations=legal_citations,
        policy_references=policy_references,
        supporting_document_checklist=checklist,
        suggested_subject_line=suggested_subject_line,
    )


def build_round2_appeal_letter_draft(
    fields: ExtractedFields,
    report: RiskReport,
    insurer_response_text: str,
) -> AppealLetterDraft:
    """Draft a Round 2 packet after the insurer responds."""
    legal_citations = build_legal_citations(report)
    policy_references = build_policy_references(report)
    checklist = _unique_preserve_order(
        build_supporting_checklist(fields, report) + ["Copy of the insurer’s written response (and any enclosures)."]
    )

    patient_name = fields.patient_name or "Patient"
    insurer_name = fields.insurer_name or "Insurer"

    response_excerpt = (insurer_response_text or "").strip()
    if len(response_excerpt) > 1200:
        response_excerpt = response_excerpt[:1200].rstrip() + "..."

    base_letter = build_appeal_letter_text(fields, report)
    # Strip the Round 1 closing/signature so we can provide a clean Round 2 signature block.
    split_marker = "\nSincerely,\n"
    base_prefix = base_letter.split(split_marker)[0].rstrip() if split_marker in base_letter else base_letter

    letter_text = f"""{base_prefix}

Round 2: Responding to the insurer’s determination

Insurer response received: [INSERT DATE]
Summary of insurer’s reasoning (excerpted):
“{response_excerpt}”

I respectfully request a further review for the same reasons outlined in my Round 1 appeal packet.
If the insurer’s response relies on additional factual findings not previously provided, please identify
the specific documents used and explain how they address each point in the original findings.

Sincerely,

______________________________
Signature
{patient_name}
Patient / Member ID: {fields.patient_id or 'N/A'}
"""

    suggested_subject_line = f"Round 2 Appeal - {patient_name} - {insurer_name}"

    return AppealLetterDraft(
        letter_text=letter_text,
        legal_citations=legal_citations,
        policy_references=policy_references,
        supporting_document_checklist=checklist,
        suggested_subject_line=suggested_subject_line,
    )


def build_escalation_letter_draft(fields: ExtractedFields, report: RiskReport) -> AppealLetterDraft:
    """Draft a regulator/escalation packet if the insurer fails to respond or denies again."""
    legal_citations = build_legal_citations(report)
    policy_references = build_policy_references(report)
    checklist = _unique_preserve_order(
        build_supporting_checklist(fields, report)
        + [
            "Copy of all appeal letters sent (Round 1 and any Round 2 correspondence).",
            "Proof of mailing/fax/email transmission for each round.",
            "Any insurer deadlines/response dates (envelopes, timestamps, tracking).",
        ]
    )

    patient_name = fields.patient_name or "Patient"
    insurer_name = fields.insurer_name or "Insurer"

    base_letter = build_appeal_letter_text(fields, report)
    # Strip the Round 1 closing/signature so we can provide a clean escalation closing.
    split_marker = "\nSincerely,\n"
    base_prefix = base_letter.split(split_marker)[0].rstrip() if split_marker in base_letter else base_letter

    letter_text = f"""{base_prefix}

Escalation / External Review Request

I am requesting escalation to an external review process and/or the appropriate oversight body because
the insurer has not provided a timely resolution or has not corrected the identified processing error(s).

This escalation packet includes the complete case history and the original findings and supporting
documentation listed in the attached checklist.

I request that the reviewer:
1) Evaluate each finding and the requested remedy in the original appeal packet, and
2) Confirm whether the insurer’s determination complies with applicable federal/state appeal rights and
   coverage requirements.

Sincerely,

______________________________
Signature
{patient_name}
Patient / Member ID: {fields.patient_id or 'N/A'}
"""

    suggested_subject_line = f"Escalation Request - {patient_name} - {insurer_name}"

    return AppealLetterDraft(
        letter_text=letter_text,
        legal_citations=legal_citations,
        policy_references=policy_references,
        supporting_document_checklist=checklist,
        suggested_subject_line=suggested_subject_line,
    )


def create_letter_version(
    *,
    case_id: str,
    round: int,
    status: str,
    draft: AppealLetterDraft,
    metadata: dict | None = None,
) -> dict:
    """Create a JSON-serializable letter version record for storage."""
    version_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    return {
        "version_id": version_id,
        "case_id": case_id,
        "round": round,
        "status": status,
        "letter_text": draft.letter_text,
        "legal_citations": draft.legal_citations,
        "policy_references": draft.policy_references,
        "supporting_document_checklist": draft.supporting_document_checklist,
        "created_at": now,
        "approved_at": None,
        "sent_at": None,
        "escalated_at": None,
        "metadata": metadata or {},
    }

