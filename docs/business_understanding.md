# Compréhension métier - dataBank CI Customer 360

> *[English version: [business_understanding_en.md](business_understanding_en.md)]*

**Auteur :** Ibrahima TRAORÉ - Analytics Engineer
**Date :** 2026-07-14

## 1. Contexte

dataBank CI est une banque de détail qui opère en Côte d'Ivoire (zone UEMOA,
devise XOF). Le fichier source couvre 140 clients, répartis en 4 groupes
appelés "segments" (Mass, Affluent, Premier, Youth). Pour chaque client, on
dispose de ses comptes, prêts, cartes, transactions, échanges avec la
banque et réclamations.

## 2. Cinq décisions métier que ce projet doit aider à prendre

1. **Priorisation des visites conseillers** - parmi les clients qui montrent
   des signes de désengagement, lesquels contacter en premier cette
   semaine ?
2. **Ciblage pour la vente croisée (cross-sell)** - parmi les clients qui
   détiennent peu de produits (par exemple les 42 clients sans carte),
   lesquels sont de bons candidats pour recevoir une offre ciblée ?
3. **Traitement prioritaire des réclamations** - parmi les réclamations
   ouvertes, lesquelles faire remonter en priorité, selon leur gravité et
   leur impact possible sur la fidélité du client ?
4. **Proposition de domiciliation de salaire** - quels clients à revenu
   mensuel élevé n'ont pas encore choisi de recevoir leur salaire chez
   dataBank CI ?
5. **Surveillance du risque de crédit** - quels emprunteurs approchent d'un
   retard de paiement (seuil de 15 jours) et ont besoin d'un suivi avant
   d'être classés `Watchlist` (à surveiller) ou `Delinquent` (en défaut) ?

## 3. Indicateurs clés (KPI) à suivre par segment

| Segment | Indicateur prioritaire | Pourquoi |
|---------|------------------|----------|
| Mass | Taux d'activation des services numériques, réclamations en cours | Segment le plus nombreux (84 clients), coût de service à surveiller |
| Affluent | Solde moyen sur 90 jours, nombre de produits détenus | Potentiel de vente croisée le plus élevé |
| Premier | Revenu généré par client (NBI, estimé), réclamations graves | Clients à forte valeur, faible tolérance à l'insatisfaction |
| Youth | Application mobile activée, offres acceptées | Segment habitué au numérique, on suit l'engagement plutôt que le solde |

Indicateurs suivis pour tous les segments dans le tableau de bord : nombre
de clients à risque, taux d'acceptation des offres, délai moyen de
résolution des réclamations, proportion de clients ayant domicilié leur
salaire.

## 4. Ce qu'il manquerait pour un vrai outil Customer 360 en production

- **Consentement RGPD (protection des données personnelles) et gouvernance
  des données** : aujourd'hui, il n'existe pas de mécanisme détaillé de
  consentement par usage (marketing, partage, etc.), seulement un champ
  simple `marketing_opt_in`.
- **Données en temps réel** : le fichier utilisé est une photo figée à un
  instant donné. Un vrai outil Customer 360 aurait besoin d'un flux de
  mise à jour continue (appelé CDC, pour "Change Data Capture") plutôt que
  d'un rechargement complet à chaque fois.
- **Détection de fraude** : il n'existe pas de données dédiées à la
  détection de fraude sur les transactions, en dehors du simple indicateur
  `is_disputed` (transaction contestée).
- **Historique sur plusieurs années** : la période couverte (février 2024 à
  décembre 2025) est courte pour analyser des tendances de façon fiable.
- **Connexion à un bureau de crédit externe** et **calcul du revenu réel du
  client (NBI comptable)** - voir `docs/ml_problem_definition.md`, section 4.
- **Étape de validation humaine** avant toute action automatique déclenchée
  par un score. Ce projet reste un outil d'aide à la décision : il ne
  prend jamais de décision seul.
