# Data Sources & Pipeline

This document describes each data source fetched by the pipeline, what it measures, and why it matters for natural gas price discovery.

## Overview

The pipeline ingests four complementary datasets that collectively provide signals about natural gas supply, demand, sentiment, and market structure:

| Data Source | Frequency | What It Measures | Pipeline Script |
|---|---|---|---|
| Futures Prices | Daily | Current and forward market prices across contract months | `fetch_futures.py` |
| Storage Levels | Weekly | Underground inventory (physical supply buffer) | `fetch_eia.py` |
| Degree Days | Weekly | Temperature-driven demand proxy | `fetch_noaa.py` |
| COT Positions | Weekly | Large trader positioning and sentiment | `fetch_cftc.py` |

---

## 1. Natural Gas Futures Prices

**Source:** Yahoo Finance (CME NYMEX contracts via yfinance)

**What it measures:**
- Daily OHLCV (Open, High, Low, Close, Volume) for NG=F (front-month continuous) and 13 monthly contract expirations
- Rolling 5-year window to capture full cycle of seasonal variation

**How it informs pricing:**
- The term structure (spread between front-month and deferred contracts) signals expectations about future supply/demand
- Volatility and volume patterns reveal periods of market stress or uncertainty
- Seasonal patterns are fundamental to natural gas (heating in winter, minimal demand in summer)

**Key learnings to document:**
- [ ] Why front-month vs. deferred spreads matter
- [ ] Seasonality patterns and their drivers
- [ ] How to interpret contango vs. backwardation in NG

---

## 2. EIA Weekly Storage Levels

**Source:** EIA (U.S. Energy Information Administration) API

**What it measures:**
- Working gas in underground storage (Lower 48 states, in Bcf = billion cubic feet)
- Weekly net change in inventory
- 5-year historical average for the same calendar week (benchmark for "normal" levels)

**How it informs pricing:**
- High storage → excess supply → downward pressure on prices
- Low storage → tight supply → upward pressure on prices
- Deviation from 5-year average signals structural imbalance (e.g., unusually warm winter → excess inventory)
- Storage "cushion" protects against supply shocks

**Key learnings to document:**
- [ ] Storage withdrawal/injection seasons (summer vs. winter)
- [ ] How storage levels relate to price spikes historically
- [ ] Why the 5-year average is the market's baseline expectation

---

## 3. NOAA Heating & Cooling Degree Days

**Source:** NOAA Climate Data Online (CDO) API

**What it measures:**
- Daily TMIN/TMAX from 12 major US weather stations
- Aggregated to weekly heating degree days (HDD) and cooling degree days (CDD)
- HDD = max(0, 65°F - avg_temp); CDD = max(0, avg_temp - 65°F)

**How it informs pricing:**
- HDD is the primary demand driver for natural gas (space heating in winter)
- Unexpectedly cold weather → surge in demand → prices spike
- CDD matters less for NG (air conditioning is electric-dominated), but included for completeness
- Week-ahead weather forecasts are a major source of intraweek volatility

**Key learnings to document:**
- [ ] How weather forecasts affect forward prices
- [ ] Historical correlation between HDD and price moves
- [ ] Regional variations (Northeast vs. Southwest heating demand)

---

## 4. CFTC Commitments of Traders (COT)

**Source:** CFTC (Commodity Futures Trading Commission)

**What it measures:**
- Weekly positions of major trader categories in NG futures:
  - **Producers/Merchants:** Commercial hedgers (supply-side)
  - **Swap Dealers:** Financial intermediaries
  - **Managed Money:** Hedge funds and CTAs (speculators)
  - **Other Reportables & Non-Reportable:** Smaller traders
- Net positions (long contracts - short contracts) for each category

**How it informs pricing:**
- Managed money net long position is a sentiment indicator; extreme longs can signal bubble risk
- Producer positioning signals hedging pressure (if short, indicates fear of falling prices)
- Dealer net position is often contrarian (dealers lean against prevailing trends)
- COT extremes historically precede reversals

**Key learnings to document:**
- [ ] How to interpret managed money extremes
- [ ] Producer hedging behavior and price signals
- [ ] Historical COT-to-price correlations

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────┐
│ GitHub Actions (Daily @ 14:00 UTC)                      │
│ Trigger: schedule or manual workflow_dispatch            │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬───────────────┐
        │             │             │               │
   ┌────▼────┐   ┌────▼────┐  ┌────▼────┐   ┌─────▼────┐
   │ Futures │   │ Storage │  │ Weather │   │   COT    │
   │ (Yahoo) │   │ (EIA)   │  │ (NOAA)  │   │ (CFTC)   │
   └────┬────┘   └────┬────┘  └────┬────┘   └─────┬────┘
        │             │             │               │
        └─────────────┼─────────────┴───────────────┘
                      │
            ┌─────────▼─────────┐
            │  data/*.parquet   │
            │  (versioned in    │
            │  git for analysis)│
            └───────────────────┘
```

---

## Next Steps

To deepen your understanding of how these datasets work together to forecast or explain price moves:

1. Pick one data source and trace its relationship to a recent price move
2. Document your findings in the relevant section above
3. Create correlation analysis between sources (e.g., HDD vs. price, COT extremes vs. reversals)
