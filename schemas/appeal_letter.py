"""Schemas for appeal letter drafting and versioning."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LetterVersionStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    ESCALATED = "escalated"


class AppealLetterDraft(BaseModel):
    """Generated appeal letter content plus metadata for the UI."""

    letter_text: str = Field(description="Full, ready-to-print appeal letter text.")

    # These are expected to be derived from the findings we already generated.
    legal_citations: list[str] = Field(
        default_factory=list,
        description="Relevant legal citations that support the findings.",
    )
    policy_references: list[str] = Field(
        default_factory=list,
        description="Policy references and procedural bases for the appeal.",
    )

    # A concrete checklist of documents the patient should attach.
    supporting_document_checklist: list[str] = Field(
        default_factory=list,
        description="Documents to attach to the appeal submission.",
    )

    # Helps the UI present drafts with a meaningful subject line.
    suggested_subject_line: Optional[str] = Field(
        default=None,
        description="Suggested email/fax subject line for the appeal packet.",
    )


class AppealLetterVersion(BaseModel):
    """A persisted, immutable version of a letter for a case."""

    version_id: str
    case_id: str
    round: int = 1
    status: LetterVersionStatus

    letter_text: str
    legal_citations: list[str] = Field(default_factory=list)
    policy_references: list[str] = Field(default_factory=list)
    supporting_document_checklist: list[str] = Field(default_factory=list)

    created_at: datetime
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None

    # Optional notes for audit trail (e.g., user edits, insurer response upload).
    metadata: dict = Field(default_factory=dict)

