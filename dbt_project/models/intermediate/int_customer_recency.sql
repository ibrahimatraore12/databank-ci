-- Calcule la récence de chaque client : jours écoulés depuis sa dernière transaction
-- Computes each customer's recency: days elapsed since their last transaction

with date_reference as (
    select max(txn_datetime) as date_ref from {{ ref('stg_transactions') }}
),

derniere_transaction as (
    select customer_id, max(txn_datetime) as derniere_txn_datetime
    from {{ ref('stg_transactions') }}
    group by customer_id
)

select
    c.customer_id,
    d.derniere_txn_datetime,
    -- Un client sans transaction observée reçoit une récence sentinelle élevée (999 jours)
    -- A customer with no observed transaction gets a high sentinel recency (999 days)
    coalesce(date_diff('day', d.derniere_txn_datetime, r.date_ref), 999) as recency_jours
from {{ ref('stg_customers') }} c
left join derniere_transaction d on c.customer_id = d.customer_id
cross join date_reference r
