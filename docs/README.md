# Documentation & Learning

This directory contains working documentation on natural gas market fundamentals, data sources, price discovery mechanisms, and your learning journey as you analyze the market.

## Quick Navigation

- **[DATA_SOURCES.md](DATA_SOURCES.md)** — What each data pipeline measures and why it matters
  - Futures prices, storage levels, weather/HDD, and COT positioning
  - Architecture and data flow diagram
  
- **[PRICE_DISCOVERY.md](PRICE_DISCOVERY.md)** — How the four datasets work together to explain/forecast prices
  - The price equation and signal mapping
  - Framework for analyzing market conditions
  - Case studies (to be filled in)
  - Backtesting ideas

- **[LEARNING_LOG.md](LEARNING_LOG.md)** — Your research notebook
  - Log findings and insights as you analyze data
  - Questions waiting for data / validation
  - Aha moments and resource tracking

---

## How to Use These Docs

These are **living documents**. Think of them as scaffolding for your learning:

1. **Start with DATA_SOURCES** if you want to understand what data you're fetching and why
2. **Move to PRICE_DISCOVERY** to see how it all fits together
3. **Use LEARNING_LOG** to document your own analysis and questions

As you work with the data:
- Update the checklists (✓ items you've validated)
- Add case studies when you find interesting patterns
- Fill in the "TODO" analyses as you complete them
- Log insights in the learning log

---

## The Big Picture

The pipeline fetches four complementary views of the natural gas market:

| Dataset | Frequency | What It Shows |
|---------|-----------|---------------|
| **Futures** | Daily | Current price consensus across contract months |
| **Storage** | Weekly | Supply cushion and inventory trends |
| **Weather (HDD)** | Weekly | Temperature-driven demand |
| **COT** | Weekly | Large trader positioning and sentiment |

Together, these reveal:
- **What happened** (prices, inventory flows, positioning)
- **Why it happened** (weather, supply/demand imbalance, leverage)
- **What might happen next** (price momentum, sentiment extremes, storage depletion risk)

---

## Example Analysis Flow

1. Notice futures prices spiked last week
2. Check: Was HDD above normal? (demand shock?)
3. Check: Is storage below normal? (supply tight?)
4. Check: What did COT show? (speculative accumulation = crash risk?)
5. Synthesize: Price spike justified by fundamentals, or built on speculation?
6. Log your finding and test your hypothesis over time

---

## Resources

- **EIA Natural Gas Fundamentals:** https://www.eia.gov/energyexplained/natural-gas/
- **CME NG Futures:** https://www.cmegroup.com/ (contract specs, open interest, volume)
- **NOAA Weather Data:** https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals
- **CFTC Commitments of Traders:** https://www.cftc.gov/MarketReports/CommitmentsofTraders/

---

## Next Steps

- [ ] Complete one full analysis using all four data sources (see PRICE_DISCOVERY framework)
- [ ] Document your first case study
- [ ] Identify one backtesting hypothesis and test it
- [ ] Write up one "aha moment" in LEARNING_LOG
