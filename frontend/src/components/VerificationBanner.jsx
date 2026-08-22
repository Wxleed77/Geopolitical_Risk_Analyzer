export default function VerificationBanner({ tags }) {
  const isCurated = tags.includes("curated-verified-analysis");
  const isExploratory = tags.includes("exploratory-estimate-limited-data");

  if (isCurated) {
    const verifiedTag = tags.find((t) => t.startsWith("last-verified:"));
    const verifiedDate = verifiedTag ? verifiedTag.split(":")[1] : null;
    return (
      <div className="verification-banner verification-banner--verified">
        <span className="verification-banner__icon">✓</span>
        <span>
          VERIFIED CURATED ANALYSIS — human-researched, source-cited
          {verifiedDate && ` (last verified ${verifiedDate})`}
        </span>
      </div>
    );
  }

  if (isExploratory) {
    return (
      <div className="verification-banner verification-banner--exploratory">
        <span className="verification-banner__icon">⚠</span>
        <span>
          EXPLORATORY ESTIMATE — no curated analysis exists for this pair; computed from
          limited live trade/energy/alliance data, treat with caution
        </span>
      </div>
    );
  }

  return null;
}
