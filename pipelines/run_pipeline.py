# Orchestration principale : Bronze (réel + synthétique) -> features enrichies -> DuckDB
# Main orchestration: Bronze (real + synthetic) -> enriched features -> DuckDB
#
# Rejouable à l'infini : nettoie ses sorties avant de les recréer (idempotence)
# Infinitely replayable: cleans its outputs before recreating them (idempotence)

import json
import os
import sys
from datetime import datetime, timezone

import duckdb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from src.data_enrichment import generate_nbi_estime, generate_score_engagement  # noqa: E402
from src.ingest import load_source_tables  # noqa: E402
from src.logger import log_event  # noqa: E402
from src.synthetic_data_generator import generate_synthetic_customers  # noqa: E402


def update_pipeline_state(step: str, status: str) -> None:
    # Met à jour pipeline_state.json à chaque étape franchie
    # Updates pipeline_state.json after every completed step
    state = {}
    if os.path.exists(config.PIPELINE_STATE_PATH):
        with open(config.PIPELINE_STATE_PATH, "r") as f:
            state = json.load(f)

    state.setdefault("steps", {})
    state["steps"][step] = status
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    state["schema_version"] = config.DATA_SCHEMA_VERSION

    with open(config.PIPELINE_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def clean_outputs() -> None:
    # Nettoie les sorties précédentes avant de les recréer (idempotence, règle 11)
    # Cleans previous outputs before recreating them (idempotence, rule 11)
    os.makedirs(config.DATA_ENRICHED_DIR, exist_ok=True)
    for filename in os.listdir(config.DATA_ENRICHED_DIR):
        os.remove(os.path.join(config.DATA_ENRICHED_DIR, filename))
    log_event("pipeline", "INFO", "[PIPELINE][CLEAN] OK", {"dossier": config.DATA_ENRICHED_DIR})


def save_bronze_to_duckdb(tables_reelles: dict, tables_synthetiques: dict) -> None:
    # Charge Bronze réel (is_synthetic=False) et Bronze synthétique dans DuckDB,
    # prêts à être combinés par UNION ALL dans les modèles staging dbt
    # Loads real Bronze (is_synthetic=False) and synthetic Bronze into DuckDB,
    # ready to be combined via UNION ALL in dbt staging models
    os.makedirs(os.path.dirname(config.DUCKDB_PATH), exist_ok=True)
    connection = duckdb.connect(config.DUCKDB_PATH)

    for nom in config.SOURCE_SHEETS:
        df_reel = tables_reelles[nom].copy()
        if "is_synthetic" not in df_reel.columns:
            df_reel["is_synthetic"] = False
        connection.execute(f"CREATE OR REPLACE TABLE bronze_{nom.lower()} AS SELECT * FROM df_reel")

        # Lu par DuckDB via la requête ci-dessous, pas directement en Python
        # Read by DuckDB via the query below, not directly in Python
        df_synth = tables_synthetiques[nom]  # noqa: F841
        connection.execute(f"CREATE OR REPLACE TABLE bronze_synthetic_{nom.lower()} AS SELECT * FROM df_synth")

    connection.close()
    log_event("pipeline", "INFO", "[BRONZE][DUCKDB] OK", {"tables": len(config.SOURCE_SHEETS) * 2})


def save_enriched_outputs(score_engagement, nbi_estime, tables_synthetiques: dict) -> None:
    # Écrit les features calculées et le dataset synthétique dans data/enriched/
    # Writes computed features and the synthetic dataset to data/enriched/
    score_engagement.to_csv(os.path.join(config.DATA_ENRICHED_DIR, "score_engagement.csv"), index=False)
    nbi_estime.to_csv(os.path.join(config.DATA_ENRICHED_DIR, "nbi_estime.csv"), index=False)

    chemin_xlsx = os.path.join(config.DATA_ENRICHED_DIR, "synthetic_dataset.xlsx")
    with __import__("pandas").ExcelWriter(chemin_xlsx) as writer:
        for nom, df in tables_synthetiques.items():
            df.to_excel(writer, sheet_name=nom, index=False)

    log_event("pipeline", "INFO", "[ENRICHMENT][SAVE] OK", {"dossier": config.DATA_ENRICHED_DIR})


def run_pipeline() -> None:
    # Point d'entrée de l'orchestration complète Bronze + enrichissement
    # Entry point for the full Bronze + enrichment orchestration
    try:
        clean_outputs()
        update_pipeline_state("clean", "OK")

        tables_reelles = load_source_tables()
        update_pipeline_state("ingestion", "OK")

        score_engagement = generate_score_engagement(
            tables_reelles["Customers"], tables_reelles["Transactions"],
            tables_reelles["Accounts"], tables_reelles["Interactions"],
        )
        nbi_estime = generate_nbi_estime(
            tables_reelles["Customers"], tables_reelles["Accounts"], tables_reelles["Transactions"],
        )
        update_pipeline_state("enrichment", "OK")

        tables_synthetiques = generate_synthetic_customers(
            tables_reelles, n=config.SYNTHETIC_N_CUSTOMERS,
            churn_rate=config.SYNTHETIC_CHURN_RATE, seed=config.RANDOM_SEED,
        )
        update_pipeline_state("synthetic", "OK")

        save_enriched_outputs(score_engagement, nbi_estime, tables_synthetiques)
        save_bronze_to_duckdb(tables_reelles, tables_synthetiques)
        update_pipeline_state("bronze_load", "OK")

        log_event("pipeline", "INFO", "[PIPELINE][RUN] OK", {"statut": "SUCCESS"})
    except Exception as error:
        update_pipeline_state("pipeline", "FAILED")
        log_event("pipeline", "ERROR", "[PIPELINE][RUN] ECHEC", {"erreur": str(error)})
        raise


if __name__ == "__main__":
    run_pipeline()
