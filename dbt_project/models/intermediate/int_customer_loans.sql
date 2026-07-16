-- Calcule le retard de paiement maximum observé parmi les prêts d'un client
-- Computes the maximum payment delinquency observed among a customer's loans

with retard_agg as (
    select customer_id, max(days_past_due) as dpd_max
    from {{ ref('stg_loans') }}
    group by customer_id
)

select
    c.customer_id,
    coalesce(r.dpd_max, 0) as dpd_max
from {{ ref('stg_customers') }} c
left join retard_agg r on c.customer_id = r.customer_id
