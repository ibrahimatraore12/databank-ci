# Définition du problème ML — dataBank CI Customer 360

**Auteur :** Ibrahima TRAORÉ — Analytics Engineer
**Date :** 2026-07-14
**Statut :** Cadrage initial, avant tout développement

## 1. Question business

> Comment identifier, parmi les clients actifs de la banque, ceux qui montrent
> des signaux précoces de désengagement — afin de prioriser les actions des
> conseillers commerciaux avant qu'un départ (fermeture de compte, inactivité
> totale) ne survienne ?

Ce score n'est pas destiné à remplacer le jugement du conseiller : il sert à
trier un portefeuille de 140 clients pour que les conseillers concentrent leur
temps sur les comptes qui en ont le plus besoin.

## 2. Type de problème

**Ce n'est pas un problème de classification supervisée classique.**

Le dataset source (`starter_dataset.xlsx`) ne contient aucune colonne
`churn_flag` observée dans le réel : il n'existe pas d'historique de départs
clients confirmés. Ce que nous appelons "churn" dans ce projet est en réalité
un **label proxy construit à partir d'heuristiques métier documentées**
(recency des transactions, réclamations non résolues, tendance d'activité,
usage digital).

Nous traitons donc ce projet comme :

- un **scoring comportemental** basé sur des règles métier explicites (Phase 1,
  `ml/rules.py`), toujours disponible et interprétable sans modèle ;
- une **expérimentation ML supervisée sur label proxy** (Phase 2), utile pour
  comparer des approches et documenter la méthodologie, mais dont les
  métriques ne doivent pas être présentées comme une prédiction de churn réel.

## 3. Hypothèses métier (H1 à H4)

| # | Hypothèse | Signal utilisé | Poids dans le score de règles |
|---|-----------|-----------------|-------------------------------|
| H1 | Un client qui n'a pas transigé depuis longtemps est en train de se désengager | `recency_jours` (dernière transaction) | 40 % |
| H2 | Un client avec des réclamations ouvertes ou mal résolues perd confiance | `nb_reclamations_ouvertes`, `sentiment`, `resolved_flag` | 30 % |
| H3 | Une baisse de fréquence/volume de transactions sur la période récente précède un départ | tendance transactions (30 derniers jours vs période antérieure) | 10 % |
| H4 | Un client peu engagé sur les canaux digitaux est plus exposé au risque de départ (moins de points de contact) | `mobile_app_active`, `internet_banking_active`, `mobile_money_linked` | 20 % |

Ces poids sont ceux du score de règles métier (Phase 1). Le score d'engagement
digital utilisé ailleurs dans le projet (génération de features) a une
pondération différente et documentée séparément dans `docs/decisions.md`.

## 4. Ce qui manque pour un vrai modèle de churn

- **Historique de churn réel** : aucune date de clôture de compte ni de motif
  de départ n'est disponible sur plus d'une période, donc impossible de
  labelliser un vrai événement de churn.
- **Net Banking Income (NBI) réel** : seule une estimation par formule UEMOA
  standard est calculable (`estimated_nbi_flag=True`), pas le NBI comptable
  réel du client.
- **Bureau de crédit externe** : aucune donnée d'endettement global du client
  hors banque (autres établissements) n'est disponible, ce qui limite la
  fiabilité du score de risque crédit.
- **Historique multi-période** : le dataset est une photo à un instant T, pas
  une série temporelle longue — la notion de "tendance" reste donc approximative.

## 5. Distribution du label et déséquilibre de classes

Chiffres mesurés sur le portefeuille réel (140 clients), pas des estimations :

- **Label naïf** (1 seul critère : recency > 90 jours) : **2 positifs, soit 1,4 %**.
  Beaucoup trop peu pour entraîner quoi que ce soit — quasiment tout le bruit
  d'échantillonnage.
- **Label enrichi** (au moins 2 signaux sur 4 déclenchés parmi recency,
  réclamation ouverte, tendance négative, digital faible) : **35 positifs,
  soit 25,0 %**. Ce taux est en réalité plus élevé qu'anticipé au cadrage
  initial du projet (une cible de 12-15 % avait été envisagée avant la mesure).
  L'écart s'explique par le critère "tendance négative", qui à lui seul
  concerne une large part du portefeuille sur la fenêtre de données observée
  — voir la Section 11 du notebook EDA pour le détail par critère.
- À titre de comparaison, un seuil à 3 critères sur 4 ne conserve qu'1 seul
  positif (0,7 %) : ce seuil est trop strict pour être exploitable. Le seuil à
  2 critères a donc été retenu comme compromis, documenté ici plutôt qu'ajusté
  a posteriori pour coller à un chiffre cible.

**Conséquences documentées honnêtement :**

- Le taux de 25 % rend le jeu réel exploitable pour un split stratifié 80/20
  (environ 7 positifs dans un jeu de test de 28 clients), mais l'échantillon
  reste petit dans l'absolu (140 clients au total).
- Les métriques (AUC, Recall, Precision, F1) calculées sur le jeu réel doivent
  être lues comme indicatives, pas comme des garanties de généralisation.
- `ml/model.py::evaluate_model` déclenche un avertissement explicite si
  `n < 200` ou si le nombre de positifs est `< 20` — ce qui se déclenche
  systématiquement sur un split du jeu réel (n=140).
- Un jeu de données synthétique enrichi (`data/enriched/`, `is_synthetic=True`)
  est généré par bootstrap métier pour porter le volume à ~540 clients,
  permettant une comparaison de modèles avec un échantillon de test plus
  confortable (voir `docs/model_comparison.md`, généré à l'étape ML).
- Toute donnée synthétique reste clairement marquée comme telle dans les tables
  Gold et dans le dashboard — elle ne remplace jamais la donnée réelle dans les
  vues opérationnelles par défaut.

## 6. Limites du projet, énoncées sans détour

- Ce score est un outil d'aide à la priorisation, pas une prédiction validée
  statistiquement sur un historique réel.
- Le dataset réel est petit (140 clients, 34 prêts, 42 réclamations) : toute
  conclusion doit être pondérée par cette taille d'échantillon.
- Les données synthétiques respectent les distributions observées en EDA mais
  ne peuvent pas inventer de corrélations que le monde réel ne confirme pas.
- Ce projet est un exercice d'ingénierie analytique de bout en bout
  (ingestion → dbt → ML → dashboard → MCP), pas un livrable de scoring crédit
  réglementaire.
