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
| Note de soumission (à lire en premier) | [FR](docs/submission_writeup.md) | [EN](docs/submission_writeup_en.md) |
| Compréhension métier — décisions soutenues, KPIs | [FR](docs/business_understanding.md) | [EN](docs/business_understanding_en.md) |
| Définition du problème ML — nature du problème, limites du label, déséquilibre de classes | [FR](docs/ml_problem_definition.md) | [EN](docs/ml_problem_definition_en.md) |
| Architecture — médaillon, choix DuckDB, chemin de migration | [FR](docs/architecture.md) | [EN](docs/architecture_en.md) |
| Diagramme ERD — schéma relationnel des tables source | [FR](docs/erd_diagram.md) | [EN](docs/erd_diagram_en.md) |
| Dictionnaire de données — colonnes des 3 tables Gold | [FR](docs/data_dictionary.md) | [EN](docs/data_dictionary_en.md) |
| Justification des données synthétiques — méthode et validation KS-test | [FR](docs/synthetic_data_rationale.md) | [EN](docs/synthetic_data_rationale_en.md) |
| Comparaison de modèles (généré automatiquement par `ml/comparison.py`) | [FR](docs/model_comparison.md) | [EN](docs/model_comparison_en.md) |
| Journal des décisions de design | [FR](docs/decisions.md) | [EN](docs/decisions_en.md) |

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
        ├──► dashboard/  (Streamlit, 9 pages, FR/EN)
        ├──► mcp_server/ (serveur MCP, 5 outils read-only)
        └──► ml/         (score de règles + modèles ML comparés)
```

Les 9 pages du dashboard partagent une identité visuelle unique (charte
noir/orange Artefact) via des composants communs
(`dashboard/components/ui.py` : bandeau de page, guide de lecture, en-têtes
de section, cartes KPI à seuil RAG, alertes) — jamais de style ad hoc page
par page.

## Installation

```bash
git clone https://github.com/ibrahimatraore12/databank-ci.git
cd databank-ci
pyenv virtualenv 3.11.9 databank-ci-env
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

## Tests et qualité

```bash
pytest tests/ -v
flake8 .
cd dbt_project && dbt test
```

## Questions fréquentes

**Pourquoi DuckDB et pas PostgreSQL ?**
Dataset < 10 Mo, embarqué dans Docker, pas de serveur à opérer.
Sur volume > 10 Go → migrer vers BigQuery en changeant `profiles.yml`
uniquement (voir `docs/architecture.md`).

**L'AUC du modèle en production est-il fiable ?**
Sur données réelles (n=140, 35 positifs) : 0,913, indicatif uniquement —
échantillon trop petit pour généraliser. Sur données enrichies (n=540) :
0,944, plus robuste. Ce n'est pas le meilleur score du comparatif
(RandomForest et XGBoost atteignent 1,0) : je n'ai pas retenu ces deux
modèles précisément parce qu'un score parfait sur des clients synthétiques
bootstrap est un signal de mémorisation, pas de généralisation. Détail dans
`docs/model_comparison.md`.

**Comment ai-je évité le data leakage ?**
`preprocess_data(fit=True)` sur le train uniquement. Le scaler est
sauvegardé dans `ml/artifacts/preprocessor.pkl` et appliqué au test sans
recalcul.

**Qu'est-ce que le serveur MCP apporte ?**
Le dashboard requiert de chercher l'information page par page. Le MCP la
ramène en langage naturel : "Quels clients VIP sont à risque ?" → réponse
structurée, calculée depuis DuckDB en temps réel.

## Mise à jour des données

Le fichier source peut être rechargé sans intervention technique depuis
l'onglet Administration du dashboard (mot de passe requis, voir
`ADMIN_PASSWORD` dans `docs/data_dictionary.md`).

**Procédure :**
1. Onglet Administration → section "Charger un nouveau fichier de données"
2. Charger le fichier Excel (même format, 10 feuilles)
3. Vérifier le rapport de validation (feuille par feuille)
4. Si valide, cliquer sur "Recalculer maintenant"

Le pipeline complet se rejoue (ingestion → dbt → ML, ~55 secondes mesurées),
le résultat est immédiatement visible sur cette instance, puis sauvegardé
dans un bucket Google Cloud Storage privé pour survivre aux redémarrages et
être repris par toutes les instances — dashboard et serveur MCP (Assistant
IA) inclus, ce dernier étant explicitement resynchronisé juste après.
Aucune action supplémentaire n'est nécessaire (pas de remplacement de
fichier dans le dépôt, pas de reconstruction d'image). Détail du mécanisme,
du garde-fou de compatibilité de schéma et des limites acceptées dans
`docs/architecture.md` (section 6).

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
├── dashboard/            application Streamlit (9 pages, i18n FR/EN)
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
