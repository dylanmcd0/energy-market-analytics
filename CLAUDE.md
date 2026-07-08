# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A data pipeline + analysis toolkit for learning US natural gas markets: fundamentals, spreads, seasonality, and positioning. It has two halves:

- `pipeline/` — four independent fetch scripts that pull raw market data and write parquet files to `data/`.
- `analysis/` and `notebooks/` — (currently scaffolding only) where exploratory analysis will be built on top of the parquet files, per `docs/PRICE_DISCOVERY.md`.

## Commands

```bash
uv sync                              # install/update the environment from pyproject.toml
uv run python pipeline/fetch_futures.py   # NG futures prices (yfinance, no key)
uv run python pipeline/fetch_eia.py       # EIA storage levels (needs EIA_API_KEY)
uv run python pipeline/fetch_weather.py   # HDD/CDD via Open-Meteo (no key)
uv run python pipeline/fetch_cftc.py      # CFTC COT positioning (no key)
```

There is no test suite, linter, or type checker configured in this repo. Verify pipeline changes by running the script directly and inspecting the resulting parquet file, e.g.:

```python
import pandas as pd
pd.read_parquet("data/degree_days.parquet").tail()
```

`fetch_futures.py` and `fetch_cftc.py` require no API keys and are the fastest way to confirm the environment works. `fetch_eia.py` needs `EIA_API_KEY` in a local `.env` file (see `SETUP.md`).

## Architecture

Each `pipeline/fetch_*.py` script is a standalone, self-contained module with the same shape:

- A module docstring explaining the source, series/endpoint used, and any domain-specific transforms.
- Module-level constants `OUTPUT_PATH` (where the parquet lands in `data/`) and `ROLLING_YEARS` (currently `2` everywhere — the window of history kept; older rows are dropped on each run, not appended to indefinitely).
- A `main()` that fetches, transforms, and writes to `OUTPUT_PATH`, printing a summary (`tail()`) for quick sanity-checking.

There is no shared library code between the fetchers — each duplicates its own HTTP/pagination/date-window logic on purpose (they hit unrelated APIs with different pagination and auth schemes). When editing one fetcher, don't assume changes need to propagate to the others.

Output parquet files (`data/futures.parquet`, `eia_storage.parquet`, `degree_days.parquet`, `cftc_cot.parquet`) are committed to git — they are the durable data store for this project, not a build artifact. `.github/workflows/update_data.yml` runs all four fetchers daily at 14:00 UTC and commits any changes back to `data/` with `[skip ci]`.

`fetch_weather.py` computes HDD/CDD (base 65°F) from an unweighted average of daily temps across 12 major US cities (`STATIONS` list of name/lat/lon), then sums to ISO weeks (Monday-start). If you change the station list or degree-day base temperature, note that `docs/DATA_SOURCES.md` documents the historical NOAA-based version of this pipeline and is stale relative to the current Open-Meteo implementation — treat the code as source of truth over that doc.

## Docs worth reading before analysis work

- `docs/DATA_SOURCES.md` — what each dataset measures and why it matters for NG price discovery (partially stale re: weather source, see above).
- `docs/PRICE_DISCOVERY.md` — the intended framework for combining the four datasets into a price narrative; this is the spec for the analysis notebooks that don't exist yet.
- `docs/LEARNING_LOG.md` — running research notes; check for context before duplicating analysis.
- `SETUP.md` — environment setup and troubleshooting for the pipeline scripts.
