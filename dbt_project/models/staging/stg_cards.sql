-- Nettoyage des cartes : typage explicite, fusion réel + synthétique
-- Card cleanup: explicit typing, merges real + synthetic

with union_reel_synthetique as (
    select * from {{ source('bronze', 'bronze_cards') }}
    union all
    select * from {{ source('bronze', 'bronze_synthetic_cards') }}
)

select
    cast(card_id as varchar) as card_id,
    cast(customer_id as varchar) as customer_id,
    cast(account_id as varchar) as account_id,
    cast(card_type as varchar) as card_type,
    cast(card_tier as varchar) as card_tier,
    cast(network as varchar) as network,
    cast(issue_date as date) as issue_date,
    cast(expiry_date as date) as expiry_date,
    cast(status as varchar) as status,
    cast(contactless_flag as boolean) as contactless_flag,
    cast(ecommerce_enabled as boolean) as ecommerce_enabled,
    cast(monthly_spend_90d_xof as decimal(15, 2)) as monthly_spend_90d_xof,
    cast(is_synthetic as boolean) as is_synthetic,
    current_timestamp as updated_at
from union_reel_synthetique
