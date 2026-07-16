-- Détermine le canal bancaire le plus utilisé par chaque client (nombre de
-- transactions par canal, canal en tête retenu)
-- Determines each customer's most-used banking channel (transaction count per
-- channel, top channel kept)

with comptage as (
    select
        t.customer_id,
        ch.channel_name,
        count(*) as nb_transactions
    from {{ ref('stg_transactions') }} t
    left join {{ ref('stg_channels') }} ch on t.channel_id = ch.channel_id
    group by t.customer_id, ch.channel_name
),

transactions_par_canal as (
    select
        customer_id,
        channel_name,
        row_number() over (
            partition by customer_id order by nb_transactions desc, channel_name
        ) as rang
    from comptage
)

select
    c.customer_id,
    p.channel_name as canal_majoritaire
from {{ ref('stg_customers') }} c
left join transactions_par_canal p on c.customer_id = p.customer_id and p.rang = 1
