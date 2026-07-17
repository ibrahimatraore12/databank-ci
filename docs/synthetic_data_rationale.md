# Explication des données synthétiques - dataBank CI Customer 360

> *[English version: [synthetic_data_rationale_en.md](synthetic_data_rationale_en.md)]*

**Auteur :** Ibrahima TRAORÉ - Analytics Engineer
**Date :** Juillet 2026

## 1. Pourquoi générer des données synthétiques (artificielles)

Le portefeuille réel compte 140 clients, dont 35 sont considérés comme
"désengagés" selon l'indicateur approché enrichi (voir
`docs/ml_problem_definition.md`, section 5), soit 25,0 %. C'est trop peu
pour comparer plusieurs modèles de Machine Learning de façon fiable, avec
une séparation entraînement/test solide. La fonction
`ml/model.py::evaluate_model` affiche d'ailleurs automatiquement un
avertissement dès que le nombre total de clients est inférieur à 200, ou
que le nombre de cas concernés est inférieur à 20 - ce qui arrive
systématiquement avec les seules données réelles.

J'ai donc choisi de générer 400 clients synthétiques
(`config.SYNTHETIC_N_CUSTOMERS`) pour porter le volume total à 540
clients, plutôt que de présenter des résultats de Machine Learning peu
fiables, calculés sur seulement 140 clients.

## 2. La méthode utilisée : une répétition basée sur des règles métier, pas du hasard pur

La fonction
`src/synthetic_data_generator.py::generate_synthetic_customers()` ne tire
pas des valeurs au hasard sans logique. Voici la méthode, étape par étape :

1. **Sélection avec répétition possible** de clients réels, utilisés comme
   modèles de départ (`_tirer_clients_source`, avec un tirage aléatoire
   fixé par `seed=42` pour pouvoir reproduire exactement le même résultat).
2. **Copie et changement d'identifiant** du client et de toutes ses
   informations liées (comptes, cartes, prêts, transactions,
   réclamations, échanges, offres), sous un nouvel identifiant :
   `SYN-0001`, `SYN-0002`, etc. Les liens entre les tables (`account_id`,
   `customer_id`) restent cohérents après ce changement
   (`_remapper_comptes`, `_remapper_avec_compte`,
   `_remapper_table_client`).
3. **Ajout contrôlé de signes de désengagement** sur une partie des
   clients générés (`churn_rate=0.10`, soit environ 40 clients
   synthétiques) : leurs transactions sont décalées de 180 jours dans le
   passé (`_injecter_desengagement`), ce qui simule une inactivité
   récente, sans inventer de nouveau type de comportement.
4. **Deux tables ne sont jamais générées artificiellement** : `Branches`
   (agences) et `Channels` (canaux) sont des données de référence
   partagées, sans lien direct avec un client précis. Elles sont donc
   réutilisées telles quelles.

Chaque ligne générée porte l'indicateur `is_synthetic=True` dès l'étape
Bronze (`bronze_synthetic_customers`, etc.). Cet indicateur suit la donnée
à travers toutes les étapes de transformation dbt, jusqu'à la colonne
`customer_360.is_synthetic`, et il n'est jamais caché dans le tableau de
bord.

## 3. Une vérification statistique : le test de Kolmogorov-Smirnov

Générer des données qui "ressemblent" aux données réelles ne suffit pas :
il faut le vérifier avec une méthode statistique. La fonction
`_valider_distributions_ks()` compare la répartition des revenus mensuels
réels et synthétiques (`monthly_income_xof`) à l'aide d'un test statistique
appelé "test de Kolmogorov-Smirnov" (fonction `scipy.stats.ks_2samp`), qui
sert à vérifier si deux groupes de données suivent la même tendance. Si le
résultat du test (la "p-value") descend sous 0,05, un message d'erreur est
enregistré dans les journaux (`[SYNTHETIC][KS-TEST] distribution
divergente`). La génération de données n'est pas bloquée automatiquement
dans ce cas, mais l'écart est enregistré et consultable dans
`logs/pipeline.log` : rien n'est caché.

## 4. Ce que cette méthode ne peut pas faire

- **Elle ne peut pas inventer de nouveaux liens entre les données** que le
  monde réel ne confirme pas : un client synthétique reste, par
  construction, une copie d'un client réel avec un nouvel identifiant. Les
  modèles entraînés sur ce jeu de données enrichi peuvent donc "apprendre
  par cœur" des détails propres à leur client d'origine, plutôt que
  d'apprendre une tendance générale valable pour tous. Voir
  `docs/model_comparison.md` pour voir l'effet concret de ce risque sur
  les scores de RandomForest et XGBoost.
- **Elle ne remplace jamais la donnée réelle** dans les vues affichées par
  défaut dans le tableau de bord : l'indicateur `is_synthetic` sert
  précisément à ne jamais confondre les deux types de données (voir
  `docs/decisions.md`).
- **Le taux de désengagement ajouté (10 %) est un choix**, pas une mesure
  réelle : il vise seulement à créer assez de cas "positifs" pour
  entraîner un modèle, pas à refléter un taux de départ de clients
  réellement observé.
