import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Zap, Shield, Search, ChevronDown } from "lucide-react";
import { api } from "../services/api";
import type { ContractType, Jurisdiction } from "../types";
import styles from "./Home.module.css";

const JURISDICTIONS: Jurisdiction[] = ["California", "New York", "Texas", "Federal", "EU"];
const CONTRACT_TYPES: { value: ContractType; label: string }[] = [
  { value: "lease", label: "Lease Agreement" },
  { value: "employment", label: "Employment Contract" },
  { value: "terms_of_service", label: "Terms of Service" },
  { value: "nda", label: "Non-Disclosure Agreement" },
  { value: "other", label: "Other Contract" },
];

export default function Home() {
  const navigate = useNavigate();
  const [contractText, setContractText] = useState("");
  const [jurisdiction, setJurisdiction] = useState<Jurisdiction>("California");
  const [contractType, setContractType] = useState<ContractType>("lease");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSample = useCallback(async () => {
    try {
      const sample = await api.getSampleContract();
      setContractText(sample.contract_text);
      setJurisdiction(sample.suggested_jurisdiction);
      setContractType(sample.suggested_contract_type);
    } catch {
      setError("Could not load sample contract — is the backend running?");
    }
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!contractText.trim() || contractText.length < 100) {
      setError("Please paste at least 100 characters of contract text.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await api.analyze({ contract_text: contractText, jurisdiction, contract_type: contractType });
      navigate(`/analyze/${res.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed. Is the backend running?");
      setLoading(false);
    }
  }, [contractText, jurisdiction, contractType, navigate]);

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.logo}>
            <span className={styles.logoIcon}>👻</span>
            <span className={styles.logoText}>Contract Ghost</span>
          </div>
          <p className={styles.tagline}>AI-powered ghost clause detection</p>
        </div>
      </header>

      <main className={styles.main}>
        {/* Hero */}
        <section className={styles.hero}>
          <h1 className={styles.heroTitle}>
            Find the clauses that<br />
            <span className={styles.heroAccent}>exist but can't enforce</span>
          </h1>
          <p className={styles.heroSub}>
            Multi-agent legal analysis that scans contracts for ghost clauses — provisions
            that are legally present but void, unenforceable, or contradictory in your jurisdiction.
          </p>
          <div className={styles.featurePills}>
            <span className={styles.pill}><Shield size={13} /> Jurisdiction-aware</span>
            <span className={styles.pill}><Zap size={13} /> AI-powered</span>
            <span className={styles.pill}><Search size={13} /> Plain-language explanations</span>
          </div>
        </section>

        {/* Upload Card */}
        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <FileText size={18} className={styles.cardIcon} />
            <h2 className={styles.cardTitle}>Analyze a Contract</h2>
            <button className={styles.sampleBtn} onClick={loadSample} type="button">
              Load sample
            </button>
          </div>

          <div className={styles.selects}>
            <label className={styles.selectWrap}>
              <span className={styles.label}>Jurisdiction</span>
              <div className={styles.selectInner}>
                <select
                  value={jurisdiction}
                  onChange={e => setJurisdiction(e.target.value as Jurisdiction)}
                  className={styles.select}
                >
                  {JURISDICTIONS.map(j => (
                    <option key={j} value={j}>{j}</option>
                  ))}
                </select>
                <ChevronDown size={14} className={styles.chevron} />
              </div>
            </label>

            <label className={styles.selectWrap}>
              <span className={styles.label}>Contract Type</span>
              <div className={styles.selectInner}>
                <select
                  value={contractType}
                  onChange={e => setContractType(e.target.value as ContractType)}
                  className={styles.select}
                >
                  {CONTRACT_TYPES.map(ct => (
                    <option key={ct.value} value={ct.value}>{ct.label}</option>
                  ))}
                </select>
                <ChevronDown size={14} className={styles.chevron} />
              </div>
            </label>
          </div>

          <label className={styles.textareaLabel}>
            <span className={styles.label}>Contract Text</span>
            <textarea
              className={styles.textarea}
              value={contractText}
              onChange={e => setContractText(e.target.value)}
              placeholder="Paste contract text here... (minimum 100 characters)"
              rows={12}
              spellCheck={false}
            />
            <span className={styles.charCount}>{contractText.length.toLocaleString()} characters</span>
          </label>

          {error && (
            <div className={styles.errorBanner}>
              <span>⚠</span> {error}
            </div>
          )}

          <button
            className={styles.submitBtn}
            onClick={handleSubmit}
            disabled={loading || contractText.length < 100}
            type="button"
          >
            {loading ? (
              <>
                <span className={styles.spinner} />
                Starting analysis...
              </>
            ) : (
              <>
                <Search size={16} />
                Detect Ghost Clauses
              </>
            )}
          </button>
        </section>

        {/* How it works */}
        <section className={styles.howIt}>
          <h3 className={styles.howTitle}>How it works</h3>
          <div className={styles.steps}>
            <div className={styles.step}>
              <div className={styles.stepNum} style={{ background: "var(--agent-extractor-light)", color: "var(--accent-primary)" }}>1</div>
              <div>
                <strong>Extractor Agent</strong>
                <p>Parses your contract into structured clauses with type classification.</p>
              </div>
            </div>
            <div className={styles.stepLine} />
            <div className={styles.step}>
              <div className={styles.stepNum} style={{ background: "var(--agent-evaluator-light)", color: "#9A7A3A" }}>2</div>
              <div>
                <strong>Evaluator Agent</strong>
                <p>Cross-references each clause against jurisdiction-specific enforceability rules via RAG.</p>
              </div>
            </div>
            <div className={styles.stepLine} />
            <div className={styles.step}>
              <div className={styles.stepNum} style={{ background: "var(--accent-success-light)", color: "#5A8A6A" }}>3</div>
              <div>
                <strong>Human Review</strong>
                <p>Low-confidence or critical findings are surfaced for your verification before finalizing.</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <p>Contract Ghost · AI analysis for informational purposes only · Not legal advice</p>
      </footer>
    </div>
  );
}
