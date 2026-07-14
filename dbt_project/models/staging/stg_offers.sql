-- Nettoyage des offres commerciales : typage explicite, fusion réel + synthétique
-- Commercial offer cleanup: explicit typing, merges real + synthetic

with union_reel_synthetique as (
    select * from {{ source('bronze', 'bronze_offers') }}
    union all
    select * from {{ source('bronze', 'bronze_synthetic_offers') }}
)

select
    cast(offer_id as varchar) as offer_id,
    cast(customer_id as varchar) as customer_id,
    cast(offer_date as date) as offer_date,
    cast(offer_type as varchar) as offer_type,
    cast(channel as varchar) as channel,
    cast(accepted_flag as boolean) as accepted_flag,
    cast(product_target as varchar) as product_target,
    cast(expected_value_xof as decimal(15, 2)) as expected_value_xof,
    cast(is_synthetic as boolean) as is_synthetic,
    current_timestamp as updated_at
from union_reel_synthetique
