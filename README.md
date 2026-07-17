# dataBank CI - Customer 360

> *[English version: [README_en.md](README_en.md)]*

Ce projet analyse les clients de la banque dataBank CI, du premier fichier
de données jusqu'au tableau de bord final. Il comprend : la récupération
des données, des contrôles de qualité, des transformations avec dbt, un
score de risque de départ des clients, un tableau de bord Streamlit, et un
serveur MCP qui permet de poser des questions en langage naturel.

**Auteur :** Ibrahima TRAORÉ - Analytics Engineer
**Outils utilisés :** Python · pyenv · dbt · DuckDB · MLflow · Streamlit · Docker

## À lire avant de modifier le code

Ces documents expliquent les choix faits sur le projet. Merci de les lire
avant toute modification (chacun existe en français et en anglais) :

| Document | FR | EN |
|----------|----|----|
| Note de présentation (à lire en premier) | [FR](docs/submission_writeup.md) | [EN](docs/submission_writeup_en.md) |
| Compréhension métier - décisions et indicateurs clés | [FR](docs/business_understanding.md) | [EN](docs/business_understanding_en.md) |
| Définition du problème de Machine Learning - type de problème, limites de la donnée, déséquilibre des classes | [FR](docs/ml_problem_definition.md) | [EN](docs/ml_problem_definition_en.md) |
| Architecture - organisation des données, choix de DuckDB, évolution possible | [FR](docs/architecture.md) | [EN](docs/architecture_en.md) |
| Schéma des données (ERD) - comment les tables sont reliées entre elles | [FR](docs/erd_diagram.md) | [EN](docs/erd_diagram_en.md) |
| Dictionnaire de données - description des colonnes des 3 tables finales | [FR](docs/data_dictionary.md) | [EN](docs/data_dictionary_en.md) |
| Explication des données synthétiques - méthode et vérification statistique | [FR](docs/synthetic_data_rationale.md) | [EN](docs/synthetic_data_rationale_en.md) |
| Comparaison des modèles (généré automatiquement par `ml/comparison.py`) | [FR](docs/model_comparison.md) | [EN](docs/model_comparison_en.md) |
| Journal des décisions prises sur le projet | [FR](docs/decisions.md) | [EN](docs/decisions_en.md) |

## Comment les données circulent

```
starter_dataset.xlsx (10 tables)
        │
        ▼
   src/ingest.py ──► Bronze (DuckDB, données réelles + synthétiques)
        │
        ▼
   dbt_project/models/staging      (10 modèles : typage et corrections)
        │
        ▼
   dbt_project/models/intermediate (calculs sur le comportement des clients)
        │
        ▼
   dbt_project/models/marts        (Gold : customer_360, customer_segments, nba)
        │
        ├──► dashboard/  (tableau de bord Streamlit, 9 pages, FR/EN)
        ├──► mcp_server/ (serveur MCP, 5 outils en lecture seule)
        └──► ml/         (score par règles + modèles de Machine Learning comparés)
```

Note : "Bronze", "Silver" et "Gold" sont les trois étapes classiques d'un
pipeline de données. Bronze = donnée brute telle que reçue. Silver = donnée
nettoyée et typée (dossier `staging`). Gold = donnée prête à l'usage, agrégée
et fiable (dossier `marts`), celle que consultent le tableau de bord et le
serveur MCP.

Les 9 pages du tableau de bord partagent le même style visuel (noir et
orange, charte Artefact) grâce à des éléments communs définis une seule fois
dans `dashboard/components/ui.py` (bandeau de page, guide de lecture,
en-têtes de section, cartes d'indicateurs avec code couleur rouge/orange/vert,
messages d'alerte). Aucune page ne doit avoir son propre style différent des
autres.

## Installation

```bash
git clone https://github.com/ibrahimatraore12/databank-ci.git
cd databank-ci
pyenv virtualenv 3.11.9 databank-ci-env
pyenv local databank-ci-env
pip install -r requirements.txt   # ou voir la liste des paquets ci-dessous
cp .env.example .env
```

## Lancer le pipeline complet

```bash
# 1. Chargement des données brutes + enrichissement + génération de données synthétiques
python3 pipelines/run_pipeline.py

# 2. Transformation des données avec dbt (Bronze -> Silver -> Gold)
cd dbt_project
export DBT_PROFILES_DIR=$(pwd)
dbt run
dbt test
cd ..

# 3. Pipeline de Machine Learning (score par règles + comparaison de modèles + suivi MLflow)
python3 pipelines/run_ml_pipeline.py

# 4. Tableau de bord
streamlit run dashboard/APP.py

# 5. Serveur MCP
python3 mcp_server/databank_mcp_server.py
```

## Tests et qualité du code

```bash
pytest tests/ -v
flake8 .
cd dbt_project && dbt test
```

## Questions fréquentes

**Pourquoi DuckDB et pas PostgreSQL ?**
Le jeu de données pèse moins de 10 Mo. DuckDB fonctionne directement dans
Docker sans avoir besoin d'un serveur de base de données séparé à faire
tourner. Si le volume de données dépasse 10 Go un jour, il suffira de
changer le fichier `profiles.yml` pour migrer vers BigQuery, sans toucher
au reste du code (voir `docs/architecture.md`).

**Peut-on faire confiance au score du modèle utilisé en production ?**
Sur les données réelles (140 clients, dont 35 qui sont partis) : le modèle
obtient un score AUC de 0,913. Ce chiffre reste indicatif seulement, car
l'échantillon est trop petit pour être sûr qu'il se comporterait aussi bien
sur beaucoup plus de clients. Sur les données enrichies avec des exemples
synthétiques (540 clients) : le score monte à 0,944, ce qui est plus fiable.
Ce n'est pourtant pas le meilleur score du comparatif (RandomForest et
XGBoost atteignent 1,0). Ces deux modèles n'ont volontairement pas été
retenus : un score parfait sur des clients synthétiques générés par
répétition (bootstrap) est le signe que le modèle a appris les exemples par
cœur, plutôt que d'avoir compris les tendances générales. Plus de détails
dans `docs/model_comparison.md`.

