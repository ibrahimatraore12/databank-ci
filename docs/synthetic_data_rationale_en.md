# Synthetic Data Rationale - dataBank CI Customer 360

> *[French version: [synthetic_data_rationale.md](synthetic_data_rationale.md)]*

**Author:** Ibrahima TRAORÉ - Analytics Engineer
**Date:** July 2026

## 1. Why generate synthetic data

The real portfolio has 140 customers, 35 positives (25.0%) on the enriched
proxy label (see `docs/ml_problem_definition_en.md`, section 5). That's too
small to compare several supervised models with a reliable train/test split:
`ml/model.py::evaluate_model` actually raises an explicit warning when
`n < 200` or when positives are `< 20`, which happens systematically on the
real dataset alone.

I chose to generate 400 synthetic customers (`config.SYNTHETIC_N_CUSTOMERS`)
to bring the total volume to 540, rather than present unreliable ML metrics
on a 140-customer sample.

## 2. Method: business bootstrap, not random generation

`src/synthetic_data_generator.py::generate_synthetic_customers()` doesn't
draw random values out of thin air. The method:

1. **Sampling with replacement** of real customers as templates
   (`_tirer_clients_source`, `rng.choice` with `seed=42`).
2. **Copying and remapping** the customer and all of their linked tables
   (accounts, cards, loans, transactions, complaints, interactions, offers)
   under a new identifier `SYN-0001`, `SYN-0002`, etc. - relationships
   between tables (`account_id`, `customer_id`) stay consistent after
   remapping (`_remapper_comptes`, `_remapper_avec_compte`,
   `_remapper_table_client`).
3. **Controlled disengagement injection** on a sub-sample
   (`churn_rate=0.10`, i.e. ~40 synthetic customers): their transactions are
   shifted 180 days into the past (`_injecter_desengagement`), simulating
   recent inactivity without inventing a new behavior pattern.
4. **Two tables stay non-synthesized**: `Branches` and `Channels` are shared
   reference data (no customer concept), so they're reused as-is.

Every produced row carries `is_synthetic=True` from the Bronze layer onward
(`bronze_synthetic_customers`, etc.), a flag that flows through every dbt
layer up to `customer_360.is_synthetic` and is never hidden in the
dashboard.

## 3. Statistical validation: Kolmogorov-Smirnov test

Generating data that "looks like" real data isn't proof by itself.
`_valider_distributions_ks()` compares the real and synthetic distribution of
monthly income (`monthly_income_xof`) with a two-sample KS test
(`scipy.stats.ks_2samp`): if the p-value falls below 0.05, an error log is
emitted (`[SYNTHETIC][KS-TEST] distribution divergente`) - generation isn't
automatically blocked on this failure, but the discrepancy is logged and
inspectable in `logs/pipeline.log`, not hidden.

## 4. What this method cannot do

- **It cannot invent new correlations** that the real world doesn't confirm:
  a synthetic customer remains, by construction, a copy of a real customer
  under a new identifier. Models trained on this enriched dataset can
  therefore memorize patterns specific to their source customer rather than
  learn true generalization - see `docs/model_comparison_en.md` for the
  concrete effect of this risk on the RandomForest/XGBoost scores.
- **It never replaces real data** in the dashboard's default operational
  views - the `is_synthetic` flag exists precisely to never confuse the two
  (see `docs/decisions_en.md`).
- **The injected disengagement rate (10%) is a chosen parameter**, not a
  measurement: it aims to produce enough positive volume for training, not
  to reflect an observed real churn rate.
