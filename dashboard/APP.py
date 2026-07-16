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
from src.storage_sync import telecharger_depuis_gcs  # noqa: E402


@st.cache_resource
def _synchroniser_donnees_au_demarrage() -> bool:
    # Une seule fois par instance (cache process-global, pas par session ni par
    # page) : Streamlit ré-exécute APP.py en entier à chaque interaction, donc un
    # appel nu ici tournerait à chaque clic sans ce cache
    # Once per instance only (process-global cache, not per session or page):
    # Streamlit re-executes APP.py in full on every interaction, so a bare call
    # here would run on every click without this cache
    return telecharger_depuis_gcs()


_synchroniser_donnees_au_demarrage()

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
