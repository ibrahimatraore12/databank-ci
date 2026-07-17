# Architecture - dataBank CI Customer 360

> *[English version: [architecture_en.md](architecture_en.md)]*

**Auteur :** Ibrahima TRAORÉ - Analytics Engineer
**Date :** Juillet 2026

## 1. Vue d'ensemble

Le projet organise les données en trois étapes successives, appelées
"architecture médaillon" (Bronze → Silver → Gold), sur DuckDB, pilotées par
dbt. Trois outils utilisent ensuite ces données : un tableau de bord
Streamlit, un serveur MCP, et un pipeline de Machine Learning.

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
dbt_project/models/intermediate  (agrégats de comportement par client)
        │
        ▼
dbt_project/models/marts         (Gold : customer_360, customer_segments, nba)
        │
        ├──► dashboard/   (Streamlit, FR/EN)
        ├──► mcp_server/  (5 outils en lecture seule, protocole MCP)
        └──► ml/          (score de règles + modèles comparés)
```

## 2. Pourquoi l'architecture "médaillon" (Bronze/Silver/Gold)

J'ai choisi cette organisation en trois étapes pour trois raisons concrètes
liées à ce projet précis, pas simplement par habitude :

1. **On peut tout rejouer sans risque.** Chaque étape (staging = vue,
   marts = table) peut être entièrement recalculée sans effet secondaire.
   Le script `pipelines/run_pipeline.py` nettoie ses résultats précédents
   avant de les recréer, et `dbt run` reconstruit les tables Gold à chaque
   exécution. Relancer tout le pipeline depuis `starter_dataset.xlsx`
   donne exactement le même résultat, à la seconde près (voir
   `RANDOM_SEED=42` dans `config.py`, qui fixe le point de départ des
   calculs aléatoires).
2. **dbt est fait pour ce genre d'organisation.** dbt est conçu pour des
   données organisées en couches successives (staging/intermediate/marts),
   avec des tests automatiques à chaque étape (`_sources.yml`,
   `_intermediate.yml`, `_marts.yml`) : 93 tests au total dans ce projet,
   tous réussis.
3. **La séparation entre données réelles et synthétiques est claire dès le
   départ.** Le générateur de données synthétiques
   (`src/synthetic_data_generator.py`) crée des lignes qui suivent
   exactement le même format que les données réelles, et elles sont
   réunies dès l'étape Bronze (`bronze_customers` combiné avec
   `bronze_synthetic_customers`). Un indicateur `is_synthetic` marque ces
   lignes et les suit jusqu'au tableau de bord. Avec une seule grande
   étape, cette séparation aurait été plus difficile à maintenir dans le
   temps.

**Les autres options envisagées, et pourquoi elles n'ont pas été retenues :**

- **Le schéma en étoile (Star Schema)**, où les tables finales (faits et
  dimensions) seraient construites directement, sans étape intermédiaire.
  Écarté car ce projet a besoin d'une étape "staging" pour appliquer des
  corrections métier (par exemple, `salary_domiciled_flag` est recalculé à
  partir des transactions observées dans `stg_accounts.sql`) avant tout
  calcul global. Faire cela directement dans un schéma en étoile
  mélangerait typage, correction et calcul dans les mêmes modèles.
- **Le Data Vault**, une méthode de modélisation plus complexe (avec des
  "hubs", "liens" et "satellites"). Écarté car sa complexité ne se
  justifie pas pour un portefeuille de 140 clients réels et 10 tables
  source : ce serait disproportionné par rapport au volume de données
  réel.

## 3. Les trois étapes en détail

| Étape | Type de résultat | Rôle | Exemple |
|--------|------------------|------|---------|
| Staging | `view` (vue, recalculée à chaque lecture) | Typage explicite des colonnes, une correction métier documentée par modèle | `stg_loans.sql` reclasse un prêt en `Delinquent` (en défaut) si le retard de paiement dépasse 15 jours |
| Intermediate | `view` | Un calcul par client, pour un seul sujet à la fois (jamais deux sujets mélangés dans le même modèle) | `int_customer_recency.sql`, `int_customer_balance.sql`, `int_customer_nbi.sql` |
| Marts | `table` (résultat sauvegardé physiquement) | Vue métier finale, sauvegardée pour que le tableau de bord reste rapide | `customer_360` (vue unique par client), `customer_segments`, `nba` |

La règle "un fichier intermediate = un seul sujet" (récence, tendance,
réclamations, score numérique, produits, solde, revenu généré, canal,
prêts) permet d'ajouter une nouvelle colonne à la table finale
`customer_360` sans toucher aux modèles déjà en place. C'est exactement ce
qui a permis d'ajouter 8 nouvelles colonnes (solde total, revenu estimé,
canal principal, ancienneté, etc.) sans casser un seul test existant.

## 4. Pourquoi DuckDB plutôt qu'un serveur de base de données classique

Le fichier source pèse moins de 10 Mo (140 clients avant enrichissement,
environ 540 après). DuckDB fonctionne directement dans l'application, sans
avoir besoin d'un serveur séparé à faire tourner. Il sauvegarde toutes ses
données dans un seul fichier (`dbt_project/databank_ci.duckdb`), qui tient
facilement dans l'image Docker, et il comprend le langage SQL standard, ce
qui le rend directement compatible avec dbt sans adaptation particulière.

**Si le volume de données dépasse un jour environ 10 Go**, il suffira de
changer le fichier `dbt_project/profiles.yml` pour utiliser BigQuery à la
place (l'outil `dbt-bigquery`, déjà prévu pour ce cas), sans modifier un
seul modèle SQL. C'est justement tout l'intérêt de passer par dbt plutôt
que d'écrire du SQL directement dans le code Python.

## 5. Les trois outils qui utilisent les données finales (Gold)

- **Tableau de bord Streamlit** (`dashboard/`) - lit la table `customer_360`
  en lecture seule uniquement (`duckdb.connect(..., read_only=True)`), et
  applique toujours une couche de traduction des noms de colonnes
  (`components/ui.py::LABELS`) avant d'afficher quoi que ce soit.
- **Serveur MCP** (`mcp_server/`) - propose 5 outils en lecture seule via le
  protocole Model Context Protocol (MCP). En local, la communication se
  fait via `stdio` ; en production sur Cloud Run, via `streamable-http`
  (avec une clé d'accès). Le tableau de bord et le serveur MCP partagent
  la même image Docker : seul le point de démarrage change au déploiement.
- **Pipeline de Machine Learning** (`ml/`) - un score basé sur des règles
  métier, toujours disponible même sans modèle entraîné (`ml/rules.py`),
  plus une comparaison de modèles de Machine Learning supervisé sur un
  indicateur approché (`ml/comparison.py`), suivie avec l'outil MLflow
  (`mlflow.db`, qui enregistre les résultats réels de chaque essai).

## 6. Comment les données sont conservées (Cloud Run ne garde rien en mémoire)

Cloud Run, la plateforme d'hébergement utilisée, ne fournit aucun disque
permanent : quand une instance de l'application redémarre (nouvelle
version, arrêt puis redémarrage automatique), tout ce qui a été écrit sur
le disque local disparaît. L'application repart alors avec les données
telles qu'elles étaient au moment de la construction de l'image Docker. Un
fichier chargé par un utilisateur métier via l'onglet Administration
serait donc perdu au premier redémarrage, sans une solution de sauvegarde
externe.

**J'ai choisi de sauvegarder les données dans un espace de stockage privé
Google Cloud Storage (GCS)** (nommé `databank-ci-data-264685034714`, situé
dans la région europe-west9, avec l'historique des versions activé),
plutôt que de sauvegarder uniquement le fichier Excel source, par exemple.
Sauvegarder directement le fichier DuckDB déjà transformé évite de
relancer les 60 secondes de calcul du pipeline (récupération des données →
dbt → Machine Learning) à chaque démarrage d'une instance : seul un
téléchargement de quelques secondes est nécessaire.

Le fichier `src/storage_sync.py` propose deux fonctions :

- `telecharger_depuis_gcs()` - appelée une seule fois, au démarrage de
  chaque instance (pour le tableau de bord : via `st.cache_resource` dans
  `dashboard/APP.py` ; pour le serveur MCP : appel simple, puisque le
  processus reste actif longtemps). Cette fonction ne provoque jamais
  d'erreur bloquante : un problème de connexion ne doit pas empêcher
  l'application de démarrer.
- `televerser_vers_gcs()` - appelée après un recalcul réussi depuis l'onglet
  Administration
  (`dashboard/pages/99_Administration.py::relancer_pipeline_complet`), pour
  que le résultat survive au redémarrage de cette instance et soit repris
  par toutes les autres instances de l'application.

**Une vérification de compatibilité protège les données.** Sans cette
vérification, un futur changement de structure dans dbt (par exemple une
nouvelle colonne dans une table finale) pourrait être silencieusement
écrasé au démarrage par un ancien fichier restauré depuis GCS, provoquant
des erreurs en chaîne sur toute requête utilisant cette nouvelle colonne.
La variable `config.DATA_SCHEMA_VERSION`, enregistrée dans
`pipeline_state.json` à chaque exécution du pipeline, est donc comparée
par `telecharger_depuis_gcs()` avant tout téléchargement. En cas de
différence, rien n'est téléchargé : l'application garde les données déjà
présentes dans l'image, dont on est sûr qu'elles sont compatibles avec le
code en cours d'exécution.

**Cas particulier du fichier `mlflow.db` (base SQLite).** Ce fichier n'est
jamais copié directement, octet par octet, vers GCS. MLflow peut garder une
connexion ouverte en tâche de fond, ce qui rendrait une copie brute
susceptible de capturer les données à un moment incohérent. La fonction
`televerser_vers_gcs()` utilise donc la fonction `backup()` de la
bibliothèque `sqlite3`, qui copie proprement les données vers un fichier
temporaire avant de l'envoyer vers GCS.

**Remise à jour de l'Assistant IA.** Le serveur MCP est un service Cloud
Run distinct (processus séparé, même image Docker, mais point de
démarrage différent) : il ne relit les données depuis GCS qu'à son propre
démarrage, pas au moment où le tableau de bord termine un recalcul. Une
route interne `POST /admin/resync` (voir `mcp_server/README_MCP.md`)
permet donc au tableau de bord de lui demander de se resynchroniser
immédiatement après un recalcul sauvegardé, plutôt que d'attendre son
prochain redémarrage naturel.

**Limite acceptée en connaissance de cause** : le nombre maximal
d'instances (`max-instances=1`) est fixé à 1 sur les deux services. Cela
évite qu'une instance déjà démarrée continue de servir des données
anciennes pendant qu'une autre vient tout juste d'être mise à jour. Le
trafic concerné reste interne et limité (administration), donc ce
compromis est acceptable dans ce contexte.
