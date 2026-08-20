import { useEffect, useState } from "react";
import { fetchCountries, analyzeConflict } from "./api.js";
import QueryBar from "./components/QueryBar.jsx";
import PipelineStatus from "./components/PipelineStatus.jsx";
import WorldMap from "./components/WorldMap.jsx";
import CountryRow from "./components/CountryRow.jsx";
import CitationList from "./components/CitationList.jsx";
import BacktestPanel from "./components/BacktestPanel.jsx";
import AnalysisProgress from "./components/AnalysisProgress.jsx";

function matchNarrative(sections, isoCode) {
  return sections.find(
    (s) => s.tag === "data-derived" && s.heading.includes(`(${isoCode})`)
  );
}

function extractPartiesFromTags(tags) {
  const tag = tags.find((t) => t.startsWith("parties-extracted-from-raw_input:"));
  if (!tag) return null;
  const [a, b] = tag.split(":")[1].split("-vs-");
  return { a, b };
}

export default function App() {
  const [countries, setCountries] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [liveTick, setLiveTick] = useState(true);
  const [parties, setParties] = useState({ a: null, b: null });
  const [view, setView] = useState("analyze"); // "analyze" | "backtest"

  useEffect(() => {
    fetchCountries().then(setCountries).catch(() => setCountries([]));
  }, []);

  useEffect(() => {
    const id = setInterval(() => setLiveTick((t) => !t), 1000);
    return () => clearInterval(id);
  }, []);

  async function handleSubmit(payload) {
    setStatus("loading");
    setErrorMsg("");
    if (payload.country_a && payload.country_b) {
      setParties({ a: payload.country_a, b: payload.country_b });
    }
    try {
      const data = await analyzeConflict(payload);
      if (!payload.country_a) {
        const extracted = extractPartiesFromTags(data.confidence_tags);
        if (extracted) setParties(extracted);
      }
      setResult(data);
      setStatus("done");
    } catch (err) {
      setErrorMsg(err.message);
      setStatus("error");
    }
  }

  const precedentSections = result
    ? result.narrative_sections.filter((s) => s.tag === "qualitative-cited")
    : [];

  return (
    <div className="app">
      <header className="topbar">
        <span className="topbar__title">▚ CONFLICT EXPOSURE ANALYZER</span>
        <div className="topbar__right">
          <div className="view-toggle">
            <button
              className={"mode-toggle" + (view === "analyze" ? " mode-toggle--active" : "")}
              onClick={() => setView("analyze")}
            >
              ANALYZE
            </button>
            <button
              className={"mode-toggle" + (view === "backtest" ? " mode-toggle--active" : "")}
              onClick={() => setView("backtest")}
            >
              BACKTEST
            </button>
          </div>
          <span className="topbar__status">
            <span className={"status-dot" + (liveTick ? " status-dot--on" : "")} />
            {status === "loading" ? "computing" : "live"}
          </span>
        </div>
      </header>

      {view === "backtest" ? (
        <BacktestPanel />
      ) : (
        <>
      <QueryBar countries={countries} onSubmit={handleSubmit} loading={status === "loading"} />

      <WorldMap
        rankedCountries={result ? result.ranked_countries : []}
        partyAIso={parties.a}
        partyBIso={parties.b}
      />

      {status === "idle" && (
        <div className="empty-state">
          <span className="empty-state__cursor">AWAITING QUERY_</span>
        </div>
      )}

      {status === "loading" && <AnalysisProgress />}

      {status === "error" && (
        <div className="error-state">
          <span className="error-state__label">QUERY FAILED</span>
          <p>{errorMsg}</p>
        </div>
      )}

      {status === "done" && result && (
        <>
          <PipelineStatus tags={result.confidence_tags} />

          {result.ranked_countries.length === 0 ? (
            <div className="empty-state">
              <span className="empty-state__cursor">
                NO EXPOSURE DATA FOR THESE PARTIES_
              </span>
            </div>
          ) : (
            <div className="results">
              <span className="results__eyebrow">RANKED EXPOSURE</span>
              {result.ranked_countries.map((country, i) => (
                <CountryRow
                  key={country.iso_code}
                  rank={i + 1}
                  country={country}
                  narrative={matchNarrative(result.narrative_sections, country.iso_code)}
                  delayMs={i * 60}
                />
              ))}
            </div>
          )}

          <CitationList citations={result.citations} precedentSections={precedentSections} />
        </>
      )}
        </>
      )}
    </div>
  );
}
