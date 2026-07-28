import { useEffect, useState } from "react";
import { fetchCountries, analyzeConflict } from "./api.js";
import QueryBar from "./components/QueryBar.jsx";
import PipelineStatus from "./components/PipelineStatus.jsx";
import CountryRow from "./components/CountryRow.jsx";
import CitationList from "./components/CitationList.jsx";

function matchNarrative(sections, isoCode) {
  return sections.find(
    (s) => s.tag === "data-derived" && s.heading.includes(`(${isoCode})`)
  );
}

export default function App() {
  const [countries, setCountries] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [liveTick, setLiveTick] = useState(true);

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
    try {
      const data = await analyzeConflict(payload);
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
        <span className="topbar__status">
          <span className={"status-dot" + (liveTick ? " status-dot--on" : "")} />
          {status === "loading" ? "computing" : "live"}
        </span>
      </header>

      <QueryBar countries={countries} onSubmit={handleSubmit} loading={status === "loading"} />

      {status === "idle" && (
        <div className="empty-state">
          <span className="empty-state__cursor">AWAITING QUERY_</span>
        </div>
      )}

      {status === "loading" && (
        <div className="empty-state">
          <span className="empty-state__cursor">COMPUTING EXPOSURE..._</span>
        </div>
      )}

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
    </div>
  );
}
