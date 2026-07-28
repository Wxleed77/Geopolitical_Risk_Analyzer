import ExposureGauge from "./ExposureGauge.jsx";

export default function CountryRow({ rank, country, narrative, delayMs }) {
  return (
    <div className="country-row">
      <span className="country-row__rank">{String(rank).padStart(2, "0")}</span>
      <div className="country-row__name">
        <span className="country-row__country">{country.name}</span>
        <span className="country-row__iso">{country.iso_code}</span>
      </div>
      <ExposureGauge score={country.exposure_score} breakdown={country.breakdown} delayMs={delayMs} />
      {narrative && (
        <div className="country-row__narrative">
          <span className="country-row__eyebrow">ANALYST BRIEFING</span>
          <p>{narrative.text}</p>
        </div>
      )}
    </div>
  );
}
