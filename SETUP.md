# SETUP.md — curve-lab environment and secrets setup

This document covers everything you need to run the pipeline locally and
configure the GitHub Actions workflow.

---

## 1. Install uv

curve-lab uses [uv](https://docs.astral.sh/uv/) for Python environment and
dependency management.

### macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify the installation:

```bash
uv --version
```

---

## 2. Set up the local environment

From the repo root, run:

```bash
uv sync
```

This reads `pyproject.toml`, creates a `.venv` directory, and installs all
dependencies.  You do **not** need to activate the virtualenv manually — every
`uv run` command automatically uses it.

---

## 3. API keys

### EIA API key (required for `fetch_eia.py`)

1. Register for a free key at: <https://www.eia.gov/opendata/register.php>
2. You will receive the key by email immediately.

**Local use:** Create a `.env` file in the repo root (it is git-ignored):

```
EIA_API_KEY=your_key_here
```

**GitHub Actions:** Add the key as a repository secret named `EIA_API_KEY`
(see §4 below).

---

### NOAA Climate Data Online token (required for `fetch_noaa.py`)

1. Register for a free token at: <https://www.ncdc.noaa.gov/cdo-web/token>
2. Enter your email address; the token arrives in your inbox within minutes.
3. The token is a short alphanumeric string (e.g. `AbCdEfGhIjKlMnOp`).

**Local use:** Add to your `.env` file:

```
NOAA_CDO_TOKEN=your_token_here
```

**GitHub Actions:** Add as a repository secret named `NOAA_CDO_TOKEN`.

---

## 4. GitHub Actions secrets

Navigate to your repository on GitHub, then:

```
Settings → Secrets and variables → Actions → New repository secret
```

Add the following secrets:

| Secret name     | Value                        |
|-----------------|------------------------------|
| `EIA_API_KEY`   | Your EIA API key             |
| `NOAA_CDO_TOKEN`| Your NOAA CDO token          |

The CFTC pipeline requires no API key (public flat files).
The yfinance pipeline requires no API key.

---

## 5. Run the pipeline locally (one-time manual run)

With your `.env` file populated, run each fetcher in order:

```bash
uv run python pipeline/fetch_futures.py
uv run python pipeline/fetch_eia.py
uv run python pipeline/fetch_noaa.py
uv run python pipeline/fetch_cftc.py
```

Each script writes a parquet file to `data/`:

| Script                     | Output file                  |
|----------------------------|------------------------------|
| `pipeline/fetch_futures.py`| `data/futures.parquet`       |
| `pipeline/fetch_eia.py`    | `data/eia_storage.parquet`   |
| `pipeline/fetch_noaa.py`   | `data/noaa_degree_days.parquet` |
| `pipeline/fetch_cftc.py`   | `data/cftc_cot.parquet`      |

Run `fetch_futures.py` and `fetch_cftc.py` first — they have no external API
key dependencies and will confirm your environment is working before you test
the keyed endpoints.

---

## 6. GitHub Actions schedule

The workflow in `.github/workflows/update_data.yml` runs automatically every
day at **14:00 UTC**.  After each run it commits updated parquet files back to
the repo (the commit message is `chore: update data [skip ci]` to avoid
triggering another run).

To trigger the workflow manually:

```
GitHub → Actions → Update Data → Run workflow
```

---

## 7. Verifying output

After a successful run, inspect the parquet files:

```python
import pandas as pd

pd.read_parquet("data/futures.parquet").tail()
pd.read_parquet("data/eia_storage.parquet").tail()
pd.read_parquet("data/noaa_degree_days.parquet").tail()
pd.read_parquet("data/cftc_cot.parquet").tail()
```

---

## 8. Troubleshooting

| Problem | Fix |
|---------|-----|
| `EIA_API_KEY not set` | Add the key to `.env` or set it as an env var |
| `NOAA_CDO_TOKEN not set` | Register and add the token as described above |
| CFTC download fails (404) | The current year's file may not yet be published — the script skips missing years |
| yfinance returns no data | Yahoo Finance occasionally throttles; wait and retry |
| `uv: command not found` | Follow the install steps in §1 |
