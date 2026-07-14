-- Nettoyage des transactions : typage explicite, fusion réel + synthétique
-- Transaction cleanup: explicit typing, merges real + synthetic

with union_reel_synthetique as (
    select * from {{ source('bronze', 'bronze_transactions') }}
    union all
    select * from {{ source('bronze', 'bronze_synthetic_transactions') }}
)

select
    cast(txn_id as varchar) as txn_id,
    cast(account_id as varchar) as account_id,
    cast(customer_id as varchar) as customer_id,
    cast(txn_datetime as timestamp) as txn_datetime,
    cast(txn_type as varchar) as txn_type,
    cast(channel_id as varchar) as channel_id,
    cast(merchant_category as varchar) as merchant_category,
    cast(amount_xof as decimal(15, 2)) as amount_xof,
    cast(direction as varchar) as direction,
    cast(counterparty_type as varchar) as counterparty_type,
    cast(city as varchar) as city,
    cast(is_international as boolean) as is_international,
    cast(is_disputed as boolean) as is_disputed,
    cast(is_synthetic as boolean) as is_synthetic,
    current_timestamp as updated_at
from union_reel_synthetique
