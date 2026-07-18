"""CRUD helpers for all database operations.

All functions are async and accept an `AsyncSession` parameter.
They return plain dicts (not ORM objects) so the API layer stays decoupled.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import asc, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    AppealLetterVersionRecord,
    Case,
    CaseTimelineEvent,
    ExtractedFieldsRecord,
    FindingRecord,
    FollowUpStateRecord,
    ProcessingStep,
    RiskReportRecord,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Case helpers
# ---------------------------------------------------------------------------


async def create_case(db: AsyncSession, *, case_id: str, filename: str, file_path: str, file_type: str) -> dict:
    """Create a new case and an initial 'upload' processing step."""
    now = _now()
    case = Case(
        case_id=case_id,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        status="uploaded",
        created_at=now,
        updated_at=now,
    )
    db.add(case)

    step = ProcessingStep(
        case_id=case_id,
        step="upload",
        status="completed",
        timestamp=now,
        sequence=0,
    )
    db.add(step)

    event = CaseTimelineEvent(
        case_id=case_id,
        event_type="case_created",
        title="Document uploaded",
        description=f"File '{filename}' uploaded successfully.",
        occurred_at=now,
    )
    db.add(event)

    await db.flush()
    return await get_case(db, case_id=case_id)  # type: ignore[return-value]


async def get_case(db: AsyncSession, *, case_id: str) -> dict | None:
    """Fetch a full case record with all relationships as a dict."""
    stmt = (
        select(Case)
        .where(Case.case_id == case_id)
        .options(
            selectinload(Case.processing_steps),
            selectinload(Case.extracted_fields),
            selectinload(Case.risk_report).selectinload(RiskReportRecord.findings),
            selectinload(Case.appeal_letter_versions),
            selectinload(Case.follow_up),
            selectinload(Case.timeline_events),
        )
    )
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    if not case:
        return None
    return _case_to_dict(case)


async def list_cases(
    db: AsyncSession,
    *,
    status: str | None = None,
    search: str | None = None,
    insurer: str | None = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> tuple[list[dict], int]:
    """List cases with optional filtering, search, and pagination."""
    stmt = (
        select(Case)
        .options(
            selectinload(Case.processing_steps),
            selectinload(Case.extracted_fields),
            selectinload(Case.risk_report).selectinload(RiskReportRecord.findings),
            selectinload(Case.appeal_letter_versions),
            selectinload(Case.follow_up),
        )
    )

    if status:
        stmt = stmt.where(Case.status == status)

    if search:
        # Search across filename, patient name (via extracted_fields join), insurer
        stmt = stmt.outerjoin(Case.extracted_fields)
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Case.filename.ilike(pattern),
                ExtractedFieldsRecord.patient_name.ilike(pattern),
                ExtractedFieldsRecord.insurer_name.ilike(pattern),
                ExtractedFieldsRecord.denial_reason_text.ilike(pattern),
            )
        )
    elif insurer:
        stmt = stmt.outerjoin(Case.extracted_fields).where(
            ExtractedFieldsRecord.insurer_name.ilike(f"%{insurer}%")
        )

    # Count total before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Apply sorting
    sort_col = getattr(Case, sort_by, Case.created_at)
    order = desc(sort_col) if sort_dir == "desc" else asc(sort_col)
    stmt = stmt.order_by(order).limit(limit).offset(offset)

    result = await db.execute(stmt)
    cases = result.scalars().unique().all()
    return [_case_to_dict(c) for c in cases], total


async def update_case_status(
    db: AsyncSession,
    *,
    case_id: str,
    status: str,
    error: str | None = None,
) -> None:
    """Update case status."""
    values: dict[str, Any] = {"status": status, "updated_at": _now()}
    if error is not None:
        values["error"] = error
    await db.execute(update(Case).where(Case.case_id == case_id).values(**values))


async def update_case_fields(db: AsyncSession, *, case_id: str, **kwargs: Any) -> None:
    """Update arbitrary case fields."""
    kwargs["updated_at"] = _now()
    await db.execute(update(Case).where(Case.case_id == case_id).values(**kwargs))


async def delete_case(db: AsyncSession, *, case_id: str) -> bool:
    """Delete a case and all related records (cascade)."""
    result = await db.execute(delete(Case).where(Case.case_id == case_id))
    return result.rowcount > 0


# ---------------------------------------------------------------------------
# Processing steps
# ---------------------------------------------------------------------------


async def add_processing_step(
    db: AsyncSession,
    *,
    case_id: str,
    step: str,
    status: str,
    details: str | None = None,
) -> None:
    """Append a processing step and flush."""
    # Get the next sequence number
    count_stmt = select(func.count()).where(ProcessingStep.case_id == case_id)
    count_result = await db.execute(count_stmt)
    seq = count_result.scalar_one()

    record = ProcessingStep(
        case_id=case_id,
        step=step,
        status=status,
        timestamp=_now(),
        details=details,
        sequence=seq,
    )
    db.add(record)
    await db.flush()


# ---------------------------------------------------------------------------
# Extracted Fields
# ---------------------------------------------------------------------------


async def save_extracted_fields(db: AsyncSession, *, case_id: str, fields_dict: dict) -> None:
    """Insert or replace extracted fields for a case."""
    # Delete existing if any (upsert via delete+insert)
    await db.execute(
        delete(ExtractedFieldsRecord).where(ExtractedFieldsRecord.case_id == case_id)
    )
    record = ExtractedFieldsRecord(
        case_id=case_id,
        document_type=fields_dict.get("document_type", "unknown"),
        patient_name=fields_dict.get("patient_name"),
        patient_id=fields_dict.get("patient_id"),
        insurer_name=fields_dict.get("insurer_name"),
        provider_name=fields_dict.get("provider_name"),
        service_date=str(fields_dict["service_date"]) if fields_dict.get("service_date") else None,
        service_date_end=str(fields_dict["service_date_end"]) if fields_dict.get("service_date_end") else None,
        cpt_codes=fields_dict.get("cpt_codes", []),
        icd_codes=fields_dict.get("icd_codes", []),
        billed_amount=_decimal_to_float(fields_dict.get("billed_amount")),
        allowed_amount=_decimal_to_float(fields_dict.get("allowed_amount")),
        paid_amount=_decimal_to_float(fields_dict.get("paid_amount")),
        patient_responsibility=_decimal_to_float(fields_dict.get("patient_responsibility")),
        denial_reason_code=fields_dict.get("denial_reason_code"),
        denial_reason_text=fields_dict.get("denial_reason_text"),
        in_network=fields_dict.get("in_network"),
        raw_denial_context=fields_dict.get("raw_denial_context"),
    )
    db.add(record)
    await db.flush()


# ---------------------------------------------------------------------------
# Risk Report + Findings
# ---------------------------------------------------------------------------


async def save_risk_report(db: AsyncSession, *, case_id: str, report_dict: dict) -> None:
    """Insert or replace risk report + findings for a case."""
    await db.execute(delete(RiskReportRecord).where(RiskReportRecord.case_id == case_id))

    report = RiskReportRecord(
        case_id=case_id,
        case_summary=report_dict["case_summary"],
        total_disputed_amount=_decimal_to_float(report_dict.get("total_disputed_amount", 0)),
        total_billed_amount=_decimal_to_float(report_dict.get("total_billed_amount", 0)),
        appeal_likelihood=report_dict["appeal_likelihood"],
        next_steps=report_dict.get("next_steps", []),
    )
    db.add(report)
    await db.flush()

    for seq, finding in enumerate(report_dict.get("findings", [])):
        record = FindingRecord(
            risk_report_id=report.id,
            case_id=case_id,
            error_type=finding["error_type"],
            confidence=finding["confidence"],
            description=finding["description"],
            evidence=finding.get("evidence", []),
            legal_citation=finding.get("legal_citation"),
            estimated_impact=_decimal_to_float(finding.get("estimated_impact")),
            recommendation=finding.get("recommendation", ""),
            sequence=seq,
        )
        db.add(record)
    await db.flush()


# ---------------------------------------------------------------------------
# Appeal Letter Versions
# ---------------------------------------------------------------------------


async def save_appeal_letter_version(db: AsyncSession, *, version_dict: dict) -> None:
    """Insert a new letter version record."""
    record = AppealLetterVersionRecord(
        version_id=version_dict["version_id"],
        case_id=version_dict["case_id"],
        round=version_dict.get("round", 1),
        status=version_dict.get("status", "draft"),
        letter_text=version_dict["letter_text"],
        legal_citations=version_dict.get("legal_citations", []),
        policy_references=version_dict.get("policy_references", []),
        supporting_document_checklist=version_dict.get("supporting_document_checklist", []),
        created_at=_parse_dt(version_dict.get("created_at")) or _now(),
        approved_at=_parse_dt(version_dict.get("approved_at")),
        sent_at=_parse_dt(version_dict.get("sent_at")),
        escalated_at=_parse_dt(version_dict.get("escalated_at")),
        metadata_=version_dict.get("metadata", {}),
    )
    db.add(record)
    await db.flush()


async def get_letter_version(db: AsyncSession, *, version_id: str) -> AppealLetterVersionRecord | None:
    result = await db.execute(
        select(AppealLetterVersionRecord).where(AppealLetterVersionRecord.version_id == version_id)
    )
    return result.scalar_one_or_none()


async def update_letter_version_status(
    db: AsyncSession, *, version_id: str, status: str, **extra_fields: Any
) -> None:
    values: dict[str, Any] = {"status": status, **extra_fields}
    await db.execute(
        update(AppealLetterVersionRecord)
        .where(AppealLetterVersionRecord.version_id == version_id)
        .values(**values)
    )


# ---------------------------------------------------------------------------
# Follow-up State
# ---------------------------------------------------------------------------


async def get_or_create_follow_up(db: AsyncSession, *, case_id: str) -> FollowUpStateRecord:
    result = await db.execute(
        select(FollowUpStateRecord).where(FollowUpStateRecord.case_id == case_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        record = FollowUpStateRecord(case_id=case_id)
        db.add(record)
        await db.flush()
    return record


async def update_follow_up(db: AsyncSession, *, case_id: str, **kwargs: Any) -> None:
    record = await get_or_create_follow_up(db, case_id=case_id)
    for key, value in kwargs.items():
        setattr(record, key, value)
    await db.flush()


# ---------------------------------------------------------------------------
# Timeline Events
# ---------------------------------------------------------------------------


async def add_timeline_event(
    db: AsyncSession,
    *,
    case_id: str,
    event_type: str,
    title: str,
    description: str | None = None,
    metadata: dict | None = None,
) -> None:
    event = CaseTimelineEvent(
        case_id=case_id,
        event_type=event_type,
        title=title,
        description=description,
        occurred_at=_now(),
        metadata_=metadata or {},
    )
    db.add(event)
    await db.flush()


async def get_timeline(db: AsyncSession, *, case_id: str) -> list[dict]:
    result = await db.execute(
        select(CaseTimelineEvent)
        .where(CaseTimelineEvent.case_id == case_id)
        .order_by(asc(CaseTimelineEvent.occurred_at))
    )
    return [_timeline_event_to_dict(e) for e in result.scalars().all()]


# ---------------------------------------------------------------------------
# Serializers — ORM → dict
# ---------------------------------------------------------------------------


def _decimal_to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        from dateutil import parser
        return parser.parse(str(value))
    except Exception:
        return None


def _case_to_dict(case: Case) -> dict:
    ef = case.extracted_fields
    rr = case.risk_report
    fu = case.follow_up

    return {
        "case_id": case.case_id,
        "filename": case.filename,
        "file_path": case.file_path,
        "file_type": case.file_type,
        "status": case.status,
        "error": case.error,
        "created_at": _iso(case.created_at),
        "updated_at": _iso(case.updated_at),
        "current_appeal_letter_version_id": case.current_appeal_letter_version_id,
        "resolution": {
            "outcome": case.resolution_outcome,
            "notes": case.resolution_notes,
            "resolved_at": _iso(case.resolved_at),
        } if case.resolution_outcome else None,
        "processing_steps": [
            {
                "step": s.step,
                "status": s.status,
                "timestamp": _iso(s.timestamp),
                "details": s.details,
            }
            for s in (case.processing_steps or [])
        ],
        "extracted_fields": _extracted_fields_to_dict(ef) if ef else None,
        "risk_report": _risk_report_to_dict(rr) if rr else None,
        "appeal_letter_versions": [
            _letter_version_to_dict(v) for v in (case.appeal_letter_versions or [])
        ],
        "follow_up": _follow_up_to_dict(fu) if fu else None,
    }


def _extracted_fields_to_dict(ef: ExtractedFieldsRecord) -> dict:
    return {
        "document_type": ef.document_type,
        "patient_name": ef.patient_name,
        "patient_id": ef.patient_id,
        "insurer_name": ef.insurer_name,
        "provider_name": ef.provider_name,
        "service_date": ef.service_date,
        "service_date_end": ef.service_date_end,
        "cpt_codes": ef.cpt_codes or [],
        "icd_codes": ef.icd_codes or [],
        "billed_amount": str(ef.billed_amount) if ef.billed_amount is not None else None,
        "allowed_amount": str(ef.allowed_amount) if ef.allowed_amount is not None else None,
        "paid_amount": str(ef.paid_amount) if ef.paid_amount is not None else None,
        "patient_responsibility": str(ef.patient_responsibility) if ef.patient_responsibility is not None else None,
        "denial_reason_code": ef.denial_reason_code,
        "denial_reason_text": ef.denial_reason_text,
        "in_network": ef.in_network,
        "raw_denial_context": ef.raw_denial_context,
    }


def _risk_report_to_dict(rr: RiskReportRecord) -> dict:
    return {
        "case_summary": rr.case_summary,
        "total_disputed_amount": str(rr.total_disputed_amount),
        "total_billed_amount": str(rr.total_billed_amount),
        "appeal_likelihood": rr.appeal_likelihood,
        "next_steps": rr.next_steps or [],
        "findings": [
            {
                "error_type": f.error_type,
                "confidence": f.confidence,
                "description": f.description,
                "evidence": f.evidence or [],
                "legal_citation": f.legal_citation,
                "estimated_impact": str(f.estimated_impact) if f.estimated_impact is not None else None,
                "recommendation": f.recommendation,
            }
            for f in (rr.findings or [])
        ],
    }


def _letter_version_to_dict(v: AppealLetterVersionRecord) -> dict:
    return {
        "version_id": v.version_id,
        "case_id": v.case_id,
        "round": v.round,
        "status": v.status,
        "letter_text": v.letter_text,
        "legal_citations": v.legal_citations or [],
        "policy_references": v.policy_references or [],
        "supporting_document_checklist": v.supporting_document_checklist or [],
        "created_at": _iso(v.created_at),
        "approved_at": _iso(v.approved_at),
        "sent_at": _iso(v.sent_at),
        "escalated_at": _iso(v.escalated_at),
        "metadata": v.metadata_ or {},
        "pdf_path": v.pdf_path,
    }


def _follow_up_to_dict(fu: FollowUpStateRecord) -> dict:
    return {
        "round": fu.round,
        "agent_state": fu.agent_state,
        "round_1_sent_at": _iso(fu.round_1_sent_at),
        "round_1_response_deadline": _iso(fu.round_1_response_deadline),
        "round_1_response_received_at": _iso(fu.round_1_response_received_at),
        "round_1_response_excerpt": fu.round_1_response_excerpt,
        "round_2_sent_at": _iso(fu.round_2_sent_at),
        "round_2_response_deadline": _iso(fu.round_2_response_deadline),
        "round_2_response_received_at": _iso(fu.round_2_response_received_at),
        "escalation_ready": fu.escalation_ready,
        "escalation_triggered_at": _iso(fu.escalation_triggered_at),
    }


def _timeline_event_to_dict(e: CaseTimelineEvent) -> dict:
    return {
        "id": e.id,
        "event_type": e.event_type,
        "title": e.title,
        "description": e.description,
        "occurred_at": _iso(e.occurred_at),
        "metadata": e.metadata_ or {},
    }
