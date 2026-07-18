"""SQLAlchemy ORM models for Phase 3 — PostgreSQL persistence.

Tables:
  cases                  — core case record
  processing_steps       — ordered log of pipeline steps
  extracted_fields       — normalized LLM-extracted fields (one-to-one)
  risk_reports           — risk analysis output (one-to-one)
  findings               — individual error findings (one-to-many)
  appeal_letter_versions — versioned letter drafts (one-to-many)
  follow_up_states       — follow-up loop state (one-to-one)
  case_timeline_events   — unified audit log for the UI timeline
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Core Case
# ---------------------------------------------------------------------------


class Case(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    processing_steps: Mapped[list[ProcessingStep]] = relationship(
        "ProcessingStep", back_populates="case", cascade="all, delete-orphan",
        order_by="ProcessingStep.sequence"
    )
    extracted_fields: Mapped[ExtractedFieldsRecord | None] = relationship(
        "ExtractedFieldsRecord", back_populates="case", cascade="all, delete-orphan", uselist=False
    )
    risk_report: Mapped[RiskReportRecord | None] = relationship(
        "RiskReportRecord", back_populates="case", cascade="all, delete-orphan", uselist=False
    )
    appeal_letter_versions: Mapped[list[AppealLetterVersionRecord]] = relationship(
        "AppealLetterVersionRecord", back_populates="case", cascade="all, delete-orphan",
        order_by="AppealLetterVersionRecord.created_at"
    )
    follow_up: Mapped[FollowUpStateRecord | None] = relationship(
        "FollowUpStateRecord", back_populates="case", cascade="all, delete-orphan", uselist=False
    )
    timeline_events: Mapped[list[CaseTimelineEvent]] = relationship(
        "CaseTimelineEvent", back_populates="case", cascade="all, delete-orphan",
        order_by="CaseTimelineEvent.occurred_at"
    )

    # Resolution (Phase 4+)
    resolution_outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # The active letter version
    current_appeal_letter_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ---------------------------------------------------------------------------
# Processing Steps
# ---------------------------------------------------------------------------


class ProcessingStep(Base):
    __tablename__ = "processing_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    case: Mapped[Case] = relationship("Case", back_populates="processing_steps")


# ---------------------------------------------------------------------------
# Extracted Fields
# ---------------------------------------------------------------------------


class ExtractedFieldsRecord(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    patient_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    patient_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    insurer_name: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    provider_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    service_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    service_date_end: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cpt_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    icd_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    billed_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    allowed_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    paid_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    patient_responsibility: Mapped[float | None] = mapped_column(Float, nullable=True)
    denial_reason_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    denial_reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    in_network: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    raw_denial_context: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped[Case] = relationship("Case", back_populates="extracted_fields")


# ---------------------------------------------------------------------------
# Risk Report + Findings
# ---------------------------------------------------------------------------


class RiskReportRecord(Base):
    __tablename__ = "risk_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    case_summary: Mapped[str] = mapped_column(Text, nullable=False)
    total_disputed_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_billed_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    appeal_likelihood: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    next_steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    case: Mapped[Case] = relationship("Case", back_populates="risk_report")
    findings: Mapped[list[FindingRecord]] = relationship(
        "FindingRecord", back_populates="risk_report", cascade="all, delete-orphan",
        order_by="FindingRecord.sequence"
    )


class FindingRecord(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_report_id: Mapped[int] = mapped_column(Integer, ForeignKey("risk_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # denorm for fast queries
    error_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    legal_citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    risk_report: Mapped[RiskReportRecord] = relationship("RiskReportRecord", back_populates="findings")


# ---------------------------------------------------------------------------
# Appeal Letter Versions
# ---------------------------------------------------------------------------


class AppealLetterVersionRecord(Base):
    __tablename__ = "appeal_letter_versions"

    version_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    letter_text: Mapped[str] = mapped_column(Text, nullable=False)
    legal_citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    policy_references: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    supporting_document_checklist: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    # PDF export path (Phase 2 enhancement)
    pdf_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    case: Mapped[Case] = relationship("Case", back_populates="appeal_letter_versions")


# ---------------------------------------------------------------------------
# Follow-up State
# ---------------------------------------------------------------------------


class FollowUpStateRecord(Base):
    __tablename__ = "follow_up_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # LangGraph state machine state (Phase 4)
    agent_state: Mapped[str] = mapped_column(String(64), nullable=False, default="idle")
    graph_state_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Round 1
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    round_1_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    round_1_response_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    round_1_response_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    round_1_response_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    round_1_response_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Round 2
    round_2_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    round_2_response_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    round_2_response_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Escalation
    escalation_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    escalation_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Deadline check job (for scheduler integration)
    deadline_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    case: Mapped[Case] = relationship("Case", back_populates="follow_up")


# ---------------------------------------------------------------------------
# Timeline Events (unified audit log for UI)
# ---------------------------------------------------------------------------


class CaseTimelineEvent(Base):
    __tablename__ = "case_timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    case: Mapped[Case] = relationship("Case", back_populates="timeline_events")
