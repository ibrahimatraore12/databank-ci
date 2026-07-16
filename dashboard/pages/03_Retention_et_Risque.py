# Clients à risque de désengagement, priorisés pour l'action commerciale —
# répond à "qui vais-je perdre cette semaine et qui dois-je appeler en priorité ?"
# Customers at risk of disengagement, prioritized for commercial action —
# answers "who am I going to lose this week, and who should I call first?"

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from components.charts import COULEUR_ATTENTION, COULEUR_CRITIQUE, COULEUR_POSITIF  # noqa: E402
from components.ui import (  # noqa: E402
    afficher_alerte, afficher_barre_score, afficher_carte_kpi, afficher_entete, afficher_entete_section,
    afficher_guide, afficher_pied_de_page, badge_action, badge_segment, format_fcfa_compact, label_technique,
    requete_duckdb, t,
)

st.set_page_config(page_title="Rétention et Risque", page_icon="🏦", layout="wide")

afficher_entete(t("nav_retention"), t("soustitre_retention"))
afficher_guide(t("guide_retention"))

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
    afficher_pied_de_page()
    st.stop()

# --- Alerte critique : VIP Premier à risque de départ --------------------------
vip_a_risque = df[(df["segment"] == "Premier") & (df["risque_composite"] > 70)]
if len(vip_a_risque) > 0:
    afficher_alerte(
        t("alerte_prioritaire_bandeau").format(
            n=len(vip_a_risque), solde=format_fcfa_compact(vip_a_risque["solde_total_xof"].sum()),
        ),
        "critical", "🚨",
    )

# --- KPIs ------------------------------------------------------------------------
zone_rouge = df[df["risque_composite"] > 70]
zone_ambre = df[(df["risque_composite"] >= 40) & (df["risque_composite"] <= 70)]
reclamations_ouvertes = df[df["nb_reclamations_ouvertes"] > 0]

col1, col2, col3, col4 = st.columns(4)
with col1:
    afficher_carte_kpi(
        t("kpi_score_superieur_70"), str(len(zone_rouge)), "", "danger" if len(zone_rouge) > 3 else "",
    )
with col2:
    afficher_carte_kpi(t("kpi_score_40_70"), str(len(zone_ambre)), "", "warning" if len(zone_ambre) > 0 else "")
with col3:
    type_carte = "danger" if len(reclamations_ouvertes) > 5 else ""
    afficher_carte_kpi(t("kpi_reclamations_ouvertes"), str(len(reclamations_ouvertes)), "", type_carte)
with col4:
    afficher_carte_kpi(t("kpi_valeur_a_risque"), format_fcfa_compact(zone_rouge["solde_total_xof"].sum()))

# --- Distribution des scores de risque --------------------------------------------
afficher_entete_section(t("titre_distribution_scores"))

fig_hist = px.histogram(df, x="risque_composite", nbins=30, labels={"risque_composite": t("score_de_risque")})
fig_hist.update_traces(marker_color=COULEUR_POSITIF)
fig_hist.add_vrect(x0=40, x1=70, fillcolor=COULEUR_ATTENTION, opacity=0.12, line_width=0)
fig_hist.add_vrect(x0=70, x1=100, fillcolor=COULEUR_CRITIQUE, opacity=0.12, line_width=0)
fig_hist.add_vline(x=40, line_dash="dash", line_color=COULEUR_ATTENTION)
fig_hist.add_vline(x=70, line_dash="dash", line_color=COULEUR_CRITIQUE)
fig_hist.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
st.plotly_chart(fig_hist, width='stretch')

zone_saine = df[df["risque_composite"] < 40]
st.caption(
    f"🟢 {t('zone_clients_sains')} — {len(zone_saine)} clients · "
    f"{format_fcfa_compact(zone_saine['solde_total_xof'].sum())}"
    f"   ·   🟠 {t('zone_clients_surveiller')} — {len(zone_ambre)} clients · "
    f"{format_fcfa_compact(zone_ambre['solde_total_xof'].sum())}"
    f"   ·   🔴 {t('zone_action_urgente')} — {len(zone_rouge)} clients · "
    f"{format_fcfa_compact(zone_rouge['solde_total_xof'].sum())}"
)
if len(zone_rouge) > 0:
    st.warning(t("encadre_zone_rouge").format(
        n=len(zone_rouge), montant=format_fcfa_compact(zone_rouge["solde_total_xof"].sum()),
    ))

# --- Clients à risque : onglets ---------------------------------------------------
afficher_entete_section(t("tableau_segment_titre"))

onglet_rouge, onglet_ambre, onglet_reclamations = st.tabs([
    t("onglet_zone_rouge"), t("onglet_a_surveiller"), t("onglet_reclamations_ouvertes"),
])


