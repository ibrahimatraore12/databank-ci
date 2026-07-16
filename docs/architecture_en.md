# Architecture — dataBank CI Customer 360

> *[French version: [architecture.md](architecture.md)]*

**Author:** Ibrahima TRAORÉ — Analytics Engineer
**Date:** July 2026

## 1. Overview

The project follows a medallion architecture (Bronze → Silver → Gold) on
DuckDB, orchestrated by dbt, feeding three downstream consumers: a Streamlit
dashboard, an MCP server, and an ML pipeline.

```
starter_dataset.xlsx (10 sheets)
        │
        ▼
src/ingest.py ──► Bronze (DuckDB, real + synthetic, raw)
        │
        ▼
dbt_project/models/staging       (explicit typing, business corrections)
        │
        ▼
dbt_project/models/intermediate  (per-customer behavioral aggregates)
        │
        ▼
dbt_project/models/marts         (Gold: customer_360, customer_segments, nba)
        │
        ├──► dashboard/   (Streamlit, FR/EN)
        ├──► mcp_server/  (5 read-only tools, MCP protocol)
        └──► ml/          (rule-based score + compared models)
```

## 2. Why the medallion architecture

I retained the medallion architecture for three concrete reasons on this
project, not by default:

1. **Native idempotence.** Every layer (staging = view, marts = table) can be
   replayed entirely without side effects. `pipelines/run_pipeline.py` cleans
   its outputs before recreating them, `dbt run` rebuilds the Gold tables on
   every run. Replaying the whole pipeline from `starter_dataset.xlsx`
   produces the same result down to the second (see `RANDOM_SEED=42` in
   `config.py`).
2. **Native fit with dbt.** dbt is built around layered models
   (staging/intermediate/marts) with declarative tests at every level
   (`_sources.yml`, `_intermediate.yml`, `_marts.yml`) — 93 tests total in
   this project, all passing.
3. **Clean real/synthetic separation from the Bronze layer onward.** The
   synthetic generator (`src/synthetic_data_generator.py`) produces rows that
   follow exactly the same schema as real data and are merged as early as
   Bronze (`bronze_customers` UNION ALL `bronze_synthetic_customers`), with
   an `is_synthetic` flag that survives all the way to the dashboard. A
   single-layer architecture would have made that separation more fragile to
   maintain.

**Alternatives ruled out:**

- **Star schema (dimensions/facts) directly in Gold** — ruled out because
  this project needs a staging layer to apply business corrections (e.g.
  `salary_domiciled_flag` recomputed from observed transactions in
  `stg_accounts.sql`) before any aggregation. A pure star schema mixes
  typing, correction, and aggregation in the same models.
- **Data Vault** — ruled out: its complexity (hubs/links/satellites) isn't
  justified for a 140-real-customer portfolio and 10 source tables. It would
  be over-engineering for this data volume.

## 3. The three layers in detail

| Layer | Materialization | Role | Example |
|-------|------------------|------|---------|
| Staging | `view` | Explicit typing, one documented business correction per model | `stg_loans.sql` reclassifies a loan as `Delinquent` when `days_past_due > 15` |
| Intermediate | `view` | One aggregate per customer per concern (never two concerns in the same model) | `int_customer_recency.sql`, `int_customer_balance.sql`, `int_customer_nbi.sql` |
| Marts | `table` | Final business view, materialized for dashboard performance | `customer_360` (single customer view), `customer_segments`, `nba` |

The "one intermediate file = one concern" split (recency, trend, complaints,
digital score, products, balance, NBI, channel, loans) makes it possible to
add a new column to the `customer_360` mart without touching existing
models — that's exactly what let me extend the mart with 8 new columns
(total balance, estimated NBI, primary channel, tenure, etc.) without
breaking a single existing test.

## 4. Why DuckDB rather than a database server

The source dataset is under 10 MB (140 customers before enrichment, ~540
after). DuckDB runs embedded, with no server to operate, serializes to a
single file (`dbt_project/databank_ci.duckdb`) that fits in the Docker image,
and speaks standard SQL — so it's directly compatible with dbt without
adaptation.

**Migration path if volume exceeds ~10 GB**: change only
`dbt_project/profiles.yml` to point to BigQuery (the `dbt-bigquery` adapter
already packaged for this case), without touching a single SQL model — that
is precisely the point of going through dbt rather than embedding SQL
directly in Python code.

## 5. The Gold layer's three consumers

- **Streamlit dashboard** (`dashboard/`) — reads `customer_360` read-only
  (`duckdb.connect(..., read_only=True)`), applies a strict semantic layer
  (`components/ui.py::LABELS`) before any display.
- **MCP server** (`mcp_server/`) — 5 read-only tools exposed over the Model
  Context Protocol, in `stdio` locally and in `streamable-http` (with an API
  key) in production on Cloud Run. The dashboard and the MCP server share the
  same Docker image; only the entry point changes (`--command`/`--args` at
  deploy time).
- **ML pipeline** (`ml/`) — a rule-based business score always available
  without a trained model (`ml/rules.py`), plus a supervised model comparison
  on a proxy label (`ml/comparison.py`), tracked in MLflow (`mlflow.db`, 20
  real runs recorded).
