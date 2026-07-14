-- Nettoyage de la table clients : typage explicite, booléens normalisés,
-- fusion des clients réels et synthétiques (marqués is_synthetic)
-- Customer cleanup: explicit typing, normalized booleans, merges real and
-- synthetic customers (flagged via is_synthetic)

with reel as (
    select * from {{ source('bronze', 'bronze_customers') }}
),

synthetique as (
    select * from {{ source('bronze', 'bronze_synthetic_customers') }}
),

union_reel_synthetique as (
    select * from reel
    union all
    select * from synthetique
)

select
    cast(customer_id as varchar) as customer_id,
    cast(full_name as varchar) as full_name,
    cast(gender as varchar) as gender,
    cast(date_of_birth as date) as date_of_birth,
    cast(city as varchar) as city,
    cast(district as varchar) as district,
    cast(occupation as varchar) as occupation,
    cast(segment as varchar) as segment,
    cast(monthly_income_xof as decimal(15, 2)) as monthly_income_xof,
    cast(onboarding_date as date) as onboarding_date,
    cast(primary_branch_id as varchar) as primary_branch_id,
    cast(preferred_channel as varchar) as preferred_channel,
    cast(mobile_app_active as boolean) as mobile_app_active,
    cast(internet_banking_active as boolean) as internet_banking_active,
    cast(mobile_money_linked as boolean) as mobile_money_linked,
    cast(kyc_level as varchar) as kyc_level,
    cast(risk_band as varchar) as risk_band,
    cast(marketing_opt_in as boolean) as marketing_opt_in,
    cast(last_contact_date as date) as last_contact_date,
    cast(marital_status as varchar) as marital_status,
    cast(is_synthetic as boolean) as is_synthetic,
    current_timestamp as updated_at
from union_reel_synthetique
