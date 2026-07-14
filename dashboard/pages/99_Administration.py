# Zone réservée aux administrateurs — état technique du pipeline et des logs
# Administrator-only area — technical pipeline and log status

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st  # noqa: E402

import config  # noqa: E402
from components.ui import afficher_entete, afficher_selecteur_langue, format_run_id, t  # noqa: E402

st.set_page_config(page_title="Administration", page_icon="🏦", layout="wide")

with st.sidebar:
    afficher_selecteur_langue()

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
    st.stop()

st.success(t("acces_autorise"))

etat_pipeline = charger_json(config.PIPELINE_STATE_PATH)
lineage = charger_json(config.LINEAGE_PATH)

st.subheader(t("etat_pipeline"))
if etat_pipeline:
    run_id = etat_pipeline.get("last_updated", "—")
    st.caption(f"run_id : {format_run_id(run_id)}")
    st.json(etat_pipeline)
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
