import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { colorForScore } from "../colorScale.js";
import { NUMERIC_TO_ISO3 } from "../countryCodes.js";

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

export default function WorldMap({ rankedCountries, partyAIso, partyBIso }) {
  const [hovered, setHovered] = useState(null);

  const scoreByIso = Object.fromEntries(rankedCountries.map((c) => [c.iso_code, c]));

  function fillFor(iso) {
    if (iso === partyAIso || iso === partyBIso) return "var(--text-primary)";
    const country = scoreByIso[iso];
    if (!country) return "var(--bg-raised)";
    return colorForScore(country.exposure_score);
  }

  return (
    <div className="world-map">
      <span className="world-map__eyebrow">EXPOSURE MAP</span>
      <div className="world-map__canvas">
        <ComposableMap
          projectionConfig={{ scale: 148 }}
          style={{ width: "100%", height: "auto" }}
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo, i) => {
                const iso = NUMERIC_TO_ISO3[geo.id];
                const isConflictParty = iso === partyAIso || iso === partyBIso;
                const country = iso ? scoreByIso[iso] : null;
                const isInteractive = isConflictParty || !!country;

                return (
                  <motion.g key={geo.rsmKey}>
                    <Geography
                      geography={geo}
                      onMouseEnter={() => isInteractive && setHovered({ iso, country, isConflictParty })}
                      onMouseLeave={() => setHovered(null)}
                      style={{
                        default: {
                          fill: fillFor(iso),
                          stroke: "var(--bg-void)",
                          strokeWidth: 0.5,
                          outline: "none",
                          cursor: isInteractive ? "pointer" : "default",
                          opacity: 0,
                        },
                        hover: {
                          fill: fillFor(iso),
                          stroke: "var(--bg-void)",
                          strokeWidth: 0.5,
                          outline: "none",
                          opacity: isInteractive ? 0.8 : 1,
                        },
                      }}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.5, delay: Math.min(i * 0.002, 0.4) }}
                    />
                  </motion.g>
                );
              })
            }
          </Geographies>
        </ComposableMap>

        <AnimatePresence>
          {hovered && (hovered.country || hovered.isConflictParty) && (
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
              ) : (
                <div className="world-map__tooltip-detail">
                  exposure {hovered.country.exposure_score.toFixed(1)}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="world-map__legend">
        <LegendSwatch color="var(--text-primary)" label="conflict party" />
        <LegendSwatch color="var(--accent-signal)" label="low" />
        <LegendSwatch color="var(--accent-warn)" label="medium" />
        <LegendSwatch color="var(--accent-danger)" label="high" />
      </div>
    </div>
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
