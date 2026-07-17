# Composition du portefeuille clients - répond à "mon portefeuille est-il en
# bonne santé ?" avec des KPIs et graphiques actionnables
# Customer portfolio composition - answers "is my portfolio healthy?" with
# actionable KPIs and charts

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from components.charts import (  # noqa: E402
    RISK_COLOR_MAP, SEGMENT_COLOR_MAP, graphique_camembert, graphique_nuage_valeur_engagement,
    graphique_pyramide_valeur,
)
from components.ui import (  # noqa: E402
    afficher_alerte, afficher_carte_kpi, afficher_entete, afficher_entete_section, afficher_guide,
    afficher_pied_de_page, format_fcfa_compact, format_pct, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="Portefeuille Clients", page_icon="🏦", layout="wide")

afficher_entete(t("nav_portefeuille"), t("soustitre_portefeuille"))
afficher_guide(t("page_portefeuille_intro"))

try:
    df = requete_duckdb("SELECT * FROM main_marts.customer_360")
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    afficher_pied_de_page()
    st.stop()

segments_disponibles = [t("tous_les_segments")] + sorted(df["segment"].unique().tolist())
segment_choisi = st.selectbox(t("selectionner_segment"), segments_disponibles)
if segment_choisi != t("tous_les_segments"):
    df = df[df["segment"] == segment_choisi]

df["solde_M"] = df["solde_total_xof"] / 1_000_000

# --- KPIs --------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    nb_actifs = int((df["recency_jours"] <= 30).sum())
    taux_actifs = 100 * nb_actifs / len(df) if len(df) else 0
    type_carte = "success" if taux_actifs > 80 else "warning" if taux_actifs >= 60 else "danger"
    afficher_carte_kpi(
        t("kpi_clients_actifs"), f"{nb_actifs} / {len(df)}", format_pct(taux_actifs), type_carte,
    )

with col2:
    afficher_carte_kpi(
        t("kpi_nbi_annuel_estime"), format_fcfa_compact(df["nbi_estime_xof"].sum()),
        t("kpi_nbi_sous_label"),
    )

with col3:
    afficher_carte_kpi(t("kpi_solde_total_gere"), format_fcfa_compact(df["solde_total_xof"].sum()))

with col4:
    taux_risque_eleve = 100 * (df["risk_band"] == "High").mean() if len(df) else 0
    type_carte = (
        "danger" if taux_risque_eleve > 5 else "warning" if taux_risque_eleve >= 3 else "success"
    )
    afficher_carte_kpi(
        t("kpi_taux_risque_eleve_court"), format_pct(taux_risque_eleve), "", type_carte,
    )

# --- Scatter décisionnel : valeur vs engagement ---
afficher_entete_section(t("titre_valeur_engagement"))

labels_scatter = {
    "recency_jours": label_technique("recency_jours"),
    "solde_M": t("solde_total") + " (M)",
}
fig_scatter = graphique_nuage_valeur_engagement(
    df, "recency_jours", "solde_M", "segment", "nbi_estime_xof",
    titre=t("titre_scatter_valeur_engagement"), labels=labels_scatter,
)

x_max = max(float(df["recency_jours"].max() or 0) * 1.05, 61)
y_max = max(float(df["solde_M"].max() or 0) * 1.05, 6)

