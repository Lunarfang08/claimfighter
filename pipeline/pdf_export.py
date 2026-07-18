"""Phase 2 — PDF export for appeal letter packets.

Generates a formatted, printable PDF from a letter version dict.
Uses reportlab for zero-dependency PDF generation (no LaTeX/headless Chrome).

Usage:
    from pipeline.pdf_export import export_letter_to_pdf

    pdf_path = export_letter_to_pdf(
        version_dict=letter_version,
        output_dir=Path("backend/uploads"),
    )
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def export_letter_to_pdf(version_dict: dict, output_dir: Path | str) -> Path:
    """Generate a PDF for an appeal letter version.

    Args:
        version_dict: Letter version as returned by create_letter_version().
        output_dir: Directory to write the PDF file into.

    Returns:
        Path to the generated PDF file.

    Raises:
        ImportError: If reportlab is not installed.
        RuntimeError: If PDF generation fails.
    """
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            HRFlowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
        from reportlab.lib import colors
    except ImportError as exc:
        raise ImportError(
            "reportlab is required for PDF export. Install it with: pip install reportlab"
        ) from exc

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    version_id = version_dict.get("version_id", "unknown")
    pdf_filename = f"{version_id}_appeal_letter.pdf"
    pdf_path = output_dir / pdf_filename

    case_id = version_dict.get("case_id", "")
    round_num = version_dict.get("round", 1)
    status = version_dict.get("status", "draft").upper()
    letter_text = version_dict.get("letter_text", "")
    legal_citations = version_dict.get("legal_citations", [])
    policy_refs = version_dict.get("policy_references", [])
    checklist = version_dict.get("supporting_document_checklist", [])
    created_at = version_dict.get("created_at", "")
    metadata = version_dict.get("metadata", {})
    subject_line = metadata.get("suggested_subject_line", "")

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=LETTER,
        rightMargin=1 * inch,
        leftMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        title=f"Appeal Letter — {subject_line or case_id}",
        author="Medical Claim Fighter",
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=16,
        spaceAfter=6,
        textColor=colors.HexColor("#1e3a5f"),
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=11,
        spaceBefore=16,
        spaceAfter=6,
        textColor=colors.HexColor("#2563eb"),
        borderPad=3,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Italic"],
        fontSize=8,
        textColor=colors.grey,
        spaceAfter=2,
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["BodyText"],
        fontSize=9,
        leftIndent=18,
        spaceAfter=3,
        bulletIndent=6,
    )

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("Medical Insurance Appeal Letter", title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2563eb")))
    story.append(Spacer(1, 6))

    # Meta info
    if subject_line:
        story.append(Paragraph(f"<b>Re:</b> {subject_line}", body_style))
    story.append(Paragraph(f"<b>Case ID:</b> {case_id}", meta_style))
    story.append(Paragraph(f"<b>Round:</b> {round_num}  |  <b>Status:</b> {status}", meta_style))
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            story.append(Paragraph(f"<b>Generated:</b> {dt.strftime('%B %d, %Y')}", meta_style))
        except Exception:
            pass

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 8))

    # ── Letter Body ─────────────────────────────────────────────────────────
    story.append(Paragraph("Appeal Letter", section_style))
    for line in letter_text.split("\n"):
        stripped = line.strip()
        if stripped:
            story.append(Paragraph(_escape_xml(stripped), body_style))
        else:
            story.append(Spacer(1, 6))

    # ── Legal Citations ─────────────────────────────────────────────────────
    if legal_citations:
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Paragraph("Legal Citations", section_style))
        for cite in legal_citations:
            story.append(Paragraph(f"• {_escape_xml(cite)}", bullet_style))

    # ── Policy References ───────────────────────────────────────────────────
    if policy_refs:
        story.append(Paragraph("Policy References", section_style))
        for ref in policy_refs:
            story.append(Paragraph(f"• {_escape_xml(ref)}", bullet_style))

    # ── Supporting Documents Checklist ──────────────────────────────────────
    if checklist:
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Paragraph("Supporting Documents Checklist", section_style))
        story.append(
            Paragraph(
                "Attach the following documents to strengthen your appeal:",
                body_style,
            )
        )
        for item in checklist:
            story.append(Paragraph(f"☐  {_escape_xml(item)}", bullet_style))

    # ── Footer note ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "Generated by Medical Claim Fighter. "
            "This letter is a draft. Review all information carefully before submission.",
            meta_style,
        )
    )

    try:
        doc.build(story)
    except Exception as exc:
        raise RuntimeError(f"PDF generation failed: {exc}") from exc

    logger.info("Generated PDF: %s", pdf_path)
    return pdf_path


def _escape_xml(text: str) -> str:
    """Escape XML special characters for reportlab Paragraph."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
