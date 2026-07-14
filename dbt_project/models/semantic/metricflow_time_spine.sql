-- Modèle technique requis par le semantic layer dbt (MetricFlow) : une ligne par jour
-- Technical model required by dbt's semantic layer (MetricFlow): one row per day
{{ config(materialized='table') }}

select cast(generate_series as date) as date_day
from generate_series(cast('2023-01-01' as date), cast('2027-12-31' as date), interval '1 day')
