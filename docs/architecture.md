# Architecture — dataBank CI Customer 360

> *[English version: [architecture_en.md](architecture_en.md)]*

**Auteur :** Ibrahima TRAORÉ — Analytics Engineer
**Date :** Juillet 2026

## 1. Vue d'ensemble

Le projet suit une architecture médaillon (Bronze → Silver → Gold) sur DuckDB,
orchestrée par dbt, avec trois consommateurs en aval : un dashboard Streamlit,
un serveur MCP, et un pipeline ML.

```
starter_dataset.xlsx (10 feuilles)
        │
        ▼
src/ingest.py ──► Bronze (DuckDB, réel + synthétique, brut)
        │
        ▼
dbt_project/models/staging       (typage explicite, corrections métier)
        │
        ▼
dbt_project/models/intermediate  (agrégats comportementaux par client)
        │
        ▼
dbt_project/models/marts         (Gold : customer_360, customer_segments, nba)
        │
        ├──► dashboard/   (Streamlit, FR/EN)
        ├──► mcp_server/  (5 outils read-only, protocole MCP)
        └──► ml/          (score de règles + modèles comparés)
```

## 2. Pourquoi l'architecture médaillon

J'ai retenu l'architecture médaillon pour trois raisons concrètes sur ce
projet, pas par défaut :

1. **Idempotence native.** Chaque couche (staging = vue, marts = table) peut
   être rejouée entièrement sans effet de bord. `pipelines/run_pipeline.py`
   nettoie ses sorties avant de les recréer, `dbt run` reconstruit les tables
   Gold à chaque exécution. Rejouer tout le pipeline depuis
   `starter_dataset.xlsx` produit le même résultat, à la seconde près (voir
   `RANDOM_SEED=42` dans `config.py`).
2. **Compatibilité native avec dbt.** dbt est pensé pour des couches en
   couches (staging/intermediate/marts) avec des tests déclaratifs à chaque
   niveau (`_sources.yml`, `_intermediate.yml`, `_marts.yml`) — 93 tests au
   total dans ce projet, tous verts.
3. **Séparation claire réel/synthétique dès la couche Bronze.** Le
   générateur synthétique (`src/synthetic_data_generator.py`) produit des
   lignes qui suivent exactement le même schéma que les données réelles et
   sont fusionnées dès Bronze (`bronze_customers` UNION ALL
   `bronze_synthetic_customers`), avec un flag `is_synthetic` qui survit
   jusqu'au dashboard. Une architecture à couche unique aurait rendu cette
   séparation plus fragile à maintenir.

**Alternatives écartées :**

- **Star Schema (dimensions/faits) directement en Gold** — écarté parce que
  ce projet a besoin d'une couche staging intermédiaire pour appliquer les
  corrections métier (ex : `salary_domiciled_flag` recalculé à partir des
  transactions observées dans `stg_accounts.sql`) avant toute agrégation. Un
  star schema pur mélange typage, correction et agrégation dans les mêmes
  modèles.
- **Data Vault** — écarté : sa complexité (hubs/liens/satellites) ne se
  justifie pas sur un portefeuille de 140 clients réels et 10 tables source.
  C'est un surdimensionnement pour ce volume de données.

## 3. Les trois couches en détail

| Couche | Matérialisation | Rôle | Exemple |
|--------|------------------|------|---------|
| Staging | `view` | Typage explicite, une correction métier documentée par modèle | `stg_loans.sql` reclasse un prêt en `Delinquent` si `days_past_due > 15` |
| Intermediate | `view` | Un agrégat par client et par concern (jamais deux concerns dans le même modèle) | `int_customer_recency.sql`, `int_customer_balance.sql`, `int_customer_nbi.sql` |
| Marts | `table` | Vue métier finale, matérialisée pour la performance du dashboard | `customer_360` (vue unique client), `customer_segments`, `nba` |

Le découpage "un fichier intermediate = un concern" (récence, tendance,
réclamations, score digital, produits, solde, NBI, canal, prêts) permet
d'ajouter une nouvelle colonne au mart `customer_360` sans toucher aux
modèles existants — c'est ce qui a permis d'étendre le mart avec 8 nouvelles
colonnes (solde total, NBI estimé, canal principal, ancienneté, etc.) sans
casser un seul test existant.

## 4. Pourquoi DuckDB plutôt qu'un serveur de base de données

Le dataset source fait moins de 10 Mo (140 clients avant enrichissement,
~540 après). DuckDB s'exécute embarqué, sans serveur à opérer, se sérialise
en un seul fichier (`dbt_project/databank_ci.duckdb`) qui tient dans l'image
Docker, et parle SQL standard — donc directement compatible avec dbt sans
adaptation.

**Chemin de migration si le volume dépasse ~10 Go** : changer uniquement
`dbt_project/profiles.yml` pour pointer vers BigQuery (adapter `dbt-bigquery`
déjà packagé pour ce cas), sans toucher un seul modèle SQL — c'est
précisément l'intérêt de passer par dbt plutôt que par du SQL directement
embarqué dans le code Python.

## 5. Les trois consommateurs de la couche Gold

- **Dashboard Streamlit** (`dashboard/`) — lit `customer_360` en lecture
  seule (`duckdb.connect(..., read_only=True)`), applique une couche
  sémantique stricte (`components/ui.py::LABELS`) avant tout affichage.
- **Serveur MCP** (`mcp_server/`) — 5 outils read-only exposés via le
  protocole Model Context Protocol, en `stdio` localement et en
  `streamable-http` (avec clé API) en production sur Cloud Run. Le dashboard
  et le serveur MCP partagent la même image Docker, seul le point d'entrée
  change (`--command`/`--args` au déploiement).
- **Pipeline ML** (`ml/`) — score de règles métier toujours disponible sans
  modèle entraîné (`ml/rules.py`), plus une comparaison de modèles supervisés
  sur label proxy (`ml/comparison.py`), suivie dans MLflow
  (`mlflow.db`, 20 runs réels enregistrés).
