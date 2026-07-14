-- Nettoyage du référentiel agences : typage explicite (référentiel réel uniquement, pas de synthétique)
-- Branch reference cleanup: explicit typing (real reference data only, no synthetic)

select
    cast(branch_id as varchar) as branch_id,
    cast(branch_name as varchar) as branch_name,
    cast(city as varchar) as city,
    cast(district as varchar) as district,
    cast(branch_type as varchar) as branch_type,
    false as is_synthetic,
    current_timestamp as updated_at
from {{ source('bronze', 'bronze_branches') }}
