# Explication métier du score de risque — pas un rapport technique de benchmark
# (le comparatif de modèles ML, réservé aux profils techniques, vit désormais
# dans l'onglet Administration)
# Business explanation of the risk score — not a technical benchmark report
# (the ML model comparison, for technical profiles, now lives in the
# Administration tab)

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import config  # noqa: E402
from components.charts import graphique_barres_horizontales  # noqa: E402
from components.ui import afficher_entete, afficher_pied_de_page, t  # noqa: E402

st.set_page_config(page_title="Intelligence Artificielle", page_icon="🏦", layout="wide")

afficher_entete(t("nav_ia"), t("page_ia_intro"))

st.write(t("ia_intro_texte_1"))
st.subheader(t("ia_intro_texte_2"))

poids = pd.DataFrame({
    "poids": [
        config.RULES_WEIGHT_RECENCY * 100,
        config.RULES_WEIGHT_COMPLAINTS * 100,
        config.RULES_WEIGHT_DIGITAL * 100,
        config.RULES_WEIGHT_TREND * 100,
    ],
    "facteur": [
        t("facteur_recence"), t("facteur_reclamations"), t("facteur_digital"), t("facteur_tendance"),
    ],
})
st.plotly_chart(graphique_barres_horizontales(poids, "poids", "facteur"), width='stretch')

st.divider()
st.info(t("ia_note_admin"))

afficher_pied_de_page()
