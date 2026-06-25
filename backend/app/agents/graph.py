"""LangGraph state machine orchestrating the contract analysis pipeline."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from app.agents.extractor_agent import run_extractor_agent
from app.agents.evaluator_agent import run_evaluator_agent
from app.agents.finalizer import run_finalizer
from app.config import get_settings
from app.models.schemas import HitlReviewInput, AgentStep, GhostClauseReport
from app.models.state import ContractState
from app.services.session_store import save_state, get_state

logger = logging.getLogger(__name__)


def _get_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.1,
    )


# ─── Node Functions ────────────────────────────────────────────────────────────

def extractor_node(state: ContractState) -> dict:
    llm = _get_llm()
    return run_extractor_agent(state, llm)


def evaluator_node(state: ContractState) -> dict:
    llm = _get_llm()
    return run_evaluator_agent(state, llm)


def finalizer_node(state: ContractState) -> dict:
    llm = _get_llm()
    return run_finalizer(state, llm)


def hitl_node(state: ContractState) -> dict:
    """HITL pause node — does nothing; the API layer resumes it."""
    step = AgentStep(
        step_name="Human Review",
        step_number=3,
        status="waiting_hitl",
        output_summary=f"{len(state.get('hitl_queue', []))} clause(s) awaiting your review.",
        timestamp=datetime.utcnow(),
    )
    return {"current_step": "hitl_waiting", "chain_log": [step]}


# ─── Conditional Edges ─────────────────────────────────────────────────────────

def route_after_evaluation(state: ContractState) -> str:
    if state.get("current_step") == "error":
        return "error_end"
    if state.get("hitl_queue"):
        return "hitl"
    return "finalizer"


def route_after_hitl(state: ContractState) -> str:
    """Check if all HITL items resolved."""
    remaining = state.get("hitl_queue", [])
    if not remaining:
        return "finalizer"
    return "hitl"


# ─── Graph Builder ─────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(ContractState)

    builder.add_node("extractor", extractor_node)
    builder.add_node("evaluator", evaluator_node)
    builder.add_node("hitl", hitl_node)
    builder.add_node("finalizer", finalizer_node)

    builder.set_entry_point("extractor")
    builder.add_edge("extractor", "evaluator")

    builder.add_conditional_edges(
        "evaluator",
        route_after_evaluation,
        {
            "hitl": "hitl",
            "finalizer": "finalizer",
            "error_end": END,
        },
    )

    builder.add_conditional_edges(
        "hitl",
        route_after_hitl,
        {
            "finalizer": "finalizer",
            "hitl": "hitl",
        },
    )

    builder.add_edge("finalizer", END)

    return builder.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ─── Public API ────────────────────────────────────────────────────────────────

def start_analysis(
    contract_text: str,
    jurisdiction: str,
    contract_type: str,
) -> str:
    """Kick off analysis pipeline; returns session_id."""
    session_id = str(uuid.uuid4())

    initial_state: ContractState = {
        "session_id": session_id,
        "contract_text": contract_text,
        "jurisdiction": jurisdiction,
        "contract_type": contract_type,
        "clauses": [],
        "reports": [],
        "hitl_queue": [],
        "hitl_feedback": None,
        "final_report": None,
        "current_step": "extractor",
        "error_message": None,
        "chain_log": [],
    }

    save_state(session_id, initial_state)

    # Run in background thread
    import threading
    def _run():
        try:
            graph = get_graph()
            result = graph.invoke(initial_state)
            save_state(session_id, result)
            logger.info("Pipeline complete for session %s", session_id)
        except Exception as exc:
            logger.error("Pipeline error for session %s: %s", session_id, exc)
            state = get_state(session_id) or initial_state
            state["current_step"] = "error"
            state["error_message"] = str(exc)
            save_state(session_id, state)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return session_id


def submit_hitl_feedback(session_id: str, feedback: HitlReviewInput) -> bool:
    """Apply HITL feedback and continue pipeline if queue is empty."""
    state = get_state(session_id)
    if not state:
        return False

    # Update the report with user verdict
    reports: list[GhostClauseReport] = state.get("reports", [])
    for i, report in enumerate(reports):
        if report.clause_id == feedback.clause_id:
            if feedback.user_verdict == "false_positive":
                reports[i] = GhostClauseReport(
                    **{**report.model_dump(),
                       "ghost_status": "clean",
                       "severity": "info",
                       "explanation": f"[Reviewed by human] {feedback.user_notes or 'Marked as false positive.'}",
                       "confidence_score": 1.0}
                )
            elif feedback.user_verdict == "confirmed_ghost":
                reports[i] = GhostClauseReport(
                    **{**report.model_dump(),
                       "confidence_score": 1.0,
                       "explanation": f"{report.explanation} [Human confirmed: {feedback.user_notes or 'Ghost confirmed.'}]"}
                )
            break

    # Remove from hitl_queue
    hitl_queue = [c for c in state.get("hitl_queue", []) if c != feedback.clause_id]

    state["reports"] = reports
    state["hitl_queue"] = hitl_queue
    state["hitl_feedback"] = feedback
    state["current_step"] = "hitl_reviewing" if hitl_queue else "finalizing"

    save_state(session_id, state)

    # If queue empty, run finalizer
    if not hitl_queue:
        import threading
        def _finalize():
            try:
                llm = _get_llm()
                result = run_finalizer(state, llm)
                state.update(result)
                save_state(session_id, state)
            except Exception as exc:
                logger.error("Finalizer error: %s", exc)

        t = threading.Thread(target=_finalize, daemon=True)
        t.start()

    return True