# Zone verte (clients actifs) dessinée en premier, ambre par-dessus, rouge en dernier -
# les zones se chevauchent volontairement (ex. x>60 satisfait aussi la zone ambre)
# Green zone (active customers) drawn first, amber on top, red last - zones
# intentionally overlap (e.g. x>60 also satisfies the amber zone)
fig_scatter.add_shape(
    type="rect", x0=0, x1=30, y0=0, y1=y_max,
    fillcolor=RISK_COLOR_MAP["Low"], opacity=0.10, line_width=0,
)
fig_scatter.add_shape(
    type="rect", x0=30, x1=x_max, y0=1, y1=y_max,
    fillcolor=RISK_COLOR_MAP["Medium"], opacity=0.12, line_width=0,
)
fig_scatter.add_shape(
    type="rect", x0=60, x1=x_max, y0=5, y1=y_max,
    fillcolor=RISK_COLOR_MAP["High"], opacity=0.15, line_width=0,
)
fig_scatter.add_annotation(x=15, y=y_max * 0.95, text=t("zone_clients_actifs"), showarrow=False)
fig_scatter.add_annotation(
    x=(30 + x_max) / 2, y=y_max * 0.8, text=t("zone_a_surveiller"), showarrow=False,
)
fig_scatter.add_annotation(
    x=(60 + x_max) / 2, y=y_max * 0.98, text=t("zone_vip_inactifs"), showarrow=False,
)

col_scatter, col_donuts = st.columns([3, 2])
with col_scatter:
    solde_a_risque = df.loc[
        (df["recency_jours"] > 60) & (df["solde_total_xof"] > 5_000_000), "solde_total_xof",
    ].sum()
    st.plotly_chart(fig_scatter, width='stretch')
    st.caption(t("annotation_scatter_risque").format(montant=format_fcfa_compact(solde_a_risque)))

with col_donuts:
    repartition_segment = df["segment"].value_counts().reset_index()
    repartition_segment.columns = ["segment", "nb_clients"]
    repartition_segment["libelle"] = (
        repartition_segment["segment"] + " (" + repartition_segment["nb_clients"].astype(str) + ")"
    )
    st.plotly_chart(
        graphique_camembert(
            repartition_segment, "libelle", "nb_clients", label_technique("segment"),
            color_col="segment", color_map=SEGMENT_COLOR_MAP,
        ),
        width='stretch',
    )

    repartition_risque = df["risk_band"].value_counts().reset_index()
    repartition_risque.columns = ["risk_band", "nb_clients"]
    repartition_risque["libelle"] = (
        repartition_risque["risk_band"] + " (" + repartition_risque["nb_clients"].astype(str) + ")"
    )
    st.plotly_chart(
        graphique_camembert(
            repartition_risque, "libelle", "nb_clients", t("titre_donut_risque"),
            color_col="risk_band", color_map=RISK_COLOR_MAP,
        ),
        width='stretch',
    )
    clients_risque_eleve = df[df["risk_band"] == "High"]
    solde_risque_eleve = clients_risque_eleve["solde_total_xof"].sum()
    st.caption(t("libelle_clients_risque_eleve").format(
        n=len(clients_risque_eleve), montant=format_fcfa_compact(solde_risque_eleve),
    ))

# --- Analyse par segment ------------------------------------------------------
afficher_entete_section(t("tableau_segment_titre"))


def action_prioritaire(ligne: pd.Series) -> str:
    # Règle simple : risque moyen élevé d'abord, puis engagement faible,
    # sinon la relation est jugée saine
    # Simple rule: high average risk first, then low engagement, otherwise
    # the relationship is considered healthy
    if ligne["risque_composite_moyen"] > 40:
        return "🔴 " + t("action_renforcer_suivi")
    if ligne["taux_actifs"] < 70:
        return "🟠 " + t("action_campagne_reactivation")
    return "🟢 " + t("action_maintenir_relation")


recap = df.groupby("segment").agg(
    nb_clients=("customer_id", "count"),
    solde_total=("solde_total_xof", "sum"),
    solde_moyen=("solde_total_xof", "mean"),
    revenu_moyen=("monthly_income_xof", "mean"),
    taux_actifs=("recency_jours", lambda s: 100 * (s <= 30).mean()),
    score_digital_moyen=("score_digital", "mean"),
    nbi_estime=("nbi_estime_xof", "mean"),
    nbi_total=("nbi_estime_xof", "sum"),
    risque_composite_moyen=("risque_composite", "mean"),
).reset_index()
recap["action_prioritaire"] = recap.apply(action_prioritaire, axis=1)
recap["pct_clients"] = 100 * recap["nb_clients"] / recap["nb_clients"].sum()
recap["pct_solde"] = 100 * recap["solde_total"] / recap["solde_total"].sum()

