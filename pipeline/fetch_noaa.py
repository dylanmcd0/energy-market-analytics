"""
fetch_noaa.py — Download weekly Heating and Cooling Degree Day data via NOAA.

Fetches daily TMIN/TMAX from the NOAA Climate Data Online (CDO) API v2 for a
representative set of major US stations, computes HDD and CDD (base 65°F),
aggregates to ISO weeks, and saves to:
  data/noaa_degree_days.parquet

Why CDO API?
------------
The NOAA CDO API provides structured, quality-controlled station data.  A free
API token is required (instant registration — see SETUP.md).  The token is
stored as GitHub secret NOAA_CDO_TOKEN.

API documentation: https://www.ncdc.noaa.gov/cdo-web/webservices/v2

HDD / CDD definition
--------------------
  Daily avg temperature = (TMAX + TMIN) / 2  (in °F)
  HDD = max(0, 65 - avg_temp)
  CDD = max(0, avg_temp - 65)

Weekly HDD and CDD are the sum of daily values within each ISO week.

Stations
--------
A curated set of 12 major US stations is used to compute a simple
(unweighted) national average.  For production-grade analysis, population
or gas-demand weights should be applied.

Requires
--------
Environment variable NOAA_CDO_TOKEN (or .env file for local runs).
Register at: https://www.ncdc.noaa.gov/cdo-web/token
"""

import os
import sys
import time
from datetime import date, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# NOAA CDO API base URL
CDO_BASE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"

# CDO API returns at most 1000 records per call; we paginate automatically.
CDO_PAGE_SIZE = 1000

OUTPUT_PATH = "data/noaa_degree_days.parquet"
ROLLING_YEARS = 2

# Representative major US stations (GHCND station IDs).
# These span the key natural gas consuming regions of the country.
STATIONS = [
    "GHCND:USW00094728",  # New York City (Central Park), NY
    "GHCND:USW00014742",  # Boston Logan, MA
    "GHCND:USW00094847",  # Chicago O'Hare, IL
    "GHCND:USW00014739",  # Detroit Metro, MI
    "GHCND:USW00013880",  # Atlanta Hartsfield, GA
    "GHCND:USW00012960",  # Houston Intercontinental, TX
    "GHCND:USW00014918",  # Minneapolis-St. Paul, MN
    "GHCND:USW00023174",  # Los Angeles, CA
    "GHCND:USW00093721",  # Denver, CO
    "GHCND:USW00023234",  # Seattle-Tacoma, WA
    "GHCND:USW00013958",  # Dallas/Fort Worth, TX
    "GHCND:USW00013994",  # Miami, FL
]


def fetch_cdo_data(
    token: str,
    station_id: str,
    datatype_ids: list[str],
    start: str,
    end: str,
) -> pd.DataFrame:
    """Fetch daily data for one station from the NOAA CDO API with pagination.

    The CDO API caps responses at 1000 records per request.  This function
    pages through the full result set automatically.

    Args:
        token:        NOAA CDO API token.
        station_id:   CDO station identifier (e.g. "GHCND:USW00094728").
        datatype_ids: List of CDO datatype IDs to request (e.g. ["TMAX","TMIN"]).
        start:        Start date (YYYY-MM-DD).
        end:          End date (YYYY-MM-DD).

    Returns:
        DataFrame with columns [date, datatype, value, station].
        Returns an empty DataFrame if the station returns no data.
    """
    headers = {"token": token}
    base_params = {
        "datasetid": "GHCND",
        "stationid": station_id,
        "datatypeid": ",".join(datatype_ids),
        "startdate": start,
        "enddate": end,
        "units": "standard",  # Fahrenheit / inches
        "limit": CDO_PAGE_SIZE,
    }

    all_rows: list[dict] = []
    offset = 1  # CDO uses 1-based offset

    while True:
        params = {**base_params, "offset": offset}
        resp = requests.get(
            f"{CDO_BASE_URL}/data",
            headers=headers,
            params=params,
            timeout=30,
        )

        # 400 can mean no data for this station/period; treat as empty
        if resp.status_code == 400:
            break

        if resp.status_code != 200:
            print(
                f"  WARNING: CDO returned {resp.status_code} for {station_id} "
                f"(offset={offset}). Skipping.",
                file=sys.stderr,
            )
            break

        payload = resp.json()
        results = payload.get("results", [])
        if not results:
            break

        all_rows.extend(results)

        # Check if there are more pages
        metadata = payload.get("metadata", {}).get("resultset", {})
        total = int(metadata.get("count", 0))
        if offset + CDO_PAGE_SIZE > total:
            break

        offset += CDO_PAGE_SIZE
        # Be polite to the CDO API (5 req/s limit)
        time.sleep(0.25)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["station"] = station_id
    return df[["date", "datatype", "value", "station"]]


