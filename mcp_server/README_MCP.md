# Serveur MCP — dataBank CI Customer 360

> *[English version: [README_MCP_en.md](README_MCP_en.md)]*

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

La logique métier de chaque outil vit dans `mcp_server/tools/customers.py`,
`mcp_server/tools/portfolio.py` et `mcp_server/tools/complaints.py`. La page
`dashboard/pages/07_Assistant_IA.py` n'importe plus ces modules directement :
elle appelle le serveur MCP déployé via `dashboard/components/mcp_client.py`,
en HTTP (transport `streamable-http`), pour que les réponses passent
réellement par le protocole MCP plutôt que par un appel de fonction en
mémoire.

## Lancer le serveur

```bash
cd databank-ci
pyenv activate databank-ci-env
python3 mcp_server/databank_mcp_server.py
```

Par défaut le serveur communique en stdio (protocole MCP standard) — il
attend une connexion d'un client MCP (Claude Desktop, Claude Code, etc.).
En production (Cloud Run), il tourne en `streamable-http` :

```bash
MCP_TRANSPORT=streamable-http MCP_API_KEY=<clé> PORT=8080 python3 mcp_server/databank_mcp_server.py
```

Chaque requête HTTP doit alors porter l'en-tête `X-API-Key: <clé>` — voir
`ApiKeyMiddleware` dans `databank_mcp_server.py`.

## Configuration client (exemple Claude Desktop, en local)

```json
{
  "mcpServers": {
    "databank-ci": {
      "command": "python3",
      "args": ["/chemin/absolu/vers/databank-ci/mcp_server/databank_mcp_server.py"]
    }
  }
}
```

## Persistance des données et resynchronisation

Ce serveur lit `dbt_project/databank_ci.duckdb` en lecture seule. Ce fichier
n'est pas fixe : voir `src/storage_sync.py` et `docs/architecture.md` (section
"Persistance des données") pour le mécanisme complet. En résumé :

- Au démarrage du processus, `telecharger_depuis_gcs()` est appelée une fois
  (ligne 41 de `databank_mcp_server.py`) : si le bucket GCS contient une
  version compatible (même `schema_version`), les fichiers locaux sont
  remplacés par cette version avant que le serveur ne commence à répondre.
- Une route interne `POST /admin/resync` (protégée par le même
  `ApiKeyMiddleware` que le reste du transport HTTP) permet de redéclencher
  ce téléchargement sans redémarrer le processus. C'est ce qu'appelle
  `dashboard/components/mcp_client.py::resynchroniser_mcp()` juste après
  qu'un recalcul déclenché depuis l'onglet Administration a été persisté
  dans GCS — pour que les réponses de l'Assistant IA reflètent les données
  fraîches sans attendre le prochain redémarrage naturel de ce service.

## Note d'implémentation

Le dossier a été renommé `mcp_server/` (et non `mcp/`) précisément pour
éviter toute collision avec le paquet Python `mcp` installé via
`pip install mcp` (le SDK officiel) : le dashboard Streamlit ajoute la
racine du projet à `sys.path`, et un dossier `mcp/` à la racine aurait
shadowé le vrai SDK dès que le dashboard aurait tenté `import mcp` pour
parler au serveur distant.
