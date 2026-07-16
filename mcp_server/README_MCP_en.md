# MCP Server — dataBank CI Customer 360

> *[Version française disponible : [README_MCP.md](README_MCP.md)]*

MCP (Model Context Protocol) server exposing 5 read-only tools over the
dataBank CI portfolio. Every DuckDB connection opened by the tools is
`read_only=True` — no write is possible from this server.

## Exposed tools

| Tool | Description | Parameters |
|-------|-------------|------------|
| `outil_clients_a_risque` | Customers most at risk of disengagement | `segment` (optional), `limit` (default 10) |
| `outil_profil_client` | Full profile of a customer | `customer_id` (required) |
| `outil_candidats_cross_sell` | Cross-sell / salary upsell target customers | `offer_type` (optional), `limit` (default 10) |
| `outil_kpis_portefeuille` | Aggregated portfolio KPIs | `segment` (optional) |
| `outil_analyse_reclamations` | Complaint analysis by severity and status | `category` (optional) |

Each tool's business logic lives in `mcp_server/tools/customers.py`,
`mcp_server/tools/portfolio.py` and `mcp_server/tools/complaints.py`. The
`dashboard/pages/07_Assistant_IA.py` page no longer imports these modules
directly: it calls the deployed MCP server through
`dashboard/components/mcp_client.py`, over HTTP (`streamable-http`
transport), so responses genuinely go through the MCP protocol rather than
an in-memory function call.

## Running the server

```bash
cd databank-ci
pyenv activate databank-ci-env
python3 mcp_server/databank_mcp_server.py
```

By default the server communicates over stdio (standard MCP protocol) — it
waits for a connection from an MCP client (Claude Desktop, Claude Code,
etc.). In production (Cloud Run), it runs in `streamable-http` mode:

```bash
MCP_TRANSPORT=streamable-http MCP_API_KEY=<key> PORT=8080 python3 mcp_server/databank_mcp_server.py
```

Each HTTP request must then carry the `X-API-Key: <key>` header — see
`ApiKeyMiddleware` in `databank_mcp_server.py`.

## Client configuration (Claude Desktop example, local)

```json
{
  "mcpServers": {
    "databank-ci": {
      "command": "python3",
      "args": ["/absolute/path/to/databank-ci/mcp_server/databank_mcp_server.py"]
    }
  }
}
```

## Implementation note

The folder was renamed to `mcp_server/` (rather than `mcp/`) specifically
to avoid any collision with the `mcp` Python package installed via
`pip install mcp` (the official SDK): the Streamlit dashboard adds the
project root to `sys.path`, and an `mcp/` folder at the root would have
shadowed the real SDK as soon as the dashboard tried `import mcp` to talk
to the remote server.
