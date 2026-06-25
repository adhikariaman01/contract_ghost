import type { AgentStep, StepStatus } from "../types";
import styles from "./AgentChainVisualizer.module.css";

interface Props {
  steps: AgentStep[];
  currentStep: string;
  hitlQueue: string[];
}

type AgentDef = {
  name: string;
  stepNumber: number;
  colorVar: string;
  lightVar: string;
  icon: string;
  description: string;
};

const AGENTS: AgentDef[] = [
  {
    name: "Extractor Agent",
    stepNumber: 1,
    colorVar: "var(--agent-extractor)",
    lightVar: "var(--agent-extractor-light)",
    icon: "📋",
    description: "Parsing clauses",
  },
  {
    name: "Evaluator Agent",
    stepNumber: 2,
    colorVar: "var(--agent-evaluator)",
    lightVar: "var(--agent-evaluator-light)",
    icon: "⚖️",
    description: "Checking enforceability",
  },
  {
    name: "Human Review",
    stepNumber: 3,
    colorVar: "var(--accent-warning)",
    lightVar: "var(--accent-warning-light)",
    icon: "👤",
    description: "Awaiting your input",
  },
  {
    name: "Finalizer",
    stepNumber: 4,
    colorVar: "var(--accent-success)",
    lightVar: "var(--accent-success-light)",
    icon: "✅",
    description: "Assembling report",
  },
];

function deriveStatus(agent: AgentDef, currentStep: string, steps: AgentStep[], hitlQueue: string[]): StepStatus {
  // Check actual step logs
  const matching = steps.filter(s => s.step_number === agent.stepNumber);
  if (matching.length > 0) {
    return matching[matching.length - 1].status;
  }

  // Derive from pipeline position
  const stepMap: Record<string, number> = {
    extractor: 1,
    evaluator: 2,
    hitl: 3,
    hitl_waiting: 3,
    hitl_reviewing: 3,
    finalizing: 4,
    finalizer: 4,
    complete: 5,
    error: -1,
  };

  const currentNum = stepMap[currentStep] ?? 0;

  if (agent.stepNumber < currentNum) return "completed";
  if (agent.stepNumber === currentNum) {
    if (currentStep === "hitl_waiting" && hitlQueue.length > 0) return "waiting_hitl";
    return "running";
  }
  return "pending";
}

function StatusBadge({ status }: { status: StepStatus }) {
  const label: Record<StepStatus, string> = {
    pending: "Pending",
    running: "Running",
    completed: "Done",
    failed: "Failed",
    waiting_hitl: "Needs Review",
  };
  return (
    <span className={`${styles.badge} ${styles[`badge_${status}`]}`}>
      {status === "running" && <span className={styles.pulseDot} />}
      {label[status]}
    </span>
  );
}

export default function AgentChainVisualizer({ steps, currentStep, hitlQueue }: Props) {
  return (
    <div className={styles.chain}>
      {AGENTS.map((agent, idx) => {
        const status = deriveStatus(agent, currentStep, steps, hitlQueue);
        const matchingSteps = steps.filter(s => s.step_number === agent.stepNumber);
        const lastStep = matchingSteps[matchingSteps.length - 1];

        return (
          <div key={agent.name} className={styles.nodeWrap}>
            <div
              className={`${styles.node} ${status === "running" ? styles.nodeRunning : ""} ${status === "completed" ? styles.nodeCompleted : ""}`}
              style={{
                borderColor: status === "pending" ? "var(--border)" :
                  status === "waiting_hitl" ? "var(--accent-warning)" :
                  status === "failed" ? "var(--accent-danger)" : agent.colorVar,
                background: status === "pending" ? "var(--bg-card)" : agent.lightVar,
              }}
            >
              <div className={styles.nodeLeft}>
                <span className={styles.nodeIcon}>{agent.icon}</span>
                <div>
                  <div className={styles.nodeName}>{agent.name}</div>
                  <div className={styles.nodeDesc}>
                    {lastStep?.output_summary || agent.description}
                  </div>
                </div>
              </div>
              <StatusBadge status={status} />
            </div>

            {idx < AGENTS.length - 1 && (
              <div
                className={styles.connector}
                style={{
                  background: status === "completed" ? agent.colorVar : "var(--border)",
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
