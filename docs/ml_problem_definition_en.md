# Machine Learning Problem Definition - dataBank CI Customer 360

> *[Version française disponible : [ml_problem_definition.md](ml_problem_definition.md)]*

**Author:** Ibrahima TRAORÉ - Analytics Engineer
**Date:** July 2026
**Status:** Initial framing, before development

## 1. The business question

> Among the bank's active customers, how do we spot the ones showing early
> signs of disengagement, so advisors can act before an actual departure
> happens (account closure, total inactivity)?

This score isn't meant to replace the advisor's judgment. It's used to
triage a 140-customer portfolio, so advisors spend their time on the
accounts that need it most.

## 2. What kind of problem is this, really?

**This is not a classic classification problem**, where we would already
know, for each customer, whether they left or not.

The source file (`starter_dataset.xlsx`) contains no `churn_flag`
(departure indicator) actually observed in real life: there is no history
of confirmed customer departures. What this project calls "churn"
(customer departure or disengagement) is actually an **approximate
indicator ("proxy label"), built from documented business rules**: how
long since the customer last transacted, whether they have unresolved
complaints, how their activity is trending, and how much they use digital
tools.

This project is therefore handled in two steps:

- a **behavioral score based on explicit business rules** (Step 1,
  `ml/rules.py`), always available and easy to understand, even without a
  trained model;
- a **supervised Machine Learning experiment on this approximate
  indicator** (Step 2), useful for comparing different methods and
  documenting the approach, but whose numeric results should not be
  presented as a real prediction of customer departure.

## 3. The business hypotheses (H1 to H4)

| # | Hypothesis | Data used | Weight in the rule-based score |
|---|-----------|-----------------|-------------------------------|
| H1 | A customer who hasn't transacted in a long time is disengaging | `recency_days` (days since last transaction) | 40% |
| H2 | A customer with open or poorly resolved complaints is losing trust | `open_complaints_count`, `sentiment`, `resolved_flag` | 30% |
| H3 | A recent drop in transaction frequency or amount often signals an upcoming departure | transaction trend (last 30 days vs. the prior period) | 10% |
| H4 | A customer with low use of digital tools is more exposed to departure risk (fewer touchpoints with the bank) | `mobile_app_active`, `internet_banking_active`, `mobile_money_linked` | 20% |

These weights belong to the rule-based score (Step 1). Another score, the
digital engagement score used elsewhere in the project (to build
indicators), uses a different weighting, documented separately in
`docs/decisions_en.md`.

## 4. What would be missing for a real churn model

- **A real history of departures**: no account closure date or departure
  reason is available across more than one period. So it's not possible to
  identify an actual customer departure in the data.
- **The customer's real generated revenue (NBI)**: only an estimate using
  the standard WAEMU formula can be computed (`estimated_nbi_flag=True`),
  not the customer's real accounting figure.
- **An external credit bureau**: no data on the customer's total
  indebtedness outside the bank is available, which limits how reliable
  the credit risk score can be.
- **A history across several periods**: the file is a snapshot taken at
  one point in time, not a record over time. So the notion of "trend"
  stays an approximation.

## 5. How cases are split and the class imbalance

Figures measured on the real portfolio (140 customers), not estimates:

- **With a single criterion** (no transaction in over 90 days): **2
  customers affected out of 140, or 1.4%**. That's far too few to train a
  reliable model on: at this level, we're mostly measuring statistical
  noise.
- **With a broader criterion** (at least 2 of 4 signals triggered:
  inactivity, open complaint, negative trend, low digital usage): **35
  customers affected, or 25.0%**. This rate turned out higher than
  expected at the start of the project (a range of 12-15% had been
  anticipated before the real measurement). The gap comes mostly from the
  "negative trend" criterion, which alone covers a large share of the
  portfolio over the observed period. The per-criterion breakdown is in
  section 11 of the exploratory data analysis (EDA) notebook.
- For comparison, requiring 3 out of 4 signals leaves only 1 customer
  affected (0.7%): that threshold is too strict to be useful. The
  2-signal threshold was therefore kept as the best compromise, and this
  choice is documented here as-is, rather than adjusted afterward to reach
  a more flattering number.

**The consequences of this choice, stated honestly:**

- The 25% rate makes it possible to split the real data into a training
  set and a test set (80%/20%) while keeping balanced proportions (roughly
  7 affected customers in a 28-customer test set). But the sample stays
  small in absolute terms (140 customers total).
- The performance indicators computed on the real data (AUC, Recall,
  Precision, F1 - standard measures used to evaluate a prediction model)
  should be read as indicative only, not as a guarantee the model would
  work as well on other customers.
- The `ml/model.py::evaluate_model` function automatically shows a warning
  if the total number of customers is below 200, or if the number of
  affected customers is below 20. This warning shows up systematically on
  the real data (140 customers).
- An enriched synthetic dataset (`data/enriched/`, `is_synthetic=True`) is
  generated from business rules and statistical repetition (a method
  called "bootstrap"), to bring the total volume to about 540 customers.
  This makes it possible to compare models on a more comfortable test
  sample (see `docs/model_comparison_en.md`, produced automatically at the
  Machine Learning step).
- Synthetic data always stays clearly flagged as such in the final (Gold)
  tables and in the dashboard. It never replaces real data in the default
  views.

## 6. Project limitations, stated plainly

- This score is a prioritization aid, not a statistically validated
  prediction based on a real history of departures.
- The real dataset is small (140 customers, 34 loans, 42 complaints): any
  conclusion drawn from this project needs to account for this small
  sample size.
- Synthetic data respects the trends observed during the exploratory
  analysis, but it cannot invent relationships between variables that the
  real world doesn't confirm.
- This project is an end-to-end data engineering exercise (data loading →
  dbt → Machine Learning → dashboard → MCP server), not a
  production-ready, regulation-compliant credit-scoring tool.
