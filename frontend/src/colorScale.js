export function colorForScore(score) {
  if (score >= 66) return "var(--accent-danger)";
  if (score >= 33) return "var(--accent-warn)";
  return "var(--accent-signal)";
}