**Comment évite-t-on que le modèle "triche" en s'entraînant (data leakage) ?**
La fonction `preprocess_data(fit=True)`, qui ajuste les échelles de valeurs,
n'est appliquée que sur les données d'entraînement. Le résultat de cet
ajustement est sauvegardé dans `ml/artifacts/preprocessor.pkl`, puis
réutilisé tel quel sur les données de test, sans le recalculer.

**À quoi sert le serveur MCP ?**
Avec le tableau de bord, il faut chercher l'information page par page. Le
serveur MCP permet de poser directement une question en langage courant,
par exemple "Quels clients VIP sont à risque ?", et de recevoir une réponse
structurée, calculée en temps réel à partir de DuckDB.

## Mettre à jour les données

Le fichier source peut être remplacé sans intervention technique, depuis
l'onglet Administration du tableau de bord (un mot de passe est demandé,
voir `ADMIN_PASSWORD` dans `docs/data_dictionary.md`).

**Étapes à suivre :**
1. Onglet Administration → section "Charger un nouveau fichier de données"
2. Charger le fichier Excel (même format, 10 feuilles)
3. Vérifier le rapport de validation (feuille par feuille)
4. Si tout est valide, cliquer sur "Recalculer maintenant"

Le pipeline complet se relance automatiquement (chargement → dbt → Machine
Learning, environ 55 secondes mesurées). Le résultat est visible
immédiatement sur cette instance, puis sauvegardé dans un espace de stockage
Google Cloud Storage privé. Cela permet de conserver les données après un
redémarrage et de les partager avec toutes les instances de l'application -
tableau de bord et serveur MCP (Assistant IA) compris, ce dernier étant
remis à jour juste après. Aucune autre action n'est nécessaire : pas besoin
de remplacer de fichier dans le dépôt de code, ni de reconstruire une image
Docker. Le détail du fonctionnement, les vérifications de compatibilité et
les limites connues sont expliqués dans `docs/architecture.md` (section 6).

## Organisation du projet

```
databank-ci/
├── docs/                 documents de cadrage et journal de décisions
├── notebooks/            analyse exploratoire complète (EDA_databank_ci.ipynb)
├── data/raw/              données source
├── data/enriched/         indicateurs calculés + jeu de données synthétique
├── src/                  chargement, validation, traçabilité, enrichissement
├── dbt_project/          staging / intermediate / marts / semantic
├── ml/                   règles métier, données, modèles, comparaison
├── dashboard/            application Streamlit (9 pages, FR/EN)
├── mcp_server/            serveur MCP (5 outils en lecture seule)
├── pipelines/            orchestration (données, Machine Learning)
├── scripts/              déploiement
└── tests/                tests automatisés (pytest)
```

## Règles de code à respecter

 - Les commentaires dans le code sont écrits en deux langues (français puis
   anglais) sur les points qui ne sont pas évidents à comprendre.
- Aucun nom de colonne technique ne doit apparaître dans le tableau de bord :
  toujours passer par `dashboard/components/ui.py::LABELS` et
  `dashboard/i18n/` pour les libellés affichés.
- Le pipeline peut être relancé plusieurs fois sans problème : le script
  `pipelines/run_pipeline.py` nettoie ses résultats précédents avant de les
  recréer, et une même valeur de départ (`seed=42`) est utilisée partout
  (dbt, Machine Learning, génération de données synthétiques) pour obtenir
  des résultats reproductibles.
- Toute donnée générée artificiellement est marquée `is_synthetic=True` et
  n'est jamais mélangée avec les données réelles dans les vues affichées par
  défaut.
