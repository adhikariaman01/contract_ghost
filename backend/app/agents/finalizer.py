"""Finalizer: assembles the FinalReport from all agent outputs."""
from __future__ import annotations

import logging
from datetime import datetime

from app.models.schemas import FinalReport, GhostClauseReport, AgentStep
from app.models.state import ContractState

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """You are a legal document analyst. Write a concise 2-3 sentence executive summary of the following contract analysis results.

Contract type: {contract_type}
Jurisdiction: {jurisdiction}
Total clauses: {total_clauses}
Ghost clauses (unenforceable): {ghost_count}
Suspicious clauses (potentially unenforceable): {suspicious_count}
Risk score: {risk_score:.0f}/100

Ghost clause details:
{ghost_details}

Write a plain-language summary for a non-lawyer. Be direct about the risks. Return only the summary text, no headers."""


def run_finalizer(state: ContractState, llm) -> dict:
    """Assemble the final report from all agent outputs."""
    logger.info("[Finalizer] Assembling report for session %s", state["session_id"])

    reports: list[GhostClauseReport] = state.get("reports", [])

    ghost_clauses = [r for r in reports if r.ghost_status == "ghost"]
    suspicious_clauses = [r for r in reports if r.ghost_status == "suspicious"]
    clean_clauses = [r for r in reports if r.ghost_status == "clean"]

    # Risk score calculation
    risk_score = _calculate_risk_score(reports)

    # Generate summary
    try:
        ghost_details = "\n".join([
            f"- {r.clause.clause_type} (Clause {r.clause_id}): {r.explanation[:150]}..."
            for r in ghost_clauses + suspicious_clauses
        ]) or "None found."

        prompt = SUMMARY_PROMPT.format(
            contract_type=state["contract_type"],
            jurisdiction=state["jurisdiction"],
            total_clauses=len(reports),
            ghost_count=len(ghost_clauses),
            suspicious_count=len(suspicious_clauses),
            risk_score=risk_score,
            ghost_details=ghost_details,
        )
        response = llm.invoke(prompt)
        summary = response.content if hasattr(response, "content") else str(response)
        summary = summary.strip()
    except Exception as exc:
        logger.error("[Finalizer] Summary generation failed: %s", exc)
        summary = (
            f"Analysis complete. Found {len(ghost_clauses)} potentially unenforceable clauses "
            f"and {len(suspicious_clauses)} clauses requiring further review "
            f"in this {state['jurisdiction']} {state['contract_type']} contract."
        )

    final_report = FinalReport(
        session_id=state["session_id"],
        contract_type=state["contract_type"],
        jurisdiction=state["jurisdiction"],
        total_clauses=len(reports),
        ghost_clauses=ghost_clauses + suspicious_clauses,
        clean_clauses=clean_clauses,
        summary=summary,
        risk_score=risk_score,
        status="complete",
        completed_at=datetime.utcnow(),
    )

    step_done = AgentStep(
        step_name="Finalizer",
        step_number=3,
        status="completed",
        output_summary=f"Report ready. Risk score: {risk_score:.0f}/100.",
        timestamp=datetime.utcnow(),
    )

    logger.info("[Finalizer] Report assembled. Risk score: %.1f", risk_score)

    return {
        "final_report": final_report,
        "current_step": "complete",
        "chain_log": [step_done],
    }


def _calculate_risk_score(reports: list[GhostClauseReport]) -> float:
    """Calculate overall risk score 0-100."""
    if not reports:
        return 0.0

    score = 0.0
    weights = {"critical": 20.0, "warning": 10.0, "info": 3.0}
    ghost_mult = {"ghost": 1.0, "suspicious": 0.5, "clean": 0.0}

    for r in reports:
        base = weights.get(r.severity, 5.0)
        mult = ghost_mult.get(r.ghost_status, 0.0)
        score += base * mult

    return min(score, 100.0)
