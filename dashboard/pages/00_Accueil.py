# Page d'accueil — KPIs de synthèse, statut du pipeline, alertes data-driven
# Home page — summary KPIs, pipeline status, data-driven alerts

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import config  # noqa: E402
from components.charts import RISK_COLOR_MAP, SEGMENT_COLOR_MAP, graphique_camembert  # noqa: E402
from components.ui import (  # noqa: E402
    afficher_entete, afficher_pied_de_page, format_date_longue, format_pct, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="Accueil", page_icon="🏦", layout="wide")


def charger_etat_pipeline() -> dict:
    # Lit pipeline_state.json pour afficher le statut technique du dernier run
    # Reads pipeline_state.json to display the last run's technical status
    if not os.path.exists(config.PIPELINE_STATE_PATH):
        return {}
    with open(config.PIPELINE_STATE_PATH, "r") as f:
        return json.load(f)


def afficher_badge_statut(etat: dict) -> None:
    # Badge compact (couleur + date) — la checklist détaillée vit dans Administration
    # Compact badge (color + date) — the detailed checklist lives in Administration
    if not etat:
        st.markdown(f"⚪ {t('statut_pipeline_inconnu')}")
        return
    tout_ok = all(statut == "OK" for statut in etat.get("steps", {}).values())
    icone = "🟢" if tout_ok else "🔴"
    libelle = t("statut_pipeline_ok") if tout_ok else t("statut_pipeline_echec")
    st.markdown(f"{icone} **{libelle}** — {t('derniere_execution')} : {format_date_longue(etat.get('last_updated'))}")


def afficher_kpis_synthese(df_customer_360: pd.DataFrame) -> None:
    # Affiche les cartes KPI de synthèse du portefeuille, en tuiles délimitées
    # Displays the portfolio summary KPI cards, as delimited tiles
    col1, col2, col3, col4 = st.columns(4)
    with col1, st.container(border=True):
        st.metric(t("kpi_nombre_clients"), len(df_customer_360))
    with col2, st.container(border=True):
        st.metric(t("kpi_risque_moyen"), f"{df_customer_360['risque_composite'].mean():.1f}/100")
    with col3, st.container(border=True):
        taux_risque = 100 * df_customer_360["is_high_value_at_risk"].mean()
        st.metric(t("kpi_taux_clients_risque"), format_pct(taux_risque))
    with col4, st.container(border=True):
        taux_salaire = 100 * df_customer_360["salaire_domicilie"].mean()
        st.metric(t("kpi_taux_salaire_domicilie"), format_pct(taux_salaire))


def afficher_alertes(df_customer_360: pd.DataFrame) -> None:
    # Alertes contextuelles dérivées des seuils réels du portefeuille
    # Contextual alerts derived from the portfolio's actual thresholds
    nb_high_value_at_risk = int(df_customer_360["is_high_value_at_risk"].sum())
    if nb_high_value_at_risk > 0:
        taux_risque_eleve = format_pct(100 * (df_customer_360["risk_band"] == "High").mean())
        st.warning(t("alerte_risque_eleve").format(pct=taux_risque_eleve, n=nb_high_value_at_risk))
        st.page_link("pages/03_Retention_et_Risque.py", label=t("voir_la_liste"))

    nb_reclamations_risque = int(df_customer_360["is_complaints_churn_risk"].sum())
    if nb_reclamations_risque > 0:
        st.warning(t("alerte_reclamations").format(n=nb_reclamations_risque))
        st.page_link("pages/03_Retention_et_Risque.py", label=t("voir_la_liste"))


afficher_entete(t("app_titre"), t("app_sous_titre"))
st.write(t("page_accueil_intro"))

try:
    donnees_customer_360 = requete_duckdb("SELECT * FROM main_marts.customer_360")
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    afficher_pied_de_page()
    st.stop()

afficher_badge_statut(charger_etat_pipeline())
st.divider()

afficher_kpis_synthese(donnees_customer_360)
afficher_alertes(donnees_customer_360)

st.divider()
col_gauche, col_droite = st.columns(2)
with col_gauche:
    repartition_segment = donnees_customer_360["segment"].value_counts().reset_index()
    repartition_segment.columns = ["segment", "nb_clients"]
    st.plotly_chart(
        graphique_camembert(repartition_segment, "segment", "nb_clients", label_technique("segment"),
                            color_map=SEGMENT_COLOR_MAP),
        width='stretch',
    )
with col_droite:
    repartition_risque = donnees_customer_360["risk_band"].value_counts().reset_index()
    repartition_risque.columns = ["risk_band", "nb_clients"]
    st.plotly_chart(
        graphique_camembert(repartition_risque, "risk_band", "nb_clients", label_technique("risk_band"),
                            color_map=RISK_COLOR_MAP),
        width='stretch',
    )

afficher_pied_de_page()
