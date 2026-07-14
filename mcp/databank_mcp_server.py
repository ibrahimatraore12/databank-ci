# Serveur MCP dataBank CI — expose 5 outils en lecture seule sur le portefeuille
# dataBank CI MCP server — exposes 5 read-only tools over the portfolio
#
# Toute connexion DuckDB ouverte par les outils est read_only=True (voir mcp/tools/*.py) :
# aucune écriture n'est possible depuis ce serveur.
# Every DuckDB connection opened by the tools is read_only=True (see mcp/tools/*.py):
# no write is possible from this server.

from mcp.server.fastmcp import FastMCP

from tools.complaints import get_complaint_analysis
from tools.customers import get_at_risk_customers, get_customer_profile
from tools.portfolio import get_cross_sell_candidates, get_portfolio_kpis

serveur = FastMCP("databank-ci")


@serveur.tool()
def outil_clients_a_risque(segment: str = None, limit: int = 10) -> list:
    """Retourne les clients les plus à risque de désengagement, triés par score décroissant."""
    return get_at_risk_customers(segment=segment, limit=limit)


@serveur.tool()
def outil_profil_client(customer_id: str) -> dict:
    """Retourne la fiche complète d'un client : profil, comportement, risque, action recommandée."""
    return get_customer_profile(customer_id=customer_id)


@serveur.tool()
def outil_candidats_cross_sell(offer_type: str = None, limit: int = 10) -> list:
    """Retourne les clients cibles de cross-sell ou d'upsell salaire."""
    return get_cross_sell_candidates(offer_type=offer_type, limit=limit)


@serveur.tool()
def outil_kpis_portefeuille(segment: str = None) -> dict:
    """Retourne les KPIs agrégés du portefeuille, globalement ou pour un segment donné."""
    return get_portfolio_kpis(segment=segment)


@serveur.tool()
def outil_analyse_reclamations(category: str = None) -> dict:
    """Retourne l'analyse des réclamations par sévérité et statut."""
    return get_complaint_analysis(category=category)


if __name__ == "__main__":
    serveur.run()
