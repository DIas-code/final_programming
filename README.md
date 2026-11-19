# Kazakhstan Legislation Analytics

Final project for **Programming for Data Analysis and Database** (ADA, Big Data Analysis master's program).

**Topic 21 — Kazakhstan Legislation Analytics.**
**Author:** Dias Yermekov, ADA-2603.
**Dataset:** [KazakhLawCorpus-clean](https://huggingface.co/datasets/Arailym-tleubayeva/KazakhLawCorpus-clean) — 215,889 Kazakh legal acts (1947–2026), 25 metadata fields, one CSV of 336.8 MB, CC BY 4.0. The file is too large for GitHub, so it is downloaded automatically by `src/data_loader.py`.

## Goal
Analyze the dynamics of legal acts by year, act form, adopting body, region and repeal status: metadata audit, normalized SQLite schema, SQL analytics with CTE and window functions, EDA and time series, a monthly forecast compared with a baseline (MAE), and a Streamlit dashboard with filters.

## Stack
Python 3.14, pandas, PyArrow (Parquet), SQLite (`sqlite3`), Matplotlib, Seaborn, Plotly, Streamlit, statsmodels, scikit-learn. Exact versions are pinned in `requirements.txt`. Tested on Windows 11 (PowerShell).

## How to run

```powershell
# 0. Environment
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt

# 1. Download CSV, read in chunks, optimize dtypes (memory before/after), save Parquet
python -m src.data_loader

# 2. Build the normalized SQLite database -> data/legislation.db  (~15 s)
python -m src.db

# 3. Run 9 SQL queries -> docs/queries/*.csv
python -m src.queries

# 4. Dashboard (opens in the browser, stop with Ctrl+C)
streamlit run src/app.py
```

Notebooks (open in VS Code / Jupyter, kernel `.venv`, **Run All**), after steps 1–2:

| Notebook | Content |
|---|---|
| `explore.ipynb` | First look at the data (first 1,000 rows) |
| `audit.ipynb` | Metadata audit: missing values and placeholders, dates, multi-value fields |
| `analysis.ipynb` | EDA, IQR outliers, time series (resample, rolling mean, seasonal decomposition), correlations, charts |
| `forecast.ipynb` | naive / seasonal naive vs moving average / linear regression, time-based split, MAE |

macOS / Linux: `python3 -m venv .venv && source .venv/bin/activate`, the rest is the same.

## Structure

```
src/
  config.py        paths and constants (pathlib)
  data_loader.py   download, chunked CSV reading, dtype optimization, Parquet
  cleaning.py      placeholders -> NaN, bracket notes removal, splitting multi-value fields
  db.py            normalized schema (9 tables) and data load into SQLite
  queries.py       9 SQL queries (JOIN, GROUP BY/HAVING, subquery, CTE, window functions)
  app.py           Streamlit dashboard with filters (years, region, legal force, status)
explore.ipynb, audit.ipynb, analysis.ipynb, forecast.ipynb
docs/
  er_diagram.svg   ER diagram (dbdiagram.io)
  er_diagram.md    ER diagram (Mermaid) and schema explanation
  schema.dbml      the same schema for dbdiagram.io
  audit_*.csv, queries/*.csv, forecast_mae.csv, acts_per_year.html   results
data/              CSV, Parquet, SQLite database (not in git, rebuilt by the scripts)
```

## Key results
- Memory: 356 MB → 206 MB after dtype optimization (−42 %); CSV 336 MB → Parquet 18.6 MB.
- Audit: `regulatory_body` has only 19 NaN but 93,272 `ЖОҚ` placeholders (43 % actually missing); `legal_relation_area` has 25,283 raw values that are combinations of only 351 real areas.
- Activity grew from 241 acts (1992) to ~14–15 thousand per year (2022–2025); a strong December peak every year.
- Forecast (test 2024–2025): linear regression with trend + month (trained on 2016–2023) MAE 214.8 vs seasonal naive baseline 300.8 (−29 %).
