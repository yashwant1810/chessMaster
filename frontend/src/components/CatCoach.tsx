import { useEffect, useRef, useState, useCallback } from "react";
import type { LearningInsight } from "../types";
import { describeInsight } from "../utils/moveDescription";
import { catSpeak, stopCatSpeech } from "../utils/catVoice";
import "./CatCoach.css";

export interface CatCoachProps {
  insight: LearningInsight | null;
}

export default function CatCoach({ insight }: CatCoachProps) {
  const [isTalking, setIsTalking] = useState(false);
  const [mouthOpen, setMouthOpen] = useState(false);
  const prevKeyRef = useRef<string | null>(null);

  const startTalking = useCallback(() => setIsTalking(true), []);
  const stopTalking = useCallback(() => { setIsTalking(false); setMouthOpen(false); }, []);
  const openMouth = useCallback(() => setMouthOpen(true), []);
  const closeMouth = useCallback(() => setMouthOpen(false), []);

  useEffect(() => {
    if (!insight) {
      prevKeyRef.current = null;
      stopCatSpeech();
      stopTalking();
      return;
    }

    const key = `${insight.move_number}-${insight.is_white}-${insight.played_move}`;
    if (key === prevKeyRef.current) return;
    prevKeyRef.current = key;

    const text = describeInsight(insight.played_move, insight.best_move, insight.classification);
    catSpeak(text, {
      onStart: startTalking,
      onEnd: stopTalking,
      onMouthOpen: openMouth,
      onMouthClose: closeMouth,
    });

    return () => { stopCatSpeech(); stopTalking(); };
  }, [insight, startTalking, stopTalking, openMouth, closeMouth]);

  useEffect(() => () => { stopCatSpeech(); stopTalking(); }, [stopTalking]);

  const desc = insight
    ? describeInsight(insight.played_move, insight.best_move, insight.classification)
    : null;

  return (
    <div className="cat-coach">
      <div className={`cat-coach__avatar ${isTalking ? "cat-coach__avatar--talking" : ""}`}>
        <img
          src={isTalking && mouthOpen ? "/sounds/cat-open.png?v=3" : "/sounds/cat-closed.png?v=3"}
          alt="Cat coach"
          className="cat-coach__img"
        />
      </div>
      <div className="cat-coach__text">
        {insight ? (
          <>
            <span className={`cat-coach__badge cat-coach__badge--${insight.classification}`}>
              {insight.classification}
            </span>
            <p className="cat-coach__desc">{desc}</p>
            {insight.principal_variation.length > 0 && (
              <p className="cat-coach__pv">
                <strong>Best line:</strong>{" "}
                {insight.principal_variation.slice(0, 4).join(" → ")}
              </p>
            )}
          </>
        ) : (
          <p className="cat-coach__ok">✓ Purrfect move — no issues here!</p>
        )}
      </div>
    </div>
  );
}
