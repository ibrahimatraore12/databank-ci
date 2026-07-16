# dataBank CI — Customer 360

> *[English version: [README_en.md](README_en.md)]*

Plateforme analytics engineering de bout en bout pour dataBank CI : ingestion,
qualité des données, transformation dbt, scoring de désengagement client,
dashboard Streamlit et serveur MCP pour l'exploration en langage naturel.

**Auteur :** Ibrahima TRAORÉ — Analytics Engineer
**Stack :** Python · pyenv · dbt · DuckDB · MLflow · Streamlit · Docker

## Avant de coder : les documents de cadrage

Lire dans l'ordre avant toute modification (chaque document existe en FR et en EN) :

| Document | FR | EN |
|----------|----|----|
| Compréhension métier — décisions soutenues, KPIs | [FR](docs/business_understanding.md) | [EN](docs/business_understanding_en.md) |
| Définition du problème ML — nature du problème, limites du label, déséquilibre de classes | [FR](docs/ml_problem_definition.md) | [EN](docs/ml_problem_definition_en.md) |
| Journal des décisions de design | [FR](docs/decisions.md) | [EN](docs/decisions_en.md) |
| Comparaison de modèles (généré automatiquement par `ml/comparison.py`) | [FR](docs/model_comparison.md) | [EN](docs/model_comparison_en.md) |

## Architecture

```
starter_dataset.xlsx (10 tables)
        │
        ▼
   src/ingest.py ──► Bronze (DuckDB, réel + synthétique)
        │
        ▼
   dbt_project/models/staging      (10 modèles, typage + corrections métier)
        │
        ▼
   dbt_project/models/intermediate (calculs comportementaux)
        │
        ▼
   dbt_project/models/marts        (Gold : customer_360, customer_segments, nba)
        │
        ├──► dashboard/  (Streamlit, 8 pages, FR/EN)
        ├──► mcp_server/ (serveur MCP, 5 outils read-only)
        └──► ml/         (score de règles + modèles ML comparés)
```

## Installation

```bash
pyenv virtualenv 3.11.9 databank-ci-env
cd databank-ci
pyenv local databank-ci-env
pip install -r requirements.txt   # ou voir la liste des paquets ci-dessous
cp .env.example .env
```

## Exécuter le pipeline complet

```bash
# 1. Bronze + enrichissement + génération synthétique
python3 pipelines/run_pipeline.py

# 2. Transformation dbt (Bronze -> Silver -> Gold)
cd dbt_project
export DBT_PROFILES_DIR=$(pwd)
dbt run
dbt test
cd ..

# 3. Pipeline ML (score de règles + comparaison de modèles + MLflow)
python3 pipelines/run_ml_pipeline.py

# 4. Dashboard
streamlit run dashboard/APP.py

# 5. Serveur MCP
python3 mcp_server/databank_mcp_server.py
```

## Tests

```bash
pytest tests/ -v
flake8 .
```

## Structure du projet

```
databank-ci/
├── docs/                 documents de cadrage et journal de décisions
├── notebooks/            EDA complète (EDA_databank_ci.ipynb)
├── data/raw/              données source
├── data/enriched/         features calculées + jeu synthétique
├── src/                  ingestion, validation, lignage, enrichissement
├── dbt_project/          staging / intermediate / marts / semantic
├── ml/                   règles métier, données, modèles, comparaison
├── dashboard/            application Streamlit (8 pages, i18n FR/EN)
├── mcp_server/            serveur MCP (5 outils read-only)
├── pipelines/            orchestration (données, ML)
├── scripts/              déploiement
└── tests/                pytest
```

## Règles de code

- Aucune programmation orientée objet dans le code métier : uniquement des fonctions.
- Commentaires bilingues (français puis anglais) sur les points non évidents.
- Couche sémantique stricte : aucun nom de colonne technique dans le dashboard,
  voir `dashboard/components/ui.py::LABELS` et `dashboard/i18n/`.
- Idempotence : `pipelines/run_pipeline.py` nettoie ses sorties avant de les
  recréer ; `seed=42` fixé partout (dbt, ML, génération synthétique).
- Toute donnée générée est marquée `is_synthetic=True` et jamais confondue
  avec la donnée réelle dans les vues par défaut.
