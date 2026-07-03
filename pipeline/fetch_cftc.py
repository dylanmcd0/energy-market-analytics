"""
fetch_cftc.py — Download CFTC Commitments of Traders (COT) data for NG futures.

Downloads the annual disaggregated futures COT flat files (zip archives) from
the CFTC website, filters to natural gas (market code 023651), retains the
relevant columns, and saves a rolling 5-year window to:
  data/cftc_cot.parquet

CFTC flat file documentation:
  https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalViewable/index.htm

File URL pattern (disaggregated futures+options):
  https://www.cftc.gov/files/dea/history/fut_disagg_txt_{YYYY}.zip

The disaggregated report breaks trader positions into:
  - Producer/Merchant/Processor/User  (often called "commercial")
  - Swap Dealers
  - Managed Money                     (hedge funds / CTAs — the "speculator" bucket)
  - Other Reportables
  - Non-Reportable (small traders)

For natural gas spread modeling the most useful metrics are:
  - Managed money net position (long - short): proxy for speculative sentiment
  - Producer net position: proxy for hedging pressure
  - Open interest: market size / liquidity
"""

import io
import sys
import zipfile
from datetime import date

import pandas as pd
import requests

OUTPUT_PATH = "data/cftc_cot.parquet"
ROLLING_YEARS = 2

# CFTC market code for Henry Hub Natural Gas futures (NYMEX)
NG_MARKET_CODE = "023651"

# Base URL for annual disaggregated futures flat files
CFTC_URL_TEMPLATE = (
    "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"
)

# Columns to retain from the raw file (all others are dropped)
KEEP_COLUMNS = [
    "Market_and_Exchange_Names",
    "As_of_Date_In_Form_YYMMDD",
    "CFTC_Market_Code",
    "Open_Interest_All",
    # Producer / Merchant / Processor / User
    "Prod_Merc_Positions_Long_All",
    "Prod_Merc_Positions_Short_All",
    # Swap Dealers
    "Swap__Positions_Long_All",
    "Swap__Positions_Short_All",
    # Managed Money (speculative)
    "M_Money_Positions_Long_All",
    "M_Money_Positions_Short_All",
    # Other Reportables
    "Other_Rept_Positions_Long_All",
    "Other_Rept_Positions_Short_All",
    # Non-Reportable (small traders)
    "NonRept_Positions_Long_All",
    "NonRept_Positions_Short_All",
    # Spread positions (within a single category)
    "M_Money_Positions_Spread_All",
    "Swap__Positions_Spread_All",
]


def download_year(year: int) -> pd.DataFrame:
    """Download and parse the CFTC disaggregated COT file for a single year.

    The CFTC publishes one zip archive per calendar year containing a single
    CSV.  We download the archive, read the CSV in memory, and filter to the
    natural gas market code.

    Args:
        year: Calendar year (e.g. 2024).

    Returns:
        DataFrame filtered to NG futures rows, or an empty DataFrame if the
        year's file is not yet available or the download fails.
    """
    url = CFTC_URL_TEMPLATE.format(year=year)
    try:
        resp = requests.get(url, timeout=60)
    except requests.RequestException as exc:
        print(f"  WARNING: Network error fetching {url}: {exc}", file=sys.stderr)
        return pd.DataFrame()

    if resp.status_code == 404:
        # Year file not yet published (common for the upcoming year)
        print(f"  {year}: file not found (404), skipping")
        return pd.DataFrame()

    if resp.status_code != 200:
        print(
            f"  WARNING: CFTC returned {resp.status_code} for {year}", file=sys.stderr
        )
        return pd.DataFrame()

    # The zip archive contains a single .txt CSV file
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        # Find the first .txt file inside the archive
        txt_files = [n for n in zf.namelist() if n.endswith(".txt")]
        if not txt_files:
            print(f"  WARNING: No .txt file found in CFTC zip for {year}", file=sys.stderr)
            return pd.DataFrame()

        with zf.open(txt_files[0]) as f:
            raw = pd.read_csv(f, low_memory=False)

    # Filter to natural gas futures (market code column name may vary slightly)
    code_col = next(
        (c for c in raw.columns if "CFTC_Market_Code" in c or "Commodity_Code" in c),
        None,
    )
    if code_col is None:
        print(f"  WARNING: Could not find market code column in {year} file", file=sys.stderr)
        return pd.DataFrame()

    raw[code_col] = raw[code_col].astype(str).str.strip()
    ng = raw[raw[code_col] == NG_MARKET_CODE].copy()

    if ng.empty:
        print(f"  {year}: no NG rows found")
        return pd.DataFrame()

    # Retain only the columns we care about (skip missing ones gracefully)
    cols_present = [c for c in KEEP_COLUMNS if c in ng.columns]
    return ng[cols_present].copy()


def clean_cot(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise column names and data types on the combined COT DataFrame.

    Args:
        df: Raw combined DataFrame from all yearly downloads.

    Returns:
        Cleaned DataFrame with a proper datetime 'date' column and numeric
        position columns, sorted ascending by date.
    """
    df = df.copy()

    # Parse the CFTC date field (YYMMDD integer, e.g. 240105 = 2024-01-05)
    date_col = "As_of_Date_In_Form_YYMMDD"
    if date_col in df.columns:
        df["date"] = pd.to_datetime(df[date_col].astype(str), format="%y%m%d", errors="coerce")
        df = df.drop(columns=[date_col])

    # Coerce all position columns to numeric
    numeric_cols = [c for c in df.columns if c not in ("date", "Market_and_Exchange_Names", "CFTC_Market_Code")]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derived net position columns (long minus short per category)
    if {"M_Money_Positions_Long_All", "M_Money_Positions_Short_All"}.issubset(df.columns):
        df["managed_money_net"] = (
            df["M_Money_Positions_Long_All"] - df["M_Money_Positions_Short_All"]
        )
    if {"Prod_Merc_Positions_Long_All", "Prod_Merc_Positions_Short_All"}.issubset(df.columns):
        df["producer_net"] = (
            df["Prod_Merc_Positions_Long_All"] - df["Prod_Merc_Positions_Short_All"]
        )

    return df.sort_values("date").reset_index(drop=True)


def main() -> None:
    """Download CFTC COT data for the rolling 5-year window and write to parquet."""
    current_year = date.today().year
    years = list(range(current_year - ROLLING_YEARS, current_year + 1))

    print(f"Downloading CFTC disaggregated COT for years: {years}")

    frames: list[pd.DataFrame] = []
    for year in years:
        print(f"  {year}...", end=" ")
        df = download_year(year)
        if not df.empty:
            print(f"{len(df)} rows")
            frames.append(df)

    if not frames:
        print("ERROR: No CFTC COT data downloaded.", file=sys.stderr)
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)
    combined = clean_cot(combined)

    # Trim to the rolling window
    cutoff = pd.Timestamp(date.today().replace(year=date.today().year - ROLLING_YEARS))
    combined = combined[combined["date"] >= cutoff].reset_index(drop=True)

    combined.to_parquet(OUTPUT_PATH, index=False)
    print(f"Saved {len(combined)} rows → {OUTPUT_PATH}")
    print(combined.tail(3).to_string())


if __name__ == "__main__":
    main()
