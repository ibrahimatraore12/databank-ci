# Chargement et préparation du jeu de données pour le pipeline ML
# Loading and preparing the dataset for the ML pipeline

import duckdb
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

import config
from ml.registry import load_preprocessor, save_preprocessor
from src.logger import log_event

# Features numériques utilisées par le modèle - risque_composite est exclu
# volontairement pour éviter la fuite de label (il partage les mêmes signaux
# que le label enrichi calculé ci-dessous)
# Numeric features used by the model - risque_composite is deliberately
# excluded to avoid label leakage (it shares the same signals as the
# enriched label computed below)
FEATURE_COLUMNS = [
    "recency_jours", "tendance_transactions", "nb_reclamations_ouvertes",
    "nb_reclamations_total", "score_digital", "nb_comptes", "nb_cartes",
    "nb_produits_total", "monthly_income_xof",
]


def load_data(path: str = config.DUCKDB_PATH, use_synthetic: bool = True) -> pd.DataFrame:
    # Charge le mart customer_360 depuis DuckDB et calcule le label enrichi à 4 critères
    # Loads the customer_360 mart from DuckDB and computes the 4-criteria enriched label
    try:
        connection = duckdb.connect(path, read_only=True)
        df = connection.execute("SELECT * FROM main_marts.customer_360").fetchdf()
        connection.close()

        if not use_synthetic:
            df = df[~df["is_synthetic"]].reset_index(drop=True)

        criteres_actifs = (
            (df["recency_jours"] > config.CHURN_RISK_RECENCY_THRESHOLD_DAYS).astype(int)
            + (df["nb_reclamations_ouvertes"] > 0).astype(int)
            + (df["tendance_transactions"] < 0).astype(int)
            + (df["score_digital"] <= 1).astype(int)
        )
        df["churn_flag"] = (criteres_actifs >= 2).astype(int)

        log_event("ml", "INFO", "[ML][load_data] OK", {
            "lignes": len(df), "positifs": int(df["churn_flag"].sum()), "use_synthetic": use_synthetic,
        })
        return df
    except Exception as error:
        log_event("ml", "ERROR", "[ML][load_data] ECHEC", {"erreur": str(error)})
        raise


def get_X_y(df: pd.DataFrame, target: str = "churn_flag") -> tuple:
    # Sépare les features numériques (sans fuite de label) de la cible
    # Separates the numeric features (no label leakage) from the target
    X = df[FEATURE_COLUMNS].fillna(0).copy()
    y = df[target].copy()
    return X, y


def split_data(
    X: pd.DataFrame, y: pd.Series, test_size: float = 0.2, random_state: int = config.RANDOM_SEED,
) -> tuple:
    # Split stratifié obligatoire pour préserver le taux de positifs dans les deux jeux
    # Stratified split mandatory to preserve the positive rate in both sets
    return train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)


def preprocess_data(X: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
    # fit=True : ajuste un nouveau scaler sur X et le sauvegarde dans le registre
    # fit=False : recharge le scaler déjà ajusté pour transformer X
    # fit=True: fits a new scaler on X and saves it to the registry
    # fit=False: reloads the already-fitted scaler to transform X
    if fit:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        save_preprocessor(scaler)
    else:
        scaler = load_preprocessor()
        X_scaled = scaler.transform(X)

    return pd.DataFrame(X_scaled, columns=X.columns, index=X.index)
