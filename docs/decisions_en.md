# Design Decision Log — dataBank CI Customer 360

> *[Version française disponible : [decisions.md](decisions.md)]*

**Author:** Ibrahima TRAORÉ — Analytics Engineer

Format: Date | Decision | Reason | Alternative rejected

| Date | Decision | Reason | Alternative rejected |
|------|----------|--------|----------------------|
| 2026-07-14 | Dedicated `databank-ci-env` environment (pyenv, Python 3.11.9), isolated from the `databank-customer360-ci` project | Avoid dependency conflicts between the two projects, even though they share the same data source | Reuse the existing `databank-c360-env` environment |
| 2026-07-14 | The disengagement score is treated as a rule-based business score in Phase 1, and as an ML experiment on a proxy label in Phase 2 | The dataset has no observed real churn (see `docs/ml_problem_definition.md`); presenting an ML score as ground truth would be misleading | Train a supervised model directly, skipping the rule-based step |
| 2026-07-14 | Generate a synthetic dataset (`is_synthetic=True`) to bring volume from 140 to ~540 customers | The naive label (1 criterion) has only 2 positives (1.4%); even the enriched label at 25.0% stays small in absolute terms on 140 customers — a larger test sample is needed for a robust model comparison | Train only on the 140 real customers and accept unreliable metrics |
| 2026-07-14 | Enriched label threshold set at >= 2 out of 4 criteria (not tuned to hit a specific positive rate) | Measured on real data: 1 criterion = 70% (too permissive), 2 criteria = 25.0%, 3 criteria = 0.7% (too strict). The 2-criteria threshold is the most defensible compromise, documented as-is rather than adjusted after the fact to match a target | Search for a threshold or weighting that would artificially produce a 12-15% positive rate |
| 2026-07-14 | All synthetic data stays flagged `is_synthetic=True` in the Gold tables and in the dashboard | Traceability: never let a user mistake generated data for real data | Silently merge real and synthetic data |
| 2026-07-14 | NBI is estimated using the standard WAEMU formula and flagged `estimated_nbi_flag=True` | Real accounting NBI is not in the source dataset | Don't produce an NBI figure at all |
| 2026-07-14 | `seed=42` and `random_state=42` fixed everywhere (dbt seeds, ML split, synthetic generation) | Idempotence: re-running the pipeline must produce the same result every time | Unfixed random seed |
| 2026-07-14 | No Python classes (OOP) in business logic; only pure, chained functions | Readability for quick human review, consistent with the coding style set for this project | Classic object-oriented modeling (`Customer`, `Pipeline` classes, etc.) |
| 2026-07-14 | Strict semantic layer: no technical column name appears in the dashboard, everything goes through `LABELS` (`dashboard/components/ui.py`) and the `i18n/*.json` files | The dashboard is built for relationship managers, not data engineers | Display raw SQL/pandas column names directly |
| 2026-07-14 | Payment delay threshold (`days_past_due`) set at 15 days for loan status correction in `stg_loans.sql` | Observed in EDA: real `Watchlist`/`Delinquent` loans exceed this threshold, `Current` loans stay below it | Use the raw `status` field from the source file without cross-checking it against actual DPD |
