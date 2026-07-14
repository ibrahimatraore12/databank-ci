-- Agrégats par segment client : vue de pilotage du portefeuille
-- Customer segment aggregates: portfolio steering view

select
    segment,
    count(*) as nb_clients,
    round(avg(risque_composite), 1) as risque_composite_moyen,
    sum(case when is_high_value_at_risk then 1 else 0 end) as nb_high_value_at_risk,
    sum(case when is_digitally_dormant_salary then 1 else 0 end) as nb_digitally_dormant_salary,
    sum(case when is_complaints_churn_risk then 1 else 0 end) as nb_complaints_churn_risk,
    sum(case when is_cross_sell_target then 1 else 0 end) as nb_cross_sell_target,
    sum(case when is_salary_upsell_opportunity then 1 else 0 end) as nb_salary_upsell_opportunity,
    round(100.0 * sum(case when salaire_domicilie then 1 else 0 end) / count(*), 1) as taux_salaire_domicilie_pct,
    round(avg(score_digital), 1) as score_digital_moyen,
    current_timestamp as updated_at
from {{ ref('customer_360') }}
group by segment
