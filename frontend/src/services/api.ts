import type {
  ContractType,
  Jurisdiction,
  StartAnalysisResponse,
  StatusResponse,
  ReportsResponse,
  FinalReport,
  HitlSubmitRequest,
  HitlSubmitResponse,
  AgentStep,
  SampleContractResponse,
} from "../types";

const BASE = "/api";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {}
    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}

export const api = {
  /** Start contract analysis */
  analyze(body: {
    contract_text: string;
    jurisdiction: Jurisdiction;
    contract_type: ContractType;
  }): Promise<StartAnalysisResponse> {
    return request("/contract/analyze", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  /** Poll analysis status */
  getStatus(sessionId: string): Promise<StatusResponse> {
    return request(`/contract/status/${sessionId}`);
  },

  /** Get ghost clause reports */
  getReports(sessionId: string): Promise<ReportsResponse> {
    return request(`/contract/reports/${sessionId}`);
  },

  /** Submit HITL verdict */
  submitHitl(sessionId: string, body: HitlSubmitRequest): Promise<HitlSubmitResponse> {
    return request(`/contract/hitl/${sessionId}`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  /** Get final report */
  getFinalReport(sessionId: string): Promise<FinalReport> {
    return request(`/contract/report/${sessionId}`);
  },

  /** Get agent chain log */
  getChain(sessionId: string): Promise<{ steps: AgentStep[] }> {
    return request(`/contract/chain/${sessionId}`);
  },

  /** Get sample contract */
  getSampleContract(): Promise<SampleContractResponse> {
    return request("/contract/sample");
  },
};
