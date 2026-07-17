"""FastAPI backend wrapper for Phase 1 pipeline.

Provides REST API endpoints for the frontend to interact with the medical claim analysis pipeline.
"""

import logging
import sys
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict

from pydantic import BaseModel
from threading import Timer

_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from config import (
    ALLOWED_ORIGINS,
    CASES_FILE,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    PORT,
    STORAGE_DIR,
    UPLOADS_DIR,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Medical Claim Fighter API",
    description="API for medical bill and insurance claim analysis",
    version="1.0.0"
)

# CORS middleware — origins from ALLOWED_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
STORAGE_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# Initialize cases file if it doesn't exist
if not CASES_FILE.exists():
    CASES_FILE.write_text(json.dumps({"cases": []}, indent=2))

# Best-effort, in-process timers for follow-up deadlines.
# For true production, replace with a durable job queue (Celery/Step Functions).
_FOLLOWUP_TIMERS: dict[str, Timer] = {}


def load_cases() -> dict:
    """Load all cases from storage."""
    return json.loads(CASES_FILE.read_text())


def save_cases(data: dict):
    """Save cases to storage."""
    # Atomic write to avoid partial file corruption if the process is interrupted.
    tmp_path = CASES_FILE.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, default=str))
    tmp_path.replace(CASES_FILE)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Medical Claim Fighter API",
        "version": "1.0.0"
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document and create a new case.
    
    Accepts: PDF, TXT, PNG, JPG
    Returns: Case ID and initial metadata
    """
    # Validate file type
    allowed_extensions = {".pdf", ".txt", ".png", ".jpg", ".jpeg"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate case ID
    case_id = str(uuid.uuid4())
    
    # Save uploaded file
    file_path = UPLOADS_DIR / f"{case_id}{file_ext}"
    content = await file.read()
    file_path.write_bytes(content)
    
    # Create case record
    case_data = {
        "case_id": case_id,
        "filename": file.filename,
        "file_path": str(file_path),
        "file_type": file_ext,
        "status": "uploaded",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "extracted_fields": None,
        "risk_report": None,
        "processing_steps": [
            {
                "step": "upload",
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }
    
    # Save to storage
    cases = load_cases()
    cases["cases"].append(case_data)
    save_cases(cases)
    
    return {
        "case_id": case_id,
        "filename": file.filename,
        "status": "uploaded",
        "message": "Document uploaded successfully. Ready for processing."
    }


@app.post("/api/process/{case_id}")
async def process_case(case_id: str):
    """Trigger Phase 1 pipeline processing for a case.
    
    Steps:
    1. Load document text
    2. Classify document type (LLM)
    3. Extract structured fields (LLM)
    4. Run rule engine checks
    5. Generate risk report
    """
    import sys
    # Ensure the project root (containing pipeline/, schemas/, main.py) is on the path
    project_root = str(Path(__file__).parent.parent.parent.resolve())
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from pipeline.llm_client import OllamaClient
    from pipeline.rule_engine import run_all_rule_checks
    from main import synthesize_risk_report
    from pipeline.appeal_letter_builder import build_appeal_letter_draft, create_letter_version
    
    # Load case
    cases = load_cases()
    case = next((c for c in cases["cases"] if c["case_id"] == case_id), None)
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if case["status"] == "processing":
        raise HTTPException(status_code=400, detail="Case is already being processed")
    
    if case["status"] == "completed":
        return {"message": "Case already processed", "case_id": case_id}
    
    from pipeline.document_loader import DocumentLoadError, extract_text

    file_path = Path(case["file_path"])
    try:
        text = extract_text(file_path)
    except DocumentLoadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        # Update status
        case["status"] = "processing"
        case["updated_at"] = datetime.utcnow().isoformat()
        save_cases(cases)
        
        case["processing_steps"].append({
            "step": "load_text",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": f"Loaded {len(text)} characters"
        })
        save_cases(cases)
        
        # Step 2: Initialize LLM client
        llm = OllamaClient(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)
        
        case["processing_steps"].append({
            "step": "initialize_llm",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        })
        save_cases(cases)
        
        # Step 3: Classify document
        doc_type = llm.classify_document(text)
        
        case["processing_steps"].append({
            "step": "classify_document",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": f"Type: {doc_type.value}"
        })
        save_cases(cases)
        
        # Step 4: Extract structured fields
        fields = llm.extract_fields(text, doc_type)
        
        case["extracted_fields"] = json.loads(fields.model_dump_json())
        case["processing_steps"].append({
            "step": "extract_fields",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        })
        save_cases(cases)
        
        # Step 5: Run rule engine
        findings = run_all_rule_checks(fields)
        
        case["processing_steps"].append({
            "step": "rule_engine",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": f"Found {len(findings)} issues"
        })
        save_cases(cases)
        
        # Step 6: Generate risk report
        report = synthesize_risk_report(fields, findings)

        case["risk_report"] = json.loads(report.model_dump_json())
        case["processing_steps"].append(
            {
                "step": "risk_report",
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Step 7 (Phase 2): Draft appeal letter + checklist (versioned)
        draft = build_appeal_letter_draft(fields, report)
        case["appeal_letter_versions"] = case.get("appeal_letter_versions", [])

        version = create_letter_version(
            case_id=case_id,
            round=1,
            status="draft",
            draft=draft,
            metadata={
                "generated_from": {
                    "risk_report_case_summary": case["risk_report"].get("case_summary"),
                    "finding_count": len(case["risk_report"].get("findings", [])),
                }
            },
        )
        case["appeal_letter_versions"].append(version)
        case["current_appeal_letter_version_id"] = version["version_id"]
        case["processing_steps"].append(
            {
                "step": "draft_appeal_letter",
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Mark as ready for user approval
        case["status"] = "drafted"
        case["updated_at"] = datetime.utcnow().isoformat()
        save_cases(cases)
        
        return {
            "message": "Processing completed successfully",
            "case_id": case_id,
            "findings_count": len(findings),
            "total_disputed": str(report.total_disputed_amount)
        }
        
    except HTTPException:
        case["status"] = "failed"
        case["updated_at"] = datetime.utcnow().isoformat()
        save_cases(cases)
        raise
    except Exception as e:
        import traceback
        logger.error("Processing failed for case %s:\n%s", case_id, traceback.format_exc())
        # Mark as failed
        case["status"] = "failed"
        case["error"] = str(e)
        case["updated_at"] = datetime.utcnow().isoformat()
        case["processing_steps"].append({
            "step": "error",
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": str(e)
        })
        save_cases(cases)
        
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


class ApproveLetterRequest(BaseModel):
    version_id: str
    letter_text: str
    notes: Optional[str] = None


class SendLetterRequest(BaseModel):
    version_id: str
    send_method: str = "mail"  # "mail" | "email" | "fax"


class ResolveCaseRequest(BaseModel):
    outcome: str  # "won" | "partial" | "lost"
    notes: Optional[str] = None


@app.get("/api/cases/{case_id}/appeal-letter")
async def get_appeal_letter(case_id: str):
    cases = load_cases()
    case = next((c for c in cases["cases"] if c["case_id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    versions = case.get("appeal_letter_versions", [])
    current_id = case.get("current_appeal_letter_version_id")
    current = None

    # Backfill Phase 2 for previously processed cases (risk_report exists, but letter versions do not).
    if not versions and case.get("extracted_fields") and case.get("risk_report"):
        try:
            from schemas import ExtractedFields, RiskReport
            from pipeline.appeal_letter_builder import build_appeal_letter_draft, create_letter_version

            extracted_fields = ExtractedFields.model_validate(case["extracted_fields"])
            report = RiskReport.model_validate(case["risk_report"])

            draft = build_appeal_letter_draft(extracted_fields, report)
            version = create_letter_version(
                case_id=case_id,
                round=1,
                status="draft",
                draft=draft,
                metadata={"generated_from": {"backfill": True}},
            )

            case["appeal_letter_versions"] = [version]
            case["current_appeal_letter_version_id"] = version["version_id"]
            case["status"] = "drafted"
            case["updated_at"] = datetime.utcnow().isoformat()
            case.setdefault("processing_steps", []).append(
                {
                    "step": "draft_appeal_letter",
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": "backfilled",
                }
            )

            versions = case["appeal_letter_versions"]
            current_id = case["current_appeal_letter_version_id"]
            current = version
            save_cases(cases)
        except Exception as exc:
            logger.error("Failed to backfill letter for case %s: %s", case_id, exc)

    if current_id:
        current = next((v for v in versions if v.get("version_id") == current_id), None)
    if current is None and versions:
        # Fallback to most recent version
        current = versions[-1]

    return {
        "case_id": case_id,
        "current": current,
        "versions": versions,
        "follow_up": case.get("follow_up", None),
    }


@app.post("/api/cases/{case_id}/appeal-letter/approve")
async def approve_letter(case_id: str, payload: ApproveLetterRequest):
    cases = load_cases()
    case = next((c for c in cases["cases"] if c["case_id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    versions = case.get("appeal_letter_versions", [])
    base_version = next((v for v in versions if v.get("version_id") == payload.version_id), None)
    if not base_version:
        raise HTTPException(status_code=404, detail="Letter version not found")

    # Create an immutable approved version using the edited text from the UI.
    from pipeline.appeal_letter_builder import create_letter_version
    from schemas.appeal_letter import AppealLetterDraft

    draft = AppealLetterDraft(
        letter_text=payload.letter_text,
        legal_citations=base_version.get("legal_citations", []),
        policy_references=base_version.get("policy_references", []),
        supporting_document_checklist=base_version.get("supporting_document_checklist", []),
        suggested_subject_line=base_version.get("metadata", {}).get("suggested_subject_line"),
    )

    approved_version = create_letter_version(
        case_id=case_id,
        round=int(base_version.get("round", 1)),
        status="approved",
        draft=draft,
        metadata={
            "approved_from_version_id": payload.version_id,
            "notes": payload.notes,
            "edited_by_user": True,
        },
    )
    case["appeal_letter_versions"] = versions + [approved_version]
    case["current_appeal_letter_version_id"] = approved_version["version_id"]

    case["status"] = "approved"
    case["updated_at"] = datetime.utcnow().isoformat()
    case.setdefault("processing_steps", []).append(
        {
            "step": "approve_appeal_letter",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": approved_version["version_id"],
        }
    )

    save_cases(cases)
    return {"message": "Letter approved", "version_id": approved_version["version_id"]}


@app.post("/api/cases/{case_id}/appeal-letter/send")
async def send_letter(case_id: str, payload: SendLetterRequest):
    cases = load_cases()
    case = next((c for c in cases["cases"] if c["case_id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    versions = case.get("appeal_letter_versions", [])
    base_version = next((v for v in versions if v.get("version_id") == payload.version_id), None)
    if not base_version:
        raise HTTPException(status_code=404, detail="Letter version not found")

    from pipeline.appeal_letter_builder import create_letter_version
    from schemas.appeal_letter import AppealLetterDraft

    draft = AppealLetterDraft(
        letter_text=base_version.get("letter_text", ""),
        legal_citations=base_version.get("legal_citations", []),
        policy_references=base_version.get("policy_references", []),
        supporting_document_checklist=base_version.get("supporting_document_checklist", []),
        suggested_subject_line=base_version.get("metadata", {}).get("suggested_subject_line"),
    )

    sent_version = create_letter_version(
        case_id=case_id,
        round=int(base_version.get("round", 1)),
        status="sent",
        draft=draft,
        metadata={
            "send_method": payload.send_method,
            "sent_from_version_id": payload.version_id,
        },
    )
    case["appeal_letter_versions"] = versions + [sent_version]
    case["current_appeal_letter_version_id"] = sent_version["version_id"]

    now = datetime.utcnow()
    # Default insurer response window (Phase 5 follow-up loop uses this).
    response_deadline_days = int(case.get("follow_up_response_deadline_days", 30))
    response_deadline_at = now.replace(microsecond=0) + timedelta(days=response_deadline_days)

    case["follow_up"] = case.get("follow_up", {})
    case["follow_up"]["round_1_sent_at"] = now.isoformat()
    case["follow_up"]["round_1_response_deadline"] = response_deadline_at.isoformat()
    case["follow_up"]["round_1_response_received_at"] = None
    case["follow_up"]["round"] = 1
    case["follow_up"]["escalation_ready"] = False

    case["status"] = "sent"
    case["updated_at"] = datetime.utcnow().isoformat()
    case.setdefault("processing_steps", []).append(
        {
            "step": "send_appeal_letter",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": payload.send_method,
        }
    )

    save_cases(cases)

    # Schedule Phase 5 deadline check (no response => escalation packet).
    try:
        seconds_until_deadline = (response_deadline_at - now).total_seconds()
        if seconds_until_deadline < 0:
            seconds_until_deadline = 0

        # Cancel any previously scheduled timer for this case (best-effort).
        old = _FOLLOWUP_TIMERS.get(case_id)
        if old:
            old.cancel()

        def _deadline_job() -> None:
            try:
                cases_in_job = load_cases()
                case_in_job = next(
                    (c for c in cases_in_job["cases"] if c.get("case_id") == case_id), None
                )
                if not case_in_job:
                    return

                follow_up = case_in_job.get("follow_up", {}) or {}
                if follow_up.get("round_1_response_received_at"):
                    # Response received in time, no escalation.
                    return

                if follow_up.get("escalation_ready"):
                    return

                # Generate escalation packet draft from existing findings.
                if not case_in_job.get("extracted_fields") or not case_in_job.get("risk_report"):
                    return

                from schemas import ExtractedFields, RiskReport
                from pipeline.appeal_letter_builder import (
                    build_escalation_letter_draft,
                    create_letter_version,
                )

                extracted_fields = ExtractedFields.model_validate(case_in_job["extracted_fields"])
                report = RiskReport.model_validate(case_in_job["risk_report"])

                draft = build_escalation_letter_draft(extracted_fields, report)
                escalation_version = create_letter_version(
                    case_id=case_id,
                    round=int(follow_up.get("round", 1)) + 1,
                    status="escalated",
                    draft=draft,
                    metadata={"generated_by": "deadline_job"},
                )

                versions_in_job = case_in_job.get("appeal_letter_versions", []) + [escalation_version]
                case_in_job["appeal_letter_versions"] = versions_in_job
                case_in_job["current_appeal_letter_version_id"] = escalation_version["version_id"]
                follow_up["escalation_ready"] = True
                case_in_job["follow_up"] = follow_up
                case_in_job["status"] = "escalated"
                case_in_job["updated_at"] = datetime.utcnow().isoformat()
                case_in_job.setdefault("processing_steps", []).append(
                    {
                        "step": "escalation_deadline_reached",
                        "status": "completed",
                        "timestamp": datetime.utcnow().isoformat(),
                        "details": escalation_version["version_id"],
                    }
                )

                save_cases(cases_in_job)
            except Exception as exc:
                logger.error("Deadline escalation job failed for case %s: %s", case_id, exc)

        _FOLLOWUP_TIMERS[case_id] = Timer(seconds_until_deadline, _deadline_job)
        _FOLLOWUP_TIMERS[case_id].daemon = True
        _FOLLOWUP_TIMERS[case_id].start()
    except Exception as exc:
        logger.error("Failed to schedule deadline job for case %s: %s", case_id, exc)

    return {"message": "Letter marked as sent", "version_id": sent_version["version_id"]}


@app.post("/api/cases/{case_id}/insurer-response")
async def upload_insurer_response(case_id: str, file: UploadFile = File(...)):
    """Upload insurer response (Phase 5 follow-up).

    Creates a Round 2 appeal letter draft version and marks the case as `drafted`.
    """
    cases = load_cases()
    case = next((c for c in cases["cases"] if c["case_id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if case.get("follow_up", {}).get("round_1_response_received_at"):
        return {"message": "Insurer response already received for Round 1."}

    # Save response file alongside uploads.
    response_ext = Path(file.filename).suffix.lower() if file.filename else ".txt"
    if response_ext not in {".pdf", ".txt", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Unsupported file type for insurer response.")

    response_path = UPLOADS_DIR / f"{case_id}_insurer_response_{uuid.uuid4().hex}{response_ext}"
    content = await file.read()
    response_path.write_bytes(content)

    from pipeline.document_loader import extract_text

    try:
        insurer_response_text = extract_text(response_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to extract insurer response text: {exc}") from exc

    # Update follow-up state.
    case.setdefault("follow_up", {})
    case["follow_up"]["round_1_response_received_at"] = datetime.utcnow().isoformat()
    case["follow_up"]["round_1_response_file_path"] = str(response_path)
    case["follow_up"]["round_1_response_excerpt"] = insurer_response_text[:2000]

    # Create Round 2 draft letter version using prior risk report/fields.
    try:
        from schemas import ExtractedFields, RiskReport
        from pipeline.appeal_letter_builder import (
            build_round2_appeal_letter_draft,
            create_letter_version,
        )

        extracted_fields = ExtractedFields.model_validate(case["extracted_fields"])
        report = RiskReport.model_validate(case["risk_report"])

        round2_draft = build_round2_appeal_letter_draft(
            extracted_fields,
            report,
            insurer_response_text=insurer_response_text,
        )
        versions = case.get("appeal_letter_versions", [])
        round2_version = create_letter_version(
            case_id=case_id,
            round=2,
            status="draft",
            draft=round2_draft,
            metadata={"generated_from": {"insurer_response_uploaded": True}},
        )

        case["appeal_letter_versions"] = versions + [round2_version]
        case["current_appeal_letter_version_id"] = round2_version["version_id"]
        case["status"] = "drafted"
        case["updated_at"] = datetime.utcnow().isoformat()
        case.setdefault("processing_steps", []).append(
            {
                "step": "insurer_response_received",
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "details": round2_version["version_id"],
            }
        )
    except Exception as exc:
        logger.error("Failed to generate Round 2 draft for case %s: %s", case_id, exc)
        raise HTTPException(status_code=500, detail="Failed to generate Round 2 letter draft.") from exc

    save_cases(cases)
    return {"message": "Insurer response uploaded and Round 2 draft generated.", "version_id": case["current_appeal_letter_version_id"]}


@app.get("/api/cases")
async def list_cases(status: Optional[str] = None):
    """List all cases, optionally filtered by status."""
    cases = load_cases()
    
    if status:
        filtered = [c for c in cases["cases"] if c["status"] == status]
        return {"cases": filtered, "total": len(filtered)}
    
    return {"cases": cases["cases"], "total": len(cases["cases"])}


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    """Get detailed information about a specific case."""
    cases = load_cases()
    case = next((c for c in cases["cases"] if c["case_id"] == case_id), None)
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return case


@app.get("/api/cases/{case_id}/status")
async def get_case_status(case_id: str):
    """Get current processing status of a case (for polling)."""
    cases = load_cases()
    case = next((c for c in cases["cases"] if c["case_id"] == case_id), None)
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {
        "case_id": case_id,
        "status": case["status"],
        "updated_at": case["updated_at"],
        "processing_steps": case["processing_steps"]
    }


@app.delete("/api/cases/{case_id}")
async def delete_case(case_id: str):
    """Delete a case and its associated files."""
    cases = load_cases()
    case = next((c for c in cases["cases"] if c["case_id"] == case_id), None)
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Delete uploaded file
    file_path = Path(case["file_path"])
    if file_path.exists():
        file_path.unlink()
    
    # Remove from cases list
    cases["cases"] = [c for c in cases["cases"] if c["case_id"] != case_id]
    save_cases(cases)
    
    return {"message": "Case deleted successfully", "case_id": case_id}


@app.post("/api/cases/{case_id}/resolve")
async def resolve_case(case_id: str, payload: ResolveCaseRequest):
    """Mark a case as resolved (Phase 7)."""
    cases = load_cases()
    case = next((c for c in cases["cases"] if c["case_id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case["status"] = "resolved"
    case["updated_at"] = datetime.utcnow().isoformat()
    case["resolution"] = {
        "outcome": payload.outcome,
        "notes": payload.notes,
        "resolved_at": datetime.utcnow().isoformat(),
    }
    case.setdefault("processing_steps", []).append(
        {
            "step": "resolve_case",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": payload.outcome,
        }
    )
    save_cases(cases)
    return {"message": "Case resolved", "case_id": case_id, "outcome": payload.outcome}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
