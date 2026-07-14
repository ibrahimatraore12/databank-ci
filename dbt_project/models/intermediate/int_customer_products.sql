-- Agrège le nombre de produits détenus par client : comptes et cartes
-- Aggregates the number of products held per customer: accounts and cards

with comptes_agg as (
    select customer_id, count(*) as nb_comptes
    from {{ ref('stg_accounts') }}
    group by customer_id
),

cartes_agg as (
    select customer_id, count(*) as nb_cartes
    from {{ ref('stg_cards') }}
    group by customer_id
)

select
    c.customer_id,
    coalesce(co.nb_comptes, 0) as nb_comptes,
    coalesce(ca.nb_cartes, 0) as nb_cartes,
    coalesce(co.nb_comptes, 0) + coalesce(ca.nb_cartes, 0) as nb_produits_total
from {{ ref('stg_customers') }} c
left join comptes_agg co on c.customer_id = co.customer_id
left join cartes_agg ca on c.customer_id = ca.customer_id
