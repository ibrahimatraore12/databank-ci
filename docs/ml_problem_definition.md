# Définition du problème de Machine Learning - dataBank CI Customer 360

> *[English version: [ml_problem_definition_en.md](ml_problem_definition_en.md)]*

**Auteur :** Ibrahima TRAORÉ - Analytics Engineer
**Date :** 2026-07-14
**Statut :** Cadrage initial, avant tout développement

## 1. La question métier

> Parmi les clients actifs de la banque, comment repérer ceux qui montrent
> des premiers signes de désengagement, pour que les conseillers puissent
> agir avant qu'un vrai départ n'arrive (fermeture de compte, inactivité
> totale) ?

Ce score n'a pas pour but de remplacer le jugement du conseiller. Il sert à
trier un portefeuille de 140 clients, pour que les conseillers concentrent
leur temps sur les comptes qui en ont le plus besoin.

## 2. Quel type de problème est-ce vraiment ?

**Ce n'est pas un problème de classification classique**, où l'on
connaîtrait déjà, pour chaque client, s'il est parti ou non.

Le fichier source (`starter_dataset.xlsx`) ne contient aucune colonne
`churn_flag` (indicateur de départ) observée dans la réalité : il n'existe
pas d'historique de départs de clients confirmés. Ce que l'on appelle
"churn" (départ ou désengagement du client) dans ce projet est en fait un
**indicateur approché ("label proxy"), construit à partir de règles métier
documentées** : depuis quand le client n'a pas transigé, s'il a des
réclamations non résolues, comment évolue son activité, et son usage des
outils numériques.

Ce projet est donc traité en deux temps :

- un **score comportemental basé sur des règles métier explicites**
  (Étape 1, `ml/rules.py`), toujours disponible et facile à comprendre,
  même sans modèle entraîné ;
- une **expérimentation de Machine Learning supervisé sur cet indicateur
  approché** (Étape 2), utile pour comparer différentes méthodes et
  documenter la démarche, mais dont les résultats chiffrés ne doivent pas
  être présentés comme une vraie prédiction de départ client.

## 3. Les hypothèses métier (H1 à H4)

| # | Hypothèse | Donnée utilisée | Poids dans le score de règles |
|---|-----------|-----------------|-------------------------------|
| H1 | Un client qui n'a pas transigé depuis longtemps est en train de se désengager | `recency_jours` (jours depuis la dernière transaction) | 40 % |
| H2 | Un client avec des réclamations ouvertes ou mal résolues perd confiance | `nb_reclamations_ouvertes`, `sentiment`, `resolved_flag` | 30 % |
| H3 | Une baisse récente de la fréquence ou du montant des transactions annonce souvent un départ | tendance des transactions (30 derniers jours comparés à la période précédente) | 10 % |
| H4 | Un client peu actif sur les outils numériques est plus exposé au risque de départ (moins de points de contact avec la banque) | `mobile_app_active`, `internet_banking_active`, `mobile_money_linked` | 20 % |

Ces poids sont ceux du score de règles métier (Étape 1). Un autre score,
celui de l'engagement numérique utilisé ailleurs dans le projet (pour
créer des indicateurs), utilise une pondération différente, documentée à
part dans `docs/decisions.md`.

## 4. Ce qui manquerait pour un vrai modèle de départ client (churn)

- **Un historique réel des départs** : aucune date de clôture de compte ni
  aucun motif de départ n'est disponible sur plus d'une période. Il est
  donc impossible d'identifier un vrai départ de client dans les données.
- **Le revenu réel généré par le client (NBI)** : seule une estimation par
  formule standard UEMOA est calculable (`estimated_nbi_flag=True`), pas le
  chiffre comptable réel du client.
- **Un bureau de crédit externe** : aucune donnée sur l'endettement global
  du client en dehors de la banque n'est disponible, ce qui limite la
  fiabilité du score de risque de crédit.
