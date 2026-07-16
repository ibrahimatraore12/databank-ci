# Dictionnaire de données — dataBank CI Customer 360

> *[English version: [data_dictionary_en.md](data_dictionary_en.md)]*

**Auteur :** Ibrahima TRAORÉ — Analytics Engineer
**Date :** Juillet 2026

Ce dictionnaire couvre les 3 tables de la couche Gold
(`dbt_project/models/marts/`), celles que consomment le dashboard, le
serveur MCP et le pipeline ML. Pour le schéma des tables source, voir
`docs/erd_diagram.md`.

## 1. `customer_360` — une ligne par client

| Colonne | Type | Description |
|---------|------|--------------|
| `customer_id` | varchar (PK) | Identifiant unique du client |
| `full_name` | varchar | Nom complet |
| `segment` | varchar | `Mass` / `Affluent` / `Premier` / `Youth` |
| `risk_band` | varchar | `Low` / `Medium` / `High` — niveau de risque crédit déclaré |
| `city`, `district` | varchar | Localisation |
| `monthly_income_xof` | decimal | Revenu mensuel déclaré (FCFA) |
| `preferred_channel` | varchar | Canal bancaire préféré déclaré par le client |
| `mobile_app_active`, `internet_banking_active`, `mobile_money_linked` | boolean | Activation des 3 canaux digitaux |
| `salaire_domicilie` | boolean | Salaire domicilié, corrigé à partir des transactions observées (voir `stg_accounts.sql`) |
| `recency_jours` | integer | Jours depuis la dernière transaction (999 si aucune transaction observée) |
| `tendance_transactions` | integer | Nb transactions 30 derniers jours moins 30 jours précédents |
| `nb_txn_30j`, `nb_txn_90j` | integer | Nombre de transactions sur les fenêtres 30j / 90j |
| `tendance_3m` | integer | Nb transactions 90 derniers jours moins 90 jours précédents |
| `nb_reclamations_ouvertes`, `nb_reclamations_total`, `nb_reclamations_severite_haute` | integer | Agrégats de réclamations |
| `score_digital` | integer (0-3) | Nombre de canaux digitaux activés |
| `nb_comptes`, `nb_cartes`, `nb_produits_total` | integer | Nombre de produits détenus |
| `solde_total_xof` | decimal | Somme des soldes courants de tous les comptes du client |
| `avg_balance_90d_xof` | decimal | Somme des soldes moyens 90 jours de tous les comptes |
| `nbi_estime_xof` | decimal | NBI estimé (formule UEMOA standard, **pas** le NBI comptable réel — voir `docs/decisions.md`) |
| `canal_majoritaire` | varchar | Canal le plus utilisé du client, par nombre de transactions |
| `dpd_max` | integer | Retard de paiement maximum observé (jours), tous prêts confondus |
| `anciennete_jours` | integer | Jours depuis `onboarding_date` |
| `risque_composite` | decimal (0-100) | Score de risque de désengagement — somme pondérée de 4 sous-scores (recency 40 %, réclamations 30 %, digital 20 %, tendance 10 %) |
| `is_high_value_at_risk` | boolean | Segment Premier/Affluent ET recency > 60j |
| `is_digitally_dormant_salary` | boolean | Salaire domicilié ET score digital ≤ 1 |
| `is_complaints_churn_risk` | boolean | Réclamation ouverte ET recency > 60j |
| `is_cross_sell_target` | boolean | Client sans carte |
| `is_salary_upsell_opportunity` | boolean | Revenu élevé (≥ 500 000 FCFA) ET salaire non domicilié |
| `is_synthetic` | boolean | `True` si ligne générée par bootstrap métier — jamais affiché à l'utilisateur final |
| `updated_at` | timestamp | Horodatage de la dernière exécution `dbt run` |

## 2. `customer_segments` — une ligne par segment

| Colonne | Type | Description |
|---------|------|--------------|
| `segment` | varchar (PK) | `Mass` / `Affluent` / `Premier` / `Youth` |
| `nb_clients` | integer | Nombre de clients du segment |
| `risque_composite_moyen` | decimal | Moyenne du score de risque sur le segment |
| `nb_high_value_at_risk`, `nb_digitally_dormant_salary`, `nb_complaints_churn_risk`, `nb_cross_sell_target`, `nb_salary_upsell_opportunity` | integer | Comptages des 5 classes ontologiques par segment |
| `taux_salaire_domicilie_pct` | decimal | Part de clients avec salaire domicilié |
| `score_digital_moyen` | decimal | Score digital moyen du segment |
| `updated_at` | timestamp | Horodatage de la dernière exécution |

## 3. `nba` — une ligne par client (Next Best Action)

| Colonne | Type | Description |
|---------|------|--------------|
| `customer_id` | varchar (PK, FK → `customer_360`) | Identifiant client |
| `segment` | varchar | Segment du client |
| `next_best_action` | varchar | Action commerciale recommandée (règle métier, voir `ml/rules.py`) |
| `risque_composite` | decimal | Score de risque du client, dupliqué depuis `customer_360` pour éviter une jointure côté dashboard |
| `updated_at` | timestamp | Horodatage de la dernière exécution |

## 4. Couche sémantique — de la colonne technique au libellé affiché

Aucune des colonnes ci-dessus n'apparaît telle quelle dans le dashboard :
chaque nom technique est traduit par `dashboard/components/ui.py::LABELS`
puis résolu dans la langue active via `dashboard/i18n/{fr,en}.json`. Le
mapping complet est dans `LABELS` ; voir aussi `docs/decisions.md` pour la
décision qui impose cette règle.
