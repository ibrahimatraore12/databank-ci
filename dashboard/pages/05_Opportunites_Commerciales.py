# Clients à cibler pour le cross-sell et l'upsell
# Customers to target for cross-sell and upsell

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st  # noqa: E402

from components.ui import (  # noqa: E402
    afficher_entete, afficher_pied_de_page, format_fcfa, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="Opportunités Commerciales", page_icon="🏦", layout="wide")

afficher_entete(t("nav_opportunites"), t("page_opportunites_intro"))

try:
    df = requete_duckdb("SELECT * FROM main_marts.customer_360")
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    afficher_pied_de_page()
    st.stop()

col1, col2 = st.columns(2)
with col1, st.container(border=True):
    st.metric(t("cible_cross_sell"), int(df["is_cross_sell_target"].sum()))
with col2, st.container(border=True):
    st.metric(t("opportunite_upsell_salaire"), int(df["is_salary_upsell_opportunity"].sum()))

st.divider()

onglet_cross_sell, onglet_upsell = st.tabs([t("candidats_cross_sell"), t("opportunite_upsell_salaire")])

colonnes_affichees = ["customer_id", "full_name", "segment", "city", "monthly_income_xof"]

with onglet_cross_sell:
    st.caption(t("cible_cross_sell"))
    candidats = df[df["is_cross_sell_target"]][colonnes_affichees]
    candidats = candidats.rename(columns={c: label_technique(c) for c in candidats.columns})
    st.dataframe(candidats, width='stretch', hide_index=True)

with onglet_upsell:
    st.caption(t("opportunite_upsell_salaire"))
    candidats = df[df["is_salary_upsell_opportunity"]][colonnes_affichees]
    candidats = candidats.assign(monthly_income_xof=candidats["monthly_income_xof"].apply(format_fcfa))
    candidats = candidats.rename(columns={c: label_technique(c) for c in candidats.columns})
    st.dataframe(candidats, width='stretch', hide_index=True)

afficher_pied_de_page()
