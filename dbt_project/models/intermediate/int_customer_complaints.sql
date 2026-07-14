-- Agrège les réclamations par client : ouvertes, total, sévérité haute
-- Aggregates complaints per customer: open, total, high severity

with reclamations_agg as (
    select
        customer_id,
        count(*) as nb_reclamations_total,
        sum(case when status = 'Open' then 1 else 0 end) as nb_reclamations_ouvertes,
        sum(case when severity = 'High' then 1 else 0 end) as nb_reclamations_severite_haute
    from {{ ref('stg_complaints') }}
    group by customer_id
)

select
    c.customer_id,
    coalesce(r.nb_reclamations_total, 0) as nb_reclamations_total,
    coalesce(r.nb_reclamations_ouvertes, 0) as nb_reclamations_ouvertes,
    coalesce(r.nb_reclamations_severite_haute, 0) as nb_reclamations_severite_haute
from {{ ref('stg_customers') }} c
left join reclamations_agg r on c.customer_id = r.customer_id
