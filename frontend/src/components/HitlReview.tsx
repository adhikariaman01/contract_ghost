import { useState } from "react";
import { CheckCircle, XCircle, HelpCircle, X } from "lucide-react";
import type { GhostClauseReport, UserVerdict } from "../types";
import styles from "./HitlReview.module.css";

interface Props {
  reports: GhostClauseReport[];
  hitlQueue: string[];
  sessionId: string;
  onSubmit: (clauseId: string, verdict: UserVerdict, notes: string) => Promise<void>;
  onDismiss: () => void;
}

export default function HitlReview({ reports, hitlQueue, sessionId, onSubmit, onDismiss }: Props) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [verdict, setVerdict] = useState<UserVerdict | null>(null);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const pendingReports = reports.filter(r => hitlQueue.includes(r.clause_id));
  const current = pendingReports[currentIndex];

  if (!current) return null;

  const totalPending = pendingReports.length;
  const progress = ((currentIndex) / totalPending) * 100;

  const handleSubmit = async () => {
    if (!verdict) return;
    setSubmitting(true);
    try {
      await onSubmit(current.clause_id, verdict, notes);
      if (currentIndex + 1 < totalPending) {
        setCurrentIndex(i => i + 1);
        setVerdict(null);
        setNotes("");
        setExpanded(false);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const severityLabel: Record<string, string> = {
    critical: "⚠️ Critical",
    warning: "⚡ Warning",
    info: "ℹ️ Info",
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        {/* Modal Header */}
        <div className={styles.modalHeader}>
          <div className={styles.modalHeaderLeft}>
            <span className={styles.modalTitle}>Review Flagged Clause</span>
            <span className={styles.modalProgress}>{currentIndex + 1} of {totalPending}</span>
          </div>
          <button className={styles.closeBtn} onClick={onDismiss} type="button">
            <X size={16} />
          </button>
        </div>

        {/* Progress bar */}
        <div className={styles.progressBar}>
          <div className={styles.progressFill} style={{ width: `${progress}%` }} />
        </div>

        {/* Content */}
        <div className={styles.content}>
          {/* Left: Original Clause */}
          <div className={styles.left}>
            <div className={styles.sectionLabel}>Original Clause</div>
            <div className={styles.clauseMeta}>
              <span className={`${styles.clauseTypeBadge}`}>{current.clause.clause_type.replace(/_/g, " ")}</span>
              {current.severity !== "info" && (
                <span className={`${styles.severityBadge} ${styles[`sev_${current.severity}`]}`}>
                  {severityLabel[current.severity]}
                </span>
              )}
              <span className={styles.lineRef}>Lines {current.clause.line_range[0]}–{current.clause.line_range[1]}</span>
            </div>
            <div className={styles.clauseText}>{current.clause.original_text}</div>
          </div>

          {/* Right: Analysis */}
          <div className={styles.right}>
            <div className={styles.sectionLabel}>AI Analysis</div>

            <div className={`${styles.ghostBadge} ${styles[`ghost_${current.ghost_status}`]}`}>
              {current.ghost_status === "ghost" && "🚫 Ghost Clause — Likely Unenforceable"}
              {current.ghost_status === "suspicious" && "⚠️ Suspicious — Review Recommended"}
              {current.ghost_status === "clean" && "✅ Appears Enforceable"}
            </div>

            <p className={styles.explanation}>{current.explanation}</p>

            {current.matched_rule && (
              <div className={styles.ruleBox}>
                <div className={styles.ruleTitle}>Matched Rule: {current.matched_rule.rule_id}</div>
                <p className={styles.ruleText}>{current.matched_rule.rule_text}</p>
                {current.matched_rule.statute_reference && (
                  <div className={styles.statute}>{current.matched_rule.statute_reference}</div>
                )}
              </div>
            )}

            {current.suggested_revision && (
              <div className={styles.revisionBox}>
                <div className={styles.revisionTitle}>Suggested Revision</div>
                <p className={styles.revisionText}>{current.suggested_revision}</p>
              </div>
            )}

            <div className={styles.confidence}>
              <span>AI confidence: </span>
              <div className={styles.confidenceBar}>
                <div
                  className={styles.confidenceFill}
                  style={{
                    width: `${current.confidence_score * 100}%`,
                    background: current.confidence_score < 0.5 ? "var(--accent-danger)" :
                      current.confidence_score < 0.75 ? "var(--accent-warning)" : "var(--accent-success)"
                  }}
                />
              </div>
              <span className={styles.confidenceNum}>{(current.confidence_score * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>

        {/* Verdict Buttons */}
        <div className={styles.verdictSection}>
          <div className={styles.verdictLabel}>Your verdict:</div>
          <div className={styles.verdictBtns}>
            <button
              className={`${styles.verdictBtn} ${styles.verdictGhost} ${verdict === "confirmed_ghost" ? styles.verdictSelected : ""}`}
              onClick={() => setVerdict("confirmed_ghost")}
              type="button"
            >
              <XCircle size={16} />
              Confirmed Ghost
            </button>
            <button
              className={`${styles.verdictBtn} ${styles.verdictClean} ${verdict === "false_positive" ? styles.verdictSelected : ""}`}
              onClick={() => setVerdict("false_positive")}
              type="button"
            >
              <CheckCircle size={16} />
              False Positive
            </button>
            <button
              className={`${styles.verdictBtn} ${styles.verdictUnsure} ${verdict === "unsure" ? styles.verdictSelected : ""}`}
              onClick={() => setVerdict("unsure")}
              type="button"
            >
              <HelpCircle size={16} />
              Unsure
            </button>
          </div>

          <textarea
            className={styles.notesField}
            placeholder="Add notes (optional)..."
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={2}
          />

          <button
            className={styles.submitBtn}
            onClick={handleSubmit}
            disabled={!verdict || submitting}
            type="button"
          >
            {submitting ? (
              <><span className={styles.spinner} /> Submitting...</>
            ) : currentIndex + 1 < totalPending ? (
              "Submit & Review Next →"
            ) : (
              "Submit & Finalize Report"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
