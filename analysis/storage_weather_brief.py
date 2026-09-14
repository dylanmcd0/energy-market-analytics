"""Generate a reproducible weekly natural gas storage and weather brief."""

from __future__ import annotations

import argparse
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "energy-market-analytics-mpl"))

import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_STORAGE_PATH = Path("data/eia_storage.parquet")
DEFAULT_WEATHER_PATH = Path("data/degree_days.parquet")
DEFAULT_OUTPUT_DIR = Path("docs/briefs")
MAX_WEATHER_STALENESS_DAYS = 7


@dataclass(frozen=True)
class BriefMetrics:
    storage_date: pd.Timestamp
    storage_week_start: pd.Timestamp
    weather_week_start: pd.Timestamp
    weather_staleness_days: int
    weather_is_stale: bool
    working_gas_bcf: float
    net_change_bcf: float
    storage_5yr_avg_bcf: float
    storage_5yr_count: int | None
    storage_vs_5yr_bcf: float
    storage_vs_5yr_pct: float
    year_ago_bcf: float | None
    storage_vs_year_ago_bcf: float | None
    hdd_weekly: float
    cdd_weekly: float
    hdd_5yr_avg: float | None
    cdd_5yr_avg: float | None
    hdd_avg_count: int
    cdd_avg_count: int
    hdd_vs_5yr: float | None
    cdd_vs_5yr: float | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the latest storage/weather Markdown brief."
    )
    parser.add_argument("--storage", type=Path, default=DEFAULT_STORAGE_PATH)
    parser.add_argument("--weather", type=Path, default=DEFAULT_WEATHER_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--charts-dir",
        type=Path,
        default=None,
        help="Directory for chart PNGs. Defaults to a date-specific assets directory under --output-dir.",
    )
    return parser.parse_args()


