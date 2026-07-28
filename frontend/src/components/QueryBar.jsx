import { useState } from "react";

export default function QueryBar({ countries, onSubmit, loading }) {
  const [mode, setMode] = useState("dropdown");
  const [rawInput, setRawInput] = useState("");
  const [countryA, setCountryA] = useState("");
  const [countryB, setCountryB] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (mode === "freetext") {
      if (!rawInput.trim()) return;
      onSubmit({ raw_input: rawInput.trim() });
    } else {
      if (!countryA || !countryB) return;
      onSubmit({ country_a: countryA, country_b: countryB });
    }
  }

  return (
    <form className="query-bar" onSubmit={handleSubmit}>
      <div className="query-bar__modes">
        <button
          type="button"
          className={"mode-toggle" + (mode === "dropdown" ? " mode-toggle--active" : "")}
          onClick={() => setMode("dropdown")}
        >
          SELECT COUNTRIES
        </button>
        <button
          type="button"
          className={"mode-toggle" + (mode === "freetext" ? " mode-toggle--active" : "")}
          onClick={() => setMode("freetext")}
        >
          DESCRIBE CONFLICT
        </button>
      </div>

      {mode === "freetext" ? (
        <div className="query-bar__row">
          <span className="query-bar__prompt">&gt;</span>
          <input
            className="query-bar__input"
            type="text"
            placeholder="describe the conflict, e.g. Russia invaded Ukraine"
            value={rawInput}
            onChange={(e) => setRawInput(e.target.value)}
          />
        </div>
      ) : (
        <div className="query-bar__row">
          <select
            className="query-bar__select"
            value={countryA}
            onChange={(e) => setCountryA(e.target.value)}
          >
            <option value="">SELECT PARTY A</option>
            {countries.map((c) => (
              <option key={c.iso_code} value={c.iso_code}>
                {c.name} ({c.iso_code})
              </option>
            ))}
          </select>
          <span className="query-bar__vs">VS</span>
          <select
            className="query-bar__select"
            value={countryB}
            onChange={(e) => setCountryB(e.target.value)}
          >
            <option value="">SELECT PARTY B</option>
            {countries.map((c) => (
              <option key={c.iso_code} value={c.iso_code}>
                {c.name} ({c.iso_code})
              </option>
            ))}
          </select>
        </div>
      )}

      <button className="run-button" type="submit" disabled={loading}>
        {loading ? "COMPUTING..." : "RUN ANALYSIS"}
      </button>
    </form>
  );
}
