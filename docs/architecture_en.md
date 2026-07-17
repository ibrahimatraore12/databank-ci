# Architecture - dataBank CI Customer 360

> *[French version: [architecture.md](architecture.md)]*

**Author:** Ibrahima TRAORÉ - Analytics Engineer
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
   (`_sources.yml`, `_intermediate.yml`, `_marts.yml`) - 93 tests total in
   this project, all passing.
3. **Clean real/synthetic separation from the Bronze layer onward.** The
   synthetic generator (`src/synthetic_data_generator.py`) produces rows that
   follow exactly the same schema as real data and are merged as early as
   Bronze (`bronze_customers` UNION ALL `bronze_synthetic_customers`), with
   an `is_synthetic` flag that survives all the way to the dashboard. A
   single-layer architecture would have made that separation more fragile to
   maintain.

**Alternatives ruled out:**

- **Star schema (dimensions/facts) directly in Gold** - ruled out because
  this project needs a staging layer to apply business corrections (e.g.
  `salary_domiciled_flag` recomputed from observed transactions in
  `stg_accounts.sql`) before any aggregation. A pure star schema mixes
  typing, correction, and aggregation in the same models.
- **Data Vault** - ruled out: its complexity (hubs/links/satellites) isn't
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
models - that's exactly what let me extend the mart with 8 new columns
(total balance, estimated NBI, primary channel, tenure, etc.) without
breaking a single existing test.

## 4. Why DuckDB rather than a database server

The source dataset is under 10 MB (140 customers before enrichment, ~540
after). DuckDB runs embedded, with no server to operate, serializes to a
single file (`dbt_project/databank_ci.duckdb`) that fits in the Docker image,
and speaks standard SQL - so it's directly compatible with dbt without
adaptation.

**Migration path if volume exceeds ~10 GB**: change only
`dbt_project/profiles.yml` to point to BigQuery (the `dbt-bigquery` adapter
already packaged for this case), without touching a single SQL model - that
is precisely the point of going through dbt rather than embedding SQL
directly in Python code.

## 5. The Gold layer's three consumers

- **Streamlit dashboard** (`dashboard/`) - reads `customer_360` read-only
  (`duckdb.connect(..., read_only=True)`), applies a strict semantic layer
  (`components/ui.py::LABELS`) before any display.
- **MCP server** (`mcp_server/`) - 5 read-only tools exposed over the Model
  Context Protocol, in `stdio` locally and in `streamable-http` (with an API
  key) in production on Cloud Run. The dashboard and the MCP server share the
  same Docker image; only the entry point changes (`--command`/`--args` at
  deploy time).
- **ML pipeline** (`ml/`) - a rule-based business score always available
  without a trained model (`ml/rules.py`), plus a supervised model comparison
  on a proxy label (`ml/comparison.py`), tracked in MLflow (`mlflow.db`,
  real runs recorded).

## 6. Data persistence (Cloud Run is stateless)

Cloud Run provides no persistent disk: when an instance restarts (new
revision, scale-down then scale-up), everything written to the local
filesystem disappears, and the container comes back with the data frozen
into the Docker image at build time. A file uploaded by the business through
the Administration tab would therefore be lost on the very first restart
without an external persistence layer.

**I retained a private Google Cloud Storage bucket**
(`databank-ci-data-264685034714`, europe-west9 region, object versioning
on) rather than, say, only persisting the source Excel file: syncing the
already-transformed DuckDB file avoids replaying the ~60-second pipeline
(ingestion → dbt → ML) on every instance startup - only a few seconds'
download is needed.

The `src/storage_sync.py` module exposes two functions:

- `telecharger_depuis_gcs()` - called once at every instance's startup
  (dashboard: `st.cache_resource` in `dashboard/APP.py`; MCP server: a plain
  call, since it's a long-lived process). Never raises: an error must not
  block the application's startup.
- `televerser_vers_gcs()` - called after a successful recompute from the
  Administration tab
  (`dashboard/pages/99_Administration.py::relancer_pipeline_complet`), so
  the result survives this instance's restart and is picked up by every
  other one.

**Schema-compatibility guard.** Without a check, a future dbt schema change
(a new mart column) could see its image silently overwritten at startup by
an older file restored from GCS - cascading failures on any request using
the new column. `config.DATA_SCHEMA_VERSION`, written into
`pipeline_state.json` on every pipeline run, is compared by
`telecharger_depuis_gcs()` before any download: on mismatch, it touches
nothing and keeps the image's own data (guaranteed compatible with the
current code).

**Special case for `mlflow.db` (SQLite).** This file is never copied to GCS
as raw bytes: mlflow can keep a connection pool open in-process, which
would make a raw copy liable to capture an inconsistent state.
`televerser_vers_gcs()` goes through sqlite3's `backup()` API to a temporary
file before uploading.

**Resyncing the AI Assistant.** The MCP server is a separate Cloud Run
service (separate process, same Docker image, different entry point): it
only re-reads GCS at its own startup, not when the dashboard finishes a
recompute. An internal `POST /admin/resync` route (see
`mcp_server/README_MCP_en.md`) lets the dashboard ask it to resync
immediately after a persisted recompute, instead of waiting for its next
natural restart.

**Accepted limitation**: `max-instances=1` is set on both services to avoid
an already-running instance serving stale data while another has just been
refreshed - internal/admin traffic, low volume, this trade-off is
acceptable here.