def load_storage(path: Path) -> pd.DataFrame:
    storage = pd.read_parquet(path).copy()
    required = {"date", "working_gas_bcf", "net_change_bcf", "value_5yr_avg"}
    missing = required - set(storage.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    storage["date"] = pd.to_datetime(storage["date"]).dt.normalize()
    return storage.sort_values("date").reset_index(drop=True)


def load_weather(path: Path) -> pd.DataFrame:
    weather = pd.read_parquet(path).copy()
    required = {"week_start", "hdd_weekly", "cdd_weekly"}
    missing = required - set(weather.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    weather["week_start"] = pd.to_datetime(weather["week_start"]).dt.normalize()
    return weather.sort_values("week_start").reset_index(drop=True)


def same_iso_week_prior_year(df: pd.DataFrame, date_col: str, target: pd.Timestamp) -> pd.Series | None:
    target_iso = target.isocalendar()
    dates = pd.to_datetime(df[date_col])
    iso = dates.dt.isocalendar()
    match = df[(iso.week == target_iso.week) & (iso.year == target_iso.year - 1)]
    if match.empty:
        return None
    return match.iloc[-1]


def same_week_average(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    target: pd.Timestamp,
    years: int = 5,
) -> tuple[float | None, int]:
    target_iso = target.isocalendar()
    dates = pd.to_datetime(df[date_col])
    iso = dates.dt.isocalendar()
    mask = (iso.week == target_iso.week) & (
        iso.year.between(target_iso.year - years, target_iso.year - 1)
    )
    values = df.loc[mask, value_col].dropna()
    if values.empty:
        return None, 0
    return float(values.mean()), int(values.count())


def build_metrics(storage: pd.DataFrame, weather: pd.DataFrame) -> BriefMetrics:
    latest_storage = storage.dropna(subset=["working_gas_bcf"]).iloc[-1]
    storage_date = pd.Timestamp(latest_storage["date"]).normalize()
    storage_week_start = storage_date - pd.to_timedelta(storage_date.dayofweek, unit="D")

    weather_candidates = weather[weather["week_start"] <= storage_week_start]
    if weather_candidates.empty:
        raise ValueError("No weather rows are available on or before the latest storage week.")

    latest_weather = weather_candidates.iloc[-1]
    weather_week_start = pd.Timestamp(latest_weather["week_start"]).normalize()
    weather_staleness_days = int((storage_week_start - weather_week_start).days)
    weather_is_stale = weather_staleness_days > MAX_WEATHER_STALENESS_DAYS

    storage_5yr_avg = float(latest_storage["value_5yr_avg"])
    working_gas = float(latest_storage["working_gas_bcf"])
    storage_vs_5yr = working_gas - storage_5yr_avg
    storage_vs_5yr_pct = storage_vs_5yr / storage_5yr_avg * 100

    year_ago = same_iso_week_prior_year(storage, "date", storage_date)
    year_ago_bcf = None if year_ago is None else float(year_ago["working_gas_bcf"])
    storage_vs_year_ago = None if year_ago_bcf is None else working_gas - year_ago_bcf

    hdd_5yr_avg, hdd_avg_count = same_week_average(
        weather, "week_start", "hdd_weekly", weather_week_start
    )
    cdd_5yr_avg, cdd_avg_count = same_week_average(
        weather, "week_start", "cdd_weekly", weather_week_start
    )

    hdd = float(latest_weather["hdd_weekly"])
    cdd = float(latest_weather["cdd_weekly"])

    return BriefMetrics(
        storage_date=storage_date,
        storage_week_start=storage_week_start,
        weather_week_start=weather_week_start,
        weather_staleness_days=weather_staleness_days,
        weather_is_stale=weather_is_stale,
        working_gas_bcf=working_gas,
        net_change_bcf=float(latest_storage["net_change_bcf"]),
        storage_5yr_avg_bcf=storage_5yr_avg,
        storage_5yr_count=(
            int(latest_storage["value_5yr_count"])
            if "value_5yr_count" in latest_storage.index and pd.notna(latest_storage["value_5yr_count"])
            else None
        ),
        storage_vs_5yr_bcf=storage_vs_5yr,
        storage_vs_5yr_pct=storage_vs_5yr_pct,
        year_ago_bcf=year_ago_bcf,
        storage_vs_year_ago_bcf=storage_vs_year_ago,
        hdd_weekly=hdd,
        cdd_weekly=cdd,
        hdd_5yr_avg=hdd_5yr_avg,
        cdd_5yr_avg=cdd_5yr_avg,
        hdd_avg_count=hdd_avg_count,
        cdd_avg_count=cdd_avg_count,
        hdd_vs_5yr=None if hdd_5yr_avg is None else hdd - hdd_5yr_avg,
        cdd_vs_5yr=None if cdd_5yr_avg is None else cdd - cdd_5yr_avg,
    )


def fmt_number(value: float | None, digits: int = 0, signed: bool = False) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    sign = "+" if signed else ""
    return f"{value:{sign},.{digits}f}"


def make_charts(
    storage: pd.DataFrame,
    weather: pd.DataFrame,
    charts_dir: Path,
    weather_cutoff: pd.Timestamp,
) -> dict[str, Path]:
    charts_dir.mkdir(parents=True, exist_ok=True)
    chart_paths = {
        "storage": charts_dir / "storage_vs_5yr.png",
        "net_change": charts_dir / "storage_net_change.png",
        "degree_days": charts_dir / "degree_days.png",
    }

    recent_storage = storage.tail(104)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(recent_storage["date"], recent_storage["working_gas_bcf"], label="Working gas")
    ax.plot(recent_storage["date"], recent_storage["value_5yr_avg"], label="5-year same-week avg")
    ax.set_title("Lower 48 working gas in storage")
    ax.set_ylabel("Bcf")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(chart_paths["storage"], dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(recent_storage["date"], recent_storage["net_change_bcf"], width=5)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Weekly net storage change")
    ax.set_ylabel("Bcf")
    ax.grid(True, axis="y", alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(chart_paths["net_change"], dpi=160)
    plt.close(fig)

    recent_weather = weather[weather["week_start"] <= weather_cutoff].tail(104)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(recent_weather["week_start"], recent_weather["hdd_weekly"], label="HDD")
    ax.plot(recent_weather["week_start"], recent_weather["cdd_weekly"], label="CDD")
    ax.set_title("Weekly degree days")
    ax.set_ylabel("Degree days")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(chart_paths["degree_days"], dpi=160)
    plt.close(fig)

    return chart_paths


def relative_chart_path(report_path: Path, chart_path: Path) -> str:
    return os.path.relpath(chart_path, start=report_path.parent)


def render_markdown(metrics: BriefMetrics, report_path: Path, chart_paths: dict[str, Path]) -> str:
    storage_count = (
        "n/a"
        if metrics.storage_5yr_count is None
        else f"{metrics.storage_5yr_count} same-week observations"
    )
    weather_average_label = (
        "5-year same-week average"
        if metrics.hdd_avg_count >= 5 and metrics.cdd_avg_count >= 5
        else "available same-week average"
    )
    weather_alignment = (
        f"stale by {metrics.weather_staleness_days} days"
        if metrics.weather_is_stale
        else f"within {metrics.weather_staleness_days} days"
    )

    return f"""# Natural Gas Storage and Weather Brief - {metrics.storage_date.date()}

## Summary

- Lower 48 working gas was {fmt_number(metrics.working_gas_bcf)} Bcf for the storage week reported {metrics.storage_date.date()}.
- Storage changed {fmt_number(metrics.net_change_bcf, signed=True)} Bcf week over week.
- Storage was {fmt_number(metrics.storage_vs_5yr_bcf, signed=True)} Bcf versus the same-week 5-year average, or {fmt_number(metrics.storage_vs_5yr_pct, 1, signed=True)}%.
- Storage was {fmt_number(metrics.storage_vs_year_ago_bcf, signed=True)} Bcf versus the same ISO week one year ago.
- Weather for the aligned week starting {metrics.weather_week_start.date()} showed {fmt_number(metrics.hdd_weekly, 1)} HDD and {fmt_number(metrics.cdd_weekly, 1)} CDD.

## Storage

| Metric | Value |
|---|---:|
| Working gas | {fmt_number(metrics.working_gas_bcf)} Bcf |
| Weekly net change | {fmt_number(metrics.net_change_bcf, signed=True)} Bcf |
| 5-year same-week average | {fmt_number(metrics.storage_5yr_avg_bcf)} Bcf |
| Difference from 5-year average | {fmt_number(metrics.storage_vs_5yr_bcf, signed=True)} Bcf |
| Difference from year ago | {fmt_number(metrics.storage_vs_year_ago_bcf, signed=True)} Bcf |
| 5-year average observations | {storage_count} |

![Storage versus 5-year average]({relative_chart_path(report_path, chart_paths["storage"])})

![Weekly storage change]({relative_chart_path(report_path, chart_paths["net_change"])})

## Weather

| Metric | Value |
|---|---:|
| Aligned weather week | {metrics.weather_week_start.date()} |
| Weather alignment status | {weather_alignment} |
| HDD | {fmt_number(metrics.hdd_weekly, 1)} |
| HDD versus {weather_average_label} | {fmt_number(metrics.hdd_vs_5yr, 1, signed=True)} |
| HDD average observations | {metrics.hdd_avg_count} |
| CDD | {fmt_number(metrics.cdd_weekly, 1)} |
| CDD versus {weather_average_label} | {fmt_number(metrics.cdd_vs_5yr, 1, signed=True)} |
| CDD average observations | {metrics.cdd_avg_count} |

![Weekly degree days]({relative_chart_path(report_path, chart_paths["degree_days"])})

## Cutoffs and Provenance

- Storage source: EIA weekly Lower 48 working gas in underground storage, series `NG.NW2_EPG0_SWO_R48_BCF.W`.
- Storage observation date: {metrics.storage_date.date()}.
- Weather source: Open-Meteo historical archive for the repository's 12 representative US stations.
- Weather alignment: latest weekly degree-day row with `week_start` on or before the storage report's ISO week start, {metrics.storage_week_start.date()}.
- Units: storage in Bcf; HDD/CDD in base-65 Fahrenheit degree days.

## Limits

- The weather series is a simple unweighted average across selected stations. It is not population-weighted or gas-demand-weighted.
- The brief is descriptive. It does not make a price forecast or trade recommendation.
- Storage norms are same-ISO-week averages from committed history and depend on the available observations in `data/eia_storage.parquet`.
"""


def main() -> None:
    args = parse_args()
    storage = load_storage(args.storage)
    weather = load_weather(args.weather)
    metrics = build_metrics(storage, weather)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / f"{metrics.storage_date.date()}-storage-weather-brief.md"
    charts_dir = args.charts_dir or args.output_dir / "assets" / str(metrics.storage_date.date())
    chart_paths = make_charts(storage, weather, charts_dir, metrics.weather_week_start)
    report_path.write_text(render_markdown(metrics, report_path, chart_paths), encoding="utf-8")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
