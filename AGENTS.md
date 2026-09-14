# Agent Guide

## Purpose

Energy Market Analytics is a natural gas research project. It supports market
learning and derivatives analysis with reproducible data pipelines for futures,
storage, weather degree days, and positioning. It is not an automated trading
system.

## Repository Map

- `pipeline/`: standalone fetch scripts that write parquet files to `data/`.
- `data/`: committed project data and the durable store for the current pipeline.
- `analysis/`: workspace for exploratory analysis.
- `notebooks/`: notebook-based exploration.
- `docs/`: source notes, methodology, and learning logs.
- `SETUP.md`: local setup and API-key guidance.

## Commands

Use `uv`; do not substitute a global Python environment. In sandboxed agent
sessions, prefer a repo-local cache:

```bash
UV_CACHE_DIR=.uv-cache uv sync
UV_CACHE_DIR=.uv-cache uv run python pipeline/fetch_futures.py
UV_CACHE_DIR=.uv-cache uv run python pipeline/fetch_cftc.py
UV_CACHE_DIR=.uv-cache uv run python pipeline/fetch_weather.py
UV_CACHE_DIR=.uv-cache uv run python pipeline/fetch_eia.py
```

`fetch_eia.py` requires `EIA_API_KEY`. The other three fetchers are the fastest
checks when credentials are unavailable. There is no configured test suite,
linter, or type checker. Verify pipeline changes by running the relevant
fetcher and inspecting the resulting parquet shape and latest rows.

## Working Rules

1. Read the relevant fetcher, docs, and current parquet schema before editing.
2. Keep each fetcher self-contained unless shared code removes real complexity.
3. Preserve source provenance, date semantics, units, and column names unless
   the docs and downstream analysis are updated in the same change.
4. Do not refactor unrelated scripts or reformat notebooks as a drive-by change.
5. Never commit credentials, `.env` files, local notebooks with secrets, or
   temporary exports. Committed parquet files in `data/` are expected project
   state, but inspect diffs before including them.

## Research Integrity

Separate facts from interpretation. Do not present a price narrative as a model
result unless the data, transformation, and cutoff are clear. For derivatives
work, state whether an observation concerns futures curves, calendar spreads,
storage, weather, positioning, or options/volatility. Do not imply trade
recommendations without explicit evidence and scope.

## Git and Pull Requests

For substantive changes, create a focused branch and open a pull request. Use
an imperative Conventional Commit subject with one leading emoji:

```text
✨ feat: add curve spread analysis
🐛 fix: correct EIA date parsing
📝 docs: clarify storage-source timing
🧪 test: add fetcher regression coverage
♻️ refactor: simplify futures download
🔧 chore: update workflow tooling
```

Before requesting review:

1. Inspect the diff for credentials, unintended data churn, and unrelated files.
2. Run the relevant fetcher or document why it could not run.
3. State the data, schema, provenance, and research impact.
4. Use `.github/pull_request_template.md`; leave unchecked items visible with a
   short reason when validation is unavailable.

Use the GitHub CLI for pull requests when authentication is valid:

```bash
gh auth status
gh pr create --fill
```

If `gh auth status` fails, push the branch and report the compare URL instead
of implying that a PR was opened.

## Keeping This Useful

Keep this file short and verified. Put detailed methodology in `docs/`, not in
always-loaded agent context.