def afficher_liste_clients(sous_ensemble: pd.DataFrame, badge_type: str) -> None:
    # Une carte par client : badge segment, barre de score colorée, action
    # recommandée en badge — l'idiome déjà établi dans ce dashboard pour tout
    # tableau nécessitant des pastilles HTML (st.dataframe ne les rend pas)
    # One card per customer: segment badge, colored score bar, recommended
    # action as a badge — the idiom already established in this dashboard for
    # any table needing HTML pills (st.dataframe can't render them)
    if sous_ensemble.empty:
        st.info(t("aucun_client_zone"))
        return
    for _, ligne in sous_ensemble.iterrows():
        with st.container(border=True):
            col_info, col_score, col_action = st.columns([2, 2, 1.5])
            with col_info:
                st.markdown(f"**{ligne['full_name']}**  {badge_segment(ligne['segment'])}", unsafe_allow_html=True)
                st.caption(
                    f"{t('col_jours_inactif')} : {int(ligne['recency_jours'])}"
                    f"  ·  {t('col_reclamations')} : {int(ligne['nb_reclamations_ouvertes'])}"
                    f"  ·  {t('col_solde_m_fcfa')} : {ligne['solde_total_xof'] / 1_000_000:.1f}"
                )
            with col_score:
                afficher_barre_score(ligne["risque_composite"], t("col_score_risque"))
            with col_action:
                texte_action = t("action_appel_urgent") if badge_type == "danger" else t("action_offre_fidelisation")
                st.markdown(badge_action(texte_action, badge_type), unsafe_allow_html=True)
                if ligne.get("next_best_action"):
                    st.caption(f"{t('col_action_recommandee')} : {ligne['next_best_action']}")


colonnes_export = [
    "customer_id", "full_name", "segment", "risque_composite", "recency_jours",
    "nb_reclamations_ouvertes", "solde_total_xof", "next_best_action",
]

with onglet_rouge:
    afficher_liste_clients(zone_rouge, "danger")
    if len(zone_rouge) > 0:
        st.download_button(
            t("exporter_csv"), zone_rouge[colonnes_export].to_csv(index=False).encode("utf-8"),
            "clients_zone_rouge.csv", "text/csv", width='stretch',
        )

with onglet_ambre:
    afficher_liste_clients(zone_ambre, "warning")
    if len(zone_ambre) > 0:
        st.download_button(
            t("exporter_csv"), zone_ambre[colonnes_export].to_csv(index=False).encode("utf-8"),
            "clients_a_surveiller.csv", "text/csv", width='stretch',
        )

with onglet_reclamations:
    afficher_liste_clients(reclamations_ouvertes, "warning")
    if len(reclamations_ouvertes) > 0:
        st.download_button(
            t("exporter_csv"), reclamations_ouvertes[colonnes_export].to_csv(index=False).encode("utf-8"),
            "clients_reclamations_ouvertes.csv", "text/csv", width='stretch',
        )

# --- Analyse des réclamations ------------------------------------------------------
afficher_entete_section(t("analyse_reclamations"))

col_gauche, col_droite = st.columns(2)
try:
    complaints = requete_duckdb(
        """
        SELECT customer_id, category, severity, status
        FROM main_staging.stg_complaints
        WHERE status = 'Open'
        """
    )
except Exception:
    complaints = pd.DataFrame()

with col_gauche:
    if not complaints.empty:
        par_categorie = complaints.groupby(["category", "severity"]).size().reset_index(name="n")
        fig_categories = px.bar(
            par_categorie, x="n", y="category", color="severity", orientation="h",
            color_discrete_map={"Low": COULEUR_POSITIF, "Medium": COULEUR_ATTENTION, "High": COULEUR_CRITIQUE},
            title=t("titre_reclamations_categorie"),
            labels={"n": t("kpi_reclamations_ouvertes"), "category": ""},
        )
        fig_categories.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_categories, width='stretch')
    else:
        st.info(t("aucun_client_zone"))

with col_droite:
    df_scatter = df.merge(
        complaints.groupby("customer_id").size().rename("n_reclamations_ouvertes").reset_index(),
        on="customer_id", how="left",
    )
    df_scatter["n_reclamations_ouvertes"] = df_scatter["n_reclamations_ouvertes"].fillna(0)
    fig_reclamations_risque = px.scatter(
        df_scatter, x="n_reclamations_ouvertes", y="risque_composite", color="segment",
        labels={
            "n_reclamations_ouvertes": label_technique("nb_reclamations_ouvertes"),
            "risque_composite": t("score_de_risque"),
        },
        title=t("titre_reclamations_vs_risque"), hover_name="customer_id",
    )
    if df_scatter["n_reclamations_ouvertes"].nunique() > 1:
        pente, ordonnee = np.polyfit(df_scatter["n_reclamations_ouvertes"], df_scatter["risque_composite"], 1)
        x_ligne = np.array([df_scatter["n_reclamations_ouvertes"].min(), df_scatter["n_reclamations_ouvertes"].max()])
        fig_reclamations_risque.add_scatter(
            x=x_ligne, y=pente * x_ligne + ordonnee, mode="lines",
            line=dict(color=COULEUR_CRITIQUE, dash="dash"), showlegend=False,
        )
    fig_reclamations_risque.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_reclamations_risque, width='stretch')
    st.caption(t("encadre_reclamations_risque"))

afficher_pied_de_page()
