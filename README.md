# IKEA Forecast — Backend (FastAPI)

REST API for the Gul Ahmed IKEA SPI supply-intelligence dashboard. It parses IKEA SPI exports, serves the aggregates behind the charts, scores the no-change revision baseline between snapshots, and exposes an optional Prophet scenario.

The React dashboard lives in a separate repo (`ikea_forcast_frontend`) and talks to this API.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate              # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt     # prophet is optional/heavy; remove it if you don't need /api/prophet
python run.py                       # http://localhost:8080  (docs at /docs)
```

Or: `uvicorn app.main:app --port 8080`.

Configuration is via environment variables — see [.env.example](.env.example) (`PORT`, `CORS_ORIGINS`, `MAX_UPLOAD_MB`, `SPI_DEFAULT_FILE`).

## Data

SPI exports are **business data and are not committed** (`data/` is git-ignored). Either:
- drop a sample export at `data/SUP_15505_1_52_202637.xls` (preloaded at startup), or
- start with no data and upload exports through `POST /api/snapshots`.

Files are IKEA's tab-delimited `.xls` text export (Windows-1252), not binary Excel.

## Layout

```
app/
  main.py            app factory, lifespan, /api/health
  config.py          environment-driven settings
  store.py           in-memory snapshot store (swap for a DB once history is archived)
  deps.py            shared snapshot / status-filter dependencies
  routers/           snapshots, overview (+weekly), insights, articles, revisions, scenario
  services/
    spi_core.py      SPI parser, no-change baseline, snapshot comparison, Prophet scenario
    spi.py           thin adapter used by the routers
    aggregation.py   weekly -> monthly/yearly aggregation (provisional allocation rule)
tests/               pytest API tests (skipped automatically when the sample file is absent)
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| GET / POST | `/api/snapshots` | list / upload SPI exports |
| GET | `/api/overview`, `/api/weekly` | KPIs, weekly/monthly/yearly totals |
| GET | `/api/insights/{lifecycle,top-articles,balance,exposure}` | overview chart data |
| GET | `/api/articles`, `/api/articles/{id}` | article list / schedule + stock + baseline |
| POST | `/api/compare` | revision backtest between two snapshots |
| GET | `/api/prophet` | exploratory scenario (not a validated forecast) |

Most GET endpoints accept `snapshot`, repeatable `status`, and repeatable `article` filters.

## Tests

```bash
pytest
```

## Notes

- Month/year totals assign ISO weeks by their Monday date — a **provisional** rule until planning approves the calendar/allocation rule.
- The Prophet endpoint extrapolates one snapshot's plan curve; it is a planning scenario, not a demand or revision forecast.
- Snapshots live in memory and are lost on restart.
