-- Table Gold Customer 360 : vue unique du client combinant profil, comportement,
-- score de risque composite et classes ontologiques métier
-- Gold Customer 360 table: single customer view combining profile, behavior,
-- composite risk score, and business ontology classes

with date_reference as (
    select max(txn_datetime) as date_ref from {{ ref('stg_transactions') }}
),

base as (
    select
        c.customer_id,
        c.full_name,
        c.segment,
        c.risk_band,
        c.city,
        c.district,
        c.monthly_income_xof,
        c.preferred_channel,
        c.mobile_app_active,
        c.internet_banking_active,
        c.mobile_money_linked,
        c.is_synthetic,
        r.recency_jours,
        t.tendance_transactions,
        t.nb_txn_recent_30j as nb_txn_30j,
        t.nb_txn_90j,
        t.tendance_3m,
        cp.nb_reclamations_ouvertes,
        cp.nb_reclamations_total,
        cp.nb_reclamations_severite_haute,
        d.score_digital,
        p.nb_comptes,
        p.nb_cartes,
        p.nb_produits_total,
        bal.solde_total_xof,
        bal.avg_balance_90d_total_xof as avg_balance_90d_xof,
        nbi.nbi_estime_xof,
        ch.canal_majoritaire,
        ln.dpd_max,
        date_diff('day', c.onboarding_date, dr.date_ref) as anciennete_jours,
        exists (
            select 1 from {{ ref('stg_accounts') }} a
            where a.customer_id = c.customer_id and a.salary_domiciled_corrige
        ) as salaire_domicilie
    from {{ ref('stg_customers') }} c
    cross join date_reference dr
    left join {{ ref('int_customer_recency') }} r on c.customer_id = r.customer_id
    left join {{ ref('int_customer_transaction_trend') }} t on c.customer_id = t.customer_id
    left join {{ ref('int_customer_complaints') }} cp on c.customer_id = cp.customer_id
    left join {{ ref('int_customer_digital_score') }} d on c.customer_id = d.customer_id
    left join {{ ref('int_customer_products') }} p on c.customer_id = p.customer_id
    left join {{ ref('int_customer_balance') }} bal on c.customer_id = bal.customer_id
    left join {{ ref('int_customer_nbi') }} nbi on c.customer_id = nbi.customer_id
    left join {{ ref('int_customer_channel') }} ch on c.customer_id = ch.customer_id
    left join {{ ref('int_customer_loans') }} ln on c.customer_id = ln.customer_id
),

-- Normalisation min-max de chaque signal sur 0-100 pour construire le score composite
-- Min-max normalization of each signal onto 0-100 to build the composite score
normalise as (
    select
        *,
        min(recency_jours) over () as recency_min,
        max(recency_jours) over () as recency_max,
        min(nb_reclamations_ouvertes) over () as reclamations_min,
        max(nb_reclamations_ouvertes) over () as reclamations_max,
        min(score_digital) over () as digital_min,
        max(score_digital) over () as digital_max,
        min(tendance_transactions) over () as tendance_min,
        max(tendance_transactions) over () as tendance_max
    from base
),

-- Sens des sous-scores de RISQUE (pas d'engagement) : plus de jours d'inactivité
-- et plus de réclamations ouvertes = risque plus élevé (relation directe) ;
-- plus de digital et une tendance positive = risque plus faible (relation inverse)
-- Direction of the RISK sub-scores (not engagement): more inactive days and
-- more open complaints = higher risk (direct relation); more digital adoption
-- and a positive trend = lower risk (inverse relation)
score as (
    select
        *,
        100.0 * (recency_jours - recency_min) / nullif(recency_max - recency_min, 0) as sous_score_recency,
        100.0 * (nb_reclamations_ouvertes - reclamations_min) / nullif(reclamations_max - reclamations_min, 0) as sous_score_reclamations,
        100 - (100.0 * (score_digital - digital_min) / nullif(digital_max - digital_min, 0)) as sous_score_digital,
        100 - (100.0 * (tendance_transactions - tendance_min) / nullif(tendance_max - tendance_min, 0)) as sous_score_tendance
    from normalise
)

select
    customer_id,
    full_name,
    segment,
    risk_band,
    city,
    district,
    monthly_income_xof,
    preferred_channel,
    mobile_app_active,
    internet_banking_active,
    mobile_money_linked,
    salaire_domicilie,
    recency_jours,
    tendance_transactions,
    nb_txn_30j,
    nb_txn_90j,
    tendance_3m,
    nb_reclamations_ouvertes,
    nb_reclamations_total,
    nb_reclamations_severite_haute,
    score_digital,
    nb_comptes,
    nb_cartes,
    nb_produits_total,
    solde_total_xof,
    avg_balance_90d_xof,
    nbi_estime_xof,
    canal_majoritaire,
    dpd_max,
    anciennete_jours,
    round(
        coalesce(sous_score_recency, 50) * {{ var('rules_weight_recency') }}
        + coalesce(sous_score_reclamations, 50) * {{ var('rules_weight_complaints') }}
        + coalesce(sous_score_digital, 50) * {{ var('rules_weight_digital') }}
        + coalesce(sous_score_tendance, 50) * {{ var('rules_weight_trend') }},
        1
    ) as risque_composite,
    -- Classe ontologique 1 : client à forte valeur montrant des signaux de désengagement
    -- Ontology class 1: high-value customer showing disengagement signals
    (segment in ('Premier', 'Affluent') and recency_jours > 60) as is_high_value_at_risk,
    -- Classe ontologique 2 : salaire domicilié mais quasiment absent des canaux digitaux
    -- Ontology class 2: salary domiciled but nearly absent from digital channels
    (salaire_domicilie and score_digital <= 1) as is_digitally_dormant_salary,
    -- Classe ontologique 3 : réclamation ouverte et activité transactionnelle en baisse
    -- Ontology class 3: open complaint and declining transaction activity
    (nb_reclamations_ouvertes > 0 and recency_jours > 60) as is_complaints_churn_risk,
    -- Classe ontologique 4 : client sans carte bancaire — cible cross-sell
    -- Ontology class 4: customer without a bank card — cross-sell target
    (nb_cartes = 0) as is_cross_sell_target,
    -- Classe ontologique 5 : revenu élevé sans domiciliation de salaire — opportunité upsell
    -- Ontology class 5: high income without salary domiciliation — upsell opportunity
    (not salaire_domicilie and monthly_income_xof >= {{ var('salary_upsell_income_threshold_xof') }}) as is_salary_upsell_opportunity,
    is_synthetic,
    current_timestamp as updated_at
from score
