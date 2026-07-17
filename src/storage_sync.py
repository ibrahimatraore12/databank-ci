# Persistance des fichiers de données sur Google Cloud Storage - Cloud Run
# n'a pas de disque persistant : un recalcul déclenché depuis l'onglet Admin
# ne modifie que l'instance en cours sans cette couche de synchronisation
# Data file persistence on Google Cloud Storage - Cloud Run has no
# persistent disk: a recompute triggered from the Admin tab only affects the
# current instance without this synchronization layer

import json
import os
import sqlite3
import tempfile

import config
from src.logger import log_event

GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

# Un fichier local par objet GCS ; mlflow.db est traité à part (copie sûre, voir plus bas)
# One local file per GCS object; mlflow.db is handled separately (safe copy, see below)
FICHIERS_SYNCHRONISES = {
    "databank_ci.duckdb": config.DUCKDB_PATH,
    "pipeline_state.json": config.PIPELINE_STATE_PATH,
    "lineage.json": config.LINEAGE_PATH,
    "model_comparison.md": os.path.join(config.PROJECT_ROOT, "docs", "model_comparison.md"),
    "starter_dataset.xlsx": config.SOURCE_EXCEL_PATH,
}
NOM_OBJET_MLFLOW = "mlflow.db"
CHEMIN_MLFLOW = os.path.join(config.PROJECT_ROOT, "mlflow.db")


def _client():
    from google.cloud import storage
    return storage.Client()


def telecharger_depuis_gcs() -> bool:
    # Au démarrage de chaque instance : si le bucket contient une version compatible
    # (même schema_version que le code courant), l'utiliser à la place des fichiers
    # bakés dans l'image. Ne lève jamais : une erreur ne doit pas bloquer le démarrage
    # On every instance startup: if the bucket holds a compatible version (same
    # schema_version as the current code), use it instead of the files baked into
    # the image. Never raises: an error must not block startup
    if not GCS_BUCKET_NAME:
        return False
    try:
        bucket = _client().bucket(GCS_BUCKET_NAME)

        blob_etat = bucket.blob("pipeline_state.json")
        if not blob_etat.exists():
            return False
        etat_distant = json.loads(blob_etat.download_as_bytes())
        if etat_distant.get("schema_version") != config.DATA_SCHEMA_VERSION:
            log_event("pipeline", "ERROR", "[GCS][SYNC] schema_version distant incompatible, image conservée", {
                "schema_version_distant": etat_distant.get("schema_version"),
                "schema_version_code": config.DATA_SCHEMA_VERSION,
            })
            return False

        for nom_objet, chemin_local in FICHIERS_SYNCHRONISES.items():
            blob = bucket.blob(nom_objet)
            if blob.exists():
                blob.download_to_filename(chemin_local)

        blob_mlflow = bucket.blob(NOM_OBJET_MLFLOW)
        if blob_mlflow.exists():
            blob_mlflow.download_to_filename(CHEMIN_MLFLOW)

        log_event("pipeline", "INFO", "[GCS][SYNC] Fichiers restaurés depuis le bucket", {"bucket": GCS_BUCKET_NAME})
        return True
    except Exception as erreur:
        log_event("pipeline", "ERROR", "[GCS][SYNC] Échec, conservation des fichiers de l'image",
                  {"erreur": str(erreur)})
        return False


def _copie_sqlite_sure(chemin_source: str) -> str:
    # sqlite3 Connection.backup() plutôt qu'une copie brute d'octets : mlflow garde un
    # pool de connexions ouvert dans le process, une copie brute risquerait de capturer
    # un état incohérent entre le fichier principal et son journal de rollback
    # sqlite3 Connection.backup() rather than a raw byte copy: mlflow keeps a
    # connection pool open in the process, a raw copy could capture an inconsistent
    # state between the main file and its rollback journal
    chemin_tmp = tempfile.mktemp(suffix=".db")
    source = sqlite3.connect(chemin_source)
    destination = sqlite3.connect(chemin_tmp)
    with destination:
        source.backup(destination)
    source.close()
    destination.close()
    return chemin_tmp


def televerser_vers_gcs() -> None:
    # Après un recalcul réussi : sauvegarde les fichiers produits pour qu'ils survivent
    # au redémarrage de cette instance et soient repris par toutes les autres. Lève en
    # cas d'échec, pour que l'appelant distingue "recalcul local OK" de "persistance échouée"
    # After a successful recompute: saves the produced files so they survive this
    # instance's restart and are picked up by every other one. Raises on failure, so the
    # caller can distinguish "local recompute OK" from "persistence failed"
    if not GCS_BUCKET_NAME:
        raise RuntimeError("GCS_BUCKET_NAME n'est pas configuré - le recalcul reste local à cette instance.")

    bucket = _client().bucket(GCS_BUCKET_NAME)
    for nom_objet, chemin_local in FICHIERS_SYNCHRONISES.items():
        if os.path.exists(chemin_local):
            bucket.blob(nom_objet).upload_from_filename(chemin_local)

    if os.path.exists(CHEMIN_MLFLOW):
        chemin_tmp = _copie_sqlite_sure(CHEMIN_MLFLOW)
        try:
            bucket.blob(NOM_OBJET_MLFLOW).upload_from_filename(chemin_tmp)
        finally:
            os.remove(chemin_tmp)

    log_event("pipeline", "INFO", "[GCS][SYNC] Fichiers sauvegardés dans le bucket", {"bucket": GCS_BUCKET_NAME})
