# Natural Gas Price Discovery

A working document on how the four data sources collectively inform natural gas prices and where to find actionable signals.

---

## The Natural Gas Price Equation (Simplified)

```
NG Price = f(Demand, Supply, Storage, Expectations, Sentiment)
```

Where:
- **Demand** = HDD (heating/cooling needs) + Industrial + Electric generation
- **Supply** = Production + Imports + Withdrawals from storage
- **Storage** = "Swing supply" — inventory that can be injected/withdrawn
- **Expectations** = Forward contract prices (term structure)
- **Sentiment** = COT positioning, speculative flows

---

## Data → Price Signal Mapping

### 1. Futures Prices (Leading/Contemporaneous)

**What the market is pricing in RIGHT NOW:**

- **Spot (NG=F):** Reflects immediately available supply/demand balance
- **1-month vs. 12-month spread:** Reveals structural expectations
  - Steep backwardation (front higher): Tight near-term supply → upside risk
  - Contango (front lower): Ample supply → downside risk
- **Volatility:** Regime shifts when uncertainty spikes (e.g., production shut-ins, extreme weather forecasts)

**How to use it:**
- Baseline for "what are traders actually paying?" — necessary input for any fundamental analysis
- Term structure changes can precede spot moves by days/weeks

---

### 2. Storage Levels (Supply Buffer)

**The "cushion" between price stability and chaos:**

Natural gas is **stockable** (unlike electricity) → storage is the swing supply that smooths seasonal demand swings.

**Key relationships:**

| Storage Level | Interpretation | Price Pressure |
|---|---|---|
| Near 5-yr avg | Normal; comfortable supply | Neutral |
| Significantly above 5-yr avg | Excess supply building | Bearish |
| Significantly below 5-yr avg | Depleting; potential tightness | Bullish |
| At seasonal lows (end of winter) | Risk of supply emergency | Very bullish |

**Historical signals:**
- [ ] Document: instances where storage diverged from seasonal normal and price impacts
- [ ] Question: How fast can storage be mobilized? (Injection/withdrawal capacity constraints)

---

### 3. Heating Degree Days (Demand Shock)

**The most powerful price driver (in winter):**

HDD is **exogenous** (weather) and **binary** (you either need heat or you don't).

**Relationship to price:**

1. **Unexpected cold snap:** 
   - HDD forecast rises sharply
   - Forward prices spike immediately
   - Storage withdrawal rates surge
   
2. **Warm winter:**
   - HDD below normal
   - Prices depressed
   - Storage builds faster than normal → bearish

**Dynamics to understand:**
- [ ] Forecast revisions matter more than absolute HDD (surprise = volatility)
- [ ] Regional granularity: Northeast winters hit differently than Texas
- [ ] Lead time: How far ahead does the market price in weather? (Typically 7-10 days out)

---

### 4. COT Positioning (Sentiment/Leverage)

**The "consensus" view, and when it breaks:**

COT tells you how much leverage is in the market and on which side.

**Interpretation:**

- **Managed Money Net Long (extreme):** 
  - Speculators are crowded long
  - Historically precedes reversals (overstretched positions get squeezed)
  - Risk: sudden liquidation cascade
  
- **Producer Net Short (holding hedges):**
  - Producers are protected (afraid of falling prices)
  - Indicates bearish sentiment from supply side
  - If they cover shorts → demand for futures → price support
  
- **Dealer Net Position (usually contrarian):**
  - Dealers absorb imbalances
  - Often lean against crowd sentiment
  - Extreme dealer long can be market bottom signal

**How to use it:**
- [ ] Backtest: correlate COT extremes with subsequent 2-week, 4-week, 8-week price moves
- [ ] Identify: what do producer short extremes tell you about forward supply expectations?

---

## Putting It Together: A Price Analysis Framework

### Step 1: Read the Spot & Term Structure
- Where is NG=F trading? Up or down week-over-week?
- Is the curve in backwardation (tight) or contango (ample)?
- Volatility: rising or falling?

### Step 2: Check Storage Status
- Where is storage vs. 5-year normal?
- What was the weekly build/draw?
- Is the injection/withdrawal rate sustainable?

### Step 3: Look at the Weather Forecast
- What is next week's HDD forecast vs. normal?
- How far out is the forecast confident?
- Any extremes (unseasonably hot/cold)?

### Step 4: Assess Positioning
- Where is managed money? Are they crowded?
- What is producer hedging ratio?
- Dealer leaning long or short?

### Step 5: Synthesize
- Are all signals aligned (bullish storage + cold HDD + bullish positioning)?
- Or are there divergences (storage low but prices weak)? → opportunity or red flag?

---

## Historical Case Studies

Use this section to document real examples as you learn:

### Case: [Date] — [Event]
**Setup:** What was the state of storage, weather, COT, prices?

**Catalyst:** What happened?

**Result:** How did prices respond? Why?

**Lesson:** What did you learn?

---

## TODO: Analyses to Run

- [ ] Correlation matrix: HDD vs. price, storage vs. price, COT extremes vs. 2-week forward returns
- [ ] Seasonality decomposition: strip out seasonal patterns to see structural trends
- [ ] Storage pulse metric: is storage changing faster/slower than 5-yr average?
- [ ] Term structure regime: identify contango vs. backwardation periods and their duration
- [ ] Producer hedging ratio: derive implied views on forward supply from COT data

---

## Resources

- EIA Natural Gas Fundamentals: https://www.eia.gov/energyexplained/natural-gas/
- NYMEX NG Contract Specs: https://www.cmegroup.com/
- NOAA Climate Normals: https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals
- CFTC COT Reports: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