col_solde_moyen, col_contribution = st.columns(2)
with col_solde_moyen:
    recap_tri_solde = recap.sort_values("solde_moyen", ascending=True)
    fig_solde = px.bar(
        recap_tri_solde, x="solde_moyen", y="segment", orientation="h", color="segment",
        color_discrete_map=SEGMENT_COLOR_MAP, title=t("titre_solde_moyen_segment"),
        labels={"solde_moyen": t("col_solde_moyen") + " (FCFA)", "segment": t("segment_client")},
        text=recap_tri_solde["solde_moyen"].apply(format_fcfa_compact),
    )
    fig_solde.update_traces(textposition="outside")
    fig_solde.update_layout(
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_solde, width='stretch')
    st.caption(t("soustitre_solde_moyen_segment"))

with col_contribution:
    contribution = recap.rename(
        columns={"pct_clients": t("serie_pct_clients"), "pct_solde": t("serie_pct_solde")},
    )
    st.plotly_chart(
        graphique_pyramide_valeur(
            contribution, "segment", t("serie_pct_clients"), t("serie_pct_solde"),
            titre=t("titre_contribution_portefeuille"),
            labels={"segment": t("segment_client"), "valeur": "%"},
        ),
        width='stretch',
    )
    ligne_premier = recap[recap["segment"] == "Premier"]
    if not ligne_premier.empty:
        st.caption(t("annotation_contribution_premier").format(
            pct_clients=format_pct(ligne_premier["pct_clients"].iloc[0]),
            pct_solde=format_pct(ligne_premier["pct_solde"].iloc[0]),
        ))

# --- Alerte automatique : part de clients à risque élevé -----------------------
# Le tableau de bord doit montrer autant les signaux positifs que les risques :
# si le portefeuille est sain, on le dit clairement plutôt que de rester muet
# The dashboard must surface positive signals as much as risks: if the
# portfolio is healthy, say so clearly rather than staying silent
if len(df):
    part_risque_eleve = 100 * (df["risk_band"] == "High").mean()
    if part_risque_eleve > 5:
        clients_risque = df[df["risk_band"] == "High"]
        afficher_alerte(
            t("alerte_risque_solde").format(
                n=len(clients_risque), solde=format_fcfa_compact(clients_risque["solde_total_xof"].sum()),
            ),
            "warning", "⚠️",
        )
        with st.expander(t("voir_la_liste")):
            colonnes_alerte = [
                "customer_id", "full_name", "segment", "city", "solde_total_xof", "recency_jours",
            ]
            tableau_alerte = clients_risque[colonnes_alerte].rename(
                columns={c: label_technique(c) for c in colonnes_alerte},
            )
            st.dataframe(tableau_alerte, width='stretch', hide_index=True)
    else:
        afficher_alerte(
            t("alerte_portefeuille_sain").format(pct=format_pct(part_risque_eleve)),
            "success", "✅",
        )

# --- Tableau récapitulatif par segment -----------------------------------------
afficher_entete_section(t("titre_tableau_segment"))

recap_tri_nbi = recap.sort_values("nbi_total", ascending=False)
tableau_recap = pd.DataFrame({
    t("segment_client"): recap_tri_nbi["segment"],
    t("col_nb_clients"): recap_tri_nbi["nb_clients"],
    t("col_solde_moyen"): recap_tri_nbi["solde_moyen"].apply(format_fcfa_compact),
    t("col_nbi_estime"): recap_tri_nbi["nbi_estime"].apply(format_fcfa_compact),
    t("col_taux_actifs"): recap_tri_nbi["taux_actifs"].apply(format_pct),
    t("col_score_digital_moyen"): recap_tri_nbi["score_digital_moyen"].round(1),
    t("col_action_prioritaire"): recap_tri_nbi["action_prioritaire"],
})
st.dataframe(tableau_recap, width='stretch', hide_index=True)

afficher_pied_de_page()
