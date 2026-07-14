# Point d'entrée Streamlit — Accueil : KPIs de synthèse et état du pipeline
# Streamlit entry point — Home: summary KPIs and pipeline status

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import config  # noqa: E402
from components.charts import graphique_camembert  # noqa: E402
from components.ui import (  # noqa: E402
    afficher_entete, afficher_selecteur_langue, format_pct, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="dataBank CI — Customer 360", page_icon="🏦", layout="wide")


def charger_etat_pipeline() -> dict:
    # Lit pipeline_state.json pour afficher le statut technique du dernier run
    # Reads pipeline_state.json to display the last run's technical status
    if not os.path.exists(config.PIPELINE_STATE_PATH):
        return {}
    with open(config.PIPELINE_STATE_PATH, "r") as f:
        return json.load(f)


def afficher_kpis_synthese(df_customer_360: pd.DataFrame) -> None:
    # Affiche les cartes KPI de synthèse du portefeuille
    # Displays the portfolio summary KPI cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("kpi_nombre_clients"), len(df_customer_360))
    col2.metric(t("kpi_risque_moyen"), f"{df_customer_360['risque_composite'].mean():.1f}/100")
    taux_risque = 100 * df_customer_360["is_high_value_at_risk"].mean()
    col3.metric(t("kpi_taux_clients_risque"), format_pct(taux_risque))
    taux_salaire = 100 * df_customer_360["salaire_domicilie"].mean()
    col4.metric(t("kpi_taux_salaire_domicilie"), format_pct(taux_salaire))


def afficher_etat_technique(etat: dict) -> None:
    # Affiche l'état technique du pipeline dans la barre latérale
    # Displays the pipeline's technical status in the sidebar
    st.sidebar.markdown(f"### {t('etat_pipeline')}")
    if not etat:
        st.sidebar.info("—")
        return
    for etape, statut in etat.get("steps", {}).items():
        icone = "✅" if statut == "OK" else "❌"
        st.sidebar.markdown(f"{icone} {etape}")
    st.sidebar.caption(f"{t('derniere_execution')} : {etat.get('last_updated', '—')[:19]}")


def main() -> None:
    with st.sidebar:
        afficher_selecteur_langue()

    afficher_entete(t("app_titre"), t("app_sous_titre"))
    st.write(t("page_accueil_intro"))

    try:
        df_customer_360 = requete_duckdb("SELECT * FROM main_marts.customer_360")
    except Exception:
        st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
        st.stop()

    afficher_kpis_synthese(df_customer_360)

    st.divider()
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        repartition_segment = df_customer_360["segment"].value_counts().reset_index()
        repartition_segment.columns = ["segment", "nb_clients"]
        st.plotly_chart(
            graphique_camembert(repartition_segment, "segment", "nb_clients", label_technique("segment")),
            width='stretch',
        )
    with col_droite:
        repartition_risque = df_customer_360["risk_band"].value_counts().reset_index()
        repartition_risque.columns = ["risk_band", "nb_clients"]
        st.plotly_chart(
            graphique_camembert(repartition_risque, "risk_band", "nb_clients", label_technique("risk_band")),
            width='stretch',
        )

    afficher_etat_technique(charger_etat_pipeline())


main()
