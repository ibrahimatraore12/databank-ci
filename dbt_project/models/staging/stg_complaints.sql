-- Nettoyage des réclamations : typage explicite, fusion réel + synthétique
-- Complaint cleanup: explicit typing, merges real + synthetic

with union_reel_synthetique as (
    select * from {{ source('bronze', 'bronze_complaints') }}
    union all
    select * from {{ source('bronze', 'bronze_synthetic_complaints') }}
)

select
    cast(complaint_id as varchar) as complaint_id,
    cast(customer_id as varchar) as customer_id,
    cast(opened_date as date) as opened_date,
    cast(closed_date as date) as closed_date,
    cast(category as varchar) as category,
    cast(severity as varchar) as severity,
    cast(status as varchar) as status,
    cast(root_cause as varchar) as root_cause,
    cast(compensation_xof as decimal(15, 2)) as compensation_xof,
    cast(free_text as varchar) as free_text,
    cast(is_synthetic as boolean) as is_synthetic,
    current_timestamp as updated_at
from union_reel_synthetique
