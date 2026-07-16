# Interface conversationnelle sur le portefeuille, appuyée sur les outils MCP
# Conversational interface over the portfolio, backed by the MCP tools

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st  # noqa: E402

from components.mcp_client import appeler_outil  # noqa: E402
from components.ui import afficher_entete, afficher_pied_de_page, t  # noqa: E402

st.set_page_config(page_title="Assistant IA", page_icon="🏦", layout="wide")

afficher_entete(t("nav_assistant"), t("page_assistant_intro"))


def repondre_a_la_question(question: str) -> str:
    # Ne reconnaît que les 4 questions prédéfinies (correspondance exacte) ;
    # toute autre question retourne un message explicite, jamais une réponse
    # sans rapport (ancien comportement : tout texte non reconnu retombait
    # silencieusement sur l'analyse des réclamations)
    # Only recognizes the 4 predefined questions (exact match); any other
    # question returns an explicit message, never an unrelated answer (old
    # behavior: any unrecognized text silently fell back to complaints)
    try:
        if question == t("question_top_risque"):
            resultat = appeler_outil("outil_clients_a_risque", limit=10)
            lignes = [f"- {c['full_name']} ({c['customer_id']}) — {c['segment']} — score {c['risque_composite']}/100"
                      for c in resultat]
            return "\n".join(lignes) if lignes else t("aucun_client_trouve")

        if question == t("question_cross_sell"):
            resultat = appeler_outil("outil_candidats_cross_sell", limit=10)
            lignes = [f"- {c['full_name']} ({c['customer_id']}) — {c['segment']} — {c['city']}" for c in resultat]
            return "\n".join(lignes) if lignes else t("aucun_client_trouve")

        if question == t("question_kpis"):
            kpis = appeler_outil("outil_kpis_portefeuille")[0]
            return "\n".join([f"- {cle} : {valeur}" for cle, valeur in kpis.items()])

        if question == t("question_reclamations"):
            analyse = appeler_outil("outil_analyse_reclamations")[0]
            lignes = [f"- {d['severity']} / {d['status']} : {d['nb_reclamations']}" for d in analyse["detail"]]
            return "\n".join(lignes) + f"\n\n**Total : {analyse['total']} réclamations**"

        return t("question_non_reconnue")
    except Exception:
        return f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}"


st.subheader(t("questions_predefinies"))
col1, col2, col3, col4 = st.columns(4)
question_choisie = None
if col1.button(t("question_top_risque")):
    question_choisie = t("question_top_risque")
if col2.button(t("question_cross_sell")):
    question_choisie = t("question_cross_sell")
if col3.button(t("question_kpis")):
    question_choisie = t("question_kpis")
if col4.button(t("question_reclamations")):
    question_choisie = t("question_reclamations")

st.caption(t("questions_comprises_intro"))
question_libre = st.text_input(t("poser_question"))
if st.button(t("envoyer")) and question_libre:
    question_choisie = question_libre

if question_choisie:
    with st.spinner("..."):
        reponse = repondre_a_la_question(question_choisie)
    st.markdown(reponse)

afficher_pied_de_page()
