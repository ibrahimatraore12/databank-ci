# Page d'accueil - KPIs de synthèse, alerte VIP, vue instantanée du portefeuille
# Home page - summary KPIs, VIP alert, at-a-glance portfolio view

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import config  # noqa: E402
from components.charts import (  # noqa: E402
    COULEUR_ORANGE_ACTION, RISK_COLOR_MAP, SEGMENT_COLOR_MAP, graphique_barres_horizontales,
    graphique_camembert, graphique_nuage_valeur_engagement,
)
from components.ui import (  # noqa: E402
    afficher_alerte, afficher_carte_kpi, afficher_entete, afficher_guide, afficher_pied_de_page,
    format_date_longue, format_fcfa_compact, format_pct, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="Accueil", page_icon="🏦", layout="wide")


def charger_etat_pipeline() -> dict:
    # Lit pipeline_state.json pour la date affichée en pied de page
    # Reads pipeline_state.json for the date shown in the page footer
    if not os.path.exists(config.PIPELINE_STATE_PATH):
        return {}
    with open(config.PIPELINE_STATE_PATH, "r") as f:
        return json.load(f)


def afficher_kpis_synthese(df: pd.DataFrame) -> None:
    # 4 cartes KPI à seuil RAG - diagnostic immédiat de la santé du portefeuille
    # 4 RAG-thresholded KPI cards - immediate portfolio health diagnosis
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        nb_actifs = int((df["recency_jours"] <= 30).sum())
        taux_actifs = 100 * nb_actifs / len(df)
        type_carte = "success" if taux_actifs > 80 else "warning" if taux_actifs >= 60 else "danger"
        afficher_carte_kpi(
            t("kpi_clients_actifs"), f"{nb_actifs} / {len(df)}",
            format_pct(taux_actifs), type_carte,
        )

    with col2:
        afficher_carte_kpi(
            t("kpi_solde_total_gere"), format_fcfa_compact(df["solde_total_xof"].sum()),
            t("sous_label_portefeuille_complet"),
        )

    with col3:
        nb_reclamations = int(df["nb_reclamations_ouvertes"].sum())
        type_carte = (
            "danger" if nb_reclamations > 5 else "warning" if nb_reclamations >= 3 else "success"
        )
        afficher_carte_kpi(t("kpi_reclamations_ouvertes"), str(nb_reclamations), "", type_carte)

    with col4:
        score_moyen = df["risque_composite"].mean()
        type_carte = (
            "danger" if score_moyen >= 70 else "warning" if score_moyen >= 40 else "success"
        )
        afficher_carte_kpi(t("kpi_risque_moyen"), f"{score_moyen:.0f}/100", "", type_carte)


def afficher_alerte_vip(df: pd.DataFrame) -> None:
    # Alerte rouge si des clients Premier affichent un score de risque critique -
    # le signal le plus coûteux à manquer (forte valeur + départ imminent) ;
    # n'apparaît que si la condition est réellement vraie sur les données
    # Red alert if Premier customers show a critical risk score - the costliest
    # signal to miss (high value + imminent departure); only shows when the
    # condition actually holds in the data
    vip_a_risque = df[(df["segment"] == "Premier") & (df["risque_composite"] > 70)]
    if len(vip_a_risque) == 0:
        return
    afficher_alerte(
        t("alerte_vip_premier").format(
            n=len(vip_a_risque), solde=format_fcfa_compact(vip_a_risque["solde_total_xof"].sum()),
        ),
        "critical", "🚨",
    )
    st.page_link("pages/03_Retention_et_Risque.py", label=t("voir_les_alertes"))


def afficher_alerte_opportunites(df: pd.DataFrame) -> None:
    # Alerte verte symétrique à l'alerte VIP : le tableau de bord doit montrer
    # aussi ce qui va bien et ce qu'il y a à gagner, pas seulement les risques -
    # calculée sur les mêmes signaux réels que la page Opportunités
    # Green alert symmetric to the VIP alert: the dashboard must also surface
    # what's going well and what there is to gain, not just risks - computed
    # from the same real signals as the Opportunities page
    opportunites = df[df["is_cross_sell_target"] | df["is_salary_upsell_opportunity"]]
    if len(opportunites) == 0:
        return
    afficher_alerte(
        t("alerte_opportunites_accueil").format(
            n=len(opportunites), montant=format_fcfa_compact(opportunites["nbi_estime_xof"].sum()),
        ),
        "success", "💡",
    )
    st.page_link("pages/05_Opportunites_Commerciales.py", label=t("voir_les_opportunites"))


