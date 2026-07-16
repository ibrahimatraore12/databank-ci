# Serveur MCP dataBank CI — expose 5 outils en lecture seule sur le portefeuille
# dataBank CI MCP server — exposes 5 read-only tools over the portfolio
#
# Toute connexion DuckDB ouverte par les outils est read_only=True (voir mcp_server/tools/*.py) :
# aucune écriture n'est possible depuis ce serveur.
# Every DuckDB connection opened by the tools is read_only=True (see mcp_server/tools/*.py):
# no write is possible from this server.
#
# Transport : stdio en local (Claude Desktop, Claude Code) — streamable-http
# quand déployé sur Cloud Run, piloté par les variables MCP_TRANSPORT et PORT
# Transport: stdio locally (Claude Desktop, Claude Code) — streamable-http
# when deployed to Cloud Run, driven by the MCP_TRANSPORT and PORT variables

import os
import sys

# Nécessaire ici (contrairement à tools/*.py qui l'ajoutent déjà chacun) car ce
# fichier importe src.storage_sync avant tout import de tools.*, qui est ce qui
# ajoutait jusqu'ici la racine du projet à sys.path comme effet de bord
# Needed here (unlike tools/*.py, which each already add it) because this file
# imports src.storage_sync before any tools.* import, which is what used to add
# the project root to sys.path as a side effect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402

from src.storage_sync import telecharger_depuis_gcs  # noqa: E402
from tools.complaints import get_complaint_analysis  # noqa: E402
from tools.customers import get_at_risk_customers, get_customer_profile  # noqa: E402
from tools.portfolio import get_cross_sell_candidates, get_portfolio_kpis  # noqa: E402

TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")
PORT = int(os.environ.get("PORT", 8080))
API_KEY = os.environ.get("MCP_API_KEY")

# Processus long-vivant (pas de ré-exécution répétée comme Streamlit) : un
# appel simple au chargement suffit, pas besoin d'équivalent à st.cache_resource
# Long-lived process (no repeated re-execution like Streamlit): a plain call
# at load time is enough, no st.cache_resource equivalent needed
telecharger_depuis_gcs()

serveur = FastMCP("databank-ci", host="0.0.0.0", port=PORT)


class ApiKeyMiddleware:
    """Exige l'en-tête X-API-Key sur le transport HTTP public ; ignoré en stdio."""

    def __init__(self, app, api_key: str):
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            provided = headers.get(b"x-api-key", b"").decode()
            if provided != self.api_key:
                response = JSONResponse({"error": "unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


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
    if TRANSPORT == "streamable-http":
        import uvicorn

        app = serveur.streamable_http_app()
        if API_KEY:
            app = ApiKeyMiddleware(app, API_KEY)
        uvicorn.run(app, host="0.0.0.0", port=PORT)
    else:
        serveur.run(transport=TRANSPORT)
