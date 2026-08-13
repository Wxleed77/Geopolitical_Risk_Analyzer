import { useEffect, useRef, useState } from "react";
import { colorForScore } from "../colorScale.js";

const RADIUS = 30;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function ExposureGauge({ score, breakdown, delayMs = 0 }) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const rafRef = useRef();

  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      setAnimatedScore(score);
      return;
    }
    const start = performance.now() + delayMs;
    const duration = 700;

    function tick(now) {
      const elapsed = now - start;
      if (elapsed < 0) {
        rafRef.current = requestAnimationFrame(tick);
        return;
      }
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(score * eased);
      if (progress < 1) rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [score, delayMs]);

  const color = colorForScore(score);
  const offset = CIRCUMFERENCE - (animatedScore / 100) * CIRCUMFERENCE;

  return (
    <div className="gauge">
      <svg width="76" height="76" viewBox="0 0 76 76">
        <circle
          cx="38"
          cy="38"
          r={RADIUS}
          fill="none"
          stroke="var(--hairline)"
          strokeWidth="5"
        />
        <circle
          cx="38"
          cy="38"
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          transform="rotate(-90 38 38)"
        />
        <text
          x="38"
          y="42"
          textAnchor="middle"
          fontFamily="var(--font-mono)"
          fontSize="18"
          fontWeight="600"
          fill="var(--text-primary)"
        >
          {Math.round(animatedScore)}
        </text>
      </svg>
      <div className="gauge__bars">
        <SignalBar label="TRD" value={breakdown.trade_score} />
        <SignalBar label="ENG" value={breakdown.energy_score} />
        <SignalBar label="ALL" value={breakdown.alliance_score} />
      </div>
    </div>
  );
}

function SignalBar({ label, value }) {
  return (
    <div className="signal-bar">
      <span className="signal-bar__label">{label}</span>
      <div className="signal-bar__track">
        <div
          className="signal-bar__fill"
          style={{ width: `${Math.min(value, 100)}%`, background: colorForScore(value) }}
        />
      </div>
    </div>
  );
}
