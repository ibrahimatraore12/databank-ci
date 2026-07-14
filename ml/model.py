# Entraînement et évaluation des modèles
# Model training and evaluation

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from xgboost import XGBClassifier

import config
from src.logger import log_event

MIN_SAMPLES_RELIABLE = 200
MIN_POSITIFS_RELIABLE = 20


def train_model(X_train: pd.DataFrame, y_train: pd.Series, model_type: str = "logistic"):
    # Entraîne un modèle du type demandé, toujours avec une pondération de classes équilibrée
    # Trains the requested model type, always with balanced class weighting
    if model_type == "logistic":
        model = LogisticRegression(class_weight="balanced", random_state=config.RANDOM_SEED, max_iter=1000)
    elif model_type == "random_forest":
        model = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=config.RANDOM_SEED)
    elif model_type == "xgboost":
        n_negatifs, n_positifs = (y_train == 0).sum(), (y_train == 1).sum()
        scale_pos_weight = n_negatifs / max(n_positifs, 1)
        model = XGBClassifier(
            scale_pos_weight=scale_pos_weight, random_state=config.RANDOM_SEED, eval_metric="logloss",
        )
    else:
        raise ValueError(f"train_model: model_type inconnu '{model_type}'")

    model.fit(X_train, y_train)
    log_event("ml", "INFO", f"[ML][train_model][{model_type}] OK", {"lignes_entrainement": len(X_train)})
    return model


def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    # Retourne AUC, Recall, Precision, F1 + avertissement si l'échantillon est trop petit
    # Returns AUC, Recall, Precision, F1 + a warning if the sample is too small
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    metrics = {
        "auc": round(roc_auc_score(y_test, y_proba), 3) if y_test.nunique() > 1 else None,
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 3),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 3),
        "f1": round(f1_score(y_test, y_pred, zero_division=0), 3),
        "n_test": len(y_test),
        "n_positifs_test": int(y_test.sum()),
    }

    if len(y_test) < MIN_SAMPLES_RELIABLE or y_test.sum() < MIN_POSITIFS_RELIABLE:
        metrics["avertissement"] = (
            f"Echantillon de test trop petit (n={len(y_test)}, positifs={int(y_test.sum())}) "
            "pour des métriques statistiquement fiables — voir docs/ml_problem_definition.md"
        )
        log_event("ml", "WARNING", "[ML][evaluate_model] ECHANTILLON INSUFFISANT", metrics)
    else:
        log_event("ml", "INFO", "[ML][evaluate_model] OK", metrics)

    return metrics
