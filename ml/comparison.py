# Étude comparative de modèles — Scénario A (réel) vs Scénario B (enrichi synthétique)
# Comparative model study — Scenario A (real) vs Scenario B (enriched synthetic)

import os

import mlflow
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

import config
from ml.data import get_X_y, load_data, preprocess_data
from ml.model import train_model
from ml.rules import calculate_risk_score
from src.logger import log_event

MLFLOW_EXPERIMENT = "databank_ci_churn_scoring"


def _evaluer_cv(model_type: str, X: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> dict:
    # Validation croisée stratifiée à 5 plis, moyenne des métriques sur tous les plis
    # 5-fold stratified cross-validation, metrics averaged across all folds
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=config.RANDOM_SEED)
    resultats = {"auc": [], "recall": [], "precision": [], "f1": []}

    for train_idx, test_idx in skf.split(X, y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        X_train_prep = preprocess_data(X_train, fit=True)
        X_test_prep = preprocess_data(X_test, fit=False)

        model = train_model(X_train_prep, y_train, model_type=model_type)
        y_pred = model.predict(X_test_prep)
        y_proba = model.predict_proba(X_test_prep)[:, 1] if hasattr(model, "predict_proba") else y_pred

        resultats["auc"].append(roc_auc_score(y_test, y_proba) if y_test.nunique() > 1 else 0.5)
        resultats["recall"].append(recall_score(y_test, y_pred, zero_division=0))
        resultats["precision"].append(precision_score(y_test, y_pred, zero_division=0))
        resultats["f1"].append(f1_score(y_test, y_pred, zero_division=0))

    return {cle: round(sum(valeurs) / len(valeurs), 3) for cle, valeurs in resultats.items()}


def _evaluer_score_regles(df: pd.DataFrame, y: pd.Series) -> dict:
    # Évalue le score de règles métier comme référence non-ML (pas de CV, pas d'entraînement)
    # Evaluates the business rule score as a non-ML reference (no CV, no training)
    score_regles = calculate_risk_score(df)
    seuil = score_regles["score_regles"].median()
    y_pred = (score_regles["score_regles"] >= seuil).astype(int)

    return {
        "auc": round(roc_auc_score(y, score_regles["score_regles"]), 3) if y.nunique() > 1 else None,
        "recall": round(recall_score(y, y_pred, zero_division=0), 3),
        "precision": round(precision_score(y, y_pred, zero_division=0), 3),
        "f1": round(f1_score(y, y_pred, zero_division=0), 3),
    }


def _logger_mlflow(nom_run: str, dataset: str, model_type: str, metrics: dict) -> None:
    # Journalise le run dans MLflow avec les tags dataset et model_type
    # Logs the run in MLflow with dataset and model_type tags
    try:
        with mlflow.start_run(run_name=nom_run):
            mlflow.set_tag("dataset", dataset)
            mlflow.set_tag("model_type", model_type)
            for cle, valeur in metrics.items():
                if isinstance(valeur, (int, float)) and valeur is not None:
                    mlflow.log_metric(cle, valeur)
    except Exception as error:
        log_event("ml", "ERROR", "[ML][MLFLOW] ECHEC", {"erreur": str(error)})
        raise


def _generer_rapport_markdown(rapport: pd.DataFrame, df_reel: pd.DataFrame, df_enrichi: pd.DataFrame) -> None:
    # Génère docs/model_comparison.md à partir des résultats de la comparaison
    # Generates docs/model_comparison.md from the comparison results
    chemin = os.path.join(config.PROJECT_ROOT, "docs", "model_comparison.md")
    lignes = [
        "# Étude comparative de modèles — dataBank CI Customer 360",
        "",
        "**Généré automatiquement par `ml/comparison.py` — ne pas éditer à la main.**",
        "",
        f"- Scénario A : {len(df_reel)} clients réels, {int(df_reel['churn_flag'].sum())} positifs "
        f"({100 * df_reel['churn_flag'].mean():.1f} %)",
        f"- Scénario B : {len(df_enrichi)} clients réels + synthétiques, "
        f"{int(df_enrichi['churn_flag'].sum())} positifs ({100 * df_enrichi['churn_flag'].mean():.1f} %)",
        "",
        "## Résultats (validation croisée stratifiée à 5 plis)",
        "",
        rapport.to_markdown(index=False),
        "",
        "## Lecture",
        "",
        "Ces métriques restent indicatives : voir `docs/ml_problem_definition.md` pour les limites "
        "du label proxy utilisé et les avertissements sur la taille d'échantillon.",
        "",
        "**Sur les scores quasi parfaits du Scénario B (RandomForest, XGBoost) :** les clients "
        "synthétiques sont générés par bootstrap métier à partir des clients réels (voir "
        "`src/synthetic_data_generator.py`), donc statistiquement très proches de leur client source. "
        "Un modèle capacitaire (forêt, boosting) peut mémoriser ces motifs facilement — ces scores "
        "élevés reflètent la facilité du jeu synthétique, pas une garantie de performance en "
        "production sur des clients inédits.",
        "",
    ]
    with open(chemin, "w") as f:
        f.write("\n".join(lignes))


def run_comparison() -> pd.DataFrame:
    # Orchestration complète : Scénario A (140 réels) vs Scénario B (540 enrichis)
    # Full orchestration: Scenario A (140 real) vs Scenario B (540 enriched)
    mlflow.set_tracking_uri(f"sqlite:///{os.path.join(config.PROJECT_ROOT, 'mlflow.db')}")
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    lignes_rapport = []

    df_reel = load_data(use_synthetic=False)
    X_reel, y_reel = get_X_y(df_reel)

    metrics_logistic_a = _evaluer_cv("logistic", X_reel, y_reel)
    _logger_mlflow("scenario_a_logistic", "reel_140", "logistic", metrics_logistic_a)
    lignes_rapport.append({"scenario": "A (n=140 réels)", "modele": "LogisticRegression", **metrics_logistic_a})

    metrics_regles_a = _evaluer_score_regles(df_reel, y_reel)
    _logger_mlflow("scenario_a_regles", "reel_140", "rule_based", metrics_regles_a)
    lignes_rapport.append({"scenario": "A (n=140 réels)", "modele": "Rule-Based Scoring", **metrics_regles_a})

    df_enrichi = load_data(use_synthetic=True)
    X_enrichi, y_enrichi = get_X_y(df_enrichi)

    for model_type, nom_modele in [
        ("logistic", "LogisticRegression"),
        ("random_forest", "RandomForestClassifier"),
        ("xgboost", "XGBClassifier"),
    ]:
        metrics_b = _evaluer_cv(model_type, X_enrichi, y_enrichi)
        _logger_mlflow(f"scenario_b_{model_type}", "enrichi_540", model_type, metrics_b)
        lignes_rapport.append({"scenario": "B (n=540 enrichis)", "modele": nom_modele, **metrics_b})

    rapport = pd.DataFrame(lignes_rapport)
    _generer_rapport_markdown(rapport, df_reel, df_enrichi)
    log_event("ml", "INFO", "[ML][COMPARISON] OK", {"lignes_rapport": len(rapport)})
    return rapport


if __name__ == "__main__":
    print(run_comparison())
