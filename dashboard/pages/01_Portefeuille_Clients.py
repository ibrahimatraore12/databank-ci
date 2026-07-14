# Composition du portefeuille clients par segment, risque et géographie
# Customer portfolio composition by segment, risk, and geography

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st  # noqa: E402

from components.charts import graphique_barres, graphique_barres_horizontales  # noqa: E402
from components.ui import (  # noqa: E402
    afficher_entete, afficher_selecteur_langue, format_pct, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="Portefeuille Clients", page_icon="🏦", layout="wide")

with st.sidebar:
    afficher_selecteur_langue()

afficher_entete(t("nav_portefeuille"), t("page_portefeuille_intro"))

try:
    df = requete_duckdb("SELECT * FROM main_marts.customer_360")
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    st.stop()

segments_disponibles = [t("tous_les_segments")] + sorted(df["segment"].unique().tolist())
segment_choisi = st.selectbox(t("selectionner_segment"), segments_disponibles)
if segment_choisi != t("tous_les_segments"):
    df = df[df["segment"] == segment_choisi]

col1, col2, col3 = st.columns(3)
col1.metric(t("kpi_nombre_clients"), len(df))
col2.metric(t("kpi_taux_salaire_domicilie"), format_pct(100 * df["salaire_domicilie"].mean()))
col3.metric(t("nombre_produits_detenus"), f"{df['nb_produits_total'].mean():.1f}")

st.divider()
col_gauche, col_droite = st.columns(2)

with col_gauche:
    repartition_segment = df["segment"].value_counts().reset_index()
    repartition_segment.columns = ["segment", "nb_clients"]
    st.plotly_chart(
        graphique_barres(repartition_segment, "segment", "nb_clients", label_technique("segment")),
        width='stretch',
    )

with col_droite:
    top_villes = df["city"].value_counts().head(8).reset_index()
    top_villes.columns = ["ville", "nb_clients"]
    st.plotly_chart(
        graphique_barres_horizontales(top_villes, "nb_clients", "ville", label_technique("city")),
        width='stretch',
    )

st.subheader(t("niveau_risque_credit"))
repartition_risque = df["risk_band"].value_counts().reset_index()
repartition_risque.columns = ["risk_band", "nb_clients"]
st.plotly_chart(
    graphique_barres(repartition_risque, "risk_band", "nb_clients", label_technique("risk_band")),
    width='stretch',
)

st.subheader(t("kpis_portefeuille"))
colonnes_affichees = [
    "customer_id", "full_name", "segment", "risk_band", "city", "salaire_domicilie", "nb_produits_total",
]
tableau = df[colonnes_affichees].rename(columns={c: label_technique(c) for c in colonnes_affichees})
st.dataframe(tableau, width='stretch', hide_index=True)
