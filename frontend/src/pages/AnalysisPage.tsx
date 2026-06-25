import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api } from "../services/api";
import { usePolling } from "../hooks/usePolling";
import AgentChainVisualizer from "../components/AgentChainVisualizer";
import HitlReview from "../components/HitlReview";
import type { StatusResponse, GhostClauseReport, UserVerdict } from "../types";
import styles from "./AnalysisPage.module.css";

const TERMINAL_STEPS = new Set(["complete", "error"]);
const HITL_STEPS = new Set(["hitl_waiting", "hitl_reviewing"]);

export default function AnalysisPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [reports, setReports] = useState<GhostClauseReport[]>([]);
  const [hitlOpen, setHitlOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(true);

  const fetchStatus = useCallback(async () => {
    if (!sessionId) return;
    try {
      const s = await api.getStatus(sessionId);
      setStatus(s);

      if (s.error_message) {
        setError(s.error_message);
        setPolling(false);
        return;
      }

      // Load reports once evaluator finishes
      if (s.reports_count > 0) {
        const r = await api.getReports(sessionId);
        setReports(r.reports);

        // Open HITL modal if needed
        if (HITL_STEPS.has(s.current_step) && r.hitl_queue.length > 0) {
          setHitlOpen(true);
        }
      }

      // Navigate to report when done
      if (s.current_step === "complete") {
        setPolling(false);
        setTimeout(() => navigate(`/report/${sessionId}`), 1200);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch status");
      setPolling(false);
    }
  }, [sessionId, navigate]);

  usePolling(fetchStatus, 2000, polling);

  const handleHitlSubmit = useCallback(async (clauseId: string, verdict: UserVerdict, notes: string) => {
    if (!sessionId) return;
    const res = await api.submitHitl(sessionId, {
      session_id: sessionId,
      clause_id: clauseId,
      user_verdict: verdict,
      user_notes: notes || undefined,
    });

    if (res.remaining_reviews === 0) {
      setHitlOpen(false);
      setPolling(true); // Resume polling for finalizer
    }
  }, [sessionId]);

  const currentStep = status?.current_step ?? "extractor";
  const isTerminal = TERMINAL_STEPS.has(currentStep);

  const stepLabels: Record<string, string> = {
    extractor: "Extracting clauses...",
    evaluator: "Evaluating enforceability...",
    hitl_waiting: "Awaiting your review",
    hitl_reviewing: "Reviewing...",
    finalizing: "Assembling report...",
    finalizer: "Assembling report...",
    complete: "Analysis complete!",
    error: "Analysis failed",
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <button className={styles.backBtn} onClick={() => navigate("/")} type="button">
            <ArrowLeft size={15} />
            New analysis
          </button>
          <div className={styles.logo}>
            <span>👻</span>
            <span>Contract Ghost</span>
          </div>
          <div className={styles.sessionId}>
            Session: {sessionId?.slice(0, 8)}…
          </div>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.layout}>
          {/* Left: Chain */}
          <div className={styles.leftCol}>
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <h2 className={styles.cardTitle}>Agent Pipeline</h2>
                {!isTerminal && (
                  <span className={styles.liveBadge}>
                    <span className={styles.liveDot} />
                    Live
                  </span>
                )}
              </div>

              <div className={styles.currentLabel}>
                {stepLabels[currentStep] || "Processing..."}
              </div>

              <AgentChainVisualizer
                steps={status?.chain_log ?? []}
                currentStep={currentStep}
                hitlQueue={status?.hitl_queue ?? []}
              />
            </div>

            {/* Stats */}
            {status && (
              <div className={styles.statsRow}>
                <div className={styles.stat}>
                  <div className={styles.statNum}>{status.clauses_count}</div>
                  <div className={styles.statLabel}>Clauses extracted</div>
                </div>
                <div className={styles.stat}>
                  <div className={styles.statNum}>{status.reports_count}</div>
                  <div className={styles.statLabel}>Clauses evaluated</div>
                </div>
                <div className={styles.stat}>
                  <div className={styles.statNum}>{status.hitl_queue.length}</div>
                  <div className={styles.statLabel}>Pending review</div>
                </div>
              </div>
            )}
          </div>

          {/* Right: Summary / Info */}
          <div className={styles.rightCol}>
            {error ? (
              <div className={styles.errorCard}>
                <div className={styles.errorTitle}>Analysis Failed</div>
                <p className={styles.errorMsg}>{error}</p>
                <button className={styles.retryBtn} onClick={() => navigate("/")} type="button">
                  Start over
                </button>
              </div>
            ) : status?.current_step === "hitl_waiting" ? (
              <div className={styles.hitlPromptCard}>
                <div className={styles.hitlIcon}>🔍</div>
                <h3 className={styles.hitlTitle}>Your Review Needed</h3>
                <p className={styles.hitlDesc}>
                  The AI flagged <strong>{status.hitl_queue.length} clause{status.hitl_queue.length !== 1 ? "s" : ""}</strong> that
                  need human verification before the final report can be generated.
                </p>
                <button
                  className={styles.reviewBtn}
                  onClick={() => setHitlOpen(true)}
                  type="button"
                >
                  Start Review ({status.hitl_queue.length})
                </button>
              </div>
            ) : currentStep === "complete" ? (
              <div className={styles.completeCard}>
                <div className={styles.completeIcon}>✅</div>
                <h3 className={styles.completeTitle}>Analysis Complete</h3>
                <p className={styles.completeDesc}>Redirecting to your report...</p>
              </div>
            ) : (
              <div className={styles.waitCard}>
                <div className={styles.waitSpinner} />
                <h3 className={styles.waitTitle}>Analyzing your contract</h3>
                <p className={styles.waitDesc}>
                  The AI agents are working through your {status?.contract_type?.replace(/_/g, " ")} contract
                  under <strong>{status?.jurisdiction}</strong> law.
                  This typically takes 20–60 seconds.
                </p>
                <div className={styles.progressSteps}>
                  {["Extracting clauses", "Evaluating enforceability", "Generating explanations"].map((s, i) => (
                    <div key={s} className={styles.progressStep}>
                      <span className={
                        i === 0 && status?.clauses_count && status.clauses_count > 0 ? styles.stepDone :
                        i === 1 && status?.reports_count && status.reports_count > 0 ? styles.stepDone :
                        styles.stepPending
                      }>
                        {(i === 0 && status?.clauses_count && status.clauses_count > 0) ||
                         (i === 1 && status?.reports_count && status.reports_count > 0) ? "✓" : "○"}
                      </span>
                      {s}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* HITL Modal */}
      {hitlOpen && sessionId && reports.length > 0 && status && (
        <HitlReview
          reports={reports}
          hitlQueue={status.hitl_queue}
          sessionId={sessionId}
          onSubmit={handleHitlSubmit}
          onDismiss={() => setHitlOpen(false)}
        />
      )}
    </div>
  );
}
