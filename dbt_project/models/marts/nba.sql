-- Action recommandée par client (Next Best Action), dérivée des classes ontologiques
-- Recommended action per customer (Next Best Action), derived from the ontology classes
-- Priorité : réclamation > risque forte valeur > upsell salaire > cross-sell carte > réactivation digitale
-- Priority: complaint > high-value risk > salary upsell > card cross-sell > digital reactivation

select
    customer_id,
    segment,
    case
        when is_complaints_churn_risk then 'Contacter en priorité — réclamation ouverte et activité en baisse'
        when is_high_value_at_risk then 'Visite conseiller — client à forte valeur en risque de désengagement'
        when is_salary_upsell_opportunity then 'Proposer la domiciliation de salaire'
        when is_cross_sell_target then 'Proposer une carte bancaire'
        when is_digitally_dormant_salary then 'Relancer sur les canaux digitaux'
        else 'Aucune action prioritaire'
    end as next_best_action,
    risque_composite,
    current_timestamp as updated_at
from {{ ref('customer_360') }}
