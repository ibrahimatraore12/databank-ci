# Compréhension métier — dataBank CI Customer 360

**Auteur :** Ibrahima TRAORÉ — Analytics Engineer
**Date :** 2026-07-14

## 1. Contexte

dataBank CI est une banque de détail opérant en Côte d'Ivoire (zone UEMOA,
devise XOF). Le portefeuille source couvre 140 clients répartis sur 4
segments (Mass, Affluent, Premier, Youth), avec comptes, prêts, cartes,
transactions, interactions et réclamations.

## 2. Cinq décisions métier que ce projet doit soutenir

1. **Priorisation des visites conseillers** — quels clients contacter en
   premier cette semaine parmi ceux qui montrent des signaux de
   désengagement ?
2. **Ciblage cross-sell** — quels clients détenant peu de produits (ex : les
   42 clients sans carte) sont de bons candidats pour une offre ciblée ?
3. **Traitement prioritaire des réclamations** — quelles réclamations
   ouvertes doivent être escaladées en priorité selon la sévérité et
   l'impact potentiel sur la rétention ?
4. **Upsell salaire domicilié** — quels clients à fort revenu mensuel n'ont
   pas encore domicilié leur salaire chez dataBank CI ?
5. **Surveillance du risque crédit** — quels emprunteurs approchent d'un
   dépassement de délai de paiement (seuil 15 jours) et nécessitent un suivi
   avant escalade en `Watchlist` ou `Delinquent` ?

## 3. KPIs guide par segment

| Segment | KPI prioritaire | Pourquoi |
|---------|------------------|----------|
| Mass | Taux d'activation digitale, réclamations en cours | Volume important (84 clients), sensible au coût de service |
| Affluent | Solde moyen 90 jours, nombre de produits détenus | Potentiel de cross-sell le plus élevé |
| Premier | NBI estimé, réclamations sévérité haute | Portefeuille à forte valeur, faible tolérance à l'insatisfaction |
| Youth | Application mobile activée, offres acceptées | Segment digital natif, KPI d'engagement plutôt que de solde |

KPIs transverses suivis dans le dashboard : nombre de clients à risque,
taux de conversion des offres, délai moyen de résolution des réclamations,
proportion de clients avec salaire domicilié.

## 4. Ce qui manque pour un Customer 360 production réel

- **Consentement RGPD/local et gouvernance des données** : aucun mécanisme de
  consentement granulaire par finalité n'est modélisé au-delà du champ
  `marketing_opt_in`.
- **Données temps réel** : le dataset est un extrait statique ; un Customer
  360 réel nécessiterait un flux d'ingestion incrémental (CDC) plutôt qu'un
  chargement complet.
- **Scoring de fraude** : aucune donnée de détection de fraude transactionnelle
  n'est disponible séparément du flag `is_disputed`.
- **Historique multi-année** : la fenêtre de données (2024-02 à 2025-12)
  est courte pour des analyses de tendance robustes.
- **Intégration bureau de crédit externe** et **NBI comptable réel** — voir
  `docs/ml_problem_definition.md` section 4.
- **Processus de validation humaine** avant toute action automatisée déclenchée
  par le score (ce projet reste un outil d'aide à la décision, pas un moteur
  de décision autonome).
