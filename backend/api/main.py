"""FastAPI backend — Phases 1-4 complete.

Phases:
  1 — Document upload, OCR/text extraction, LLM field extraction, rule engine, risk report
  2 — AI-enhanced appeal letters, PDF export, editable letter interface
  3 — PostgreSQL/SQLite persistence, search & filtering, full case timeline
  4 — LangGraph agentic follow-up state machine, durable deadline tracking
"""

import logging
import sys
from pathlib import Path

_backend_dir = Path(__file__).parent.parent
_project_root = _backend_dir.parent
for p in [str(_backend_dir), str(_project_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    ALLOWED_ORIGINS,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    PORT,
    STORAGE_DIR,
    UPLOADS_DIR,
)
from database import (
    AppealLetterVersionRecord,
    Base,
    Case,
    CaseTimelineEvent,
    ExtractedFieldsRecord,
    FindingRecord,
    FollowUpStateRecord,
    ProcessingStep,
    RiskReportRecord,
    engine,
    get_db,
)
from database.crud import (
    add_processing_step,
    add_timeline_event,
    create_case,
    delete_case as db_delete_case,
    get_case,
    get_letter_version,
    get_or_create_follow_up,
    get_timeline,
    list_cases,
    save_appeal_letter_version,
    save_extracted_fields,
    save_risk_report,
    update_case_fields,
    update_case_status,
    update_follow_up,
    update_letter_version_status,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — create DB tables on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Durable deadline sweep: re-checks pending response deadlines that were
    # scheduled before a restart (in-process timers don't survive restarts).
    sweep_task = asyncio.create_task(_deadline_sweep_loop())
    yield
    sweep_task.cancel()
    await engine.dispose()


async def _deadline_sweep_loop(interval_seconds: int = 3600) -> None:
    """Periodically escalate cases whose response deadline has passed."""
    import asyncio

    from sqlalchemy import select

    # Short delay so the app finishes booting before the first sweep
    await asyncio.sleep(10)
    while True:
        try:
            from database.engine import AsyncSessionLocal

            now = datetime.now(timezone.utc)
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(FollowUpStateRecord.case_id).where(
                        FollowUpStateRecord.round_1_response_deadline.is_not(None),
                        FollowUpStateRecord.round_1_response_deadline < now,
                        FollowUpStateRecord.round_1_response_received_at.is_(None),
                        FollowUpStateRecord.escalation_ready.is_(False),
                    )
                )
                overdue_case_ids = [row[0] for row in result.all()]

            for case_id in overdue_case_ids:
                logger.info("Deadline sweep: case %s is overdue, checking escalation", case_id)
                await _check_and_escalate(case_id)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.error("Deadline sweep failed: %s", exc)

        await asyncio.sleep(interval_seconds)


app = FastAPI(
    title="Medical Claim Fighter API",
    description="Phases 1-4: OCR → extraction → rule engine → risk report → AI appeal letter → follow-up loop",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ApproveLetterRequest(BaseModel):
    version_id: str
    letter_text: str
    notes: Optional[str] = None


class SendLetterRequest(BaseModel):
    version_id: str
    send_method: str = "mail"
    response_deadline_days: int = 30


class ResolveCaseRequest(BaseModel):
    outcome: str  # "won" | "partial" | "lost"
    notes: Optional[str] = None


class EscalateRequest(BaseModel):
    reason: Optional[str] = "manual_escalation"


class SearchRequest(BaseModel):
    q: Optional[str] = None
    status: Optional[str] = None
    insurer: Optional[str] = None
    limit: int = 50
    offset: int = 0
    sort_by: str = "created_at"
    sort_dir: str = "desc"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get_case_or_404(case_id: str, db: AsyncSession) -> dict:
    case = await get_case(db, case_id=case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Medical Claim Fighter API",
        "version": "4.0.0",
        "phases": ["1-upload-extract", "2-appeal-pdf", "3-postgres-search", "4-langgraph-followup"],
    }


# ---------------------------------------------------------------------------
# Phase 1 — Upload
# ---------------------------------------------------------------------------


@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a medical document and create a new case."""
    allowed = {".pdf", ".txt", ".png", ".jpg", ".jpeg"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(allowed)}")

    case_id = str(uuid.uuid4())
    file_path = UPLOADS_DIR / f"{case_id}{ext}"
    content = await file.read()
    file_path.write_bytes(content)

    case = await create_case(
        db,
        case_id=case_id,
        filename=file.filename or "upload",
        file_path=str(file_path),
        file_type=ext,
    )
    return {
        "case_id": case_id,
        "filename": file.filename,
        "status": "uploaded",
        "message": "Document uploaded successfully. Ready for processing.",
    }


# ---------------------------------------------------------------------------
# Phase 1 — Process (async background task)
# ---------------------------------------------------------------------------


@app.post("/api/process/{case_id}")
async def process_case(
    case_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger the full pipeline for a case (runs as a background task)."""
    case = await _get_case_or_404(case_id, db)

    if case["status"] == "processing":
        raise HTTPException(400, "Case is already being processed")
    if case["status"] in ("drafted", "approved", "sent", "resolved"):
        return {"message": "Case already processed", "case_id": case_id}

    await update_case_status(db, case_id=case_id, status="processing")
    background_tasks.add_task(_run_pipeline, case_id, case["file_path"])
    return {"message": "Processing started", "case_id": case_id}


async def _run_pipeline(case_id: str, file_path: str) -> None:
    """Full async pipeline — runs in background."""
    from database.engine import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            await _pipeline_inner(db, case_id, file_path)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            import traceback
            logger.error("Pipeline failed for %s:\n%s", case_id, traceback.format_exc())
            async with AsyncSessionLocal() as db2:
                try:
                    await update_case_status(db2, case_id=case_id, status="failed", error=str(exc))
                    await add_processing_step(db2, case_id=case_id, step="error", status="failed", details=str(exc))
                    await add_timeline_event(db2, case_id=case_id, event_type="pipeline_failed",
                                             title="Processing failed", description=str(exc))
                    await db2.commit()
                except Exception:
                    pass


async def _pipeline_inner(db: AsyncSession, case_id: str, file_path: str) -> None:
    """Inner pipeline — all DB writes share one session."""
    from pipeline.document_loader import DocumentLoadError, extract_text
    from pipeline.llm_client import OllamaClient
    from pipeline.rule_engine import run_all_rule_checks
    from pipeline.appeal_letter_builder import build_appeal_letter_draft, create_letter_version
    from pipeline.llm_appeal_enhancer import enhance_appeal_letter
    from pipeline.pdf_export import export_letter_to_pdf
    from main import synthesize_risk_report

    # Step 1: Load text
    try:
        text = extract_text(file_path)
    except DocumentLoadError as exc:
        raise HTTPException(400, str(exc)) from exc

    await add_processing_step(db, case_id=case_id, step="load_text", status="completed",
                              details=f"Loaded {len(text)} characters")

    # Step 2: LLM client
    llm = OllamaClient(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)
    await add_processing_step(db, case_id=case_id, step="initialize_llm", status="completed")

    # Step 3: Classify
    doc_type = llm.classify_document(text)
    await add_processing_step(db, case_id=case_id, step="classify_document", status="completed",
                              details=f"Type: {doc_type.value}")

    # Step 4: Extract fields
    fields = llm.extract_fields(text, doc_type)
    fields_dict = json.loads(fields.model_dump_json())
    await save_extracted_fields(db, case_id=case_id, fields_dict=fields_dict)
    await add_processing_step(db, case_id=case_id, step="extract_fields", status="completed")

    # Step 5: Rule engine
    findings = run_all_rule_checks(fields)
    await add_processing_step(db, case_id=case_id, step="rule_engine", status="completed",
                              details=f"Found {len(findings)} issues")

    # Step 6: Risk report
    report = synthesize_risk_report(fields, findings)
    report_dict = json.loads(report.model_dump_json())
    await save_risk_report(db, case_id=case_id, report_dict=report_dict)
    await add_processing_step(db, case_id=case_id, step="risk_report", status="completed")

    # Step 7 (Phase 2): AI-enhanced appeal letter
    base_draft = build_appeal_letter_draft(fields, report)
    enhanced_text = enhance_appeal_letter(llm, base_draft.letter_text, fields, report)
    from schemas.appeal_letter import AppealLetterDraft
    enhanced_draft = AppealLetterDraft(
        letter_text=enhanced_text,
        legal_citations=base_draft.legal_citations,
        policy_references=base_draft.policy_references,
        supporting_document_checklist=base_draft.supporting_document_checklist,
        suggested_subject_line=base_draft.suggested_subject_line,
    )
    version = create_letter_version(
        case_id=case_id, round=1, status="draft", draft=enhanced_draft,
        metadata={
            "generated_from": {"risk_report_finding_count": len(findings)},
            "suggested_subject_line": enhanced_draft.suggested_subject_line,
            "ai_enhanced": True,
        },
    )
    await save_appeal_letter_version(db, version_dict=version)

    # Generate PDF
    try:
        pdf_path = export_letter_to_pdf(version_dict=version, output_dir=UPLOADS_DIR)
        version["pdf_path"] = str(pdf_path)
        # Update the record with pdf_path
        from sqlalchemy import update
        from database.models import AppealLetterVersionRecord
        await db.execute(
            update(AppealLetterVersionRecord)
            .where(AppealLetterVersionRecord.version_id == version["version_id"])
            .values(pdf_path=str(pdf_path))
        )
    except Exception as exc:
        logger.warning("PDF generation failed (non-fatal): %s", exc)

    await add_processing_step(db, case_id=case_id, step="draft_appeal_letter", status="completed")

    # Update case to 'drafted'
    await update_case_fields(
        db, case_id=case_id,
        status="drafted",
        current_appeal_letter_version_id=version["version_id"],
    )

    # Timeline event
    await add_timeline_event(
        db, case_id=case_id, event_type="processing_completed",
        title="Analysis complete — draft letter ready",
        description=f"Found {len(findings)} issue(s). Appeal likelihood: {report.appeal_likelihood.value}.",
        metadata={"findings_count": len(findings), "appeal_likelihood": report.appeal_likelihood.value},
    )


# ---------------------------------------------------------------------------
# Phase 3 — Cases CRUD with search & filtering
# ---------------------------------------------------------------------------


@app.get("/api/cases")
async def list_cases_endpoint(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by filename, patient name, or insurer"),
    insurer: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    cases, total = await list_cases(
        db, status=status, search=search, insurer=insurer,
        limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir,
    )
    return {"cases": cases, "total": total, "limit": limit, "offset": offset}


@app.get("/api/cases/{case_id}")
async def get_case_endpoint(case_id: str, db: AsyncSession = Depends(get_db)):
    return await _get_case_or_404(case_id, db)


@app.get("/api/cases/{case_id}/status")
async def get_case_status(case_id: str, db: AsyncSession = Depends(get_db)):
    case = await _get_case_or_404(case_id, db)
    return {
        "case_id": case_id,
        "status": case["status"],
        "updated_at": case["updated_at"],
        "processing_steps": case["processing_steps"],
    }


@app.delete("/api/cases/{case_id}")
async def delete_case_endpoint(case_id: str, db: AsyncSession = Depends(get_db)):
    case = await _get_case_or_404(case_id, db)
    # Remove uploaded file
    fp = Path(case["file_path"])
    if fp.exists():
        fp.unlink(missing_ok=True)
    deleted = await db_delete_case(db, case_id=case_id)
    if not deleted:
        raise HTTPException(404, "Case not found")
    return {"message": "Case deleted successfully", "case_id": case_id}


# ---------------------------------------------------------------------------
# Phase 3 — Full case timeline
# ---------------------------------------------------------------------------


@app.get("/api/cases/{case_id}/timeline")
async def get_case_timeline(case_id: str, db: AsyncSession = Depends(get_db)):
    await _get_case_or_404(case_id, db)
    events = await get_timeline(db, case_id=case_id)
    return {"case_id": case_id, "events": events}


# ---------------------------------------------------------------------------
# Phase 2 — Appeal Letter endpoints
# ---------------------------------------------------------------------------


@app.get("/api/cases/{case_id}/appeal-letter")
async def get_appeal_letter(case_id: str, db: AsyncSession = Depends(get_db)):
    case = await _get_case_or_404(case_id, db)
    versions = case.get("appeal_letter_versions", [])
    current_id = case.get("current_appeal_letter_version_id")

    # Backfill: if no versions but risk_report exists, generate now
    if not versions and case.get("extracted_fields") and case.get("risk_report"):
        try:
            from schemas import ExtractedFields, RiskReport
            from pipeline.appeal_letter_builder import build_appeal_letter_draft, create_letter_version
            from pipeline.pdf_export import export_letter_to_pdf

            ef = ExtractedFields.model_validate(case["extracted_fields"])
            rr = RiskReport.model_validate(case["risk_report"])
            draft = build_appeal_letter_draft(ef, rr)
            version = create_letter_version(
                case_id=case_id, round=1, status="draft", draft=draft,
                metadata={"generated_from": {"backfill": True},
                          "suggested_subject_line": draft.suggested_subject_line},
            )
            await save_appeal_letter_version(db, version_dict=version)
            try:
                pdf_path = export_letter_to_pdf(version_dict=version, output_dir=UPLOADS_DIR)
                from sqlalchemy import update
                from database.models import AppealLetterVersionRecord
                await db.execute(
                    update(AppealLetterVersionRecord)
                    .where(AppealLetterVersionRecord.version_id == version["version_id"])
                    .values(pdf_path=str(pdf_path))
                )
            except Exception:
                pass
            await update_case_fields(
                db, case_id=case_id, status="drafted",
                current_appeal_letter_version_id=version["version_id"],
            )
            versions = [version]
            current_id = version["version_id"]
        except Exception as exc:
            logger.error("Backfill failed for case %s: %s", case_id, exc)

    follow_up = case.get("follow_up")
    current = next((v for v in versions if v.get("version_id") == current_id), None)
    if not current and versions:
        current = versions[-1]

    return {"case_id": case_id, "current": current, "versions": versions, "follow_up": follow_up}


@app.post("/api/cases/{case_id}/appeal-letter/approve")
async def approve_letter(
    case_id: str,
    payload: ApproveLetterRequest,
    db: AsyncSession = Depends(get_db),
):
    case = await _get_case_or_404(case_id, db)
    versions = case.get("appeal_letter_versions", [])
    base = next((v for v in versions if v.get("version_id") == payload.version_id), None)
    if not base:
        raise HTTPException(404, "Letter version not found")

    from pipeline.appeal_letter_builder import create_letter_version
    from schemas.appeal_letter import AppealLetterDraft
    from pipeline.pdf_export import export_letter_to_pdf

    draft = AppealLetterDraft(
        letter_text=payload.letter_text,
        legal_citations=base.get("legal_citations", []),
        policy_references=base.get("policy_references", []),
        supporting_document_checklist=base.get("supporting_document_checklist", []),
    )
    approved = create_letter_version(
        case_id=case_id, round=int(base.get("round", 1)), status="approved", draft=draft,
        metadata={"approved_from_version_id": payload.version_id, "notes": payload.notes,
                  "edited_by_user": True},
    )
    await save_appeal_letter_version(db, version_dict=approved)

    # Generate updated PDF for the approved version
    try:
        pdf_path = export_letter_to_pdf(version_dict=approved, output_dir=UPLOADS_DIR)
        from sqlalchemy import update
        from database.models import AppealLetterVersionRecord
        await db.execute(
            update(AppealLetterVersionRecord)
            .where(AppealLetterVersionRecord.version_id == approved["version_id"])
            .values(pdf_path=str(pdf_path))
        )
    except Exception as exc:
        logger.warning("PDF generation failed on approve: %s", exc)

    await update_case_fields(
        db, case_id=case_id, status="approved",
        current_appeal_letter_version_id=approved["version_id"],
    )
    await add_processing_step(db, case_id=case_id, step="approve_appeal_letter", status="completed",
                              details=approved["version_id"])
    await add_timeline_event(db, case_id=case_id, event_type="letter_approved",
                             title="Appeal letter approved",
                             description="Patient approved the letter for sending.",
                             metadata={"version_id": approved["version_id"]})
    return {"message": "Letter approved", "version_id": approved["version_id"]}


@app.post("/api/cases/{case_id}/appeal-letter/send")
async def send_letter(
    case_id: str,
    payload: SendLetterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    case = await _get_case_or_404(case_id, db)
    versions = case.get("appeal_letter_versions", [])
    base = next((v for v in versions if v.get("version_id") == payload.version_id), None)
    if not base:
        raise HTTPException(404, "Letter version not found")

    from pipeline.appeal_letter_builder import create_letter_version
    from schemas.appeal_letter import AppealLetterDraft
    from pipeline.follow_up_agent import FollowUpAgent, FollowUpEvent

    draft = AppealLetterDraft(
        letter_text=base.get("letter_text", ""),
        legal_citations=base.get("legal_citations", []),
        policy_references=base.get("policy_references", []),
        supporting_document_checklist=base.get("supporting_document_checklist", []),
    )
    sent_version = create_letter_version(
        case_id=case_id, round=int(base.get("round", 1)), status="sent", draft=draft,
        metadata={"send_method": payload.send_method, "sent_from_version_id": payload.version_id},
    )
    await save_appeal_letter_version(db, version_dict=sent_version)

    # Phase 4 — advance agent state
    follow_up_record = await get_or_create_follow_up(db, case_id=case_id)
    agent = FollowUpAgent(case_id=case_id)
    state = agent.load_state(follow_up_record.graph_state_json)
    state = agent.advance(
        state, event=FollowUpEvent.LETTER_SENT,
        payload={"sent_at": _now_iso(), "version_id": sent_version["version_id"],
                 "response_deadline_days": payload.response_deadline_days},
    )

    await update_follow_up(
        db, case_id=case_id,
        agent_state=state["agent_state"],
        graph_state_json=dict(state),
        round=state.get("round", 1),
        round_1_sent_at=_parse_iso(state.get("round_1_sent_at")),
        round_1_response_deadline=_parse_iso(state.get("round_1_response_deadline")),
        round_1_response_received_at=None,
    )
    await update_case_fields(
        db, case_id=case_id, status="sent",
        current_appeal_letter_version_id=sent_version["version_id"],
    )
    await add_processing_step(db, case_id=case_id, step="send_appeal_letter", status="completed",
                              details=payload.send_method)
    await add_timeline_event(
        db, case_id=case_id, event_type="letter_sent",
        title=f"Appeal letter sent via {payload.send_method}",
        description=f"Response deadline: {state.get('round_1_response_deadline', 'N/A')}",
        metadata={"version_id": sent_version["version_id"],
                  "response_deadline": state.get("round_1_response_deadline")},
    )

    # Schedule background deadline check (Phase 4 durable timer)
    deadline_str = state.get("round_1_response_deadline")
    if deadline_str:
        background_tasks.add_task(
            _schedule_deadline_check, case_id, deadline_str,
            payload.response_deadline_days,
        )

    return {
        "message": "Letter marked as sent",
        "version_id": sent_version["version_id"],
        "response_deadline": state.get("round_1_response_deadline"),
    }


@app.post("/api/cases/{case_id}/insurer-response")
async def upload_insurer_response(
    case_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload insurer response and generate Round 2 draft (Phase 4 event: response_received)."""
    case = await _get_case_or_404(case_id, db)

    follow_up = case.get("follow_up", {}) or {}
    if follow_up.get("round_1_response_received_at"):
        return {"message": "Insurer response already received for Round 1."}

    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".pdf", ".txt", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(400, "Unsupported file type for insurer response.")

    response_path = UPLOADS_DIR / f"{case_id}_insurer_response_{uuid.uuid4().hex}{ext}"
    content = await file.read()
    response_path.write_bytes(content)

    from pipeline.document_loader import extract_text
    try:
        insurer_text = extract_text(response_path)
    except Exception as exc:
        raise HTTPException(400, f"Failed to extract text: {exc}") from exc

    # Build Round 2 letter
    try:
        from schemas import ExtractedFields, RiskReport
        from pipeline.appeal_letter_builder import build_round2_appeal_letter_draft, create_letter_version
        from pipeline.pdf_export import export_letter_to_pdf
        from pipeline.follow_up_agent import FollowUpAgent, FollowUpEvent

        ef = ExtractedFields.model_validate(case["extracted_fields"])
        rr = RiskReport.model_validate(case["risk_report"])
        round2_draft = build_round2_appeal_letter_draft(ef, rr, insurer_response_text=insurer_text)
        round2_version = create_letter_version(
            case_id=case_id, round=2, status="draft", draft=round2_draft,
            metadata={"generated_from": {"insurer_response_uploaded": True}},
        )
        await save_appeal_letter_version(db, version_dict=round2_version)

        try:
            pdf_path = export_letter_to_pdf(version_dict=round2_version, output_dir=UPLOADS_DIR)
            from sqlalchemy import update
            from database.models import AppealLetterVersionRecord
            await db.execute(
                update(AppealLetterVersionRecord)
                .where(AppealLetterVersionRecord.version_id == round2_version["version_id"])
                .values(pdf_path=str(pdf_path))
            )
        except Exception as exc:
            logger.warning("PDF generation failed for round 2: %s", exc)

        # Phase 4 — advance agent state
        follow_up_record = await get_or_create_follow_up(db, case_id=case_id)
        agent = FollowUpAgent(case_id=case_id)
        state = agent.load_state(follow_up_record.graph_state_json)
        state = agent.advance(
            state, event=FollowUpEvent.RESPONSE_RECEIVED,
            payload={"received_at": _now_iso(),
                     "response_excerpt": insurer_text[:2000]},
        )
        await update_follow_up(
            db, case_id=case_id,
            agent_state=state["agent_state"],
            graph_state_json=dict(state),
            round_1_response_received_at=_parse_iso(_now_iso()),
            round_1_response_excerpt=insurer_text[:2000],
            round_1_response_file_path=str(response_path),
        )
        await update_case_fields(
            db, case_id=case_id, status="drafted",
            current_appeal_letter_version_id=round2_version["version_id"],
        )
        await add_processing_step(db, case_id=case_id, step="insurer_response_received",
                                  status="completed", details=round2_version["version_id"])
        await add_timeline_event(
            db, case_id=case_id, event_type="insurer_response_received",
            title="Insurer response received — Round 2 draft ready",
            description="Upload processed. Round 2 appeal letter generated.",
            metadata={"version_id": round2_version["version_id"]},
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to generate Round 2 for case %s: %s", case_id, exc)
        raise HTTPException(500, f"Failed to generate Round 2 letter: {exc}") from exc

    return {
        "message": "Insurer response processed. Round 2 draft ready.",
        "version_id": round2_version["version_id"],
    }


# ---------------------------------------------------------------------------
# Phase 2 — PDF download
# ---------------------------------------------------------------------------


@app.get("/api/cases/{case_id}/appeal-letter/{version_id}/pdf")
async def download_appeal_pdf(
    case_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download the PDF for an appeal letter version."""
    await _get_case_or_404(case_id, db)
    record = await get_letter_version(db, version_id=version_id)
    if not record or record.case_id != case_id:
        raise HTTPException(404, "Letter version not found")

    pdf_path = record.pdf_path
    if not pdf_path or not Path(pdf_path).exists():
        # Generate on the fly
        from pipeline.pdf_export import export_letter_to_pdf
        from database.crud import _letter_version_to_dict
        version_dict = _letter_version_to_dict(record)
        try:
            pdf_path_obj = export_letter_to_pdf(version_dict=version_dict, output_dir=UPLOADS_DIR)
            pdf_path = str(pdf_path_obj)
            from sqlalchemy import update
            from database.models import AppealLetterVersionRecord
            await db.execute(
                update(AppealLetterVersionRecord)
                .where(AppealLetterVersionRecord.version_id == version_id)
                .values(pdf_path=pdf_path)
            )
        except Exception as exc:
            raise HTTPException(500, f"PDF generation failed: {exc}") from exc

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"appeal_letter_{version_id[:8]}.pdf",
    )


# ---------------------------------------------------------------------------
# Phase 4 — Manual escalation
# ---------------------------------------------------------------------------


@app.post("/api/cases/{case_id}/escalate")
async def manual_escalate(
    case_id: str,
    payload: EscalateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger escalation packet generation (Phase 4)."""
    case = await _get_case_or_404(case_id, db)

    if not case.get("extracted_fields") or not case.get("risk_report"):
        raise HTTPException(400, "Cannot escalate — case not yet processed.")

    from schemas import ExtractedFields, RiskReport
    from pipeline.appeal_letter_builder import build_escalation_letter_draft, create_letter_version
    from pipeline.pdf_export import export_letter_to_pdf
    from pipeline.follow_up_agent import FollowUpAgent, FollowUpEvent

    ef = ExtractedFields.model_validate(case["extracted_fields"])
    rr = RiskReport.model_validate(case["risk_report"])
    escalation_draft = build_escalation_letter_draft(ef, rr)
    escalation_version = create_letter_version(
        case_id=case_id, round=99, status="escalated", draft=escalation_draft,
        metadata={"generated_from": {"manual_escalation": True},
                  "escalation_reason": payload.reason},
    )
    await save_appeal_letter_version(db, version_dict=escalation_version)

    try:
        pdf_path = export_letter_to_pdf(version_dict=escalation_version, output_dir=UPLOADS_DIR)
        from sqlalchemy import update
        from database.models import AppealLetterVersionRecord
        await db.execute(
            update(AppealLetterVersionRecord)
            .where(AppealLetterVersionRecord.version_id == escalation_version["version_id"])
            .values(pdf_path=str(pdf_path))
        )
    except Exception as exc:
        logger.warning("PDF gen failed for escalation: %s", exc)

    # Advance agent state
    follow_up_record = await get_or_create_follow_up(db, case_id=case_id)
    agent = FollowUpAgent(case_id=case_id)
    state = agent.load_state(follow_up_record.graph_state_json)
    state = agent.advance(
        state, event=FollowUpEvent.MANUAL_ESCALATE,
        payload={"reason": payload.reason,
                 "escalation_version_id": escalation_version["version_id"]},
    )
    await update_follow_up(
        db, case_id=case_id,
        agent_state=state["agent_state"],
        graph_state_json=dict(state),
        escalation_ready=True,
        escalation_triggered_at=_parse_iso(_now_iso()),
    )
    await update_case_fields(
        db, case_id=case_id, status="escalated",
        current_appeal_letter_version_id=escalation_version["version_id"],
    )
    await add_timeline_event(
        db, case_id=case_id, event_type="manual_escalation",
        title="Manually escalated",
        description=f"Reason: {payload.reason}. Escalation packet generated.",
        metadata={"version_id": escalation_version["version_id"]},
    )
    return {
        "message": "Escalation packet generated",
        "version_id": escalation_version["version_id"],
    }


# ---------------------------------------------------------------------------
# Case resolution
# ---------------------------------------------------------------------------


@app.post("/api/cases/{case_id}/resolve")
async def resolve_case(
    case_id: str,
    payload: ResolveCaseRequest,
    db: AsyncSession = Depends(get_db),
):
    await _get_case_or_404(case_id, db)
    from pipeline.follow_up_agent import FollowUpAgent, FollowUpEvent

    follow_up_record = await get_or_create_follow_up(db, case_id=case_id)
    agent = FollowUpAgent(case_id=case_id)
    state = agent.load_state(follow_up_record.graph_state_json)
    state = agent.advance(
        state, event=FollowUpEvent.CASE_RESOLVED,
        payload={"outcome": payload.outcome, "notes": payload.notes or ""},
    )
    await update_follow_up(
        db, case_id=case_id,
        agent_state=state["agent_state"],
        graph_state_json=dict(state),
    )
    await update_case_fields(
        db, case_id=case_id,
        status="resolved",
        resolution_outcome=payload.outcome,
        resolution_notes=payload.notes,
        resolved_at=_parse_iso(_now_iso()),
    )
    await add_processing_step(db, case_id=case_id, step="resolve_case", status="completed",
                              details=payload.outcome)
    await add_timeline_event(
        db, case_id=case_id, event_type="case_resolved",
        title=f"Case resolved — {payload.outcome}",
        description=payload.notes or "",
        metadata={"outcome": payload.outcome},
    )
    return {"message": "Case resolved", "case_id": case_id, "outcome": payload.outcome}


# ---------------------------------------------------------------------------
# Phase 4 — Background deadline scheduler
# ---------------------------------------------------------------------------


async def _schedule_deadline_check(
    case_id: str, deadline_str: str, deadline_days: int
) -> None:
    """Wait until the deadline then check if escalation is needed."""
    import asyncio
    from dateutil import parser as date_parser

    try:
        deadline_dt = date_parser.parse(deadline_str)
        if deadline_dt.tzinfo is None:
            deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        wait_seconds = (deadline_dt - now).total_seconds()
        if wait_seconds > 0:
            logger.info("Scheduled deadline check for case %s in %.0f seconds", case_id, wait_seconds)
            await asyncio.sleep(wait_seconds)

        await _check_and_escalate(case_id)
    except Exception as exc:
        logger.error("Scheduler error for case %s: %s", case_id, exc)


async def _check_and_escalate(case_id: str) -> None:
    """Check a single case's deadline and generate an escalation packet if needed."""
    try:
        from database.engine import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            try:
                case = await get_case(db, case_id=case_id)
                if not case:
                    return
                follow_up = case.get("follow_up", {}) or {}
                if follow_up.get("round_1_response_received_at"):
                    logger.info("Case %s: response received before deadline, no escalation", case_id)
                    return
                if follow_up.get("escalation_ready"):
                    return

                # Generate escalation
                if not case.get("extracted_fields") or not case.get("risk_report"):
                    return

                from schemas import ExtractedFields, RiskReport
                from pipeline.appeal_letter_builder import build_escalation_letter_draft, create_letter_version
                from pipeline.pdf_export import export_letter_to_pdf
                from pipeline.follow_up_agent import FollowUpAgent, FollowUpEvent

                ef = ExtractedFields.model_validate(case["extracted_fields"])
                rr = RiskReport.model_validate(case["risk_report"])
                draft = build_escalation_letter_draft(ef, rr)
                follow_up_data = case.get("follow_up", {}) or {}
                esc_round = (follow_up_data.get("round") or 1) + 1
                esc_version = create_letter_version(
                    case_id=case_id, round=esc_round, status="escalated", draft=draft,
                    metadata={"generated_by": "deadline_check"},
                )
                await save_appeal_letter_version(db, version_dict=esc_version)
                try:
                    export_letter_to_pdf(version_dict=esc_version, output_dir=UPLOADS_DIR)
                except Exception:
                    pass

                follow_up_record = await get_or_create_follow_up(db, case_id=case_id)
                agent = FollowUpAgent(case_id=case_id)
                state = agent.load_state(follow_up_record.graph_state_json)
                state = agent.advance(state, event=FollowUpEvent.DEADLINE_EXCEEDED,
                                      payload={"escalation_version_id": esc_version["version_id"]})
                await update_follow_up(
                    db, case_id=case_id,
                    agent_state=state["agent_state"],
                    graph_state_json=dict(state),
                    escalation_ready=True,
                    escalation_triggered_at=_parse_iso(_now_iso()),
                )
                await update_case_fields(
                    db, case_id=case_id, status="escalated",
                    current_appeal_letter_version_id=esc_version["version_id"],
                )
                await add_timeline_event(
                    db, case_id=case_id, event_type="deadline_exceeded",
                    title="Deadline exceeded — escalation triggered",
                    description="No insurer response received by the deadline.",
                    metadata={"version_id": esc_version["version_id"]},
                )
                await db.commit()
                logger.info("Escalation triggered for case %s", case_id)
            except Exception as exc:
                await db.rollback()
                logger.error("Deadline check failed for case %s: %s", case_id, exc)
    except Exception as exc:
        logger.error("Scheduler error for case %s: %s", case_id, exc)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        from dateutil import parser
        return parser.parse(value)
    except Exception:
        return None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