def compute_hdd_cdd(daily_temps: pd.DataFrame) -> pd.DataFrame:
    """Compute daily HDD and CDD from TMIN/TMAX station data.

    Pivots the long-format temperature data, computes average daily temp,
    then derives HDD and CDD with a 65°F base.

    Args:
        daily_temps: DataFrame with columns [date, datatype, value, station]
                     containing TMIN and TMAX records.

    Returns:
        DataFrame with columns [date, station, hdd, cdd].
    """
    pivot = daily_temps.pivot_table(
        index=["date", "station"], columns="datatype", values="value", aggfunc="mean"
    ).reset_index()

    # Require both TMAX and TMIN to be present for a valid observation
    pivot = pivot.dropna(subset=["TMAX", "TMIN"])
    pivot["tavg"] = (pivot["TMAX"] + pivot["TMIN"]) / 2.0
    pivot["hdd"] = (65.0 - pivot["tavg"]).clip(lower=0.0)
    pivot["cdd"] = (pivot["tavg"] - 65.0).clip(lower=0.0)

    return pivot[["date", "station", "hdd", "cdd"]]


def aggregate_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily HDD/CDD to ISO weekly means across all stations.

    Takes the simple mean across stations each day, then sums within each
    ISO week (Mon–Sun).

    Args:
        daily: DataFrame with columns [date, station, hdd, cdd].

    Returns:
        DataFrame with columns [week_start, hdd_weekly, cdd_weekly] where
        week_start is the Monday of each ISO week.
    """
    # Average across stations per day
    daily_avg = (
        daily.groupby("date")[["hdd", "cdd"]].mean().reset_index()
    )

    # ISO week label — set period to Monday of the week
    daily_avg["week_start"] = daily_avg["date"] - pd.to_timedelta(
        daily_avg["date"].dt.dayofweek, unit="D"
    )

    # Sum daily HDD/CDD within each week
    weekly = (
        daily_avg.groupby("week_start")[["hdd", "cdd"]]
        .sum()
        .rename(columns={"hdd": "hdd_weekly", "cdd": "cdd_weekly"})
        .reset_index()
    )

    return weekly.sort_values("week_start").reset_index(drop=True)


def main() -> None:
    """Fetch NOAA temperature data, compute degree days, and write to parquet."""
    token = os.environ.get("NOAA_CDO_TOKEN", "")
    if not token:
        print("ERROR: NOAA_CDO_TOKEN environment variable is not set.", file=sys.stderr)
        print("Register at https://www.ncdc.noaa.gov/cdo-web/token", file=sys.stderr)
        sys.exit(1)

    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=ROLLING_YEARS * 365)).isoformat()

    print(f"Fetching NOAA CDO data from {start_date} to {end_date}")
    print(f"Stations: {len(STATIONS)}")

    frames: list[pd.DataFrame] = []
    for station in STATIONS:
        print(f"  Fetching {station}...", end=" ")
        df = fetch_cdo_data(token, station, ["TMAX", "TMIN"], start_date, end_date)
        if df.empty:
            print("no data (skipped)")
        else:
            print(f"{len(df)} records")
            frames.append(df)

    if not frames:
        print("ERROR: No temperature data returned from any station.", file=sys.stderr)
        sys.exit(1)

    all_temps = pd.concat(frames, ignore_index=True)
    daily = compute_hdd_cdd(all_temps)
    weekly = aggregate_weekly(daily)

    weekly.to_parquet(OUTPUT_PATH, index=False)
    print(f"Saved {len(weekly)} weekly rows → {OUTPUT_PATH}")
    print(weekly.tail(5).to_string())


if __name__ == "__main__":
    main()