def graphique_scatter_accueil(df: pd.DataFrame):
    # Nuage de points valeur vs engagement avec zones vert/ambre/rouge en fond -
    # priorise visuellement les clients à valeur qui se désengagent
    # Value vs engagement scatter with green/amber/red background zones -
    # visually surfaces valuable customers who are disengaging
    labels = {
        "recency_jours": label_technique("recency_jours"),
        "solde_m_fcfa": label_technique("solde_total_xof"),
    }
    fig = graphique_nuage_valeur_engagement(
        df.assign(solde_m_fcfa=df["solde_total_xof"] / 1_000_000),
        x="recency_jours", y="solde_m_fcfa", couleur="segment", taille="nbi_estime_xof",
        titre=t("titre_scatter_accueil"), labels=labels,
    )
    recency_max = float(df["recency_jours"].max())
    borne_haute = max(recency_max, 61)
    fig.add_vrect(x0=0, x1=30, fillcolor=RISK_COLOR_MAP["Low"], opacity=0.08, line_width=0)
    fig.add_vrect(x0=30, x1=60, fillcolor=RISK_COLOR_MAP["Medium"], opacity=0.08, line_width=0)
    fig.add_vrect(x0=60, x1=borne_haute, fillcolor=RISK_COLOR_MAP["High"], opacity=0.08, line_width=0)  # noqa: E501
    for x_centre, cle, couleur in [
        (15, "zone_clients_actifs", RISK_COLOR_MAP["Low"]),
        (45, "zone_a_surveiller", RISK_COLOR_MAP["Medium"]),
        (borne_haute - 15, "zone_vip_inactifs", RISK_COLOR_MAP["High"]),
    ]:
        fig.add_annotation(
            x=x_centre, y=1.06, xref="x", yref="paper", text=t(cle),
            showarrow=False, font=dict(size=10, color=couleur),
        )
    return fig


def graphique_top_actions(df: pd.DataFrame):
    # Classement des 5 actions les plus prioritaires, issu des données réelles
    # (pas de texte figé) - couleur CTA orange, distincte des couleurs de segment
    # Ranking of the 5 highest-priority actions, computed from real data
    # (no hardcoded text) - orange CTA color, distinct from segment colors
    actions = pd.DataFrame([
        {"action": t("action_sans_carte"), "n": int((df["nb_cartes"] == 0).sum())},
        {"action": t("action_risque_credit_eleve"), "n": int((df["risk_band"] == "High").sum())},
        {"action": t("kpi_reclamations_ouvertes"), "n": int(df["nb_reclamations_ouvertes"].sum())},
        {"action": t("action_forte_valeur_a_risque"), "n": int(df["is_high_value_at_risk"].sum())},
        {"action": t("action_reclamation_desengagement"),
         "n": int(df["is_complaints_churn_risk"].sum())},
    ]).sort_values("n", ascending=True)
    return graphique_barres_horizontales(
        actions, "n", "action", t("titre_actions_prioritaires"), couleur=COULEUR_ORANGE_ACTION,
    )


afficher_entete(t("app_titre"), t("app_sous_titre"))
afficher_guide(t("page_accueil_intro"))

try:
    donnees_customer_360 = requete_duckdb("SELECT * FROM main_marts.customer_360")
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    afficher_pied_de_page()
    st.stop()

afficher_kpis_synthese(donnees_customer_360)
afficher_alerte_vip(donnees_customer_360)
afficher_alerte_opportunites(donnees_customer_360)

st.divider()
col_scatter, col_donut = st.columns([3, 2])
with col_scatter:
    st.plotly_chart(graphique_scatter_accueil(donnees_customer_360), width='stretch')
    st.caption(t("soustitre_scatter_accueil"))
with col_donut:
    repartition_segment = donnees_customer_360["segment"].value_counts().reset_index()
    repartition_segment.columns = ["segment", "nb_clients"]
    fig_donut = graphique_camembert(
        repartition_segment, "segment", "nb_clients", t("titre_composition_portefeuille"),
        color_col="segment", color_map=SEGMENT_COLOR_MAP,
        trou=0.55, texte_centre=f"{len(donnees_customer_360)}<br>{t('nav_portefeuille')}",
    )
    st.plotly_chart(fig_donut, width='stretch')

st.divider()
st.plotly_chart(graphique_top_actions(donnees_customer_360), width='stretch')

afficher_pied_de_page(format_date_longue(charger_etat_pipeline().get("last_updated")))