- **Un historique sur plusieurs périodes** : le fichier est une photo prise
  à un instant donné, pas un suivi dans le temps. La notion de "tendance"
  reste donc une approximation.

## 5. Répartition des cas et déséquilibre entre les groupes

Chiffres mesurés sur le portefeuille réel (140 clients), pas des
estimations :

- **Avec un seul critère** (pas de transaction depuis plus de 90 jours) :
  **2 clients concernés sur 140, soit 1,4 %**. C'est beaucoup trop peu pour
  entraîner un modèle fiable : à ce niveau, on ne mesure quasiment que du
  bruit statistique.
- **Avec un critère plus large** (au moins 2 signaux déclenchés parmi les 4 :
  inactivité, réclamation ouverte, tendance négative, faible usage
  numérique) : **35 clients concernés, soit 25,0 %**. Ce taux est en
  réalité plus élevé que prévu au démarrage du projet (une fourchette de
  12 à 15 % avait été envisagée avant la mesure réelle). L'écart s'explique
  surtout par le critère "tendance négative", qui à lui seul concerne une
  large part du portefeuille sur la période observée. Le détail par critère
  est visible dans la section 11 du notebook d'analyse exploratoire (EDA).
- À titre de comparaison, exiger 3 signaux sur 4 ne laisse plus qu'1 seul
  client concerné (0,7 %) : ce seuil est trop strict pour être utile. Le
  seuil à 2 signaux a donc été retenu comme le meilleur compromis, et ce
  choix est documenté ici tel quel, plutôt qu'ajusté après coup pour
  obtenir un chiffre qui semblerait plus flatteur.

**Les conséquences de ce choix, dites honnêtement :**

- Le taux de 25 % permet de séparer les données réelles en un jeu
  d'entraînement et un jeu de test (80 %/20 %) tout en gardant des
  proportions équilibrées (environ 7 clients concernés dans un jeu de test
  de 28 clients). Mais l'échantillon reste petit dans l'absolu (140 clients
  au total).
- Les indicateurs de performance calculés sur les données réelles (AUC,
  Recall, Precision, F1 - des mesures classiques pour évaluer un modèle de
  prédiction) doivent être lus comme indicatifs seulement, pas comme une
  garantie que le modèle fonctionnerait aussi bien sur d'autres clients.
- La fonction `ml/model.py::evaluate_model` affiche automatiquement un
  avertissement si le nombre total de clients est inférieur à 200, ou si
  le nombre de clients concernés est inférieur à 20. Cet avertissement
  s'affiche systématiquement sur les données réelles (140 clients).
- Un jeu de données synthétique enrichi (`data/enriched/`,
  `is_synthetic=True`) est généré à partir de règles métier et de
  répétitions statistiques (méthode dite "bootstrap"), pour porter le
  volume total à environ 540 clients. Cela permet de comparer les modèles
  sur un échantillon de test plus confortable (voir
  `docs/model_comparison.md`, généré automatiquement à l'étape de Machine
  Learning).
- Toute donnée synthétique reste toujours clairement identifiée comme
  telle dans les tables finales (Gold) et dans le tableau de bord. Elle ne
  remplace jamais la donnée réelle dans les vues affichées par défaut.

## 6. Les limites du projet, dites sans détour

- Ce score est un outil d'aide à la priorisation, pas une prédiction
  validée statistiquement sur un historique réel de départs.
- Le jeu de données réel est petit (140 clients, 34 prêts, 42
  réclamations) : toute conclusion tirée de ce projet doit tenir compte de
  cette petite taille d'échantillon.
- Les données synthétiques respectent les tendances observées lors de
  l'analyse exploratoire, mais elles ne peuvent pas inventer des liens
  entre variables que le monde réel ne confirme pas.
- Ce projet est un exercice d'ingénierie de données de bout en bout
  (récupération des données → dbt → Machine Learning → tableau de bord →
  serveur MCP), pas un outil de scoring de crédit réglementaire prêt pour
  la production.
