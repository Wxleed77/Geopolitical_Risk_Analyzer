import { motion } from "framer-motion";

const INDICATOR_COLOR = {
  fuel_price: "var(--accent-warn)",
  cpi: "var(--accent-danger)",
  currency: "var(--accent-signal)",
};

const INDICATOR_LABEL = {
  fuel_price: "fuel price",
  cpi: "inflation (CPI)",
  currency: "currency",
};

export default function ShockComparisonChart({ shocks }) {
  if (!shocks || shocks.length === 0) return null;

  const maxAbs = Math.max(...shocks.map((s) => Math.abs(s.change_pct)), 1);
  const cases = [...new Set(shocks.map((s) => s.case_name))];

  return (
    <div className="shock-chart">
      <span className="shock-chart__eyebrow">
        HISTORICAL SHOCK COMPARISON — real recorded movements in comparable past events
      </span>

      {cases.map((caseName) => (
        <div className="shock-chart__case" key={caseName}>
          <div className="shock-chart__case-name">{caseName}</div>
          {shocks
            .filter((s) => s.case_name === caseName)
            .map((s, i) => {
              const widthPct = (Math.abs(s.change_pct) / maxAbs) * 100;
              const isNegative = s.change_pct < 0;
              return (
                <div className="shock-bar" key={`${s.country_iso}-${s.indicator}`}>
                  <div className="shock-bar__label">
                    <span className="shock-bar__country">{s.country_iso}</span>
                    <span className="shock-bar__indicator">{INDICATOR_LABEL[s.indicator] || s.indicator}</span>
                  </div>
                  <div className="shock-bar__track">
                    <div className="shock-bar__zero" />
                    <motion.div
                      className="shock-bar__fill"
                      style={{
                        background: INDICATOR_COLOR[s.indicator] || "var(--text-muted)",
                        [isNegative ? "right" : "left"]: "50%",
                      }}
                      initial={{ width: 0 }}
                      animate={{ width: `${widthPct / 2}%` }}
                      transition={{ duration: 0.5, delay: i * 0.08, ease: "easeOut" }}
                    />
                  </div>
                  <span className="shock-bar__value">
                    {s.change_pct > 0 ? "+" : ""}
                    {s.change_pct.toFixed(1)}%
                  </span>
                  <span className="shock-bar__timeframe">{s.timeframe}</span>
                </div>
              );
            })}
        </div>
      ))}

      <div className="shock-chart__legend">
        {Object.entries(INDICATOR_LABEL).map(([key, label]) => (
          <span className="shock-chart__legend-item" key={key}>
            <span
              className="shock-chart__legend-swatch"
              style={{ background: INDICATOR_COLOR[key] }}
            />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
