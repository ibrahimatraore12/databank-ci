-- Nettoyage des comptes : typage explicite, fusion réel + synthétique, et
-- correction de salary_domiciled_flag à partir des transactions observées
-- (un compte non-flaggé qui reçoit un crédit "salary_credit" est en réalité domicilié)
-- Account cleanup: explicit typing, merges real + synthetic, and corrects
-- salary_domiciled_flag from observed transactions (an unflagged account that
-- receives a "salary_credit" is in fact salary-domiciled) — see docs/decisions.md

with union_reel_synthetique as (
    select * from {{ source('bronze', 'bronze_accounts') }}
    union all
    select * from {{ source('bronze', 'bronze_synthetic_accounts') }}
),

comptes_avec_credit_salaire as (
    select distinct account_id
    from {{ ref('stg_transactions') }}
    where txn_type = 'salary_credit'
)

select
    cast(a.account_id as varchar) as account_id,
    cast(a.customer_id as varchar) as customer_id,
    cast(a.account_type as varchar) as account_type,
    cast(a.currency as varchar) as currency,
    cast(a.open_date as date) as open_date,
    cast(a.status as varchar) as status,
    cast(a.branch_id as varchar) as branch_id,
    cast(a.avg_balance_90d_xof as decimal(15, 2)) as avg_balance_90d_xof,
    cast(a.current_balance_xof as decimal(15, 2)) as current_balance_xof,
    cast(a.salary_domiciled_flag as boolean) as salary_domiciled_flag,
    (cast(a.salary_domiciled_flag as boolean) or c.account_id is not null) as salary_domiciled_corrige,
    cast(a.overdraft_limit_xof as decimal(15, 2)) as overdraft_limit_xof,
    cast(a.is_synthetic as boolean) as is_synthetic,
    current_timestamp as updated_at
from union_reel_synthetique a
left join comptes_avec_credit_salaire c on a.account_id = c.account_id
