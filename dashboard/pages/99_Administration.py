# Zone réservée aux administrateurs — état technique du pipeline et des logs
# Administrator-only area — technical pipeline and log status

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import config  # noqa: E402
from components.ui import (  # noqa: E402
    afficher_entete, afficher_etapes_pipeline, afficher_pied_de_page, format_run_id, t,
)

st.set_page_config(page_title="Administration", page_icon="🏦", layout="wide")

afficher_entete(t("nav_admin"), t("page_admin_intro"))

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "databank-admin")


def verifier_mot_de_passe() -> bool:
    # Contrôle d'accès simple par mot de passe pour la zone d'administration
    # Simple password gate for the administration area
    if st.session_state.get("admin_authentifie"):
        return True

    saisie = st.text_input(t("mot_de_passe"), type="password")
    if st.button(t("connexion")):
        if saisie == ADMIN_PASSWORD:
            st.session_state["admin_authentifie"] = True
            st.rerun()
        else:
            st.error(t("acces_refuse"))
    return False


def charger_json(chemin: str) -> dict:
    # Charge un fichier JSON d'état, retourne un dict vide s'il n'existe pas encore
    # Loads a JSON state file, returns an empty dict if it doesn't exist yet
    if not os.path.exists(chemin):
        return {}
    with open(chemin, "r") as f:
        return json.load(f)


def valider_fichier_uploade(fichier) -> list:
    # Même contrôle que src/ingest.py::load_source_tables (feuille non vide,
    # taux de valeurs nulles), mais sans jamais lever : on veut le rapport
    # complet des 10 feuilles, pas un arrêt à la première erreur
    # Same check as src/ingest.py::load_source_tables (non-empty sheet, null
    # rate), but never raising: we want the full 10-sheet report, not a stop
    # at the first error
    rapports = []
    for nom_feuille in config.SOURCE_SHEETS:
        try:
            df = pd.read_excel(fichier, sheet_name=nom_feuille)
            taux_nuls = round(100 * df.isna().sum().sum() / max(df.size, 1), 2)
            erreurs = [t("feuille_vide")] if df.empty else []
            rapports.append({
                "table": nom_feuille, "lignes": len(df), "taux_nuls_pct": taux_nuls, "erreurs": ", ".join(erreurs),
            })
        except Exception as erreur:
            rapports.append({
                "table": nom_feuille, "lignes": 0, "taux_nuls_pct": None,
                "erreurs": f"{t('feuille_illisible')} : {erreur}",
            })
    return rapports


def relancer_pipeline_complet(fichier) -> None:
    # Écrit le fichier uploadé à la place du fichier source, puis rejoue tout le
    # pipeline dans le processus courant : ingestion+enrichissement (Python),
    # dbt run (sous-processus, même commande que le Dockerfile), puis ML.
    # Effet confiné à l'instance Cloud Run en cours — rien n'est persistant
    # Writes the uploaded file over the source file, then replays the whole
    # pipeline in the current process: ingestion+enrichment (Python), dbt run
    # (subprocess, same command as the Dockerfile), then ML. Effect confined
    # to the current Cloud Run instance — nothing is persistent
    from pipelines.run_ml_pipeline import run_ml_pipeline
    from pipelines.run_pipeline import run_pipeline

    fichier.seek(0)
    with open(config.SOURCE_EXCEL_PATH, "wb") as f:
        f.write(fichier.read())

    run_pipeline()

    dbt_dir = os.path.join(config.PROJECT_ROOT, "dbt_project")
    resultat = subprocess.run(
        ["dbt", "run"], cwd=dbt_dir, env={**os.environ, "DBT_PROFILES_DIR": dbt_dir},
        capture_output=True, text=True, timeout=120,
    )
    if resultat.returncode != 0:
        raise RuntimeError(resultat.stderr[-1000:] or resultat.stdout[-1000:])

    run_ml_pipeline()


def afficher_derniere_lignes_log(chemin: str, n: int = 20) -> None:
    # Affiche les dernières lignes d'un fichier de log
    # Displays the last lines of a log file
    if not os.path.exists(chemin):
        st.caption("—")
        return
    with open(chemin, "r") as f:
        lignes = f.readlines()
    st.code("".join(lignes[-n:]) or "—", language="text")


if not verifier_mot_de_passe():
    afficher_pied_de_page()
    st.stop()

st.success(t("acces_autorise"))

etat_pipeline = charger_json(config.PIPELINE_STATE_PATH)
lineage = charger_json(config.LINEAGE_PATH)

st.subheader(t("etat_pipeline"))
if etat_pipeline:
    run_id = etat_pipeline.get("last_updated", "—")
    st.caption(f"run_id : {format_run_id(run_id)}")
    afficher_etapes_pipeline(etat_pipeline)
else:
    st.info("—")

st.subheader("Lineage")
st.json(lineage) if lineage else st.info("—")

st.subheader("Logs")
onglet_pipeline, onglet_ml, onglet_api, onglet_errors = st.tabs(["pipeline.log", "ml.log", "api.log", "errors.log"])
with onglet_pipeline:
    afficher_derniere_lignes_log(os.path.join(config.LOGS_DIR, "pipeline.log"))
with onglet_ml:
    afficher_derniere_lignes_log(os.path.join(config.LOGS_DIR, "ml.log"))
with onglet_api:
    afficher_derniere_lignes_log(os.path.join(config.LOGS_DIR, "api.log"))
with onglet_errors:
    afficher_derniere_lignes_log(os.path.join(config.LOGS_DIR, "errors.log"))

st.subheader(t("titre_etude_modeles"))
chemin_rapport = os.path.join(config.PROJECT_ROOT, "docs", "model_comparison.md")
try:
    with open(chemin_rapport, "r", encoding="utf-8") as f:
        st.markdown(f.read())
except Exception:
    st.info("—")

st.subheader(t("titre_upload"))
st.caption(t("upload_intro"))
fichier_uploade = st.file_uploader(t("uploader_label"), type=["xlsx"])
if fichier_uploade is not None:
    rapports_feuilles = valider_fichier_uploade(fichier_uploade)
    nb_erreurs = sum(1 for r in rapports_feuilles if r["erreurs"])

    if nb_erreurs == 0:
        st.success(t("upload_valide"))
    else:
        st.error(t("upload_invalide").format(n=nb_erreurs))

    tableau_validation = pd.DataFrame(rapports_feuilles).rename(columns={
        "table": t("col_feuille"), "lignes": t("col_lignes"),
        "taux_nuls_pct": t("col_taux_nuls"), "erreurs": t("col_erreurs"),
    })
    st.dataframe(tableau_validation, width='stretch', hide_index=True)

    if nb_erreurs == 0:
        st.info(t("upload_instructions"))
        if st.button(t("recalculer_maintenant")):
            try:
                with st.spinner(t("recalcul_en_cours")):
                    relancer_pipeline_complet(fichier_uploade)
                st.success(t("recalcul_succes"))
            except Exception as erreur:
                st.error(t("recalcul_echec"))
                st.code(str(erreur)[:1000], language="text")

afficher_pied_de_page()
