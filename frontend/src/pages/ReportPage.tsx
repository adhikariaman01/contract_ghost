import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronDown, ChevronUp, AlertTriangle, CheckCircle, XCircle, FileText } from "lucide-react";
import { api } from "../services/api";
import type { FinalReport, GhostClauseReport } from "../types";
import styles from "./ReportPage.module.css";

type Tab = "all" | "ghost" | "clean";

export default function ReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<FinalReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("ghost");
  const [expandedClauses, setExpandedClauses] = useState<Set<string>>(new Set());

  const fetchReport = useCallback(async () => {
    if (!sessionId) return;
    try {
      const r = await api.getFinalReport(sessionId);
      setReport(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report not ready yet.");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => { fetchReport(); }, [fetchReport]);

  const toggleClause = (id: string) => {
    setExpandedClauses(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  if (loading) {
    return (
      <div className={styles.loadingPage}>
        <div className={styles.loadingSpinner} />
        <p>Loading report...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className={styles.loadingPage}>
        <div className={styles.errorBox}>
          <p>{error || "Report not found."}</p>
          <button onClick={() => navigate("/")} className={styles.homeBtn} type="button">Go Home</button>
        </div>
      </div>
    );
  }

  const ghostClauses = report.ghost_clauses;
  const cleanClauses = report.clean_clauses;

  const tabClauses: Record<Tab, GhostClauseReport[]> = {
    all: [...ghostClauses, ...cleanClauses],
    ghost: ghostClauses,
    clean: cleanClauses,
  };

  const visibleClauses = tabClauses[activeTab].sort((a, b) => {
    const sevOrder = { critical: 0, warning: 1, info: 2 };
    return (sevOrder[a.severity] ?? 3) - (sevOrder[b.severity] ?? 3);
  });

  const riskColor =
    report.risk_score >= 60 ? "var(--accent-danger)" :
    report.risk_score >= 30 ? "var(--accent-warning)" :
    "var(--accent-success)";

  const riskLabel =
    report.risk_score >= 60 ? "High Risk" :
    report.risk_score >= 30 ? "Medium Risk" :
    "Low Risk";

  const circumference = 2 * Math.PI * 40; // r=40
  const dashOffset = circumference - (report.risk_score / 100) * circumference;

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <button className={styles.backBtn} onClick={() => navigate("/")} type="button">
            <ArrowLeft size={15} />
            New analysis
          </button>
          <div className={styles.logo}><span>👻</span><span>Contract Ghost</span></div>
          <div className={styles.sessionId}>Session: {sessionId?.slice(0, 8)}…</div>
        </div>
      </header>

      <main className={styles.main}>
        {/* ─── Summary Row ─── */}
        <section className={styles.summaryRow}>
          {/* Risk Score */}
          <div className={styles.riskCard}>
            <div className={styles.riskTitle}>Risk Score</div>
            <div className={styles.riskCircleWrap}>
              <svg width="100" height="100" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="none" stroke="var(--bg-secondary)" strokeWidth="8" />
                <circle
                  cx="50" cy="50" r="40" fill="none"
                  stroke={riskColor}
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={dashOffset}
                  transform="rotate(-90 50 50)"
                  style={{ transition: "stroke-dashoffset 1s ease" }}
                />
              </svg>
              <div className={styles.riskNumber} style={{ color: riskColor }}>
                {Math.round(report.risk_score)}
              </div>
            </div>
            <div className={styles.riskLabel} style={{ color: riskColor }}>{riskLabel}</div>
          </div>

          {/* Summary text */}
          <div className={styles.summaryCard}>
            <div className={styles.summaryMeta}>
              <span className={styles.metaPill}>{report.jurisdiction}</span>
              <span className={styles.metaPill}>{report.contract_type.replace(/_/g, " ")}</span>
              <span className={styles.metaPill}>{report.total_clauses} clauses</span>
            </div>
            <p className={styles.summaryText}>{report.summary}</p>
          </div>

          {/* Quick stats */}
          <div className={styles.quickStats}>
            <div className={styles.qStat}>
              <div className={styles.qNum} style={{ color: "var(--accent-danger)" }}>
                {ghostClauses.filter(r => r.ghost_status === "ghost").length}
              </div>
              <div className={styles.qLabel}>Ghost clauses</div>
            </div>
            <div className={styles.qDivider} />
            <div className={styles.qStat}>
              <div className={styles.qNum} style={{ color: "var(--accent-warning)" }}>
                {ghostClauses.filter(r => r.ghost_status === "suspicious").length}
              </div>
              <div className={styles.qLabel}>Suspicious</div>
            </div>
            <div className={styles.qDivider} />
            <div className={styles.qStat}>
              <div className={styles.qNum} style={{ color: "var(--accent-success)" }}>
                {cleanClauses.length}
              </div>
              <div className={styles.qLabel}>Clean</div>
            </div>
          </div>
        </section>

        {/* ─── Clause List ─── */}
        <section className={styles.clauseSection}>
          <div className={styles.tabBar}>
            <button
              className={`${styles.tab} ${activeTab === "ghost" ? styles.tabActive : ""}`}
              onClick={() => setActiveTab("ghost")}
              type="button"
            >
              <XCircle size={14} />
              Flagged ({ghostClauses.length})
            </button>
            <button
              className={`${styles.tab} ${activeTab === "clean" ? styles.tabActive : ""}`}
              onClick={() => setActiveTab("clean")}
              type="button"
            >
              <CheckCircle size={14} />
              Clean ({cleanClauses.length})
            </button>
            <button
              className={`${styles.tab} ${activeTab === "all" ? styles.tabActive : ""}`}
              onClick={() => setActiveTab("all")}
              type="button"
            >
              <FileText size={14} />
              All ({report.total_clauses})
            </button>
          </div>

          <div className={styles.clauseList}>
            {visibleClauses.length === 0 ? (
              <div className={styles.emptyState}>
                {activeTab === "ghost"
                  ? "No flagged clauses found — this contract looks clean."
                  : activeTab === "clean"
                  ? "No clean clauses in this view."
                  : "No clauses found."}
              </div>
            ) : (
              visibleClauses.map(report => (
                <ClauseCard
                  key={report.clause_id}
                  report={report}
                  expanded={expandedClauses.has(report.clause_id)}
                  onToggle={() => toggleClause(report.clause_id)}
                />
              ))
            )}
          </div>
        </section>

        {/* ─── Actions ─── */}
        <section className={styles.actions}>
          <button className={styles.newBtn} onClick={() => navigate("/")} type="button">
            Analyze another contract
          </button>
          <button
            className={styles.printBtn}
            onClick={() => window.print()}
            type="button"
          >
            Print report
          </button>
        </section>

        <p className={styles.disclaimer}>
          ⚠ This analysis is for informational purposes only and does not constitute legal advice.
          Consult a qualified attorney before relying on these findings.
        </p>
      </main>
    </div>
  );
}

// ─── ClauseCard ────────────────────────────────────────────────────────────────

function ClauseCard({
  report,
  expanded,
  onToggle,
}: {
  report: GhostClauseReport;
  expanded: boolean;
  onToggle: () => void;
}) {
  const isGhost = report.ghost_status === "ghost";
  const isSuspicious = report.ghost_status === "suspicious";
  const isClean = report.ghost_status === "clean";

  const borderColor = isGhost ? "var(--border-ghost)" : isSuspicious ? "var(--border-suspicious)" : "var(--border-clean)";
  const iconEl = isGhost ? <XCircle size={15} /> : isSuspicious ? <AlertTriangle size={15} /> : <CheckCircle size={15} />;

  const statusLabel = isGhost ? "Ghost" : isSuspicious ? "Suspicious" : "Clean";
  const statusClass = isGhost ? styles.statusGhost : isSuspicious ? styles.statusSuspicious : styles.statusClean;

  const severityClass = report.severity === "critical" ? styles.sevCritical :
    report.severity === "warning" ? styles.sevWarning : styles.sevInfo;

  return (
    <div className={styles.clauseCard} style={{ borderLeftColor: borderColor }}>
      {/* Card header row */}
      <button className={styles.clauseHeader} onClick={onToggle} type="button">
        <div className={styles.clauseHeaderLeft}>
          <span className={`${styles.clauseStatus} ${statusClass}`}>
            {iconEl}
            {statusLabel}
          </span>
          <span className={styles.clauseType}>
            {report.clause.clause_type.replace(/_/g, " ")}
          </span>
          <span className={styles.clauseId}>{report.clause_id}</span>
          {report.severity !== "info" && (
            <span className={`${styles.sevBadge} ${severityClass}`}>{report.severity}</span>
          )}
        </div>
        <div className={styles.clauseHeaderRight}>
          <span className={styles.confidencePct}>
            {(report.confidence_score * 100).toFixed(0)}% confidence
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {/* Clause summary (always visible) */}
      <div className={styles.clauseSummary}>{report.clause.summary}</div>

      {/* Expanded details */}
      {expanded && (
        <div className={styles.clauseDetails}>
          <div className={styles.detailGrid}>
            {/* Original text */}
            <div className={styles.detailSection}>
              <div className={styles.detailLabel}>Original Text</div>
              <div className={styles.clauseText}>{report.clause.original_text}</div>
            </div>

            {/* Analysis */}
            <div className={styles.detailSection}>
              <div className={styles.detailLabel}>Analysis</div>
              <p className={styles.explanationText}>{report.explanation}</p>

              {report.matched_rule && (
                <div className={styles.ruleBox}>
                  <div className={styles.ruleId}>{report.matched_rule.rule_id}</div>
                  <p className={styles.ruleText}>{report.matched_rule.rule_text}</p>
                  {report.matched_rule.statute_reference && (
                    <div className={styles.statute}>{report.matched_rule.statute_reference}</div>
                  )}
                  {report.matched_rule.case_law_reference && (
                    <div className={styles.caseRef}>{report.matched_rule.case_law_reference}</div>
                  )}
                </div>
              )}

              {report.suggested_revision && (
                <div className={styles.revisionBox}>
                  <div className={styles.revisionLabel}>Suggested Revision</div>
                  <p className={styles.revisionText}>{report.suggested_revision}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
