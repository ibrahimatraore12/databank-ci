# Note de soumission - dataBank CI Customer 360

> *[English version: [submission_writeup_en.md](submission_writeup_en.md)]*

**Auteur :** Ibrahima TRAORÉ - Analytics Engineer
**Date :** Juillet 2026
**Dashboard en production :** https://databank-ci-264685034714.europe-west9.run.app

## 1. Ce que j'ai construit

J'ai construit une plateforme analytics engineering de bout en bout : d'un
fichier Excel source (10 feuilles, 140 clients réels) jusqu'à un dashboard
Streamlit déployé et un serveur MCP interrogeable en langage naturel, en
passant par une transformation dbt en trois couches et un pipeline ML
comparant plusieurs approches de scoring.

De bout en bout, rejouer tout le pipeline (ingestion + enrichissement +
génération synthétique, transformation dbt, entraînement ML) prend moins de
60 secondes sur ma machine de développement - un temps mesuré, pas estimé,
qui exclut le démarrage du dashboard lui-même.

## 2. Les décisions qui comptent

**J'ai retenu l'architecture médaillon** (Bronze/Silver/Gold sur DuckDB,
orchestrée par dbt) pour son idempotence et sa compatibilité native avec dbt
- voir `docs/architecture.md` pour le détail et les alternatives écartées
(star schema, Data Vault).

**J'ai traité le score de désengagement en deux phases**, pas comme un seul
modèle ML présenté comme vérité terrain : un scoring de règles métier
explicite (`ml/rules.py`, toujours disponible sans modèle entraîné) et une
expérimentation ML supervisée sur un label proxy (`ml/comparison.py`). Le
dataset source ne contient aucun départ client confirmé - voir
`docs/ml_problem_definition.md` pour la définition complète du problème et
ses limites.

**J'ai choisi le modèle en production sur un critère de robustesse, pas sur
le meilleur score brut.** La comparaison sur le jeu enrichi (540 clients,
151 positifs) donne un AUC de 1,0 pour RandomForest et XGBoost, contre 0,944
pour la régression logistique. Je n'ai pas retenu les deux premiers : les
clients synthétiques sont des copies bootstrap de clients réels (voir
`docs/synthetic_data_rationale.md`), et un modèle à forte capacité peut
mémoriser ces motifs sans généraliser. J'ai retenu la régression logistique
(`ml/artifacts/churn_scoring_logistic.pkl`) comme modèle champion,
documentant ce choix dans `docs/model_comparison.md` plutôt que de présenter
le score parfait comme une réussite.

**J'ai généré 400 clients synthétiques** pour porter le volume de test de
140 à 540 clients, avec traçabilité stricte (`is_synthetic=True` visible du
Bronze au dashboard) et validation statistique par test de
Kolmogorov-Smirnov sur la distribution du revenu - voir
`docs/synthetic_data_rationale.md`.

**J'ai imposé une couche sémantique stricte** : aucun nom de colonne
technique (`risk_band`, `nb_reclamations_ouvertes`...) n'apparaît dans le
dashboard. Tout passe par `dashboard/components/ui.py::LABELS` puis par les
fichiers `i18n/{fr,en}.json`, y compris les titres de graphiques, les
en-têtes de tableaux et les messages d'alerte.

**J'ai connecté le dashboard au serveur MCP en HTTP réel**, pas par import
Python direct : la page Assistant IA appelle le serveur MCP déployé
(`streamable-http`, clé API) via un vrai client MCP
(`dashboard/components/mcp_client.py`), pour que les réponses passent
réellement par le protocole plutôt que par un raccourci en mémoire.

**J'ai ajouté une couche de persistance GCS pour l'upload de données depuis
l'Administration**, plutôt que d'accepter que Cloud Run (stateless) perde
tout à chaque redémarrage. Un fichier chargé par le métier est validé,
recalculé (pipeline complet, ~55 secondes mesurées dans un conteneur isolé),
puis sauvegardé dans un bucket GCS que chaque instance relit à son démarrage
(`src/storage_sync.py`, détaillé dans `docs/architecture.md` section 6). J'ai
ajouté un garde-fou de version de schéma après avoir identifié, en revue de
conception, qu'un futur changement de schéma dbt pourrait sinon se faire
silencieusement écraser par une ancienne donnée restaurée depuis GCS.

**J'ai appliqué une identité visuelle unique aux 9 pages du dashboard**
(charte noir/orange, composants communs dans `dashboard/components/ui.py` :
bandeau, guide de lecture, en-têtes de section, cartes KPI à seuil RAG,
alertes) plutôt qu'un style ad hoc par page, pour que le dashboard se lise
comme un seul outil cohérent. J'ai gardé la palette de couleurs de segment
déjà validée plutôt que les couleurs initialement proposées pour la charte,
après avoir constaté que deux d'entre elles étaient trop proches pour un
daltonien. Chaque page d'alerte montre aussi un signal positif réel
(portefeuille sain, opportunités identifiées), pas seulement des risques -
voir `docs/decisions.md` pour le détail de ces choix.

## 3. Une conclusion d'analyse, pas une suggestion générique

Sur le portefeuille réel (hors clients synthétiques, pour ne pas présenter
un doublon comme deux clients distincts), 2 clients du segment Premier
affichent un niveau de risque crédit élevé (`risk_band = High`) : Murielle
Aka (score de risque 26,4/100, solde 6,44 M FCFA) et Bintou Soro (score
19,0/100, solde 5,52 M FCFA) - solde combiné 11,97 M FCFA. Ce sont les 2
seuls clients Premier dans ce cas sur les 49 clients réels du segment. Un
appel conseiller sous 48h sur ces 2 comptes est la priorité commerciale
immédiate identifiée par le dashboard (page Rétention et Risque), pas une
recommandation générique de "contacter les clients à risque".

## 4. Les limites, énoncées sans détour

- Le dataset réel est petit (140 clients, 34 prêts, 42 réclamations) : voir
  `docs/ml_problem_definition.md` section 6 pour le détail.
- Le NBI est une estimation par formule standard, pas le NBI comptable réel
  du client - `docs/decisions.md`.
- Les scores quasi parfaits de RandomForest/XGBoost sur le jeu enrichi ne
  sont pas une garantie de performance en production sur des clients
  inédits - `docs/model_comparison.md`.
- Ce projet reste un outil d'aide à la décision : aucune action n'est
  déclenchée automatiquement à partir d'un score, l'humain reste dans la
  boucle.

## 5. Stack

Python 3.11 · dbt-duckdb · DuckDB · scikit-learn/XGBoost · MLflow ·
Streamlit · Model Context Protocol (MCP) · Docker · Google Cloud Run.
