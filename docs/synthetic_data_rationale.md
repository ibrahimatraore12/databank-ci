# Justification des données synthétiques - dataBank CI Customer 360

> *[English version: [synthetic_data_rationale_en.md](synthetic_data_rationale_en.md)]*

**Auteur :** Ibrahima TRAORÉ - Analytics Engineer
**Date :** Juillet 2026

## 1. Pourquoi générer des données synthétiques

Le portefeuille réel compte 140 clients, 35 positifs (25,0 %) sur le label
proxy enrichi (voir `docs/ml_problem_definition.md`, section 5). C'est trop
petit pour comparer plusieurs modèles supervisés avec un split train/test
fiable : `ml/model.py::evaluate_model` déclenche d'ailleurs un avertissement
explicite si `n < 200` ou si les positifs sont `< 20`, ce qui se produit
systématiquement sur le seul jeu réel.

J'ai choisi de générer 400 clients synthétiques (`config.SYNTHETIC_N_CUSTOMERS`)
pour porter le volume total à 540, plutôt que de présenter des métriques ML
non fiables sur un échantillon de 140 clients.

## 2. Méthode : bootstrap métier, pas génération aléatoire

`src/synthetic_data_generator.py::generate_synthetic_customers()` ne tire pas
des valeurs aléatoires dans le vide. La méthode :

1. **Tirage avec remise** de clients réels comme gabarits
   (`_tirer_clients_source`, `rng.choice` avec `seed=42`).
2. **Copie et remappage** du client et de toutes ses tables liées (comptes,
   cartes, prêts, transactions, réclamations, interactions, offres) sous un
   nouvel identifiant `SYN-0001`, `SYN-0002`, etc. - les relations entre
   tables (`account_id`, `customer_id`) restent cohérentes après remappage
   (`_remapper_comptes`, `_remapper_avec_compte`, `_remapper_table_client`).
3. **Injection contrôlée de désengagement** sur un sous-échantillon
   (`churn_rate=0.10`, soit ~40 clients synthétiques) : leurs transactions
   sont décalées de 180 jours dans le passé
   (`_injecter_desengagement`), simulant une inactivité récente sans
   inventer de nouveau schéma de comportement.
4. **Deux tables restent non synthétisées** : `Branches` et `Channels` sont
   des référentiels partagés (pas de notion de client), donc réutilisés tels
   quels.

Chaque ligne produite porte `is_synthetic=True` dès la couche Bronze
(`bronze_synthetic_customers`, etc.), un flag qui traverse toutes les
couches dbt jusqu'à `customer_360.is_synthetic` et qui n'est jamais masqué
dans le dashboard.

## 3. Validation statistique : test de Kolmogorov-Smirnov

Générer des données qui "ressemblent" au réel ne suffit pas à le prouver.
`_valider_distributions_ks()` compare la distribution réelle et synthétique
du revenu mensuel (`monthly_income_xof`) avec un test KS à deux échantillons
(`scipy.stats.ks_2samp`) : si la p-value tombe sous 0,05, un log d'erreur est
émis (`[SYNTHETIC][KS-TEST] distribution divergente`) - la génération n'est
pas bloquée automatiquement sur cet échec, mais l'écart est tracé et
consultable dans `logs/pipeline.log`, pas caché.

## 4. Ce que cette méthode ne peut pas faire

- **Elle ne peut pas inventer de nouvelles corrélations** que le monde réel
  ne confirme pas : un client synthétique reste, par construction, une copie
  d'un client réel avec un nouvel identifiant. Les modèles entraînés sur ce
  jeu enrichi peuvent donc mémoriser des motifs propres à leur client source
  plutôt qu'apprendre une vraie généralisation - voir `docs/model_comparison.md`
  pour l'effet concret de ce risque sur les scores RandomForest/XGBoost.
- **Elle ne remplace jamais la donnée réelle** dans les vues opérationnelles
  par défaut du dashboard - le flag `is_synthetic` sert précisément à ne
  jamais confondre les deux (voir `docs/decisions.md`).
- **Le taux de désengagement injecté (10 %) est un paramètre choisi**, pas
  une mesure : il vise à produire un volume de positifs suffisant pour
  l'entraînement, pas à refléter un taux de churn réel observé.
