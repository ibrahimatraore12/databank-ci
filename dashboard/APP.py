# Point d'entrée Streamlit — routeur de navigation (les onglets se retraduisent
# dynamiquement au changement de langue, ce qu'une navigation multipage par
# fichiers ne permet pas nativement)
# Streamlit entry point — navigation router (tabs re-translate dynamically on
# language change, which a file-based multipage navigation can't do natively)

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st  # noqa: E402

import config  # noqa: E402
from components.ui import afficher_selecteur_langue, injecter_css_artefact, t  # noqa: E402
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


def _statut_pipeline_sidebar() -> str:
    # Badge compact (icône + date) pour le pied de sidebar ; le détail étape par
    # étape reste réservé à la page Administration
    # Compact badge (icon + date) for the sidebar footer; step-by-step detail
    # stays reserved for the Administration page
    if not os.path.exists(config.PIPELINE_STATE_PATH):
        return f"⚪ {t('statut_pipeline_inconnu')}"
    with open(config.PIPELINE_STATE_PATH, "r") as f:
        etat = json.load(f)
    tout_ok = all(statut == "OK" for statut in etat.get("steps", {}).values())
    icone = "✅" if tout_ok else "❌"
    libelle = t("statut_pipeline_ok") if tout_ok else t("statut_pipeline_echec")
    return f"{icone} {libelle} · {etat.get('last_updated', '—')[:10]}"


_synchroniser_donnees_au_demarrage()
injecter_css_artefact()

with st.sidebar:
    st.markdown(
        """
        <div style="padding:20px 16px 16px; border-bottom:1px solid #2C2C2C">
          <div style="display:flex;align-items:center;gap:10px">
            <svg width="34" height="34" viewBox="0 0 34 34" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="databank-logo-grad" x1="0" y1="1" x2="0" y2="0">
                  <stop offset="0%" stop-color="#FF4500"/>
                  <stop offset="100%" stop-color="#FF8C42"/>
                </linearGradient>
              </defs>
              <rect width="34" height="34" rx="9" fill="#1A1A1A" stroke="#FF4500" stroke-width="1"/>
              <rect x="7" y="19" width="4" height="9" rx="1.5" fill="url(#databank-logo-grad)"/>
              <rect x="15" y="13" width="4" height="15" rx="1.5" fill="url(#databank-logo-grad)"/>
              <rect x="23" y="7" width="4" height="21" rx="1.5" fill="url(#databank-logo-grad)"/>
            </svg>
            <div>
              <div style="font-size:18px;font-weight:700;color:#FFFFFF;line-height:1.1">
                data<span style="color:#FF4500">Bank</span>
              </div>
              <div style="font-size:10px;color:rgba(255,255,255,0.5);
                          letter-spacing:1.5px;text-transform:uppercase;margin-top:2px">
                Customer 360 · CI
              </div>
            </div>
          </div>
          <div style="width:32px;height:2px;background:#FF4500;
                      border-radius:1px;margin-top:10px"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
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

with st.sidebar:
    st.markdown(
        f"""
        <div style="margin-top:16px;padding:12px 16px 4px;
                    border-top:1px solid #2C2C2C;font-size:12px">
          <div style="color:rgba(255,255,255,0.7);margin-bottom:10px">
            {_statut_pipeline_sidebar()}
          </div>
          <div style="color:rgba(255,255,255,0.5);line-height:1.5">
            Ibrahima TRAORÉ<br>Analytics Engineer
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.navigation(pages).run()
