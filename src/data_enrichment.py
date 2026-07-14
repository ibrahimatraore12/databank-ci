# Calcul des features enrichies à partir des données réelles du portefeuille
# Computes enriched features from the real portfolio data

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


def generate_score_engagement(
    df_customers: pd.DataFrame,
    df_transactions: pd.DataFrame,
    df_accounts: pd.DataFrame,
    df_interactions: pd.DataFrame,
) -> pd.DataFrame:
    # Score composite d'engagement 0-100 : recency(30%), activité(25%), digital(25%), produits(20%)
    # Composite 0-100 engagement score: recency(30%), activity(25%), digital(25%), products(20%)
    # Pondération documentée dans docs/decisions.md
    date_reference = df_transactions["txn_datetime"].max()

    derniere_txn = df_transactions.groupby("customer_id")["txn_datetime"].max()
    recency_jours = (date_reference - derniere_txn).dt.days.reindex(df_customers["customer_id"])
    recency_jours = recency_jours.fillna(recency_jours.max())

    nb_transactions = df_transactions.groupby("customer_id").size().reindex(df_customers["customer_id"], fill_value=0)
    nb_interactions = df_interactions.groupby("customer_id").size().reindex(df_customers["customer_id"], fill_value=0)
    activite = nb_transactions + nb_interactions

    colonnes_digital = ["mobile_app_active", "internet_banking_active", "mobile_money_linked"]
    score_digital_brut = df_customers.set_index("customer_id")[colonnes_digital].sum(axis=1)

    nb_produits = df_accounts.groupby("customer_id").size().reindex(df_customers["customer_id"], fill_value=0)

    score = (
        _normaliser_0_100(recency_jours, sens_positif=False) * config.ENGAGEMENT_WEIGHT_RECENCY
        + _normaliser_0_100(activite, sens_positif=True) * config.ENGAGEMENT_WEIGHT_TRANSACTIONS
        + _normaliser_0_100(score_digital_brut, sens_positif=True) * config.ENGAGEMENT_WEIGHT_DIGITAL
        + _normaliser_0_100(nb_produits, sens_positif=True) * config.ENGAGEMENT_WEIGHT_PRODUCTS
    )

    resultat = pd.DataFrame({
        "customer_id": df_customers["customer_id"].values,
        "score_engagement": score.round(1).values,
    })
    log_event("pipeline", "INFO", "[ENRICHMENT][score_engagement] OK", {"lignes": len(resultat)})
    return resultat


def generate_nbi_estime(
    df_customers: pd.DataFrame,
    df_accounts: pd.DataFrame,
    df_transactions: pd.DataFrame,
) -> pd.DataFrame:
    # NBI estimé par formule UEMOA standard — n'est PAS le NBI comptable réel du client
    # Estimated NBI using the standard UEMOA formula — NOT the customer's real accounting NBI
    solde_par_client = df_accounts.groupby("customer_id")["avg_balance_90d_xof"].sum()
    solde_par_client = solde_par_client.reindex(df_customers["customer_id"], fill_value=0)

    nb_txn_par_client = df_transactions.groupby("customer_id").size()
    nb_txn_par_client = nb_txn_par_client.reindex(df_customers["customer_id"], fill_value=0)
    nb_produits_par_client = df_accounts.groupby("customer_id").size()
    nb_produits_par_client = nb_produits_par_client.reindex(df_customers["customer_id"], fill_value=0)

    nbi_estime = (
        solde_par_client * config.NBI_BALANCE_RATE
        + nb_txn_par_client * config.NBI_PER_TRANSACTION_XOF
        + nb_produits_par_client * config.NBI_PER_PRODUCT_XOF
    )

    resultat = pd.DataFrame({
        "customer_id": df_customers["customer_id"].values,
        "nbi_estime_xof": nbi_estime.round(0).values,
        "estimated_nbi_flag": True,
    })
    log_event("pipeline", "INFO", "[ENRICHMENT][nbi_estime] OK", {"lignes": len(resultat)})
    return resultat


def generate_risque_composite(df_customers: pd.DataFrame) -> pd.DataFrame:
    # Score de risque composite basé sur les 4 hypothèses métier (H1-H4, voir docs/decisions.md)
    # Composite risk score based on the 4 business hypotheses (H1-H4, see docs/decisions.md)
    # Attend un df_customers déjà enrichi en amont du pipeline avec les colonnes :
    # recency_jours, nb_reclamations_ouvertes, tendance_transactions, score_digital (0-3)
    # Expects a df_customers already enriched upstream in the pipeline with those columns
    colonnes_requises = [
        "customer_id", "recency_jours", "nb_reclamations_ouvertes",
        "tendance_transactions", "score_digital",
    ]
    manquantes = [c for c in colonnes_requises if c not in df_customers.columns]
    if manquantes:
        raise ValueError(f"generate_risque_composite: colonnes manquantes {manquantes}")

    # Sens du score de RISQUE : recency et réclamations en relation directe
    # (plus élevé = plus risqué), digital et tendance en relation inverse
    # Risk score direction: recency and complaints are a direct relation
    # (higher = riskier); digital and trend are an inverse relation
    sous_score_reclamations = _normaliser_0_100(df_customers["nb_reclamations_ouvertes"], sens_positif=True)
    score = (
        _normaliser_0_100(df_customers["recency_jours"], sens_positif=True) * config.RULES_WEIGHT_RECENCY
        + sous_score_reclamations * config.RULES_WEIGHT_COMPLAINTS
        + _normaliser_0_100(df_customers["score_digital"], sens_positif=False) * config.RULES_WEIGHT_DIGITAL
        + _normaliser_0_100(df_customers["tendance_transactions"], sens_positif=False) * config.RULES_WEIGHT_TREND
    )

    resultat = pd.DataFrame({
        "customer_id": df_customers["customer_id"].values,
        "risque_composite": score.round(1).values,
    })
    log_event("pipeline", "INFO", "[ENRICHMENT][risque_composite] OK", {"lignes": len(resultat)})
    return resultat
