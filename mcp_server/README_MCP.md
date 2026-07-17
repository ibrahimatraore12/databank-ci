# Serveur MCP - dataBank CI Customer 360

> *[English version: [README_MCP_en.md](README_MCP_en.md)]*

Un serveur MCP (Model Context Protocol) est un programme qui permet à un
assistant en langage naturel de poser des questions à une source de
données, ici le portefeuille de clients dataBank CI. Ce serveur propose 5
outils, tous en lecture seule : aucune écriture n'est possible depuis ce
serveur. Chaque connexion à DuckDB qu'il ouvre utilise l'option
`read_only=True`.

## Les outils disponibles

| Outil | Ce qu'il fait | Paramètres |
|-------|-------------|------------|
| `outil_clients_a_risque` | Liste les clients les plus à risque de désengagement | `segment` (facultatif), `limit` (10 par défaut) |
| `outil_profil_client` | Donne la fiche complète d'un client | `customer_id` (obligatoire) |
| `outil_candidats_cross_sell` | Liste les clients ciblés pour une vente croisée ou une proposition de domiciliation de salaire | `offer_type` (facultatif), `limit` (10 par défaut) |
| `outil_kpis_portefeuille` | Donne les indicateurs clés agrégés du portefeuille | `segment` (facultatif) |
| `outil_analyse_reclamations` | Analyse les réclamations par gravité et par statut | `category` (facultatif) |

La logique de calcul de chaque outil se trouve dans
`mcp_server/tools/customers.py`, `mcp_server/tools/portfolio.py` et
`mcp_server/tools/complaints.py`. La page
`dashboard/pages/07_Assistant_IA.py` n'importe plus ces fichiers
directement : elle appelle le serveur MCP en ligne via
`dashboard/components/mcp_client.py`, par une vraie connexion HTTP
(protocole `streamable-http`). Les réponses passent donc réellement par le
protocole MCP, et non par un simple appel de fonction en mémoire.

## Lancer le serveur

```bash
cd databank-ci
pyenv activate databank-ci-env
python3 mcp_server/databank_mcp_server.py
```

Par défaut, le serveur communique via `stdio` (le mode de communication
standard du protocole MCP) : il attend qu'un client MCP se connecte
(Claude Desktop, Claude Code, etc., qui sont des exemples de logiciels
compatibles avec ce protocole). En production (sur Cloud Run), il
fonctionne en mode `streamable-http` :

```bash
MCP_TRANSPORT=streamable-http MCP_API_KEY=<clé> PORT=8080 python3 mcp_server/databank_mcp_server.py
```

Dans ce mode, chaque requête HTTP doit alors contenir l'en-tête
`X-API-Key: <clé>` pour prouver qu'elle est autorisée. Voir la classe
`ApiKeyMiddleware` dans `databank_mcp_server.py`.

## Configuration côté client (exemple avec Claude Desktop, en local)

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

## Sauvegarde des données et remise à jour

Ce serveur lit le fichier `dbt_project/databank_ci.duckdb` en lecture
seule. Ce fichier n'est pas figé une fois pour toutes : voir
`src/storage_sync.py` et la section "Comment les données sont conservées"
de `docs/architecture.md` pour le fonctionnement complet. En résumé :

- Au démarrage du programme, la fonction `telecharger_depuis_gcs()` est
  appelée une seule fois (ligne 41 de `databank_mcp_server.py`). Si
  l'espace de stockage GCS contient une version compatible (même numéro de
  version de schéma), les fichiers locaux sont remplacés par cette version
  avant que le serveur ne commence à répondre aux questions.
- Une route interne `POST /admin/resync` (protégée par la même
  vérification `ApiKeyMiddleware` que le reste du serveur) permet de
  redéclencher ce téléchargement sans avoir à redémarrer le programme.
  C'est cette route qu'appelle
  `dashboard/components/mcp_client.py::resynchroniser_mcp()` juste après
  qu'un recalcul, lancé depuis l'onglet Administration, a été sauvegardé
  dans GCS. Cela permet aux réponses de l'Assistant IA de refléter les
  données les plus récentes, sans attendre le prochain redémarrage naturel
  de ce service.

## Note technique

Le dossier a été nommé `mcp_server/` (et non simplement `mcp/`) pour une
raison précise : éviter toute confusion avec le paquet Python `mcp`
installé via `pip install mcp` (le kit de développement officiel du
protocole MCP). Le tableau de bord Streamlit ajoute le dossier racine du
projet à son chemin de recherche Python (`sys.path`). Si le dossier
s'était appelé `mcp/`, il aurait masqué le vrai paquet officiel dès que le
tableau de bord aurait essayé de faire `import mcp` pour parler au serveur
distant.
