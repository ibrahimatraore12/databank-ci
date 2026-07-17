# Outil MCP lié aux réclamations : analyse par sévérité, statut et taux de résolution
# Complaint-related MCP tool: analysis by severity, status, and resolution rate

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import duckdb  # noqa: E402

import config  # noqa: E402
from src.logger import log_event  # noqa: E402


def _connexion_lecture_seule() -> duckdb.DuckDBPyConnection:
    # Connexion DuckDB toujours en lecture seule - aucune écriture possible depuis le MCP
    # DuckDB connection always read-only - no write possible from the MCP server
    return duckdb.connect(config.DUCKDB_PATH, read_only=True)


def get_complaint_analysis(category: str = None) -> dict:
    # Analyse des réclamations : répartition par sévérité et statut, total, taux de résolution
    # Complaint analysis: breakdown by severity and status, total, resolution rate
    try:
        connection = _connexion_lecture_seule()
        if category:
            sql = """
                SELECT severity, status, count(*) AS nb_reclamations
                FROM main_staging.stg_complaints
                WHERE category = ?
                GROUP BY severity, status
                ORDER BY severity, status
            """
            resultat = connection.execute(sql, [category]).fetchdf()
        else:
            sql = """
                SELECT severity, status, count(*) AS nb_reclamations
                FROM main_staging.stg_complaints
                GROUP BY severity, status
                ORDER BY severity, status
            """
            resultat = connection.execute(sql).fetchdf()
        connection.close()

        log_event("api", "INFO", "[MCP][get_complaint_analysis] OK", {"category": category})
        return {
            "detail": resultat.to_dict(orient="records"),
            "total": int(resultat["nb_reclamations"].sum()) if not resultat.empty else 0,
        }
    except Exception as error:
        log_event("api", "ERROR", "[MCP][get_complaint_analysis] ECHEC", {"erreur": str(error)})
        raise
