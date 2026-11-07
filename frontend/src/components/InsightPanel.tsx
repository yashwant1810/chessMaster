import type { LearningInsight } from "../types";
import { sanToEnglish, describeInsight } from "../utils/moveDescription";
import "./InsightPanel.css";

export interface InsightPanelProps {
  insight: LearningInsight | null;
}

const CLASS_LABELS: Record<string, { label: string; color: string }> = {
  blunder:    { label: "Blunder",    color: "#e74c3c" },
  mistake:    { label: "Mistake",    color: "#e67e22" },
  inaccuracy: { label: "Inaccuracy", color: "#f1c40f" },
};

export default function InsightPanel({ insight }: InsightPanelProps) {
  if (!insight) {
    return (
      <div className="insight-panel insight-panel--empty">
        <h3>Move Insight</h3>
        <p className="insight-good">✓ No issues with this move.</p>
      </div>
    );
  }

  const cls = CLASS_LABELS[insight.classification] ?? { label: insight.classification, color: "#f1c40f" };
  const desc = describeInsight(insight.played_move, insight.best_move, insight.classification);
  const pvEnglish = insight.principal_variation
    .slice(0, 3)
    .map(sanToEnglish)
    .join(" → ");

  return (
    <div className="insight-panel">
      <h3>Move Insight</h3>
      <div className="insight-badge" style={{ background: cls.color + "22", color: cls.color, borderColor: cls.color }}>
        {cls.label}
      </div>
      <p className="insight-desc">{desc}</p>
      {pvEnglish && (
        <p className="insight-continuation">
          <span className="insight-label">Best line:</span> {pvEnglish}
        </p>
      )}
    </div>
  );
}
