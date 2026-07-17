# Dictionnaire de données - dataBank CI Customer 360

> *[English version: [data_dictionary_en.md](data_dictionary_en.md)]*

**Auteur :** Ibrahima TRAORÉ - Analytics Engineer
**Date :** Juillet 2026

Ce document décrit les 3 tables finales (couche Gold,
`dbt_project/models/marts/`), celles qui sont utilisées par le tableau de
bord, le serveur MCP et le pipeline de Machine Learning. Pour voir comment
les tables sources sont reliées entre elles, consulter
`docs/erd_diagram.md`.

Repère de lecture : `PK` veut dire "clé primaire" (l'identifiant unique de
chaque ligne). `FK` veut dire "clé étrangère" (une colonne qui pointe vers
l'identifiant d'une autre table).

## 1. `customer_360` - une ligne par client

| Colonne | Type | Description |
|---------|------|--------------|
| `customer_id` | varchar (PK) | Identifiant unique du client |
| `full_name` | varchar | Nom complet |
| `segment` | varchar | `Mass` / `Affluent` / `Premier` / `Youth` |
| `risk_band` | varchar | `Low` / `Medium` / `High` - niveau de risque de crédit déclaré |
| `city`, `district` | varchar | Localisation du client |
| `monthly_income_xof` | decimal | Revenu mensuel déclaré, en FCFA |
| `preferred_channel` | varchar | Canal bancaire préféré, déclaré par le client |
| `mobile_app_active`, `internet_banking_active`, `mobile_money_linked` | boolean | Indique si chacun des 3 canaux numériques est activé |
| `salaire_domicilie` | boolean | Salaire domicilié à la banque, vérifié à partir des transactions réellement observées (voir `stg_accounts.sql`) |
| `recency_jours` | integer | Nombre de jours depuis la dernière transaction (999 si aucune transaction observée) |
| `tendance_transactions` | integer | Nombre de transactions des 30 derniers jours, moins celles des 30 jours précédents |
| `nb_txn_30j`, `nb_txn_90j` | integer | Nombre de transactions sur les 30 / 90 derniers jours |
| `tendance_3m` | integer | Nombre de transactions des 90 derniers jours, moins celles des 90 jours précédents |
| `nb_reclamations_ouvertes`, `nb_reclamations_total`, `nb_reclamations_severite_haute` | integer | Compteurs de réclamations |
| `score_digital` | integer (0 à 3) | Nombre de canaux numériques activés |
| `nb_comptes`, `nb_cartes`, `nb_produits_total` | integer | Nombre de produits détenus par le client |
| `solde_total_xof` | decimal | Somme des soldes actuels de tous les comptes du client |
| `avg_balance_90d_xof` | decimal | Somme des soldes moyens sur 90 jours, tous comptes confondus |
| `nbi_estime_xof` | decimal | Revenu généré par le client (NBI), estimé avec la formule standard UEMOA. Ce **n'est pas** le chiffre comptable réel du client - voir `docs/decisions.md` |
| `canal_majoritaire` | varchar | Canal le plus utilisé par le client, selon le nombre de transactions |
| `dpd_max` | integer | Le plus grand retard de paiement observé (en jours), tous prêts confondus |
| `anciennete_jours` | integer | Nombre de jours depuis la date d'entrée du client (`onboarding_date`) |
| `risque_composite` | decimal (0 à 100) | Score de risque de désengagement : somme pondérée de 4 sous-scores (inactivité 40 %, réclamations 30 %, usage numérique 20 %, tendance 10 %) |
| `is_high_value_at_risk` | boolean | Vrai si le client est du segment Premier ou Affluent ET inactif depuis plus de 60 jours |
| `is_digitally_dormant_salary` | boolean | Vrai si le salaire est domicilié ET le score numérique est de 1 ou moins |
| `is_complaints_churn_risk` | boolean | Vrai si le client a une réclamation ouverte ET est inactif depuis plus de 60 jours |
| `is_cross_sell_target` | boolean | Vrai si le client n'a pas de carte |
| `is_salary_upsell_opportunity` | boolean | Vrai si le revenu est élevé (500 000 FCFA ou plus) ET le salaire n'est pas domicilié |
| `is_synthetic` | boolean | `True` si la ligne a été générée artificiellement. N'est jamais affiché à l'utilisateur final |
| `updated_at` | timestamp | Date et heure de la dernière exécution de `dbt run` |

