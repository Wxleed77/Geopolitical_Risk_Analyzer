import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { colorForScore } from "../colorScale.js";
import { NUMERIC_TO_ISO3 } from "../countryCodes.js";

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// Visible by default so the whole globe is always browsable, even before
// any analysis has run - intentionally lighter than the panel background
// so country outlines are actually readable at rest, not just on hover.
const DEFAULT_FILL = "#2a3540";
const DEFAULT_FILL_HOVER = "#3a4a58";

export default function WorldMap({ rankedCountries, partyAIso, partyBIso }) {
  const [hovered, setHovered] = useState(null);

  const scoreByIso = Object.fromEntries((rankedCountries || []).map((c) => [c.iso_code, c]));
  const hasData = rankedCountries && rankedCountries.length > 0;

  function fillFor(iso) {
    if (iso === partyAIso || iso === partyBIso) return "var(--text-primary)";
    const country = scoreByIso[iso];
    if (country) return colorForScore(country.exposure_score);
    return DEFAULT_FILL;
  }

  function hoverFillFor(iso) {
    if (iso === partyAIso || iso === partyBIso) return "var(--text-primary)";
    const country = scoreByIso[iso];
    if (country) return colorForScore(country.exposure_score);
    return DEFAULT_FILL_HOVER;
  }

  return (
    <motion.div
      className="world-map"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <span className="world-map__eyebrow">
        {hasData ? "EXPOSURE MAP" : "WORLD MAP — run an analysis to color by exposure"}
      </span>
      <div className="world-map__canvas">
        <ComposableMap
          projectionConfig={{ scale: 148 }}
          style={{ width: "100%", height: "auto" }}
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const iso = NUMERIC_TO_ISO3[geo.id];
                const isConflictParty = iso === partyAIso || iso === partyBIso;
                const country = iso ? scoreByIso[iso] : null;

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    onMouseEnter={() => iso && setHovered({ iso, country, isConflictParty })}
                    onMouseLeave={() => setHovered(null)}
                    style={{
                      default: {
                        fill: fillFor(iso),
                        stroke: "var(--bg-void)",
                        strokeWidth: 0.5,
                        outline: "none",
                        cursor: iso ? "pointer" : "default",
                      },
                      hover: {
                        fill: hoverFillFor(iso),
                        stroke: "var(--bg-void)",
                        strokeWidth: 0.5,
                        outline: "none",
                      },
                    }}
                  />
                );
              })
            }
          </Geographies>
        </ComposableMap>

        <AnimatePresence>
          {hovered && (
            <motion.div
              className="world-map__tooltip"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <div className="world-map__tooltip-name">{hovered.iso}</div>
              {hovered.isConflictParty ? (
                <div className="world-map__tooltip-detail">conflict party</div>
              ) : hovered.country ? (
                <div className="world-map__tooltip-detail">
                  exposure {hovered.country.exposure_score.toFixed(1)}
                </div>
              ) : (
                <div className="world-map__tooltip-detail">no analysis run yet</div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {hasData && (
        <div className="world-map__legend">
          <LegendSwatch color="var(--text-primary)" label="conflict party" />
          <LegendSwatch color="var(--accent-signal)" label="low" />
          <LegendSwatch color="var(--accent-warn)" label="medium" />
          <LegendSwatch color="var(--accent-danger)" label="high" />
        </div>
      )}
    </motion.div>
  );
}

function LegendSwatch({ color, label }) {
  return (
    <span className="world-map__legend-item">
      <span className="world-map__legend-swatch" style={{ background: color }} />
      {label}
    </span>
  );
}
