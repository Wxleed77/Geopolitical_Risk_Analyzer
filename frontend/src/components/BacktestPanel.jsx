import { useEffect, useState } from "react";
import { fetchBacktestCases, runBacktest } from "../api.js";
import CountryRow from "./CountryRow.jsx";

export default function BacktestPanel() {
  const [cases, setCases] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    fetchBacktestCases().then(setCases).catch(() => setCases([]));
  }, []);

  const selectedCase = cases.find((c) => c.id === selectedId);

  async function handleRun() {
    if (!selectedCase) return;
    setStatus("loading");
    setErrorMsg("");
    try {
      const data = await runBacktest(selectedCase.id, selectedCase.start_date);
      setResult(data);
      setStatus("done");
    } catch (err) {
      setErrorMsg(err.message);
      setStatus("error");
    }
  }

  return (
    <div className="backtest">
      <span className="backtest__eyebrow">
        BACKTEST — compare predicted exposure against real documented outcomes
      </span>

      <div className="backtest__cases">
        {cases.map((c) => (
          <button
            key={c.id}
            className={"backtest-case" + (selectedId === c.id ? " backtest-case--selected" : "")}
            onClick={() => {
              setSelectedId(c.id);
              setResult(null);
              setStatus("idle");
            }}
          >
            <div className="backtest-case__name">{c.name}</div>
            <div className="backtest-case__meta">
              {c.country_a} vs {c.country_b} · {c.start_date}
            </div>
          </button>
        ))}
      </div>

      {selectedCase && (
        <button className="run-button backtest__run" onClick={handleRun} disabled={status === "loading"}>
          {status === "loading" ? "RUNNING..." : `RUN BACKTEST: ${selectedCase.name}`}
        </button>
      )}

      {status === "error" && (
        <div className="error-state">
          <span className="error-state__label">BACKTEST FAILED</span>
          <p>{errorMsg}</p>
        </div>
      )}

      {status === "done" && result && (
        <div className="backtest__results">
          <div className="backtest__column">
            <span className="backtest__column-label">PREDICTED (current data, not time-adjusted)</span>
            {result.predicted.ranked_countries.length === 0 ? (
              <p className="backtest__empty">No ranked countries returned.</p>
            ) : (
              result.predicted.ranked_countries.map((country, i) => (
                <CountryRow key={country.iso_code} rank={i + 1} country={country} delayMs={i * 60} />
              ))
            )}
          </div>

          <div className="backtest__column">
            <span className="backtest__column-label">DOCUMENTED OUTCOME (real history)</span>
            <div className="backtest__outcome">{result.documented_outcome}</div>
            <span className="backtest__column-label backtest__column-label--secondary">
              COMPARISON NOTES
            </span>
            <div className="backtest__outcome backtest__outcome--muted">{result.comparison_notes}</div>
          </div>
        </div>
      )}
    </div>
  );
}
