-- Nettoyage des interactions client : typage explicite, fusion réel + synthétique
-- Customer interaction cleanup: explicit typing, merges real + synthetic

with union_reel_synthetique as (
    select * from {{ source('bronze', 'bronze_interactions') }}
    union all
    select * from {{ source('bronze', 'bronze_synthetic_interactions') }}
)

select
    cast(interaction_id as varchar) as interaction_id,
    cast(customer_id as varchar) as customer_id,
    cast(interaction_datetime as timestamp) as interaction_datetime,
    cast(channel as varchar) as channel,
    cast(interaction_type as varchar) as interaction_type,
    cast(topic as varchar) as topic,
    cast(sentiment as varchar) as sentiment,
    cast(resolved_flag as boolean) as resolved_flag,
    cast(resolution_time_hours as decimal(10, 2)) as resolution_time_hours,
    cast(agent_team as varchar) as agent_team,
    cast(notes as varchar) as notes,
    cast(is_synthetic as boolean) as is_synthetic,
    current_timestamp as updated_at
from union_reel_synthetique
