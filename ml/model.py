# Entraînement et évaluation des modèles
# Model training and evaluation

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, roc_curve
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


def compute_roc_data(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    # Courbe ROC + seuil retenu par le critère de Youden (maximise TPR-FPR) —
    # un choix de seuil réel, pas une valeur arbitraire recopiée d'un exemple
    # ROC curve + threshold picked by Youden's criterion (maximizes TPR-FPR) —
    # a real threshold choice, not an arbitrary value copied from an example
    y_proba = model.predict_proba(X_test)[:, 1]
    fpr, tpr, seuils = roc_curve(y_test, y_proba)
    auc = round(roc_auc_score(y_test, y_proba), 3) if y_test.nunique() > 1 else None

    idx_optimal = int(np.argmax(tpr - fpr))
    seuil_retenu = float(seuils[idx_optimal])
    y_pred_seuil = (y_proba >= seuil_retenu).astype(int)
    precision_seuil = round(precision_score(y_test, y_pred_seuil, zero_division=0), 3)

    return {
        "fpr": fpr.tolist(), "tpr": tpr.tolist(), "auc": auc,
        "seuil_retenu": round(seuil_retenu, 3),
        "fpr_seuil": float(fpr[idx_optimal]), "tpr_seuil": float(tpr[idx_optimal]),
        "precision_seuil": precision_seuil,
    }


def calculate_psi(reference: pd.Series, actuel: pd.Series, nb_bins: int = 10) -> float:
    # PSI (Population Stability Index) entre deux distributions, sur des bins
    # définis par les quantiles de la distribution de référence — stable si < 0,1,
    # dérive modérée si < 0,2, dérive significative au-delà
    # PSI (Population Stability Index) between two distributions, on bins defined
    # by the reference distribution's quantiles — stable if < 0.1, moderate drift
    # if < 0.2, significant drift beyond
    quantiles = np.linspace(0, 1, nb_bins + 1)
    bornes = np.unique(reference.quantile(quantiles).values)
    if len(bornes) < 3:
        return 0.0
    bornes[0], bornes[-1] = -np.inf, np.inf

    pct_reference = pd.cut(reference, bins=bornes).value_counts(normalize=True).sort_index()
    pct_actuel = pd.cut(actuel, bins=bornes).value_counts(normalize=True).sort_index()

    epsilon = 1e-4
    pct_reference = pct_reference.clip(lower=epsilon)
    pct_actuel = pct_actuel.reindex(pct_reference.index, fill_value=0).clip(lower=epsilon)

    return round(float(((pct_actuel - pct_reference) * np.log(pct_actuel / pct_reference)).sum()), 4)
