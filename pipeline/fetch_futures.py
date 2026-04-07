"""
fetch_futures.py — Download natural gas futures prices via yfinance.

Fetches daily OHLCV data for a rolling 5-year window and saves to:
  data/futures.parquet

Contracts fetched
-----------------
NG=F   : front-month continuous contract (Yahoo Finance synthetic roll)
NGK..  : individual monthly contracts for the current front month through
         the 12-month deferred, constructed from the CME contract code
         scheme (Month code + 2-digit year + ".NYM").

NG month codes (CME):
  F=Jan  G=Feb  H=Mar  J=Apr  K=May  M=Jun
  N=Jul  Q=Aug  U=Sep  V=Oct  X=Nov  Z=Dec

Yahoo Finance uses the pattern NGK25.NYM for the May-2025 contract.
Not all deferred months trade actively; we attempt each ticker and
silently skip any that return empty data.
"""

import sys
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

import pandas as pd
import yfinance as yf

# Path to output file
OUTPUT_PATH = "data/futures.parquet"

# Rolling window in years
ROLLING_YEARS = 5

# CME month codes (1-based index = calendar month)
MONTH_CODES = {
    1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
    7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z",
}


def build_ng_tickers(num_deferred: int = 13) -> list[str]:
    """Return a list of NG contract tickers from front month + num_deferred.

    Includes the continuous ticker NG=F plus individual month contracts
    from the current month through num_deferred months out.

    Args:
        num_deferred: Number of individual monthly contracts to include
                      (front month = 1, so 13 = front + 12 deferred).

    Returns:
        List of Yahoo Finance ticker strings.
    """
    tickers = ["NG=F"]
    today = date.today()

    for offset in range(num_deferred):
        target = today + relativedelta(months=offset)
        code = MONTH_CODES[target.month]
        # Yahoo uses a 2-digit year suffix, e.g. NGK25.NYM
        year_suffix = str(target.year)[-2:]
        tickers.append(f"NG{code}{year_suffix}.NYM")

    return tickers


def fetch_ohlcv(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Download OHLCV data for a single ticker and tag it with the ticker name.

    Args:
        ticker: Yahoo Finance ticker symbol.
        start:  Start date string (YYYY-MM-DD).
        end:    End date string (YYYY-MM-DD).

    Returns:
        DataFrame with columns [Open, High, Low, Close, Volume, ticker],
        indexed by Date. Returns an empty DataFrame if yfinance returns
        no data (e.g. contract has expired or doesn't exist yet).
    """
    raw = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )

    if raw.empty:
        return pd.DataFrame()

    # yfinance may return MultiIndex columns when a single ticker is passed;
    # flatten to simple column names.
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.droplevel(1)

    df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index.name = "Date"
    df["ticker"] = ticker
    return df


def main() -> None:
    """Fetch all NG futures contracts and write to parquet."""
    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=ROLLING_YEARS * 365)).isoformat()

    tickers = build_ng_tickers(num_deferred=13)
    print(f"Fetching {len(tickers)} tickers from {start_date} to {end_date}")

    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        df = fetch_ohlcv(ticker, start_date, end_date)
        if df.empty:
            print(f"  {ticker}: no data (skipped)")
        else:
            print(f"  {ticker}: {len(df)} rows")
            frames.append(df)

    if not frames:
        print("ERROR: No data returned for any ticker.", file=sys.stderr)
        sys.exit(1)

    combined = pd.concat(frames).sort_index()
    combined.to_parquet(OUTPUT_PATH, index=True)
    print(f"Saved {len(combined)} rows → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
