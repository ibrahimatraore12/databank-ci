# Serveur MCP — dataBank CI Customer 360

Serveur MCP (Model Context Protocol) exposant 5 outils en lecture seule sur
le portefeuille dataBank CI. Toute connexion DuckDB ouverte par les outils
est `read_only=True` — aucune écriture n'est possible depuis ce serveur.

## Outils exposés

| Outil | Description | Paramètres |
|-------|-------------|------------|
| `outil_clients_a_risque` | Clients les plus à risque de désengagement | `segment` (optionnel), `limit` (défaut 10) |
| `outil_profil_client` | Fiche complète d'un client | `customer_id` (obligatoire) |
| `outil_candidats_cross_sell` | Clients cibles de cross-sell / upsell salaire | `offer_type` (optionnel), `limit` (défaut 10) |
| `outil_kpis_portefeuille` | KPIs agrégés du portefeuille | `segment` (optionnel) |
| `outil_analyse_reclamations` | Analyse des réclamations par sévérité et statut | `category` (optionnel) |

La logique métier de chaque outil vit dans `mcp/tools/customers.py`,
`mcp/tools/portfolio.py` et `mcp/tools/complaints.py` — ces modules sont
utilisés à la fois par le serveur MCP et par la page
`dashboard/pages/07_Assistant_IA.py`, pour ne jamais dupliquer les requêtes.

## Lancer le serveur

```bash
cd databank-ci
pyenv activate databank-ci-env
python3 mcp/databank_mcp_server.py
```

Le serveur communique en stdio (protocole MCP standard) — il attend une
connexion d'un client MCP (Claude Desktop, Claude Code, etc.).

## Configuration client (exemple Claude Desktop)

```json
{
  "mcpServers": {
    "databank-ci": {
      "command": "python3",
      "args": ["/chemin/absolu/vers/databank-ci/mcp/databank_mcp_server.py"]
    }
  }
}
```

## Note d'implémentation

Le dossier s'appelle `mcp/`, comme le paquet Python `mcp` installé via
`pip install mcp` (le SDK officiel). Pour éviter toute collision de nom :
- `databank_mcp_server.py` importe le SDK (`from mcp.server.fastmcp import FastMCP`)
  avant toute manipulation de `sys.path`, donc la résolution du nom `mcp`
  pointe sans ambiguïté vers le SDK installé dans l'environnement.
- Les imports internes au serveur utilisent des chemins relatifs au dossier
  (`from tools.customers import ...`), jamais `from mcp.tools... import ...`.
