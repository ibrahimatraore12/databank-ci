# Interface conversationnelle sur le portefeuille, appuyée sur les outils MCP
# Conversational interface over the portfolio, backed by the MCP tools

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st  # noqa: E402

from components.ui import afficher_entete, afficher_selecteur_langue, t  # noqa: E402
from mcp.tools.customers import get_at_risk_customers  # noqa: E402
from mcp.tools.complaints import get_complaint_analysis  # noqa: E402
from mcp.tools.portfolio import get_cross_sell_candidates, get_portfolio_kpis  # noqa: E402

st.set_page_config(page_title="Assistant IA", page_icon="🏦", layout="wide")

with st.sidebar:
    afficher_selecteur_langue()

afficher_entete(t("nav_assistant"), t("page_assistant_intro"))


def repondre_a_la_question(question: str) -> str:
    # Route une question prédéfinie vers l'outil MCP correspondant et formate la réponse
    # Routes a predefined question to the matching MCP tool and formats the response
    try:
        if question == t("question_top_risque"):
            resultat = get_at_risk_customers(limit=10)
            lignes = [f"- {c['full_name']} ({c['customer_id']}) — {c['segment']} — score {c['risque_composite']}/100"
                      for c in resultat]
            return "\n".join(lignes) if lignes else t("aucun_client_trouve")

        if question == t("question_cross_sell"):
            resultat = get_cross_sell_candidates(limit=10)
            lignes = [f"- {c['full_name']} ({c['customer_id']}) — {c['segment']} — {c['city']}" for c in resultat]
            return "\n".join(lignes) if lignes else t("aucun_client_trouve")

        if question == t("question_kpis"):
            kpis = get_portfolio_kpis()
            return "\n".join([f"- {cle} : {valeur}" for cle, valeur in kpis.items()])

        analyse = get_complaint_analysis()
        lignes = [f"- {d['severity']} / {d['status']} : {d['nb_reclamations']}" for d in analyse["detail"]]
        return "\n".join(lignes) + f"\n\n**Total : {analyse['total']} réclamations**"
    except Exception:
        return f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}"


st.subheader(t("questions_predefinies"))
col1, col2, col3 = st.columns(3)
question_choisie = None
if col1.button(t("question_top_risque")):
    question_choisie = t("question_top_risque")
if col2.button(t("question_cross_sell")):
    question_choisie = t("question_cross_sell")
if col3.button(t("question_kpis")):
    question_choisie = t("question_kpis")

question_libre = st.text_input(t("poser_question"))
if st.button(t("envoyer")) and question_libre:
    question_choisie = question_libre

if question_choisie:
    with st.spinner("..."):
        reponse = repondre_a_la_question(question_choisie)
    st.markdown(reponse)
