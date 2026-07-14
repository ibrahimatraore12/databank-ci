# Validation de la qualité des données à l'ingestion
# Data quality validation at ingestion time

import pandas as pd

from src.logger import log_event


def validate_dataframe(df: pd.DataFrame, table_name: str, required_columns: list = None) -> dict:
    # Vérifie qu'une table n'est pas vide, ne contient pas de colonnes requises manquantes,
    # et mesure son taux de valeurs nulles. Log le résultat, ne lève jamais silencieusement.
    # Checks a table is not empty, has no missing required columns, and measures its null
    # rate. Logs the result, never fails silently.
    try:
        erreurs = []

        if df.empty:
            erreurs.append("table vide")

        if required_columns:
            manquantes = [c for c in required_columns if c not in df.columns]
            if manquantes:
                erreurs.append(f"colonnes manquantes: {manquantes}")

        taux_nuls = round(100 * df.isna().sum().sum() / max(df.size, 1), 2)
        rapport = {"table": table_name, "lignes": len(df), "taux_nuls_pct": taux_nuls, "erreurs": erreurs}

        if erreurs:
            log_event("pipeline", "ERROR", f"[VALIDATION][{table_name}] ECHEC", rapport)
            raise ValueError(f"Validation échouée pour {table_name}: {erreurs}")

        log_event("pipeline", "INFO", f"[VALIDATION][{table_name}] OK", rapport)
        return rapport
    except ValueError:
        raise
    except Exception as error:
        log_event("pipeline", "ERROR", f"[VALIDATION][{table_name}] ERREUR INATTENDUE", {"erreur": str(error)})
        raise
