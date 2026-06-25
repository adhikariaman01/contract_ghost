"""Contract analysis API endpoints."""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.agents.graph import start_analysis, submit_hitl_feedback
from app.models.schemas import (
    ContractUploadInput,
    HitlReviewInput,
    StartAnalysisResponse,
    AgentStep,
    FinalReport,
)
from app.services.session_store import get_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contract", tags=["contract"])


@router.post("/analyze", response_model=StartAnalysisResponse)
async def analyze_contract(body: ContractUploadInput):
    """Start contract analysis pipeline. Returns session_id for polling."""
    try:
        session_id = start_analysis(
            contract_text=body.contract_text,
            jurisdiction=body.jurisdiction,
            contract_type=body.contract_type,
        )
        return StartAnalysisResponse(
            session_id=session_id,
            status="started",
            message="Analysis pipeline started. Poll /contract/status/{session_id} for updates.",
        )
    except Exception as exc:
        logger.error("Failed to start analysis: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status/{session_id}")
async def get_status(session_id: str):
    """Poll for current analysis state."""
    state = get_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Serialize carefully — exclude large contract_text
    return {
        "session_id": state["session_id"],
        "current_step": state["current_step"],
        "jurisdiction": state["jurisdiction"],
        "contract_type": state["contract_type"],
        "clauses_count": len(state.get("clauses", [])),
        "reports_count": len(state.get("reports", [])),
        "hitl_queue": state.get("hitl_queue", []),
        "error_message": state.get("error_message"),
        "has_final_report": state.get("final_report") is not None,
        "chain_log": [step.model_dump() for step in state.get("chain_log", [])],
    }


@router.get("/clauses/{session_id}")
async def get_clauses(session_id: str):
    """Get extracted clauses."""
    state = get_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    clauses = state.get("clauses", [])
    return {"clauses": [c.model_dump() for c in clauses]}


@router.get("/reports/{session_id}")
async def get_reports(session_id: str):
    """Get ghost clause reports (available after evaluation)."""
    state = get_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    reports = state.get("reports", [])
    hitl_queue = state.get("hitl_queue", [])

    return {
        "reports": [r.model_dump() for r in reports],
        "hitl_queue": hitl_queue,
        "pending_review_count": len(hitl_queue),
    }


@router.post("/hitl/{session_id}", response_model=dict)
async def submit_hitl(session_id: str, body: HitlReviewInput):
    """Submit human review verdict for a flagged clause."""
    if body.session_id != session_id:
        raise HTTPException(status_code=400, detail="session_id mismatch")

    state = get_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.clause_id not in state.get("hitl_queue", []):
        raise HTTPException(
            status_code=400,
            detail=f"Clause {body.clause_id} is not in the review queue"
        )

    success = submit_hitl_feedback(session_id, body)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to apply feedback")

    updated_state = get_state(session_id)
    remaining = len(updated_state.get("hitl_queue", []))

    return {
        "status": "accepted",
        "clause_id": body.clause_id,
        "verdict": body.user_verdict,
        "remaining_reviews": remaining,
        "next_step": "finalizing" if remaining == 0 else "hitl",
    }


@router.get("/report/{session_id}")
async def get_final_report(session_id: str):
    """Get final report (available after pipeline completes)."""
    state = get_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    final_report = state.get("final_report")
    if not final_report:
        current = state.get("current_step", "unknown")
        raise HTTPException(
            status_code=202,
            detail=f"Report not ready yet. Current step: {current}"
        )

    return final_report.model_dump()


@router.get("/chain/{session_id}")
async def get_chain(session_id: str):
    """Get full agent chain log."""
    state = get_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    chain = state.get("chain_log", [])
    return {"steps": [s.model_dump() for s in chain]}


@router.get("/sample")
async def get_sample_contract():
    """Return a sample contract for demo purposes."""
    from pathlib import Path
    sample_path = Path(__file__).parent.parent / "data" / "sample_contracts" / "sample_lease_ca.txt"

    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample contract not found")

    return {
        "contract_text": sample_path.read_text(encoding="utf-8"),
        "suggested_jurisdiction": "California",
        "suggested_contract_type": "lease",
    }
