# Geopolitical Conflict Impact Analyzer

A tool that estimates which countries would be most affected by a geopolitical
conflict between two nations, and — for a growing set of real, researched
scenarios — explains *how* people in those countries might actually feel the
impact (inflation, fuel prices, currency shifts), grounded in real historical
precedent rather than invented numbers.

Built as a portfolio/learning project. Full-stack: Python/FastAPI backend,
React frontend, real external data (UN Comtrade, live geopolitical research),
an LLM narrative layer with a critic agent that fact-checks its own output
before it reaches the user.

## What it actually does

1. Pick two countries (or describe a conflict in free text)
2. Get a ranked list of which other countries are most exposed
3. See *why* — trade/energy/alliance breakdown, an interactive world map,
   and (where real data exists) a plain-language explanation grounded in
   actual historical precedent
4. Backtest the system against real past conflicts to see how its
   predictions compare with documented outcomes

## The two-tier honesty system

This project's central design decision, and the thing most worth reading the
code for: **the system never pretends to know more than it does.**

- **Curated tier** (`curated-verified-analysis`): for a growing set of major
  real-world conflicts (USA-China, Russia-Ukraine, India-Pakistan...), the
  ranking and reasoning are human-researched and source-cited — not computed
  by a formula. Shown with a green "VERIFIED" banner.
- **Exploratory tier** (`exploratory-estimate-limited-data`): for any other
  pair, the system falls back to a deterministic scoring engine (real trade/
  energy/alliance data, where available) and clearly labels the result with
  an amber "EXPLORATORY ESTIMATE, treat with caution" banner instead of
  presenting a rough guess as if it were authoritative.

This split exists because early testing showed the deterministic formula
alone — while internally consistent — just doesn't have enough underlying
data (a few dozen seeded countries, a handful of live-fetched trade pairs)
to give expert-quality answers for arbitrary conflicts. Rather than hide
that limitation behind confident-looking numbers, the app says so.

## Architecture

**Backend** (`backend/`, FastAPI + SQLite + SQLAlchemy):
- `app/services/scoring_service.py` — pure, unit-tested deterministic
  scoring functions (trade/energy/alliance exposure, confidence-penalized
  composite). Zero network calls, zero LLM calls.
- `app/services/exposure_service.py` — orchestrates scoring against the DB
  to rank all countries for a given conflict pair.
- `app/services/curated_service.py` — looks up human-researched analyses,
  order-independent (USA/CHN and CHN/USA both match).
- `app/agents/context_agent.py` — extracts two country codes from free-text
  conflict descriptions via LLM.
- `app/agents/critic_agent.py` — fact-checks every LLM-written sentence
  against the actual data it was given; rejects (drops, doesn't just flag)
  anything unsupported. Two layers: free deterministic number-checking,
  then an LLM semantic check for invented facts/events.
- `app/services/narrative_service.py` / `impact_service.py` — turn scores
  and real historical shock data into plain-language narrative via LLM,
  parallelized (thread pool) since sequential LLM calls were the main
  latency bottleneck.
- `app/services/rag_service.py` — retrieves relevant historical case
  studies by conflict-party overlap (deliberately not embedding-based —
  for a corpus this small, exact metadata matching beats semantic
  similarity, and avoids a dependency on a model download this sandbox
  couldn't reach anyway).
- `backend/ingestion/` — idempotent scripts that populate the DB:
  - `ingest_alliances.py`, `ingest_comtrade.py`, `ingest_eia.py` — seed
    data (hand-curated, clearly labeled illustrative where precision
    wasn't verifiable)
  - `ingest_comtrade_live.py`, `ingest_energy_live.py` — live UN Comtrade
    API pulls (real bilateral trade/energy data, requires a free API key)
  - `curate_case_studies.py`, `ingest_shock_impacts.py` — real historical
    conflict outcomes (1973 Oil Crisis, Soleimani strike, etc.) with real
    sourced inflation/fuel-price figures
  - `ingest_curated_conflicts.py` — the human-researched "verified" tier

**Frontend** (`frontend/`, React + Vite):
- Dark, data-dense "command center" UI
- `WorldMap.jsx` — real geographic map (react-simple-maps), countries
  colored by exposure, always visible (browsable without spending an
  analysis run)
- `ShockComparisonChart.jsx` — real historical indicator movements
  (fuel/CPI/currency), not LLM-invented numbers
- `BacktestPanel.jsx` — run the system against real historical cases,
  compare predicted ranking to documented outcome
- `AnalysisProgress.jsx` — honestly-labeled *estimated* progress (the
  backend returns one response, it doesn't stream; the progress bar says
  so in its own code comments)

## Tech stack

Backend: FastAPI, SQLAlchemy, SQLite, pytest
LLM: OpenRouter (free-tier models, OpenAI-compatible client)
Frontend: React, Vite, react-simple-maps, framer-motion
Data sources: UN Comtrade API (real), hand-verified historical research

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp ../.env.example .env   # fill in COMTRADE_API_KEY and LLM_API_KEY (both free)

# Run ingestion, in order:
python ingestion/ingest_alliances.py
python ingestion/ingest_comtrade_live.py      # needs COMTRADE_API_KEY
python ingestion/ingest_energy_live.py        # needs COMTRADE_API_KEY, takes a few minutes
python ingestion/curate_case_studies.py
python ingestion/ingest_shock_impacts.py
python ingestion/ingest_curated_conflicts.py

uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Then open `http://localhost:5173`.

### Tests
```bash
cd backend
pytest tests/unit -v
```

## Known limitations (stated plainly, not hidden)

- **Free OpenRouter tier caps at ~50 requests/day** — each `/analyze` call
  on the exploratory tier uses ~10-14 LLM calls, so budget roughly 4 runs/
  day unless you add credits. Curated-tier results use zero LLM calls.
- **Exploratory tier only has real trade/energy data for a handful of
  countries** — this is *why* the curated tier exists.
- **Backtest doesn't time-travel** — it scores historical cases using
  current data, not data as it existed at the time, since only a
  single-year snapshot is ingested. Stated honestly in the API response
  itself (`comparison_notes`).
- **`ingest_eia_live.py` is unused/abandoned** — kept in the repo as a
  record of a dead end: EIA's international data is country-level
  aggregate, not bilateral, so it couldn't answer what this project needs.
  `ingest_energy_live.py` (via Comtrade) replaced it.
- India Comtrade data is unreliable — the live API rate-limits it more
  than other countries in testing; not fully resolved.

## Possible next steps

- More curated conflicts (China-Taiwan directly, Korea, USA-Iran)
- Real RAG over live news sources for the exploratory tier (bigger scope —
  needs live API integration this environment couldn't build+test blind)
- Real-time streaming progress instead of the estimated progress bar
