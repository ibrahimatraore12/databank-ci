# Composition du portefeuille clients — répond à "mon portefeuille est-il en
# bonne santé ce matin ?" avec des KPIs et graphiques actionnables
# Customer portfolio composition — answers "is my portfolio healthy this
# morning?" with actionable KPIs and charts

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from components.charts import (  # noqa: E402
    COULEUR_ATTENTION, COULEUR_CRITIQUE, COULEUR_POSITIF,
    graphique_camembert, graphique_nuage_valeur_engagement, graphique_pyramide_valeur,
)
from components.ui import (  # noqa: E402
    afficher_entete, afficher_pied_de_page, format_fcfa_compact, format_pct, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="Portefeuille Clients", page_icon="🏦", layout="wide")

afficher_entete(t("nav_portefeuille"), t("page_portefeuille_intro"))

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

# --- KPIs ------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1, st.container(border=True):
    nb_actifs = int((df["recency_jours"] <= 30).sum())
    st.metric(
        t("kpi_clients_actifs"), f"{nb_actifs} / {len(df)}",
        delta=format_pct(100 * nb_actifs / len(df)) if len(df) else None, delta_color="off",
    )

with col2, st.container(border=True):
    st.metric(t("kpi_nbi_estime_total"), format_fcfa_compact(df["nbi_estime_xof"].sum()))
    st.caption(t("kpi_nbi_sous_label"))

with col3, st.container(border=True):
    st.metric(t("kpi_solde_total_gere"), format_fcfa_compact(df["solde_total_xof"].sum()))

with col4, st.container(border=True):
    taux_risque_eleve = 100 * (df["risk_band"] == "High").mean() if len(df) else 0
    couleur = COULEUR_CRITIQUE if taux_risque_eleve > 5 else (
        COULEUR_POSITIF if taux_risque_eleve < 3 else COULEUR_ATTENTION
    )
    st.markdown(f"<div style='font-size:0.8rem;color:#888;'>{t('kpi_taux_risque_eleve')}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:1.75rem;font-weight:600;color:{couleur};'>{format_pct(taux_risque_eleve)}</div>",
        unsafe_allow_html=True,
    )

st.divider()

# --- Scatter décisionnel : valeur vs engagement -----------------------------
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

# Zone verte (clients actifs) dessinée en premier, ambre par-dessus, rouge en dernier —
# les zones se chevauchent volontairement (ex. x>60 satisfait aussi la zone ambre)
# Green zone (active customers) drawn first, amber on top, red last — zones
# intentionally overlap (e.g. x>60 also satisfies the amber zone)
fig_scatter.add_shape(type="rect", x0=0, x1=30, y0=0, y1=y_max,
                      fillcolor=COULEUR_POSITIF, opacity=0.10, line_width=0)
fig_scatter.add_shape(type="rect", x0=30, x1=x_max, y0=1, y1=y_max,
                      fillcolor=COULEUR_ATTENTION, opacity=0.12, line_width=0)
fig_scatter.add_shape(type="rect", x0=60, x1=x_max, y0=5, y1=y_max,
                      fillcolor=COULEUR_CRITIQUE, opacity=0.15, line_width=0)
fig_scatter.add_annotation(x=15, y=y_max * 0.95, text=t("zone_clients_actifs"), showarrow=False)
fig_scatter.add_annotation(x=(30 + x_max) / 2, y=y_max * 0.8, text=t("zone_a_surveiller"), showarrow=False)
fig_scatter.add_annotation(x=(60 + x_max) / 2, y=y_max * 0.98, text=t("zone_vip_inactifs"), showarrow=False)

solde_a_risque = df.loc[
    (df["recency_jours"] > 60) & (df["solde_total_xof"] > 5_000_000), "solde_total_xof",
].sum()
st.plotly_chart(fig_scatter, width='stretch')
st.caption(t("annotation_scatter_risque").format(montant=format_fcfa_compact(solde_a_risque)))

st.divider()

# --- Pyramide de valeur par segment -----------------------------------------
agg_segment = df.groupby("segment").agg(
    solde_total_xof=("solde_total_xof", "sum"),
    nbi_estime_xof=("nbi_estime_xof", "sum"),
    nb_clients=("customer_id", "count"),
).reset_index()
agg_segment["solde_M"] = agg_segment["solde_total_xof"] / 1_000_000
agg_segment["nbi_M"] = agg_segment["nbi_estime_xof"] / 1_000_000
agg_segment = agg_segment.sort_values("solde_M", ascending=True)

