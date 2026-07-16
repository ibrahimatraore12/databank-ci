# ML Problem Definition — dataBank CI Customer 360

> *[Version française disponible : [ml_problem_definition.md](ml_problem_definition.md)]*

**Author:** Ibrahima TRAORÉ — Analytics Engineer
**Date:** July 2026
**Status:** Initial framing, before development

## 1. Business question

> Among the bank's active customers, how do we identify those showing early
> signals of disengagement — so that relationship managers can prioritize
> their actions before an actual departure (account closure, total
> inactivity) occurs?

This score isn't meant to replace the advisor's judgment: it's used to
triage a 140-customer portfolio so advisors spend their time on the accounts
that need it most.

## 2. Problem type

**This is not a classic supervised classification problem.**

The source dataset (`starter_dataset.xlsx`) contains no observed real
`churn_flag` column: there is no history of confirmed customer departures.
What we call "churn" in this project is actually a **proxy label built from
documented business heuristics** (transaction recency, unresolved
complaints, activity trend, digital usage).

I treat this project as:

- a **rule-based behavioral score** (Phase 1, `ml/rules.py`), always
  available and interpretable without a model;
- a **supervised ML experiment on a proxy label** (Phase 2), useful for
  comparing approaches and documenting methodology, but whose metrics
  should not be presented as a prediction of real churn.

## 3. Business hypotheses (H1 to H4)

| # | Hypothesis | Signal used | Weight in the rule-based score |
|---|-----------|-----------------|-------------------------------|
| H1 | A customer who hasn't transacted in a long time is disengaging | `recency_days` (last transaction) | 40% |
| H2 | A customer with open or poorly resolved complaints is losing trust | `open_complaints_count`, `sentiment`, `resolved_flag` | 30% |
| H3 | A drop in transaction frequency/volume over the recent period precedes a departure | transaction trend (last 30 days vs. prior period) | 10% |
| H4 | A customer with low digital channel engagement is more exposed to churn risk (fewer touchpoints) | `mobile_app_active`, `internet_banking_active`, `mobile_money_linked` | 20% |

These weights belong to the rule-based score (Phase 1). The digital
engagement score used elsewhere in the project (feature generation) has a
different weighting, documented separately in `docs/decisions_en.md`.

## 4. What is missing for a real churn model

- **Real churn history**: no account closure date or departure reason is
  available across more than one period, so labeling an actual churn event
  is not possible.
- **Real Net Banking Income (NBI)**: only an estimate using the standard
  WAEMU formula can be computed (`estimated_nbi_flag=True`), not the
  customer's real accounting NBI.
- **External credit bureau**: no data on a customer's total indebtedness
  outside the bank is available, which limits the reliability of the credit
  risk score.
- **Multi-period history**: the dataset is a single point-in-time snapshot,
  not a long time series — so the notion of "trend" stays approximate.

## 5. Label distribution and class imbalance

Figures measured on the real portfolio (140 customers), not estimates:

- **Naive label** (single criterion: recency > 90 days): **2 positives, or
  1.4%**. Far too few to train anything on — essentially sampling noise.
- **Enriched label** (at least 2 of 4 signals triggered among recency, open
  complaint, negative trend, low digital usage): **35 positives, or 25.0%**.
  This rate turned out higher than expected during initial project scoping
  (a target of 12-15% had been anticipated before measurement). The gap
  comes from the "negative trend" criterion, which alone covers a large
  share of the portfolio over the observed data window — see Section 11 of
  the EDA notebook for the per-criterion breakdown.
- For comparison, a 3-out-of-4 threshold keeps only 1 positive (0.7%): too
  strict to be usable. I retained the 2-criteria threshold as the most
  defensible compromise, documented here rather than adjusted after the
  fact to hit a target figure.

**Consequences documented honestly:**

- The 25% rate makes the real dataset usable for an 80/20 stratified split
  (roughly 7 positives in a 28-customer test set), but the sample stays
  small in absolute terms (140 customers total).
- Metrics (AUC, Recall, Precision, F1) computed on the real dataset should
  be read as indicative, not as guarantees of generalization.
- `ml/model.py::evaluate_model` raises an explicit warning if `n < 200` or
  if the number of positives is `< 20` — which triggers systematically on a
  split of the real dataset (n=140).
- An enriched synthetic dataset (`data/enriched/`, `is_synthetic=True`) is
  generated through business-rule bootstrapping to bring volume to ~540
  customers, enabling a model comparison with a more comfortable test
  sample (see `docs/model_comparison.md`, produced at the ML step).
- Synthetic data always stays clearly flagged as such in the Gold tables and
  in the dashboard — it never replaces real data in the default operational
  views.

## 6. Project limitations, stated plainly

- This score is a prioritization aid, not a statistically validated
  prediction based on real historical outcomes.
- The real dataset is small (140 customers, 34 loans, 42 complaints): any
  conclusion needs to be weighed against this sample size.
- Synthetic data respects the distributions observed during EDA but cannot
  invent correlations the real world doesn't confirm.
- This project is an end-to-end analytics engineering exercise (ingestion →
  dbt → ML → dashboard → MCP), not a regulatory credit-scoring deliverable.
