-- Agrège les soldes de tous les comptes d'un client : solde courant total et
-- base de solde moyen 90j utilisée par le calcul du NBI estimé
-- Aggregates all of a customer's account balances: total current balance and
-- the 90-day average balance base used by the estimated NBI calculation

with soldes_agg as (
    select
        customer_id,
        sum(current_balance_xof) as solde_total_xof,
        sum(avg_balance_90d_xof) as avg_balance_90d_total_xof
    from {{ ref('stg_accounts') }}
    group by customer_id
)

select
    c.customer_id,
    coalesce(s.solde_total_xof, 0) as solde_total_xof,
    coalesce(s.avg_balance_90d_total_xof, 0) as avg_balance_90d_total_xof
from {{ ref('stg_customers') }} c
left join soldes_agg s on c.customer_id = s.customer_id
