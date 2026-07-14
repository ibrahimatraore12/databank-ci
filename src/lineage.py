# Traçabilité et lignage des données — met à jour lineage.json à chaque ingestion
# Data traceability and lineage — updates lineage.json on every ingestion

import json
import os
from datetime import datetime, timezone

import config
from src.logger import log_event


def load_lineage() -> dict:
    # Charge le fichier de lignage existant, ou un dict vide s'il n'existe pas encore
    # Loads the existing lineage file, or an empty dict if it doesn't exist yet
    if not os.path.exists(config.LINEAGE_PATH):
        return {}
    with open(config.LINEAGE_PATH, "r") as f:
        return json.load(f)


def update_lineage(table_name: str, source: str, row_count: int, is_synthetic: bool = False) -> None:
    # Enregistre la provenance et le volume d'une table à chaque ingestion/transformation
    # Records the provenance and row count of a table on every ingestion/transformation
    try:
        lineage = load_lineage()
        lineage[table_name] = {
            "source": source,
            "row_count": row_count,
            "is_synthetic": is_synthetic,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(config.LINEAGE_PATH, "w") as f:
            json.dump(lineage, f, indent=2, ensure_ascii=False)
        log_event("pipeline", "INFO", f"[LINEAGE][{table_name}] OK", {"lignes": row_count, "synthetic": is_synthetic})
    except Exception as error:
        log_event("pipeline", "ERROR", f"[LINEAGE][{table_name}] ECHEC", {"erreur": str(error)})
        raise
