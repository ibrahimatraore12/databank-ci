-- Nettoyage du référentiel canaux : typage explicite (référentiel réel uniquement, pas de synthétique)
-- Channel reference cleanup: explicit typing (real reference data only, no synthetic)

select
    cast(channel_id as varchar) as channel_id,
    cast(channel_name as varchar) as channel_name,
    cast(channel_group as varchar) as channel_group,
    cast(description as varchar) as description,
    false as is_synthetic,
    current_timestamp as updated_at
from {{ source('bronze', 'bronze_channels') }}
