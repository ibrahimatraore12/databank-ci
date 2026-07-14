# Étude comparative de modèles — dataBank CI Customer 360

**Généré automatiquement par `ml/comparison.py` — ne pas éditer à la main.**

- Scénario A : 140 clients réels, 35 positifs (25.0 %)
- Scénario B : 540 clients réels + synthétiques, 151 positifs (28.0 %)

## Résultats (validation croisée stratifiée à 5 plis)

| scenario           | modele                 |   auc |   recall |   precision |    f1 |
|:-------------------|:-----------------------|------:|---------:|------------:|------:|
| A (n=140 réels)    | LogisticRegression     | 0.913 |    0.829 |       0.62  | 0.698 |
| A (n=140 réels)    | Rule-Based Scoring     | 0.83  |    0.914 |       0.451 | 0.604 |
| B (n=540 enrichis) | LogisticRegression     | 0.944 |    0.934 |       0.737 | 0.822 |
| B (n=540 enrichis) | RandomForestClassifier | 1     |    0.987 |       1     | 0.993 |
| B (n=540 enrichis) | XGBClassifier          | 1     |    1     |       1     | 1     |

## Lecture

Ces métriques restent indicatives : voir `docs/ml_problem_definition.md` pour les limites du label proxy utilisé et les avertissements sur la taille d'échantillon.

**Sur les scores quasi parfaits du Scénario B (RandomForest, XGBoost) :** les clients synthétiques sont générés par bootstrap métier à partir des clients réels (voir `src/synthetic_data_generator.py`), donc statistiquement très proches de leur client source. Un modèle capacitaire (forêt, boosting) peut mémoriser ces motifs facilement — ces scores élevés reflètent la facilité du jeu synthétique, pas une garantie de performance en production sur des clients inédits.
