# Client MCP du dashboard — appelle le serveur MCP déployé en HTTP
# (transport streamable-http) au lieu d'importer les outils en mémoire,
# pour que les réponses passent réellement par le protocole MCP.
# Dashboard's MCP client — calls the deployed MCP server over HTTP
# (streamable-http transport) instead of importing the tools in-process,
# so answers actually go through the MCP protocol.

import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL")
MCP_API_KEY = os.environ.get("MCP_API_KEY")


async def _appeler_outil_async(nom_outil: str, arguments: dict) -> list:
    headers = {"X-API-Key": MCP_API_KEY} if MCP_API_KEY else None
    async with streamablehttp_client(MCP_SERVER_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resultat = await session.call_tool(nom_outil, arguments)
            if resultat.isError:
                message = resultat.content[0].text if resultat.content else "Erreur MCP inconnue"
                raise RuntimeError(message)
            return [json.loads(bloc.text) for bloc in resultat.content]


def appeler_outil(nom_outil: str, **arguments) -> list:
    """Appelle un outil MCP distant et retourne la liste des blocs désérialisés.

    FastMCP sérialise chaque élément d'une liste Python en un bloc de contenu
    séparé (un outil retournant 10 clients renvoie 10 blocs, pas un tableau
    JSON unique) : pour les outils qui retournent un dict (KPIs, profil...),
    prendre le premier élément de la liste renvoyée ici.
    """
    if not MCP_SERVER_URL:
        raise RuntimeError("MCP_SERVER_URL n'est pas configuré.")
    return asyncio.run(_appeler_outil_async(nom_outil, arguments))
