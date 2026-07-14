-- Nettoyage des prêts : typage explicite, fusion réel + synthétique, et
-- correction du statut à partir du retard réel (days_past_due > seuil = Delinquent)
-- Loan cleanup: explicit typing, merges real + synthetic, and corrects status
-- from the real days past due (days_past_due > threshold = Delinquent) — see docs/decisions.md

with union_reel_synthetique as (
    select * from {{ source('bronze', 'bronze_loans') }}
    union all
    select * from {{ source('bronze', 'bronze_synthetic_loans') }}
)

select
    cast(loan_id as varchar) as loan_id,
    cast(customer_id as varchar) as customer_id,
    cast(repayment_account_id as varchar) as repayment_account_id,
    cast(loan_type as varchar) as loan_type,
    cast(origination_date as date) as origination_date,
    cast(principal_xof as decimal(15, 2)) as principal_xof,
    cast(interest_rate_pct as decimal(5, 2)) as interest_rate_pct,
    cast(term_months as integer) as term_months,
    cast(monthly_installment_xof as decimal(15, 2)) as monthly_installment_xof,
    cast(outstanding_balance_xof as decimal(15, 2)) as outstanding_balance_xof,
    cast(days_past_due as integer) as days_past_due,
    cast(status as varchar) as status,
    case
        when cast(days_past_due as integer) > {{ var('loan_dpd_threshold_days') }} then 'Delinquent'
        else cast(status as varchar)
    end as status_corrige,
    cast(purpose as varchar) as purpose,
    cast(collateral_flag as boolean) as collateral_flag,
    cast(next_due_date as date) as next_due_date,
    cast(is_synthetic as boolean) as is_synthetic,
    current_timestamp as updated_at
from union_reel_synthetique
