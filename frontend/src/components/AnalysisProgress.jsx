import { useEffect, useState } from "react";

// NOTE: the backend returns one single response, it doesn't stream real
// progress - so this is an ESTIMATE based on the pipeline's known shape
// (scoring is near-instant, narrative + critic dominate the wait), not a
// live signal from the server. Progress asymptotically approaches 92%
// and holds there rather than hitting 100% and freezing if a run takes
// longer than usual (rate limits, slow free-tier models) - it only
// snaps to 100% when the real response actually arrives.
const STAGES = [
  { label: "Scoring trade / energy / alliance exposure", afterSeconds: 0 },
  { label: "Retrieving historical precedents", afterSeconds: 1 },
  { label: "Generating narrative for top countries", afterSeconds: 2 },
  { label: "Running critic review", afterSeconds: 10 },
  { label: "Finalizing response", afterSeconds: 20 },
];

const CAP_PERCENT = 92;
const TAU_SECONDS = 8; // controls how fast progress approaches the cap

export default function AnalysisProgress() {
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    const start = performance.now();
    const id = setInterval(() => setElapsedMs(performance.now() - start), 150);
    return () => clearInterval(id);
  }, []);

  const elapsedSeconds = elapsedMs / 1000;
  const progress = CAP_PERCENT * (1 - Math.exp(-elapsedSeconds / TAU_SECONDS));

  const currentStage = [...STAGES].reverse().find((s) => elapsedSeconds >= s.afterSeconds) || STAGES[0];

  return (
    <div className="analysis-progress">
      <span className="analysis-progress__stage">{currentStage.label}_</span>
      <div className="analysis-progress__track">
        <div className="analysis-progress__fill" style={{ width: `${progress}%` }} />
      </div>
      <span className="analysis-progress__elapsed">{elapsedSeconds.toFixed(0)}s elapsed</span>
    </div>
  );
}
