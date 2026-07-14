# Comparaison des modèles de scoring et explication des résultats
# Scoring model comparison and result explanation

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st  # noqa: E402

import config  # noqa: E402
from components.ui import afficher_entete, afficher_selecteur_langue, t  # noqa: E402

st.set_page_config(page_title="Intelligence Artificielle", page_icon="🏦", layout="wide")

with st.sidebar:
    afficher_selecteur_langue()

afficher_entete(t("nav_ia"), t("page_ia_intro"))

chemin_rapport = os.path.join(config.PROJECT_ROOT, "docs", "model_comparison.md")

try:
    with open(chemin_rapport, "r", encoding="utf-8") as f:
        contenu_rapport = f.read()
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    st.stop()

st.markdown(contenu_rapport)

st.divider()
st.info(
    "Le score de règles métier (non-ML) reste toujours disponible même sans modèle entraîné — "
    "voir `ml/rules.py`. Les limites du label utilisé pour l'entraînement sont détaillées dans "
    "`docs/ml_problem_definition.md`."
)
