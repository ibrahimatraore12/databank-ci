-- NBI estimé (formule UEMOA standard, voir docs/decisions.md) — porte à
-- l'identique la formule déjà documentée et testée dans
-- src/data_enrichment.py::generate_nbi_estime() : ce n'est PAS le NBI
-- comptable réel du client
-- Estimated NBI (standard UEMOA formula, see docs/decisions.md) — mirrors
-- exactly the formula already documented and tested in
-- src/data_enrichment.py::generate_nbi_estime(): NOT the customer's real
-- accounting NBI

with transactions_agg as (
    select customer_id, count(*) as nb_transactions_total
    from {{ ref('stg_transactions') }}
    group by customer_id
)

select
    c.customer_id,
    round(
        coalesce(b.avg_balance_90d_total_xof, 0) * {{ var('nbi_balance_rate') }}
        + coalesce(t.nb_transactions_total, 0) * {{ var('nbi_per_transaction_xof') }}
        + coalesce(p.nb_comptes, 0) * {{ var('nbi_per_product_xof') }},
        0
    ) as nbi_estime_xof
from {{ ref('stg_customers') }} c
left join {{ ref('int_customer_balance') }} b on c.customer_id = b.customer_id
left join transactions_agg t on c.customer_id = t.customer_id
left join {{ ref('int_customer_products') }} p on c.customer_id = p.customer_id
