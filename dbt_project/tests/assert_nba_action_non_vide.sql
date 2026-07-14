-- Test singulier : chaque client doit avoir une action recommandée non vide
-- Singular test: every customer must have a non-empty recommended action
-- Un dbt test échoue si cette requête renvoie une ou plusieurs lignes
-- A dbt test fails if this query returns any row

select customer_id, next_best_action
from {{ ref('nba') }}
where next_best_action is null or trim(next_best_action) = ''
