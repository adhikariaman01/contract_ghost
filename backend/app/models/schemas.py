from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal, Annotated
from pydantic import BaseModel, Field, ConfigDict


# ─── Input Schemas ────────────────────────────────────────────────────────────

class ContractUploadInput(BaseModel):
    """User input: contract text and jurisdiction."""
    contract_text: str = Field(..., min_length=100, max_length=50000)
    jurisdiction: Literal["California", "New York", "Texas", "Federal", "EU"]
    contract_type: Literal["lease", "employment", "terms_of_service", "nda", "other"]

    model_config = ConfigDict(json_schema_extra={"example": {
        "contract_text": "LEASE AGREEMENT...",
        "jurisdiction": "California",
        "contract_type": "lease"
    }})


# ─── Core Domain Models ────────────────────────────────────────────────────────

class Clause(BaseModel):
    clause_id: str = Field(..., pattern=r"^C-\d+$")
    clause_type: Literal[
        "termination", "liability", "non_compete", "arbitration",
        "warranty", "indemnification", "auto_renewal", "habitability",
        "payment", "confidentiality", "other"
    ]
    original_text: str
    line_range: tuple[int, int]
    summary: str

    model_config = ConfigDict(from_attributes=True)


class EnforceabilityRule(BaseModel):
    rule_id: str
    jurisdiction: str
    clause_type: str
    rule_text: str
    statute_reference: Optional[str] = None
    case_law_reference: Optional[str] = None
    enforceability: Literal["enforceable", "unenforceable", "conditional", "void"]

    model_config = ConfigDict(from_attributes=True)


class GhostClauseReport(BaseModel):
    clause_id: str
    clause: Clause
    matched_rule: Optional[EnforceabilityRule] = None
    ghost_status: Literal["clean", "suspicious", "ghost"]
    severity: Literal["info", "warning", "critical"]
    explanation: str
    suggested_revision: Optional[str] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)

    model_config = ConfigDict(from_attributes=True)


# ─── HITL Schemas ─────────────────────────────────────────────────────────────

class HitlReviewInput(BaseModel):
    session_id: str
    clause_id: str
    user_verdict: Literal["confirmed_ghost", "false_positive", "unsure"]
    user_notes: Optional[str] = None
    corrected_explanation: Optional[str] = None


# ─── Output Schemas ───────────────────────────────────────────────────────────

class FinalReport(BaseModel):
    session_id: str
    contract_type: str
    jurisdiction: str
    total_clauses: int
    ghost_clauses: list[GhostClauseReport]
    clean_clauses: list[GhostClauseReport]
    summary: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    status: Literal["complete", "needs_review"]
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class AgentStep(BaseModel):
    step_name: str
    step_number: int
    status: Literal["pending", "running", "completed", "failed", "waiting_hitl"]
    output_summary: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class StartAnalysisResponse(BaseModel):
    session_id: str
    status: str
    message: str
