# Engagement digital et comportement transactionnel des clients
# Digital engagement and transaction behavior of customers

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st  # noqa: E402

from components.charts import graphique_barres, graphique_histogramme  # noqa: E402
from components.ui import (  # noqa: E402
    afficher_entete, afficher_pied_de_page, format_pct, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="Comportement et Engagement", page_icon="🏦", layout="wide")

afficher_entete(t("nav_comportement"), t("page_comportement_intro"))

try:
    df = requete_duckdb("SELECT * FROM main_marts.customer_360")
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    afficher_pied_de_page()
    st.stop()

col1, col2, col3 = st.columns(3)
with col1, st.container(border=True):
    st.metric(t("kpi_score_digital_moyen"), f"{df['score_digital'].mean():.1f} / 3")
with col2, st.container(border=True):
    st.metric(t("jours_depuis_derniere_transaction"), f"{df['recency_jours'].median():.0f}")
with col3, st.container(border=True):
    taux_tendance_positive = 100 * (df["tendance_transactions"] >= 0).mean()
    st.metric(t("tendance_activite"), format_pct(taux_tendance_positive))

st.divider()
col_gauche, col_droite = st.columns(2)

with col_gauche:
    repartition_digital = df["score_digital"].value_counts().sort_index().reset_index()
    repartition_digital.columns = ["score_digital", "nb_clients"]
    st.plotly_chart(
        graphique_barres(repartition_digital, "score_digital", "nb_clients", label_technique("score_digital")),
        width='stretch',
    )

with col_droite:
    st.plotly_chart(
        graphique_histogramme(df, "recency_jours", label_technique("recency_jours")),
        width='stretch',
    )

st.subheader(t("tendance_activite"))
st.plotly_chart(
    graphique_histogramme(df, "tendance_transactions", label_technique("tendance_transactions")),
    width='stretch',
)

st.subheader(t("kpis_portefeuille"))
par_segment = df.groupby("segment").agg(
    score_digital_moyen=("score_digital", "mean"),
    recency_mediane=("recency_jours", "median"),
).round(1).reset_index()
par_segment = par_segment.rename(columns={
    "segment": label_technique("segment"),
    "score_digital_moyen": label_technique("score_digital"),
    "recency_mediane": label_technique("recency_jours"),
})
st.dataframe(par_segment, width='stretch', hide_index=True)

afficher_pied_de_page()
