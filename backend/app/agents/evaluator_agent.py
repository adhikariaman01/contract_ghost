"""Evaluator Agent: checks each clause against jurisdiction enforceability rules."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from app.models.schemas import Clause, GhostClauseReport, EnforceabilityRule, AgentStep
from app.models.state import ContractState
from app.services.vector_store import retrieve_rules

logger = logging.getLogger(__name__)

EVALUATION_PROMPT = """You are a contract law analyst specializing in identifying unenforceable clauses.

Analyze the following contract clause against the jurisdiction's enforceability rules provided.

CONTRACT CLAUSE:
Type: {clause_type}
Text: {clause_text}
Summary: {clause_summary}

JURISDICTION: {jurisdiction}

RELEVANT ENFORCEABILITY RULES:
{rules_text}

Evaluate this clause and return ONLY valid JSON (no markdown, no preamble) with this structure:
{{
  "ghost_status": "clean" | "suspicious" | "ghost",
  "severity": "info" | "warning" | "critical",
  "explanation": "Plain-language explanation of why this clause is or isn't enforceable. Be specific about what makes it problematic.",
  "suggested_revision": "A concrete suggested revision if the clause is a ghost or suspicious, otherwise null",
  "confidence_score": 0.0 to 1.0,
  "matched_rule_id": "The rule_id of the most applicable rule, or null if no rule applies"
}}

Rules:
- "ghost" = clearly unenforceable based on the rules
- "suspicious" = potentially unenforceable but context-dependent
- "clean" = appears enforceable in this jurisdiction
- confidence_score < 0.7 means the human should review this
- severity "critical" = likely void and could expose parties to liability"""


def run_evaluator_agent(state: ContractState, llm) -> dict:
    """Evaluate all extracted clauses for enforceability."""
    logger.info("[Evaluator] Evaluating %d clauses for session %s",
                len(state["clauses"]), state["session_id"])

    step_start = AgentStep(
        step_name="Evaluator Agent",
        step_number=2,
        status="running",
        output_summary=f"Checking {len(state['clauses'])} clauses against {state['jurisdiction']} law...",
        timestamp=datetime.utcnow(),
    )

    reports: list[GhostClauseReport] = []
    hitl_queue: list[str] = []

    for clause in state["clauses"]:
        try:
            report = _evaluate_clause(clause, state["jurisdiction"], llm)
            reports.append(report)

            # Queue for human review if confidence low or severity critical
            if report.confidence_score < 0.7 or report.severity == "critical":
                hitl_queue.append(clause.clause_id)

        except Exception as exc:
            logger.error("[Evaluator] Failed to evaluate clause %s: %s", clause.clause_id, exc)
            # Add a low-confidence report
            reports.append(GhostClauseReport(
                clause_id=clause.clause_id,
                clause=clause,
                ghost_status="suspicious",
                severity="warning",
                explanation=f"Evaluation error — manual review recommended. Error: {exc}",
                suggested_revision=None,
                confidence_score=0.5,
            ))
            hitl_queue.append(clause.clause_id)

    ghost_count = sum(1 for r in reports if r.ghost_status == "ghost")
    suspicious_count = sum(1 for r in reports if r.ghost_status == "suspicious")

    step_done = AgentStep(
        step_name="Evaluator Agent",
        step_number=2,
        status="completed" if not hitl_queue else "waiting_hitl",
        output_summary=(
            f"Found {ghost_count} ghost clause(s), {suspicious_count} suspicious. "
            f"{len(hitl_queue)} flagged for human review."
        ),
        timestamp=datetime.utcnow(),
    )

    next_step = "hitl" if hitl_queue else "finalizer"

    logger.info("[Evaluator] Complete. %d reports, %d in HITL queue", len(reports), len(hitl_queue))

    return {
        "reports": reports,
        "hitl_queue": hitl_queue,
        "current_step": next_step,
        "chain_log": [step_start, step_done],
    }


def _evaluate_clause(clause: Clause, jurisdiction: str, llm) -> GhostClauseReport:
    """Evaluate a single clause."""
    # Retrieve relevant rules from vector store
    relevant_rules = retrieve_rules(
        jurisdiction=jurisdiction,
        clause_type=clause.clause_type,
        clause_text=clause.original_text,
        k=3,
    )

    rules_text = _format_rules(relevant_rules)

    prompt = EVALUATION_PROMPT.format(
        clause_type=clause.clause_type,
        clause_text=clause.original_text[:2000],
        clause_summary=clause.summary,
        jurisdiction=jurisdiction,
        rules_text=rules_text,
    )

    response = llm.invoke(prompt)
    raw_text = response.content if hasattr(response, "content") else str(response)
    raw_text = re.sub(r"```(?:json)?", "", raw_text).strip()

    data = json.loads(raw_text)

    # Find matched rule
    matched_rule = None
    matched_rule_id = data.get("matched_rule_id")
    if matched_rule_id and relevant_rules:
        for rule in relevant_rules:
            if rule.rule_id == matched_rule_id:
                matched_rule = rule
                break
        if not matched_rule:
            matched_rule = relevant_rules[0] if relevant_rules else None

    return GhostClauseReport(
        clause_id=clause.clause_id,
        clause=clause,
        matched_rule=matched_rule,
        ghost_status=data.get("ghost_status", "suspicious"),
        severity=data.get("severity", "warning"),
        explanation=data.get("explanation", "No explanation provided."),
        suggested_revision=data.get("suggested_revision"),
        confidence_score=float(data.get("confidence_score", 0.6)),
    )


def _format_rules(rules: list[EnforceabilityRule]) -> str:
    if not rules:
        return "No specific rules found for this jurisdiction and clause type."

    parts = []
    for rule in rules:
        part = f"[{rule.rule_id}] {rule.enforceability.upper()}: {rule.rule_text}"
        if rule.statute_reference:
            part += f" (Statute: {rule.statute_reference})"
        parts.append(part)

    return "\n".join(parts)
