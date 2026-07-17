# Étude comparative de modèles - dataBank CI Customer 360

> *[English version: [model_comparison_en.md](model_comparison_en.md)]*

**Ce fichier est généré automatiquement par `ml/comparison.py`. Ne pas le modifier à la main : les changements seraient écrasés au prochain calcul.**

- Scénario A (données réelles seulement) : 140 clients, 35 considérés à risque (25.0 %)
- Scénario B (données réelles + synthétiques) : 540 clients, 151 considérés à risque (28.0 %)

## Résultats (validation croisée : les données sont découpées en 5 groupes, chaque groupe sert une fois de test)

| scenario           | modele                 |   auc |   recall |   precision |    f1 |
|:-------------------|:-----------------------|------:|---------:|------------:|------:|
| A (n=140 réels)    | LogisticRegression     | 0.913 |    0.829 |       0.62  | 0.698 |
| A (n=140 réels)    | Rule-Based Scoring     | 0.83  |    0.914 |       0.451 | 0.604 |
| B (n=540 enrichis) | LogisticRegression     | 0.944 |    0.934 |       0.737 | 0.822 |
| B (n=540 enrichis) | RandomForestClassifier | 1     |    0.987 |       1     | 0.993 |
| B (n=540 enrichis) | XGBClassifier          | 1     |    1     |       1     | 1     |

Repère de lecture des colonnes : `auc` (qualité générale de prédiction, entre 0 et 1, plus c'est proche de 1 mieux c'est), `recall` (part des clients à risque bien repérés par le modèle), `precision` (part des alertes du modèle qui étaient justes), `f1` (moyenne équilibrée entre recall et precision).

## Comment lire ces résultats

Ces chiffres restent indicatifs. Voir `docs/ml_problem_definition.md` pour comprendre les limites de l'indicateur de risque utilisé et les avertissements sur la petite taille de l'échantillon.

**À propos des scores quasi parfaits du Scénario B (RandomForest, XGBoost) :** les clients synthétiques sont générés à partir de clients réels, par une méthode de répétition basée sur des règles métier (voir `src/synthetic_data_generator.py`). Ils restent donc statistiquement très proches de leur client d'origine. Un modèle puissant (forêt aléatoire, boosting) peut facilement "apprendre par cœur" ces ressemblances. Ces scores élevés montrent seulement que le jeu de données synthétique est facile à prédire pour ces modèles, pas qu'ils fonctionneraient aussi bien en production sur de nouveaux clients jamais vus.
