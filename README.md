# energy-market-analytics

Learning US energy markets through data and analysis.

A data pipeline and analysis toolkit for understanding natural gas markets:
fundamentals, spreads, seasonality, and positioning.

## Data sources

- **NG Futures** — prices (via yfinance)
- **EIA Storage** — weekly inventory
- **NOAA Weather** — heating/cooling degree days
- **CFTC COT** — trader positioning

## Structure

```
├── pipeline/       # Data fetching (runs daily via GitHub Actions)
├── data/           # Parquet files (5-year rolling window)
├── analysis/       # Notebooks exploring energy fundamentals
└── .github/        # Automation
```

## Next: Build analysis notebooks

See [SETUP.md](SETUP.md) to get data pipelines running, then we'll build
analysis notebooks one at a time.

