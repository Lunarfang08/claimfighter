"""Phase 2 — LLM-enhanced appeal letter generation.

This module adds an AI pass on top of the deterministic letter builder.
It uses the LLM to:
  1. Write a more persuasive, personalized opening paragraph.
  2. Strengthen the finding-specific arguments based on document context.
  3. Add a closing paragraph that is assertive and professional.

The deterministic letter from `appeal_letter_builder.py` is used as the
structural template. The LLM enriches specific sections, not the entire letter.
This keeps the output auditable while making it more compelling.

IMPORTANT: The LLM is only used here — all citations/checklists still come
from the deterministic builder. The LLM cannot hallucinate citations.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.llm_client import OllamaClient
    from schemas import ExtractedFields, RiskReport

logger = logging.getLogger(__name__)


_OPENING_SYSTEM_PROMPT = """You are an expert healthcare patient advocate and medical billing attorney.
Your task is to write the opening 2-3 paragraphs of a formal appeal letter to an insurance company.

Requirements:
- Professional, formal legal-adjacent tone
- Cite the specific denial reason and challenge it directly
- Reference any relevant findings (medical necessity, No Surprises Act, billing errors)
- Do NOT invent legal citations — they will be added separately
- Do NOT include any preamble, just start the letter body
- Keep it under 200 words
- Output ONLY the letter body paragraphs, no subject line, no signature block

Respond with plain text only. No markdown, no quotes around the text."""

_CLOSING_SYSTEM_PROMPT = """You are an expert healthcare patient advocate.
Write a strong, professional closing paragraph for an insurance appeal letter.

Requirements:
- Assert the patient's rights under their plan and applicable law
- State a clear requested remedy (reversal of denial / recalculation / re-processing)
- Request a written response within the plan's standard timeframe
- Mention that the patient will pursue external review if necessary
- Professional, firm, non-aggressive tone
- Keep it under 100 words
- Output ONLY the closing paragraph, no signature block"""


def _safe_llm_call(client: "OllamaClient", system: str, user: str) -> str:
    """Call LLM and return plain text response. Returns empty string on any failure."""
    try:
        response = client.client.chat.completions.create(
            model=client.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,  # Slightly creative for prose
            max_tokens=512,
        )
        content = response.choices[0].message.content or ""
        # Strip any accidental markdown
        content = re.sub(r"```[a-z]*\n?", "", content).strip("`").strip()
        return content
    except Exception as exc:
        logger.warning("LLM appeal enhancement failed: %s", exc)
        return ""


def enhance_appeal_letter(
    client: "OllamaClient",
    base_letter: str,
    fields: "ExtractedFields",
    report: "RiskReport",
) -> str:
    """Enhance a base appeal letter with LLM-generated prose.

    The structure of the base letter is preserved. The LLM replaces:
    - The opening paragraph (after the header/address block)
    - The closing paragraph (before the signature block)

    Args:
        client: Initialized OllamaClient instance.
        base_letter: Deterministically generated letter text.
        fields: Extracted fields from the document.
        report: Risk report with findings.

    Returns:
        Enhanced letter text, or the original if LLM fails.
    """
    if not base_letter.strip():
        return base_letter

    # ── Build context for LLM ───────────────────────────────────────────────
    findings_summary = "\n".join(
        f"- {f.error_type.value}: {f.description[:200]}"
        for f in report.findings[:5]
    )
    context_block = f"""Patient: {fields.patient_name or 'Patient'}
Insurer: {fields.insurer_name or 'Insurance Company'}
Provider: {fields.provider_name or 'Provider'}
Service date: {fields.service_date or 'N/A'}
CPT codes: {', '.join(fields.cpt_codes) or 'N/A'}
Denial reason: {fields.denial_reason_code or 'N/A'} — {fields.denial_reason_text or 'N/A'}
Billed amount: ${fields.billed_amount or 0}
Patient responsibility: ${fields.patient_responsibility or 0}
Key findings:
{findings_summary or 'No specific billing errors detected.'}"""

    # ── Generate AI opening ─────────────────────────────────────────────────
    opening_user = f"""Write the opening paragraphs for this appeal letter.

CONTEXT:
{context_block}

The patient is appealing a denial and needs a compelling, fact-based opening that:
1. Identifies the specific denial and claim
2. States the primary ground for appeal (medical necessity / billing error / No Surprises Act)
3. Sets a confident tone"""

    ai_opening = _safe_llm_call(client, _OPENING_SYSTEM_PROMPT, opening_user)

    # ── Generate AI closing ─────────────────────────────────────────────────
    closing_user = f"""Write the closing paragraph for this appeal letter.

CONTEXT:
{context_block}

Total disputed amount: ${report.total_disputed_amount}
Appeal likelihood: {report.appeal_likelihood.value}"""

    ai_closing = _safe_llm_call(client, _CLOSING_SYSTEM_PROMPT, closing_user)

    # ── Splice AI content into the deterministic structure ──────────────────
    if not ai_opening and not ai_closing:
        # LLM unavailable — return original
        return base_letter

    enhanced = base_letter

    if ai_opening:
        # Find the position of "Dear Appeals Department," and inject after it
        marker = "Dear Appeals Department,"
        idx = enhanced.find(marker)
        if idx != -1:
            insert_at = idx + len(marker)
            enhanced = (
                enhanced[:insert_at]
                + "\n\n"
                + ai_opening
                + "\n\n"
                + enhanced[insert_at:].lstrip()
            )

    if ai_closing:
        # Find the position of "Requested remedy:" section and insert after "Sincerely,"
        sincerely_marker = "\nSincerely,"
        idx = enhanced.rfind(sincerely_marker)
        if idx != -1:
            enhanced = (
                enhanced[:idx]
                + "\n\n"
                + ai_closing
                + enhanced[idx:]
            )

    return enhanced
