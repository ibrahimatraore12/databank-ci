# Submission Writeup — dataBank CI Customer 360

> *[French version: [submission_writeup.md](submission_writeup.md)]*

**Author:** Ibrahima TRAORÉ — Analytics Engineer
**Date:** July 2026
**Live dashboard:** https://databank-ci-264685034714.europe-west9.run.app

## 1. What I built

I built an end-to-end analytics engineering platform: from a source Excel
file (10 sheets, 140 real customers) to a deployed Streamlit dashboard and an
MCP server queryable in natural language, going through a three-layer dbt
transformation and an ML pipeline comparing several scoring approaches.

End to end, replaying the whole pipeline (ingestion + enrichment + synthetic
generation, dbt transformation, ML training) takes under 60 seconds on my
development machine — a measured time, not an estimate, excluding the
dashboard's own startup.

## 2. The decisions that matter

**I chose the medallion architecture** (Bronze/Silver/Gold on DuckDB,
orchestrated by dbt) for its idempotence and native fit with dbt — see
`docs/architecture_en.md` for the detail and the alternatives ruled out
(star schema, Data Vault).

**I treated the disengagement score in two phases**, not as a single ML
model presented as ground truth: an explicit rule-based score (`ml/rules.py`,
always available without a trained model) and a supervised ML experiment on
a proxy label (`ml/comparison.py`). The source dataset contains no confirmed
customer departure — see `docs/ml_problem_definition_en.md` for the full
problem definition and its limitations.

**I chose the production model on a robustness criterion, not the raw best
score.** The comparison on the enriched dataset (540 customers, 151
positives) gives an AUC of 1.0 for both RandomForest and XGBoost, versus
0.944 for logistic regression. I did not retain the first two: synthetic
customers are bootstrap copies of real customers (see
`docs/synthetic_data_rationale_en.md`), and a high-capacity model can
memorize these patterns without generalizing. I retained logistic regression
(`ml/artifacts/churn_scoring_logistic.pkl`) as the champion model,
documenting this choice in `docs/model_comparison_en.md` rather than
presenting the perfect score as a win.

**I generated 400 synthetic customers** to bring the test volume from 140 to
540 customers, with strict traceability (`is_synthetic=True` visible from
Bronze to the dashboard) and statistical validation via a Kolmogorov-Smirnov
test on the income distribution — see `docs/synthetic_data_rationale_en.md`.

**I enforced a strict semantic layer**: no technical column name
(`risk_band`, `nb_reclamations_ouvertes`...) appears in the dashboard.
Everything goes through `dashboard/components/ui.py::LABELS` then through
`i18n/{fr,en}.json`, including chart titles, table headers, and alert
messages.

**I connected the dashboard to the MCP server over real HTTP**, not via a
direct Python import: the AI Assistant page calls the deployed MCP server
(`streamable-http`, API key) through a real MCP client
(`dashboard/components/mcp_client.py`), so answers actually go through the
protocol rather than an in-memory shortcut.

**I added a GCS persistence layer for Administration-tab data uploads**,
rather than accepting that stateless Cloud Run loses everything on every
restart. A file uploaded by the business is validated, recomputed (full
pipeline, ~55 seconds measured in an isolated container), then saved to a
GCS bucket that every instance re-reads at its own startup
(`src/storage_sync.py`, detailed in `docs/architecture_en.md` section 6). I
added a schema-version guard after identifying, during design review, that
a future dbt schema change could otherwise get silently overwritten by
older data restored from GCS.

## 3. An analytical conclusion, not a generic suggestion

On the real portfolio (excluding synthetic customers, to avoid presenting a
duplicate as two distinct customers), 2 Premier-segment customers show a
high credit risk level (`risk_band = High`): Murielle Aka (risk score
26.4/100, balance 6.44M FCFA) and Bintou Soro (score 19.0/100, balance 5.52M
FCFA) — combined balance 11.97M FCFA. These are the only 2 Premier customers
in this situation among the segment's 49 real customers. An advisor call
within 48h on these 2 accounts is the immediate commercial priority
identified by the dashboard (Retention and Risk page) — not a generic
recommendation to "contact at-risk customers."

## 4. Limitations, stated plainly

- The real dataset is small (140 customers, 34 loans, 42 complaints) — see
  `docs/ml_problem_definition_en.md` section 6 for detail.
- NBI is a standard-formula estimate, not the customer's real accounting NBI
  — `docs/decisions_en.md`.
- The near-perfect RandomForest/XGBoost scores on the enriched dataset are
  not a guarantee of production performance on unseen customers —
  `docs/model_comparison_en.md`.
- This project remains a decision-support tool: no action is triggered
  automatically from a score, the human stays in the loop.

## 5. Stack

Python 3.11 · dbt-duckdb · DuckDB · scikit-learn/XGBoost · MLflow ·
Streamlit · Model Context Protocol (MCP) · Docker · Google Cloud Run.
