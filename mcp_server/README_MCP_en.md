# MCP Server - dataBank CI Customer 360

> *[Version française disponible : [README_MCP.md](README_MCP.md)]*

An MCP (Model Context Protocol) server is a program that lets a
plain-language assistant ask questions to a data source, here the
dataBank CI customer portfolio. This server offers 5 tools, all
read-only: no write is possible from this server. Every DuckDB connection
it opens uses the `read_only=True` option.

## Available tools

| Tool | What it does | Parameters |
|-------|-------------|------------|
| `outil_clients_a_risque` | Lists the customers most at risk of disengagement | `segment` (optional), `limit` (default 10) |
| `outil_profil_client` | Returns a customer's full profile | `customer_id` (required) |
| `outil_candidats_cross_sell` | Lists customers targeted for cross-sell or a salary domiciliation offer | `offer_type` (optional), `limit` (default 10) |
| `outil_kpis_portefeuille` | Returns aggregated key portfolio indicators | `segment` (optional) |
| `outil_analyse_reclamations` | Analyzes complaints by severity and status | `category` (optional) |

Each tool's calculation logic lives in `mcp_server/tools/customers.py`,
`mcp_server/tools/portfolio.py`, and `mcp_server/tools/complaints.py`. The
`dashboard/pages/07_Assistant_IA.py` page no longer imports these files
directly: it calls the live MCP server through
`dashboard/components/mcp_client.py`, over a real HTTP connection
(`streamable-http` protocol). Answers genuinely go through the MCP
protocol, not a plain in-memory function call.

## Running the server

```bash
cd databank-ci
pyenv activate databank-ci-env
python3 mcp_server/databank_mcp_server.py
```

By default, the server communicates via `stdio` (the standard
communication mode of the MCP protocol): it waits for an MCP client to
connect (Claude Desktop, Claude Code, etc. are examples of software
compatible with this protocol). In production (on Cloud Run), it runs in
`streamable-http` mode:

```bash
MCP_TRANSPORT=streamable-http MCP_API_KEY=<key> PORT=8080 python3 mcp_server/databank_mcp_server.py
```

In this mode, every HTTP request must carry the `X-API-Key: <key>` header
to prove it's authorized. See the `ApiKeyMiddleware` class in
`databank_mcp_server.py`.

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

## Data backup and resync

This server reads the `dbt_project/databank_ci.duckdb` file read-only.
This file isn't fixed once and for all: see `src/storage_sync.py` and the
"How data is kept safe" section of `docs/architecture_en.md` for the full
mechanism. In short:

- At program startup, the `telecharger_depuis_gcs()` function ("download
  from GCS") is called once (line 41 of `databank_mcp_server.py`). If the
  GCS storage space holds a compatible version (same schema version
  number), local files are replaced with that version before the server
  starts answering questions.
- An internal `POST /admin/resync` route (protected by the same
  `ApiKeyMiddleware` check as the rest of the server) lets that download
  be re-triggered without restarting the program. This is the route
  called by `dashboard/components/mcp_client.py::resynchroniser_mcp()`
  right after a recompute, launched from the Administration tab, has been
  saved to GCS. This lets the AI Assistant's answers reflect the most
  recent data, without waiting for this service's next natural restart.

## Technical note

The folder was named `mcp_server/` (rather than simply `mcp/`) for a
specific reason: to avoid any confusion with the `mcp` Python package
installed via `pip install mcp` (the official MCP protocol development
kit). The Streamlit dashboard adds the project's root folder to its
Python search path (`sys.path`). If the folder had been named `mcp/`, it
would have hidden the real official package as soon as the dashboard
tried `import mcp` to talk to the remote server.
