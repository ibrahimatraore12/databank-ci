# Score de règles métier — Phase 1 — toujours calculé, même sans modèle ML
# Business rule score — Phase 1 — always computed, even without an ML model

import pandas as pd

import config
from src.logger import log_event


def _normaliser_0_100(serie: pd.Series, sens_positif: bool = True) -> pd.Series:
    # Ramène une série numérique sur une échelle 0-100
    # Rescales a numeric series onto a 0-100 scale
    valeur_min, valeur_max = serie.min(), serie.max()
    if valeur_max == valeur_min:
        return pd.Series(50.0, index=serie.index)
    normalisee = (serie - valeur_min) / (valeur_max - valeur_min) * 100
    return normalisee if sens_positif else 100 - normalisee


def calculate_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    # Score 0-100 basé sur les 4 hypothèses métier : recency(40%) réclamations(30%)
    # digital(20%) tendance(10%). Attend un df déjà enrichi avec recency_jours,
    # nb_reclamations_ouvertes, score_digital, tendance_transactions (mart customer_360)
    # 0-100 score based on the 4 business hypotheses: recency(40%) complaints(30%)
    # digital(20%) trend(10%). Expects a df already enriched with those columns
    # (customer_360 mart)
    colonnes_requises = [
        "customer_id", "recency_jours", "nb_reclamations_ouvertes",
        "score_digital", "tendance_transactions",
    ]
    manquantes = [c for c in colonnes_requises if c not in df.columns]
    if manquantes:
        raise ValueError(f"calculate_risk_score: colonnes manquantes {manquantes}")

    # Recency et réclamations en relation directe (plus élevé = plus risqué) ;
    # digital et tendance en relation inverse (plus élevé = moins risqué)
    # Recency and complaints are a direct relation (higher = riskier);
    # digital and trend are an inverse relation (higher = less risky)
    score = (
        _normaliser_0_100(df["recency_jours"], sens_positif=True) * config.RULES_WEIGHT_RECENCY
        + _normaliser_0_100(df["nb_reclamations_ouvertes"], sens_positif=True) * config.RULES_WEIGHT_COMPLAINTS
        + _normaliser_0_100(df["score_digital"], sens_positif=False) * config.RULES_WEIGHT_DIGITAL
        + _normaliser_0_100(df["tendance_transactions"], sens_positif=False) * config.RULES_WEIGHT_TREND
    )

    resultat = pd.DataFrame({
        "customer_id": df["customer_id"].values,
        "score_regles": score.round(1).values,
    })
    log_event("ml", "INFO", "[RULES][calculate_risk_score] OK", {"lignes": len(resultat)})
    return resultat
