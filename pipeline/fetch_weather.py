"""
fetch_weather.py — Download weekly Heating and Cooling Degree Day data via Open-Meteo.

Fetches daily min/max temperatures from the Open-Meteo Historical Weather API
for a representative set of major US locations, computes HDD and CDD
(base 65°F), aggregates to ISO weeks, and saves to:
  data/degree_days.parquet

Why Open-Meteo?
----------------
Open-Meteo's historical weather archive is free, requires no API key or
registration, and returns a full date range in a single request (no
pagination), which is far faster and more reliable than the NOAA CDO API.

API documentation: https://open-meteo.com/en/docs/historical-weather-api

HDD / CDD definition
--------------------
  Daily avg temperature = (TMAX + TMIN) / 2  (in °F)
  HDD = max(0, 65 - avg_temp)
  CDD = max(0, avg_temp - 65)

Weekly HDD and CDD are the sum of daily values within each ISO week.

Stations
--------
A curated set of 12 major US locations is used to compute a simple
(unweighted) national average.  For production-grade analysis, population
or gas-demand weights should be applied.
"""

import sys
import time
from datetime import date, timedelta

import pandas as pd
import requests

# Open-Meteo Historical Weather API base URL
ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

OUTPUT_PATH = "data/degree_days.parquet"
ROLLING_YEARS = 2

REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5

# Representative major US locations (name, latitude, longitude).
# These span the key natural gas consuming regions of the country.
STATIONS = [
    ("New York City, NY", 40.7794, -73.9692),
    ("Boston, MA", 42.3656, -71.0096),
    ("Chicago, IL", 41.9786, -87.9048),
    ("Detroit, MI", 42.2124, -83.3534),
    ("Atlanta, GA", 33.6407, -84.4277),
    ("Houston, TX", 29.9902, -95.3368),
    ("Minneapolis, MN", 44.8848, -93.2223),
    ("Los Angeles, CA", 33.9382, -118.3865),
    ("Denver, CO", 39.8561, -104.6737),
    ("Seattle, WA", 47.4502, -122.3088),
    ("Dallas, TX", 32.8998, -97.0403),
    ("Miami, FL", 25.7959, -80.2870),
]


def fetch_station_data(
    station: str,
    lat: float,
    lon: float,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Fetch daily min/max temperature for one location from Open-Meteo.

    Args:
        station: Human-readable location name (used as station label).
        lat:     Latitude.
        lon:     Longitude.
        start:   Start date (YYYY-MM-DD).
        end:     End date (YYYY-MM-DD).

    Returns:
        DataFrame with columns [date, station, TMAX, TMIN].
        Returns an empty DataFrame on error or missing data.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "timezone": "America/New_York",
    }

    resp = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(ARCHIVE_BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
            break
        except requests.exceptions.RequestException as exc:
            if attempt == MAX_RETRIES - 1:
                print(
                    f"  WARNING: Open-Meteo request failed for {station} after "
                    f"{MAX_RETRIES} attempts ({exc}). Skipping.",
                    file=sys.stderr,
                )
                return pd.DataFrame()
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))

    if resp.status_code != 200:
        print(
            f"  WARNING: Open-Meteo returned {resp.status_code} for {station}. Skipping.",
            file=sys.stderr,
        )
        return pd.DataFrame()

    payload = resp.json()
    daily = payload.get("daily", {})
    dates = daily.get("time", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])

    if not dates:
        return pd.DataFrame()

    df = pd.DataFrame({"date": dates, "TMAX": tmax, "TMIN": tmin})
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["station"] = station
    return df[["date", "station", "TMAX", "TMIN"]]


def compute_hdd_cdd(daily_temps: pd.DataFrame) -> pd.DataFrame:
    """Compute daily HDD and CDD from TMIN/TMAX station data.

    Args:
        daily_temps: DataFrame with columns [date, station, TMAX, TMIN].

    Returns:
        DataFrame with columns [date, station, hdd, cdd].
    """
    pivot = daily_temps.dropna(subset=["TMAX", "TMIN"]).copy()
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
    """Fetch weather data, compute degree days, and write to parquet."""
    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=ROLLING_YEARS * 365)).isoformat()

    print(f"Fetching Open-Meteo historical data from {start_date} to {end_date}")
    print(f"Stations: {len(STATIONS)}")

    frames: list[pd.DataFrame] = []
    for station, lat, lon in STATIONS:
        print(f"  Fetching {station}...", end=" ")
        df = fetch_station_data(station, lat, lon, start_date, end_date)
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