## 2. `customer_segments` - une ligne par segment

| Colonne | Type | Description |
|---------|------|--------------|
| `segment` | varchar (PK) | `Mass` / `Affluent` / `Premier` / `Youth` |
| `nb_clients` | integer | Nombre de clients dans le segment |
| `risque_composite_moyen` | decimal | Score de risque moyen du segment |
| `nb_high_value_at_risk`, `nb_digitally_dormant_salary`, `nb_complaints_churn_risk`, `nb_cross_sell_target`, `nb_salary_upsell_opportunity` | integer | Nombre de clients concernés par chacune des 5 catégories, pour ce segment |
| `taux_salaire_domicilie_pct` | decimal | Part des clients ayant domicilié leur salaire |
| `score_digital_moyen` | decimal | Score numérique moyen du segment |
| `updated_at` | timestamp | Date et heure de la dernière exécution |

## 3. `nba` - une ligne par client (Next Best Action = "meilleure action à mener")

| Colonne | Type | Description |
|---------|------|--------------|
| `customer_id` | varchar (PK, FK → `customer_360`) | Identifiant du client |
| `segment` | varchar | Segment du client |
| `next_best_action` | varchar | Action commerciale recommandée pour ce client (calculée par une règle métier, voir `ml/rules.py`) |
| `risque_composite` | decimal | Score de risque du client, recopié depuis `customer_360` pour éviter un calcul supplémentaire côté tableau de bord |
| `updated_at` | timestamp | Date et heure de la dernière exécution |

## 4. Comment un nom de colonne technique devient un texte affiché

Aucune des colonnes ci-dessus n'apparaît telle quelle dans le tableau de
bord. Chaque nom technique est d'abord traduit en texte lisible par
`dashboard/components/ui.py::LABELS`, puis affiché dans la bonne langue
grâce aux fichiers `dashboard/i18n/{fr,en}.json`. La liste complète de ces
correspondances se trouve dans `LABELS`. Voir aussi `docs/decisions.md`
pour comprendre pourquoi cette règle a été mise en place.

## 5. Variables d'environnement (réglages de configuration)

| Variable | Valeur par défaut si absente | Utilisée par | Description |
|----------|--------------------|--------------|--------------|
| `ADMIN_PASSWORD` | `databank-admin` | `dashboard/pages/99_Administration.py` | Mot de passe pour accéder à la zone Administration |
| `MCP_SERVER_URL` | aucune (obligatoire) | `dashboard/components/mcp_client.py` | Adresse du serveur MCP en ligne (exemple : `https://databank-ci-mcp-….run.app/mcp`) |
| `MCP_API_KEY` | aucune (la vérification est désactivée si absente) | `mcp_server/databank_mcp_server.py`, `dashboard/components/mcp_client.py` | Clé secrète demandée pour se connecter au serveur MCP en ligne |
| `MCP_TRANSPORT` | `stdio` | `mcp_server/databank_mcp_server.py` | Mode de communication : `stdio` en local, `streamable-http` en production |
| `PORT` | `8080` | `mcp_server/databank_mcp_server.py`, Dockerfile | Port d'écoute de l'application (donné automatiquement par Cloud Run) |
| `GCS_BUCKET_NAME` | aucune (la sauvegarde est désactivée si absente) | `src/storage_sync.py` | Espace de stockage Google Cloud Storage utilisé pour conserver les données au-delà de la durée de vie d'une instance Cloud Run - voir `docs/architecture.md`, section 6 |
