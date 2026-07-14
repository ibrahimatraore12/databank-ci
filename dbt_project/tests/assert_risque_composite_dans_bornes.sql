-- Test singulier : le risque composite doit toujours rester dans l'intervalle 0-100
-- Singular test: the composite risk score must always stay within the 0-100 range
-- Un dbt test échoue si cette requête renvoie une ou plusieurs lignes
-- A dbt test fails if this query returns any row

select customer_id, risque_composite
from {{ ref('customer_360') }}
where risque_composite < 0 or risque_composite > 100
