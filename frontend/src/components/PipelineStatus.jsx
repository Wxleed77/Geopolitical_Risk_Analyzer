function parseTags(tags) {
  const steps = [{ label: "SCORED", done: true }]; // always true if we got a response at all

  const hasNarrative = tags.some((t) => t === "narrative-critic-reviewed");
  const skippedNoKey = tags.includes("narrative-skipped-no-llm-api-key");
  const failed = tags.includes("narrative-generation-failed");
  const rejectedTag = tags.find((t) => t.startsWith("critic-rejected-"));
  const extractedTag = tags.find((t) => t.startsWith("parties-extracted-from-raw_input:"));

  if (extractedTag) {
    steps.push({ label: `PARSED: ${extractedTag.split(":")[1]}`, done: true });
  }

  if (hasNarrative) {
    steps.push({ label: "NARRATED", done: true });
    const rejectedCount = rejectedTag ? rejectedTag.match(/\d+/)?.[0] : "0";
    steps.push({
      label:
        rejectedCount && rejectedCount !== "0"
          ? `CRITIC-REVIEWED (${rejectedCount} REJECTED)`
          : "CRITIC-REVIEWED",
      done: true,
      warn: rejectedCount && rejectedCount !== "0",
    });
  } else if (skippedNoKey) {
    steps.push({ label: "NARRATIVE SKIPPED (NO LLM KEY)", done: false });
  } else if (failed) {
    steps.push({ label: "NARRATIVE FAILED", done: false, error: true });
  }

  return steps;
}

export default function PipelineStatus({ tags }) {
  const steps = parseTags(tags);
  return (
    <div className="pipeline">
      <span className="pipeline__eyebrow">PIPELINE</span>
      {steps.map((step, i) => (
        <span
          key={i}
          className={
            "pipeline__step" +
            (step.error ? " pipeline__step--error" : step.warn ? " pipeline__step--warn" : step.done ? " pipeline__step--done" : "")
          }
        >
          {step.error ? "✗" : step.done ? "✓" : "○"} {step.label}
        </span>
      ))}
    </div>
  );
}
