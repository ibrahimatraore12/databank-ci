# Architecture - dataBank CI Customer 360

> *[French version: [architecture.md](architecture.md)]*

**Author:** Ibrahima TRAORÉ - Analytics Engineer
**Date:** July 2026

## 1. Overview

The project organizes data through three successive stages, called a
"medallion architecture" (Bronze → Silver → Gold), on DuckDB, run by dbt.
Three tools then use this data: a Streamlit dashboard, an MCP server, and a
Machine Learning pipeline.

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
dbt_project/models/intermediate  (per-customer behavior aggregates)
        │
        ▼
dbt_project/models/marts         (Gold: customer_360, customer_segments, nba)
        │
        ├──► dashboard/   (Streamlit, FR/EN)
        ├──► mcp_server/  (5 read-only tools, MCP protocol)
        └──► ml/          (rule-based score + compared models)
```

## 2. Why the "medallion" architecture (Bronze/Silver/Gold)

I chose this three-stage setup for three concrete reasons tied to this
specific project, not just out of habit:

1. **Everything can be re-run safely.** Every stage (staging = view,
   marts = table) can be fully recomputed with no side effects. The
   `pipelines/run_pipeline.py` script cleans up its previous results
   before recreating them, and `dbt run` rebuilds the Gold tables on every
   run. Replaying the whole pipeline from `starter_dataset.xlsx` gives
   exactly the same result, down to the second (see `RANDOM_SEED=42` in
   `config.py`, which fixes the starting point for random calculations).
2. **dbt is built for this kind of setup.** dbt is designed for data
   organized in successive layers (staging/intermediate/marts), with
   automatic tests at every stage (`_sources.yml`, `_intermediate.yml`,
   `_marts.yml`): 93 tests in total on this project, all passing.
3. **The split between real and synthetic data is clear from the start.**
   The synthetic data generator (`src/synthetic_data_generator.py`)
   creates rows that follow exactly the same format as real data, and
   they're combined as early as the Bronze stage (`bronze_customers`
   merged with `bronze_synthetic_customers`). An `is_synthetic` flag marks
   these rows and follows them all the way to the dashboard. With a
   single big stage instead, this split would have been harder to
   maintain over time.

**Other options considered, and why they weren't chosen:**

- **Star schema**, where the final tables (facts and dimensions) would be
  built directly, with no intermediate stage. Ruled out because this
  project needs a "staging" stage to apply business corrections (for
  example, `salary_domiciled_flag` is recomputed from transactions
  observed in `stg_accounts.sql`) before any overall calculation. Doing
  this directly in a star schema would mix typing, correction, and
  calculation in the same models.
- **Data Vault**, a more complex modeling method (with "hubs", "links",
  and "satellites"). Ruled out because its complexity isn't justified for
  a portfolio of 140 real customers and 10 source tables: it would be
  overkill for this data volume.

## 3. The three stages in detail

| Stage | Result type | Role | Example |
|-------|------------------|------|---------|
| Staging | `view` (recomputed on every read) | Explicit column typing, one documented business correction per model | `stg_loans.sql` reclassifies a loan as `Delinquent` when the payment delay is over 15 days |
| Intermediate | `view` | One calculation per customer, for a single topic at a time (never two topics mixed in the same model) | `int_customer_recency.sql`, `int_customer_balance.sql`, `int_customer_nbi.sql` |
| Marts | `table` (result physically saved) | Final business view, saved so the dashboard stays fast | `customer_360` (single per-customer view), `customer_segments`, `nba` |

The rule "one intermediate file = one topic" (recency, trend, complaints,
digital score, products, balance, generated revenue, channel, loans) makes
it possible to add a new column to the final `customer_360` table without
touching existing models. That's exactly what allowed adding 8 new columns
(total balance, estimated revenue, primary channel, tenure, etc.) without
breaking a single existing test.

## 4. Why DuckDB instead of a classic database server

The source file weighs under 10 MB (140 customers before enrichment, about
540 after). DuckDB runs directly inside the app, with no separate server
to operate. It saves all its data in a single file
(`dbt_project/databank_ci.duckdb`), which easily fits inside the Docker
image, and it understands standard SQL, which makes it directly compatible
with dbt with no special adaptation.

**If the data volume ever grows past about 10 GB**, switching to BigQuery
just means changing the `dbt_project/profiles.yml` file (the
`dbt-bigquery` adapter, already set up for this case), without modifying a
single SQL model. That's precisely the point of going through dbt instead
of writing SQL directly inside the Python code.

## 5. The three tools that use the final (Gold) data

- **Streamlit dashboard** (`dashboard/`) - reads the `customer_360` table
  read-only only (`duckdb.connect(..., read_only=True)`), and always
  applies a label-translation layer (`components/ui.py::LABELS`) before
  displaying anything.
- **MCP server** (`mcp_server/`) - offers 5 read-only tools through the
  Model Context Protocol (MCP). Locally, it communicates via `stdio`; in
  production on Cloud Run, via `streamable-http` (with an access key). The
  dashboard and the MCP server share the same Docker image: only the
  startup entry point changes at deploy time.
- **Machine Learning pipeline** (`ml/`) - a score based on business rules,
  always available even without a trained model (`ml/rules.py`), plus a
  comparison of supervised Machine Learning models on an approximate
  indicator (`ml/comparison.py`), tracked with the MLflow tool
  (`mlflow.db`, which records the real results of every run).

## 6. How data is kept safe (Cloud Run doesn't keep anything in memory)

Cloud Run, the hosting platform used here, provides no permanent disk: when
an app instance restarts (new version, automatic stop then restart),
everything written to the local disk disappears. The app then starts back
up with the data exactly as it was when the Docker image was built. A file
uploaded by a business user through the Administration tab would therefore
be lost on the very first restart, without an external backup solution.

**I chose to back up the data to a private Google Cloud Storage (GCS)
space** (named `databank-ci-data-264685034714`, located in the
europe-west9 region, with version history turned on), rather than backing
up only the source Excel file, for example. Backing up the already
transformed DuckDB file directly avoids re-running the 60-second pipeline
(data loading → dbt → Machine Learning) every time an instance starts:
only a few seconds' download is needed.

The `src/storage_sync.py` file offers two functions:

- `telecharger_depuis_gcs()` ("download from GCS") - called once, at the
  startup of every instance (for the dashboard: through
  `st.cache_resource` in `dashboard/APP.py`; for the MCP server: a plain
  call, since the process stays running for a long time). This function
  never raises a blocking error: a connection issue must not prevent the
  app from starting.
- `televerser_vers_gcs()` ("upload to GCS") - called after a successful
  recompute from the Administration tab
  (`dashboard/pages/99_Administration.py::relancer_pipeline_complet`), so
  the result survives this instance's restart and is picked up by every
  other instance of the app.

**A compatibility check protects the data.** Without this check, a future
structural change in dbt (for example a new column in a final table) could
get silently overwritten at startup by an older file restored from GCS,
causing cascading errors on any request that uses the new column. The
`config.DATA_SCHEMA_VERSION` variable, saved into `pipeline_state.json` on
every pipeline run, is therefore compared by `telecharger_depuis_gcs()`
before any download. If there's a mismatch, nothing gets downloaded: the
app keeps the data already present in the image, which is guaranteed to be
compatible with the code currently running.

**Special case for the `mlflow.db` file (SQLite database).** This file is
never copied directly, byte for byte, to GCS. MLflow can keep a connection
open in the background, which would make a raw copy likely to capture the
data at an inconsistent moment. The `televerser_vers_gcs()` function
therefore uses the `backup()` function from the `sqlite3` library, which
cleanly copies the data to a temporary file before sending it to GCS.

**Refreshing the AI Assistant.** The MCP server is a separate Cloud Run
service (separate process, same Docker image, but a different startup
entry point): it only re-reads data from GCS at its own startup, not when
the dashboard finishes a recompute. An internal `POST /admin/resync` route
(see `mcp_server/README_MCP_en.md`) lets the dashboard ask it to resync
immediately after a saved recompute, instead of waiting for its next
natural restart.

**Accepted, deliberate limitation**: the maximum number of instances
(`max-instances=1`) is set to 1 on both services. This avoids an
already-running instance continuing to serve old data while another one
has just been refreshed. The traffic involved stays internal and limited
(administration), so this trade-off is acceptable in this context.
