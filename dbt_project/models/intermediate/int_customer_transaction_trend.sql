-- Calcule la tendance d'activité transactionnelle : 30 derniers jours vs les 30 jours précédents
-- Computes transaction activity trend: last 30 days vs. the 30 days before that

with date_reference as (
    select max(txn_datetime) as date_ref from {{ ref('stg_transactions') }}
),

activite_recente as (
    select t.customer_id, count(*) as nb_txn_recent_30j
    from {{ ref('stg_transactions') }} t
    cross join date_reference d
    where t.txn_datetime > d.date_ref - interval '30 days'
    group by t.customer_id
),

activite_precedente as (
    select t.customer_id, count(*) as nb_txn_precedent_30j
    from {{ ref('stg_transactions') }} t
    cross join date_reference d
    where t.txn_datetime > d.date_ref - interval '60 days'
      and t.txn_datetime <= d.date_ref - interval '30 days'
    group by t.customer_id
)

select
    c.customer_id,
    coalesce(r.nb_txn_recent_30j, 0) as nb_txn_recent_30j,
    coalesce(p.nb_txn_precedent_30j, 0) as nb_txn_precedent_30j,
    coalesce(r.nb_txn_recent_30j, 0) - coalesce(p.nb_txn_precedent_30j, 0) as tendance_transactions
from {{ ref('stg_customers') }} c
left join activite_recente r on c.customer_id = r.customer_id
left join activite_precedente p on c.customer_id = p.customer_id
