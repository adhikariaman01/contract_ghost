// ─── API Types ────────────────────────────────────────────────────────────────

export type Jurisdiction = "California" | "New York" | "Texas" | "Federal" | "EU";
export type ContractType = "lease" | "employment" | "terms_of_service" | "nda" | "other";

export type ClauseType =
  | "termination"
  | "liability"
  | "non_compete"
  | "arbitration"
  | "warranty"
  | "indemnification"
  | "auto_renewal"
  | "habitability"
  | "payment"
  | "confidentiality"
  | "other";

export type GhostStatus = "clean" | "suspicious" | "ghost";
export type Severity = "info" | "warning" | "critical";
export type StepStatus = "pending" | "running" | "completed" | "failed" | "waiting_hitl";
export type UserVerdict = "confirmed_ghost" | "false_positive" | "unsure";
export type Enforceability = "enforceable" | "unenforceable" | "conditional" | "void";

export interface Clause {
  clause_id: string;
  clause_type: ClauseType;
  original_text: string;
  line_range: [number, number];
  summary: string;
}

export interface EnforceabilityRule {
  rule_id: string;
  jurisdiction: string;
  clause_type: string;
  rule_text: string;
  statute_reference: string | null;
  case_law_reference: string | null;
  enforceability: Enforceability;
}

export interface GhostClauseReport {
  clause_id: string;
  clause: Clause;
  matched_rule: EnforceabilityRule | null;
  ghost_status: GhostStatus;
  severity: Severity;
  explanation: string;
  suggested_revision: string | null;
  confidence_score: number;
}

export interface AgentStep {
  step_name: string;
  step_number: number;
  status: StepStatus;
  output_summary: string;
  timestamp: string;
}

export interface FinalReport {
  session_id: string;
  contract_type: string;
  jurisdiction: string;
  total_clauses: number;
  ghost_clauses: GhostClauseReport[];
  clean_clauses: GhostClauseReport[];
  summary: string;
  risk_score: number;
  status: "complete" | "needs_review";
  completed_at: string;
}

export interface StatusResponse {
  session_id: string;
  current_step: string;
  jurisdiction: string;
  contract_type: string;
  clauses_count: number;
  reports_count: number;
  hitl_queue: string[];
  error_message: string | null;
  has_final_report: boolean;
  chain_log: AgentStep[];
}

export interface StartAnalysisResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface HitlSubmitRequest {
  session_id: string;
  clause_id: string;
  user_verdict: UserVerdict;
  user_notes?: string;
  corrected_explanation?: string;
}

export interface HitlSubmitResponse {
  status: string;
  clause_id: string;
  verdict: UserVerdict;
  remaining_reviews: number;
  next_step: string;
}

export interface ReportsResponse {
  reports: GhostClauseReport[];
  hitl_queue: string[];
  pending_review_count: number;
}

export interface SampleContractResponse {
  contract_text: string;
  suggested_jurisdiction: Jurisdiction;
  suggested_contract_type: ContractType;
}
