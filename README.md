# curve-lab

Natural gas spread analysis and modeling.

## Overview

curve-lab is a data pipeline and modeling project for natural gas markets.
It collects and maintains a rolling 5-year dataset covering:

- **NG Futures** — front month, next month, and 12-month deferred (via yfinance)
- **EIA Storage** — weekly working gas in storage, net change, 5-year average
- **NOAA Weather** — weekly heating degree days (HDD) and cooling degree days (CDD)
- **CFTC COT** — Commitments of Traders disaggregated report for NG futures

Data is stored as parquet files in `/data` and refreshed daily via GitHub Actions.

## Structure

```
curve-lab/
├── data/           # Parquet files (rolling 5-year window, overwritten daily)
├── pipeline/       # Data fetching scripts (one per source)
├── notebooks/      # Analysis notebooks
├── models/         # Spread and pricing models
└── site/           # Web output (future)
```

## Quick start

See [SETUP.md](SETUP.md) for environment setup, API key registration, and
instructions for running the pipeline locally.

