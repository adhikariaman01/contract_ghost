from __future__ import annotations

import operator
from typing import Optional, Annotated, TypedDict

from app.models.schemas import (
    Clause,
    GhostClauseReport,
    HitlReviewInput,
    FinalReport,
    AgentStep,
)


class ContractState(TypedDict):
    """LangGraph state — single source of truth for the analysis pipeline."""
    session_id: str
    contract_text: str
    jurisdiction: str
    contract_type: str
    clauses: Annotated[list[Clause], operator.add]
    reports: Annotated[list[GhostClauseReport], operator.add]
    hitl_queue: list[str]           # clause_ids awaiting human review
    hitl_feedback: Optional[HitlReviewInput]
    final_report: Optional[FinalReport]
    current_step: str
    error_message: Optional[str]
    chain_log: Annotated[list[AgentStep], operator.add]
