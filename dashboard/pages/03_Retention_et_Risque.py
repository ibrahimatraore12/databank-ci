# Clients à risque de désengagement, priorisés pour l'action commerciale
# Customers at risk of disengagement, prioritized for commercial action

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st  # noqa: E402

from components.ui import (  # noqa: E402
    afficher_barre_score, afficher_entete, afficher_selecteur_langue, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="Rétention et Risque", page_icon="🏦", layout="wide")

with st.sidebar:
    afficher_selecteur_langue()

afficher_entete(t("nav_retention"), t("page_retention_intro"))

try:
    df = requete_duckdb(
        """
        SELECT c.*, n.next_best_action
        FROM main_marts.customer_360 c
        LEFT JOIN main_marts.nba n ON c.customer_id = n.customer_id
        ORDER BY c.risque_composite DESC
        """
    )
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric(t("client_forte_valeur_a_risque"), int(df["is_high_value_at_risk"].sum()))
col2.metric(t("risque_reclamation"), int(df["is_complaints_churn_risk"].sum()))
col3.metric(t("salaire_domicilie_digital_dormant"), int(df["is_digitally_dormant_salary"].sum()))

st.divider()
st.subheader(t("top_clients_risque"))

top_risque = df.head(10)
for _, ligne in top_risque.iterrows():
    with st.container(border=True):
        col_info, col_score = st.columns([3, 1])
        with col_info:
            st.markdown(f"**{ligne['full_name']}** — {ligne['segment']} — {ligne['city']}")
            st.caption(f"{t('action_recommandee')} : {ligne['next_best_action']}")
        with col_score:
            afficher_barre_score(ligne["risque_composite"], label_technique("risque_composite"))

st.divider()
st.subheader(t("kpis_portefeuille"))
colonnes_affichees = ["customer_id", "full_name", "segment", "risque_composite", "next_best_action"]
tableau = df[colonnes_affichees].rename(columns={c: label_technique(c) for c in colonnes_affichees})
st.dataframe(tableau, width='stretch', hide_index=True)
