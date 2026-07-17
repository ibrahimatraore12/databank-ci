# Outils MCP liés au portefeuille : candidats cross-sell et KPIs agrégés
# Portfolio-related MCP tools: cross-sell candidates and aggregated KPIs

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


def get_cross_sell_candidates(offer_type: str = None, limit: int = 10) -> list:
    # Retourne les clients cibles de cross-sell/upsell, optionnellement filtrés par offre déjà proposée
    # Returns cross-sell/upsell target customers, optionally filtered by an offer already proposed
    try:
        connection = _connexion_lecture_seule()
        if offer_type:
            sql = """
                SELECT DISTINCT c.customer_id, c.full_name, c.segment, c.city, c.monthly_income_xof
                FROM main_marts.customer_360 c
                JOIN main_staging.stg_offers o ON c.customer_id = o.customer_id
                WHERE (c.is_cross_sell_target OR c.is_salary_upsell_opportunity) AND o.offer_type = ?
                LIMIT ?
            """
            resultat = connection.execute(sql, [offer_type, int(limit)]).fetchdf()
        else:
            sql = """
                SELECT customer_id, full_name, segment, city, monthly_income_xof
                FROM main_marts.customer_360
                WHERE is_cross_sell_target OR is_salary_upsell_opportunity
                LIMIT ?
            """
            resultat = connection.execute(sql, [int(limit)]).fetchdf()
        connection.close()

        log_event("api", "INFO", "[MCP][get_cross_sell_candidates] OK", {"offer_type": offer_type, "limit": limit})
        return resultat.to_dict(orient="records")
    except Exception as error:
        log_event("api", "ERROR", "[MCP][get_cross_sell_candidates] ECHEC", {"erreur": str(error)})
        raise


def get_portfolio_kpis(segment: str = None) -> dict:
    # Retourne les KPIs agrégés du portefeuille, globalement ou pour un segment donné
    # Returns the portfolio's aggregated KPIs, overall or for a given segment
    try:
        connection = _connexion_lecture_seule()
        if segment:
            sql = "SELECT * FROM main_marts.customer_segments WHERE segment = ?"
            resultat = connection.execute(sql, [segment]).fetchdf()
        else:
            sql = """
                SELECT
                    count(*) AS nb_clients,
                    round(avg(risque_composite), 1) AS risque_composite_moyen,
                    sum(CASE WHEN is_high_value_at_risk THEN 1 ELSE 0 END) AS nb_high_value_at_risk,
                    sum(CASE WHEN is_cross_sell_target THEN 1 ELSE 0 END) AS nb_cross_sell_target,
                    round(100.0 * avg(CASE WHEN salaire_domicilie THEN 1 ELSE 0 END), 1) AS taux_salaire_domicilie_pct
                FROM main_marts.customer_360
            """
            resultat = connection.execute(sql).fetchdf()
        connection.close()

        log_event("api", "INFO", "[MCP][get_portfolio_kpis] OK", {"segment": segment})
        return {} if resultat.empty else resultat.iloc[0].to_dict()
    except Exception as error:
        log_event("api", "ERROR", "[MCP][get_portfolio_kpis] ECHEC", {"erreur": str(error)})
        raise
