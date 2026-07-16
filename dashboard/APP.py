# Point d'entrée Streamlit — routeur de navigation (les onglets se retraduisent
# dynamiquement au changement de langue, ce qu'une navigation multipage par
# fichiers ne permet pas nativement)
# Streamlit entry point — navigation router (tabs re-translate dynamically on
# language change, which a file-based multipage navigation can't do natively)

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st  # noqa: E402

from components.ui import afficher_selecteur_langue, t  # noqa: E402

with st.sidebar:
    afficher_selecteur_langue()

pages = [
    st.Page("pages/00_Accueil.py", title=t("nav_accueil"), icon="🏠", default=True),
    st.Page("pages/01_Portefeuille_Clients.py", title=t("nav_portefeuille"), icon="👥"),
    st.Page("pages/02_Comportement_et_Engagement.py", title=t("nav_comportement"), icon="📈"),
    st.Page("pages/03_Retention_et_Risque.py", title=t("nav_retention"), icon="⚠️"),
    st.Page("pages/04_Vue_Client_360.py", title=t("nav_360"), icon="🔎"),
    st.Page("pages/05_Opportunites_Commerciales.py", title=t("nav_opportunites"), icon="💡"),
    st.Page("pages/06_Intelligence_Artificielle.py", title=t("nav_ia"), icon="🤖"),
    st.Page("pages/07_Assistant_IA.py", title=t("nav_assistant"), icon="💬"),
    st.Page("pages/99_Administration.py", title=t("nav_admin"), icon="🔧"),
]

st.navigation(pages).run()