labels_pyramide = {
    "valeur": t("solde_total") + " / " + t("nbi_estime") + " (M)",
    "segment": t("segment_client"),
    "solde_M": t("solde_total") + " (M)",
    "nbi_M": t("nbi_estime") + " (M)",
}
st.plotly_chart(
    graphique_pyramide_valeur(agg_segment, "segment", "solde_M", "nbi_M",
                              titre=t("titre_pyramide_valeur"), labels=labels_pyramide),
    width='stretch',
)

if agg_segment["nbi_estime_xof"].sum() > 0 and len(df) > 0:
    part_nbi_premier = 100 * agg_segment.loc[agg_segment["segment"] == "Premier", "nbi_estime_xof"].sum() \
        / agg_segment["nbi_estime_xof"].sum()
    part_clients_premier = 100 * (df["segment"] == "Premier").sum() / len(df)
    st.caption(t("annotation_pyramide").format(
        pct_nbi=format_pct(part_nbi_premier), pct_clients=format_pct(part_clients_premier),
    ))

st.divider()

# --- Donuts segment et risque, avec valeur absolue dans chaque part --------
col_gauche, col_droite = st.columns(2)
with col_gauche:
    repartition_segment = df["segment"].value_counts().reset_index()
    repartition_segment.columns = ["segment", "nb_clients"]
    repartition_segment["libelle"] = repartition_segment["segment"] + " (" \
        + repartition_segment["nb_clients"].astype(str) + ")"
    st.plotly_chart(
        graphique_camembert(repartition_segment, "libelle", "nb_clients", label_technique("segment")),
        width='stretch',
    )

with col_droite:
    repartition_risque = df["risk_band"].value_counts().reset_index()
    repartition_risque.columns = ["risk_band", "nb_clients"]
    repartition_risque["libelle"] = repartition_risque["risk_band"] + " (" \
        + repartition_risque["nb_clients"].astype(str) + ")"
    st.plotly_chart(
        graphique_camembert(repartition_risque, "libelle", "nb_clients", label_technique("risk_band")),
        width='stretch',
    )

st.divider()

# --- Alerte automatique : part de clients à risque élevé --------------------
if len(df) and 100 * (df["risk_band"] == "High").mean() > 5:
    clients_risque = df[df["risk_band"] == "High"]
    st.warning(t("alerte_risque_solde").format(
        n=len(clients_risque), solde=format_fcfa_compact(clients_risque["solde_total_xof"].sum()),
    ))
    with st.expander(t("voir_la_liste")):
        colonnes_alerte = ["customer_id", "full_name", "segment", "city", "solde_total_xof", "recency_jours"]
        tableau_alerte = clients_risque[colonnes_alerte].rename(
            columns={c: label_technique(c) for c in colonnes_alerte},
        )
        st.dataframe(tableau_alerte, width='stretch', hide_index=True)

st.divider()

# --- Tableau récapitulatif par segment --------------------------------------
st.subheader(t("tableau_segment_titre"))


def action_prioritaire(ligne: pd.Series) -> str:
    # Règle simple : risque moyen élevé d'abord, puis engagement faible,
    # sinon la relation est jugée saine
    # Simple rule: high average risk first, then low engagement, otherwise
    # the relationship is considered healthy
    if ligne["risque_composite_moyen"] > 40:
        return t("action_renforcer_suivi")
    if ligne["taux_actifs"] < 70:
        return t("action_campagne_reactivation")
    return t("action_maintenir_relation")


recap = df.groupby("segment").agg(
    nb_clients=("customer_id", "count"),
    solde_moyen=("solde_total_xof", "mean"),
    revenu_moyen=("monthly_income_xof", "mean"),
    taux_actifs=("recency_jours", lambda s: 100 * (s <= 30).mean()),
    score_digital_moyen=("score_digital", "mean"),
    nbi_estime=("nbi_estime_xof", "mean"),
    risque_composite_moyen=("risque_composite", "mean"),
).reset_index()
recap["action_prioritaire"] = recap.apply(action_prioritaire, axis=1)

tableau_recap = pd.DataFrame({
    t("segment_client"): recap["segment"],
    t("kpi_nombre_clients"): recap["nb_clients"],
    t("col_solde_moyen"): recap["solde_moyen"].apply(format_fcfa_compact),
    t("col_revenu_moyen"): recap["revenu_moyen"].apply(format_fcfa_compact),
    t("col_taux_actifs"): recap["taux_actifs"].apply(format_pct),
    t("col_score_digital_moyen"): recap["score_digital_moyen"].round(1),
    t("nbi_estime"): recap["nbi_estime"].apply(format_fcfa_compact),
    t("col_action_prioritaire"): recap["action_prioritaire"],
})
st.dataframe(tableau_recap, width='stretch', hide_index=True)

afficher_pied_de_page()
