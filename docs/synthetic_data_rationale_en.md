# Synthetic Data Explanation - dataBank CI Customer 360

> *[French version: [synthetic_data_rationale.md](synthetic_data_rationale.md)]*

**Author:** Ibrahima TRAORÉ - Analytics Engineer
**Date:** July 2026

## 1. Why generate synthetic (artificial) data

The real portfolio has 140 customers, 35 of whom count as "disengaged"
under the enriched approximate indicator (see
`docs/ml_problem_definition_en.md`, section 5), or 25.0%. That's too few
to reliably compare several Machine Learning models with a solid
training/test split. The `ml/model.py::evaluate_model` function actually
shows an automatic warning whenever the total number of customers is
below 200, or the number of affected cases is below 20 - which happens
systematically with the real data alone.

So I chose to generate 400 synthetic customers
(`config.SYNTHETIC_N_CUSTOMERS`) to bring the total volume to 540
customers, rather than present unreliable Machine Learning results
computed on only 140 customers.

## 2. The method used: repetition based on business rules, not pure chance

The `src/synthetic_data_generator.py::generate_synthetic_customers()`
function doesn't pull random values with no logic behind them. Here is
the method, step by step:

1. **Selection with possible repetition** of real customers, used as
   starting templates (`_tirer_clients_source`, with a random draw fixed
   by `seed=42` so the exact same result can be reproduced).
2. **Copying and re-identifying** the customer and all their linked
   information (accounts, cards, loans, transactions, complaints,
   interactions, offers), under a new identifier: `SYN-0001`, `SYN-0002`,
   etc. The links between tables (`account_id`, `customer_id`) stay
   consistent after this change (`_remapper_comptes`,
   `_remapper_avec_compte`, `_remapper_table_client`).
3. **Controlled addition of disengagement signs** on part of the
   generated customers (`churn_rate=0.10`, about 40 synthetic customers):
   their transactions are shifted 180 days into the past
   (`_injecter_desengagement`), simulating recent inactivity, without
   inventing a new type of behavior.
4. **Two tables are never artificially generated**: `Branches` and
   `Channels` are shared reference data, with no direct link to a
   specific customer. They are reused as-is.

Every generated row carries the `is_synthetic=True` flag from the Bronze
stage onward (`bronze_synthetic_customers`, etc.). This flag follows the
data through every dbt transformation stage, all the way to the
`customer_360.is_synthetic` column, and it is never hidden in the
dashboard.

## 3. A statistical check: the Kolmogorov-Smirnov test

Generating data that "looks like" real data isn't enough on its own: it
needs to be checked with a statistical method. The
`_valider_distributions_ks()` function compares the spread of real and
synthetic monthly incomes (`monthly_income_xof`) using a statistical test
called the "Kolmogorov-Smirnov test" (the `scipy.stats.ks_2samp`
function), which checks whether two groups of data follow the same
overall pattern. If the test result (the "p-value") drops below 0.05, an
error message is logged (`[SYNTHETIC][KS-TEST] distribution divergente`).
Data generation isn't automatically blocked in that case, but the
discrepancy is logged and can be checked in `logs/pipeline.log`: nothing
is hidden.

## 4. What this method cannot do

- **It cannot invent new relationships between data points** that the
  real world doesn't confirm: a synthetic customer remains, by
  construction, a copy of a real customer with a new identifier. Models
  trained on this enriched dataset can therefore "memorize" details
  specific to their source customer, instead of learning a general trend
  that holds for everyone. See `docs/model_comparison_en.md` to see the
  concrete effect of this risk on the RandomForest and XGBoost scores.
- **It never replaces real data** in the dashboard's default views: the
  `is_synthetic` flag exists precisely so the two types of data are never
  mixed up (see `docs/decisions_en.md`).
- **The added disengagement rate (10%) is a choice**, not a real
  measurement: it only aims to create enough "positive" cases to train a
  model, not to reflect an actually observed customer departure rate.
