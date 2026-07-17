# Submission Writeup - dataBank CI Customer 360

> *[French version: [submission_writeup.md](submission_writeup.md)]*

**Author:** Ibrahima TRAORÉ - Analytics Engineer
**Date:** July 2026
**Live dashboard:** https://databank-ci-264685034714.europe-west9.run.app

## 1. What I built

I built a complete data pipeline, start to finish. It starts from a source
Excel file (10 sheets, 140 real customers) and ends with a live Streamlit
dashboard, plus an MCP server you can query in plain language. In between,
the data goes through a three-stage dbt transformation, then a Machine
Learning pipeline that compares several ways of computing a risk score.

Replaying the whole pipeline (loading the data + enrichment + synthetic
data generation, dbt transformation, model training) takes under 60 seconds
on my development machine. That's a measured time, not an estimate, and it
doesn't include the dashboard's own startup time.

## 2. The decisions that matter

**I chose the "medallion" architecture** (Bronze/Silver/Gold, with DuckDB
and dbt) because it can be re-run safely and fits naturally with dbt. The
detail, along with the other options considered (star schema, Data Vault),
is explained in `docs/architecture_en.md`.

**I computed the disengagement score in two steps**, instead of relying on
a single Machine Learning model presented as absolute truth: first a score
based on clear business rules (`ml/rules.py`, always available even without
a trained model), then a supervised Machine Learning experiment on an
approximate label (`ml/comparison.py`). That's because the source file
contains no confirmed customer departure. The full problem definition and
its limits are explained in `docs/ml_problem_definition_en.md`.

**I chose the model used in production for its reliability, not its raw
best score.** On the enriched dataset (540 customers, 151 of whom left),
the comparison gives an AUC score (a prediction-quality indicator, between
0 and 1) of 1.0 for both RandomForest and XGBoost, versus 0.944 for
logistic regression. I did not keep the first two models. Why? Synthetic
customers are statistical copies of real customers (see
`docs/synthetic_data_rationale_en.md`), and a very powerful model can
"memorize" these copies instead of understanding the general trend. So I
kept logistic regression (`ml/artifacts/churn_scoring_logistic.pkl`) as the
main model, and I explain this choice in detail in
`docs/model_comparison_en.md`, rather than presenting a perfect score as a
win.

**I created 400 synthetic customers** to raise the test volume from 140 to
540 customers. Every generated customer stays identifiable
(`is_synthetic=True`, visible from Bronze all the way to the dashboard),
and I statistically checked that this data stays realistic using a
Kolmogorov-Smirnov test on the income distribution. Details in
`docs/synthetic_data_rationale_en.md`.

**I enforced one strict rule: no technical column name**
(`risk_band`, `nb_reclamations_ouvertes`...) is ever shown on the
dashboard. Every piece of displayed text goes through
`dashboard/components/ui.py::LABELS`, then through the
`i18n/{fr,en}.json` files, including chart titles, table headers, and
alert messages.

**I connected the dashboard to the MCP server through a real HTTP
connection**, not a simple Python code import. The "AI Assistant" page
calls the deployed MCP server (`streamable-http` protocol, with an access
key) through a real MCP client (`dashboard/components/mcp_client.py`).
Answers genuinely go through this protocol, with no in-memory shortcut.

**I added a data backup on Google Cloud Storage (GCS)** for files uploaded
from the Administration tab. Without it, the hosting platform used (Cloud
Run) would lose all data on every restart, since it doesn't keep anything
permanently in memory. How it works: a file uploaded by a business user is
first checked, then the whole pipeline runs again (about 55 seconds
measured, in an isolated space), and the result is saved to a GCS location
that every copy of the app reloads on its own startup
(`src/storage_sync.py`, detailed in `docs/architecture_en.md` section 6). I
also added a data-schema version check. This safeguard prevents a future
structural change in dbt from being silently overwritten by an older
backup restored from GCS.

**I gave the dashboard's 9 pages one single, shared visual identity**
(black and orange colors, shared building blocks defined in
`dashboard/components/ui.py`: page banner, reading guide, section headers,
indicator cards with red/orange/green color coding, alert messages),
instead of letting each page have its own style. The dashboard now reads as
one coherent tool. I kept the already-validated segment color palette
instead of the colors originally planned, after noticing two of them were
too close to be clearly told apart by color-vision-deficient users. Every
page that shows alerts also displays a real positive signal (healthy
portfolio, identified opportunities), not just risks. The detail behind
these choices is in `docs/decisions_en.md`.

## 3. A real analytical conclusion, not generic advice

Looking only at real customers (synthetic customers are excluded, so a copy
isn't counted as a second customer), 2 Premier-segment customers have a
high credit risk level (`risk_band = High`): Murielle Aka (risk score
26.4/100, balance 6.44M FCFA) and Bintou Soro (score 19.0/100, balance
5.52M FCFA), for a combined balance of 11.97M FCFA. These are the only 2
Premier customers in this situation, out of the segment's 49 real
customers. The dashboard (Retention and Risk page) points to a clear,
immediate business priority: call these 2 accounts within 48 hours. This is
not generic advice like "contact at-risk customers."

## 4. Limitations, stated plainly

- The real dataset is small (140 customers, 34 loans, 42 complaints).
  Detail in `docs/ml_problem_definition_en.md`, section 6.
- The NBI (Net Banking Income, a revenue indicator generated by the
  customer) shown is an estimate computed with a standard formula, not the
  customer's real accounting figure. See `docs/decisions_en.md`.
- The near-perfect RandomForest and XGBoost scores on the enriched dataset
  don't guarantee they would work as well in production on new, unseen
  customers. See `docs/model_comparison_en.md`.
- This project remains a decision-support tool: no action is triggered
  automatically from a score. A person always stays in the decision loop.

## 5. Tools used

Python 3.11 · dbt-duckdb · DuckDB · scikit-learn/XGBoost · MLflow ·
Streamlit · Model Context Protocol (MCP) · Docker · Google Cloud Run.
