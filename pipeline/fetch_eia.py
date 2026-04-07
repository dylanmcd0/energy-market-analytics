"""
fetch_eia.py — Download EIA natural gas storage data via the EIA API v2.

Fetches weekly working gas in underground storage and saves to:
  data/eia_storage.parquet

API documentation: https://www.eia.gov/opendata/

Series used
-----------
NG.NW2_EPG0_SWO_R48_BCF.W
  Weekly working gas in underground storage, Lower 48 states (Bcf)

NG.NW2_EPG0_SWO_R48_BCF.A (5-year average, weekly)
  This is not a direct API series; instead we compute the 5-year
  average in post-processing from the weekly history.

Requires
--------
Environment variable EIA_API_KEY (or .env file for local runs).
Register for a free key at: https://www.eia.gov/opendata/register.php
"""

import os
import sys
from datetime import date, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()  # Loads .env when running locally; no-op in CI where env vars are set

# EIA API v2 base URL
EIA_BASE_URL = "https://api.eia.gov/v2"

# Storage series: Lower 48 weekly working gas (Bcf)
STORAGE_SERIES = "NG.NW2_EPG0_SWO_R48_BCF.W"

OUTPUT_PATH = "data/eia_storage.parquet"
ROLLING_YEARS = 5


def fetch_eia_series(api_key: str, series_id: str, start: str, end: str) -> pd.DataFrame:
    """Fetch a single EIA v2 series and return a tidy DataFrame.

    The EIA v2 API uses a /seriesid/{id} endpoint that returns paginated
    JSON.  We request up to 5000 rows which is more than enough for a
    5-year weekly window (~260 observations).

    Args:
        api_key:   EIA API key.
        series_id: EIA series identifier string.
        start:     Start date string (YYYY-MM-DD).
        end:       End date string (YYYY-MM-DD).

    Returns:
        DataFrame with columns [date, value, series_id].

    Raises:
        SystemExit: If the API returns a non-200 response or empty data.
    """
    url = f"{EIA_BASE_URL}/seriesid/{series_id}"
    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "offset": 0,
        "length": 5000,
    }

    resp = requests.get(url, params=params, timeout=30)

    if resp.status_code != 200:
        print(
            f"ERROR: EIA API returned {resp.status_code} for {series_id}",
            file=sys.stderr,
        )
        print(f"Response: {resp.text[:500]}", file=sys.stderr)
        sys.exit(1)

    payload = resp.json()
    rows = payload.get("response", {}).get("data", [])

    if not rows:
        print(f"ERROR: EIA returned no data for series {series_id}", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame(rows)
    df = df.rename(columns={"period": "date", "value": "value"})
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["series_id"] = series_id
    return df[["date", "value", "series_id"]].sort_values("date").reset_index(drop=True)


def compute_5yr_average(df: pd.DataFrame) -> pd.DataFrame:
    """Compute a rolling 5-year average for each calendar week of the year.

    The EIA publishes a 5-year average for each storage week (EIA uses
    a 5-year rolling average of the same calendar week across the prior
    5 years).  We replicate that calculation here so the metric is
    available even if the EIA API doesn't expose it as a direct series.

    Args:
        df: DataFrame with columns [date, value] for the storage series.

    Returns:
        DataFrame with columns [date, value_5yr_avg] aligned to the same
        dates as the input.
    """
    df = df.copy()
    df["week"] = df["date"].dt.isocalendar().week.astype(int)
    df["year"] = df["date"].dt.year

    # For each row compute mean of the same ISO week across the prior 5 years
    def _avg(row: pd.Series) -> float:
        mask = (df["week"] == row["week"]) & (df["year"].between(row["year"] - 5, row["year"] - 1))
        return df.loc[mask, "value"].mean()

    df["value_5yr_avg"] = df.apply(_avg, axis=1)
    return df[["date", "value_5yr_avg"]]


def main() -> None:
    """Fetch EIA storage data and write to parquet."""
    api_key = os.environ.get("EIA_API_KEY", "")
    if not api_key:
        print("ERROR: EIA_API_KEY environment variable is not set.", file=sys.stderr)
        print("Register at https://www.eia.gov/opendata/register.php", file=sys.stderr)
        sys.exit(1)

    end_date = date.today().isoformat()
    # Fetch an extra year so the 5-yr average has enough history
    start_date = (date.today() - timedelta(days=(ROLLING_YEARS + 1) * 365)).isoformat()

    print(f"Fetching EIA storage series from {start_date} to {end_date}")
    storage = fetch_eia_series(api_key, STORAGE_SERIES, start_date, end_date)
    print(f"  {STORAGE_SERIES}: {len(storage)} rows")

    # Compute weekly net change in storage (current week minus prior week)
    storage = storage.rename(columns={"value": "working_gas_bcf"})
    storage["net_change_bcf"] = storage["working_gas_bcf"].diff()

    # Compute 5-year average for each calendar week
    avg_df = compute_5yr_average(storage.rename(columns={"working_gas_bcf": "value"}))
    storage = storage.merge(avg_df, on="date", how="left")

    # Trim to the requested rolling window (discard the extra year used for avg computation)
    cutoff = pd.Timestamp(date.today() - timedelta(days=ROLLING_YEARS * 365))
    storage = storage[storage["date"] >= cutoff].reset_index(drop=True)

    storage.to_parquet(OUTPUT_PATH, index=False)
    print(f"Saved {len(storage)} rows → {OUTPUT_PATH}")
    print(storage.tail(3).to_string())


if __name__ == "__main__":
    main()
