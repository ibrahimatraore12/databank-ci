# Outils MCP liés aux clients : clients à risque et profil détaillé d'un client
# Customer-related MCP tools: at-risk customers and a detailed customer profile

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import duckdb  # noqa: E402

import config  # noqa: E402
from src.logger import log_event  # noqa: E402


def _connexion_lecture_seule() -> duckdb.DuckDBPyConnection:
    # Connexion DuckDB toujours en lecture seule — aucune écriture possible depuis le MCP
    # DuckDB connection always read-only — no write possible from the MCP server
    return duckdb.connect(config.DUCKDB_PATH, read_only=True)


def get_at_risk_customers(segment: str = None, limit: int = 10) -> list:
    # Retourne les clients les plus à risque, triés par score de risque composite décroissant
    # Returns the highest-risk customers, sorted by descending composite risk score
    try:
        connection = _connexion_lecture_seule()
        colonnes = """customer_id, full_name, segment, city, risque_composite,
                      recency_jours, nb_reclamations_ouvertes"""
        if segment:
            sql = f"""SELECT {colonnes} FROM main_marts.customer_360
                      WHERE segment = ? ORDER BY risque_composite DESC LIMIT ?"""
            resultat = connection.execute(sql, [segment, int(limit)]).fetchdf()
        else:
            sql = f"""SELECT {colonnes} FROM main_marts.customer_360
                      ORDER BY risque_composite DESC LIMIT ?"""
            resultat = connection.execute(sql, [int(limit)]).fetchdf()
        connection.close()

        log_event("api", "INFO", "[MCP][get_at_risk_customers] OK", {"segment": segment, "limit": limit})
        return resultat.to_dict(orient="records")
    except Exception as error:
        log_event("api", "ERROR", "[MCP][get_at_risk_customers] ECHEC", {"erreur": str(error)})
        raise


def get_customer_profile(customer_id: str) -> dict:
    # Retourne la fiche complète d'un client : profil, comportement, risque, action recommandée
    # Returns a customer's full record: profile, behavior, risk, recommended action
    try:
        connection = _connexion_lecture_seule()
        sql = """
            SELECT c.*, n.next_best_action
            FROM main_marts.customer_360 c
            LEFT JOIN main_marts.nba n ON c.customer_id = n.customer_id
            WHERE c.customer_id = ?
        """
        resultat = connection.execute(sql, [customer_id]).fetchdf()
        connection.close()

        log_event("api", "INFO", "[MCP][get_customer_profile] OK", {"customer_id": customer_id})
        return {} if resultat.empty else resultat.iloc[0].to_dict()
    except Exception as error:
        log_event("api", "ERROR", "[MCP][get_customer_profile] ECHEC", {"erreur": str(error)})
        raise
