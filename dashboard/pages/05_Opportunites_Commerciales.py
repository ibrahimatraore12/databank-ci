# Opportunités commerciales - répond à "qui peut prendre quel produit cette
# semaine, et combien ça vaut ?", à partir des taux d'acceptation historiques réels
# Commercial opportunities - answers "who can take which product this week,
# and how much is it worth?", from real historical acceptance rates

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from components.charts import COULEUR_ACCENT, PALETTE_CATEGORIELLE  # noqa: E402
from components.ui import (  # noqa: E402
    afficher_carte_kpi, afficher_entete, afficher_entete_section, afficher_guide, afficher_pied_de_page,
    format_fcfa, format_fcfa_compact, format_pct, requete_duckdb, t,
)

st.set_page_config(page_title="Opportunités Commerciales", page_icon="🏦", layout="wide")

afficher_entete(t("nav_opportunites"), t("soustitre_opportunites"), "💡")
afficher_guide(t("guide_opportunites"))

try:
    df = requete_duckdb("SELECT * FROM main_marts.customer_360")
    historique_offres = requete_duckdb(
        """
        SELECT offer_type, count(*) as n, avg(accepted_flag::int) as taux_acceptation,
               avg(expected_value_xof) as valeur_moyenne
        FROM main_staging.stg_offers
        GROUP BY offer_type
        """
    )
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    afficher_pied_de_page()
    st.stop()

taux_moyen_global = historique_offres["taux_acceptation"].mean()
meilleure_offre = historique_offres.sort_values("taux_acceptation", ascending=False).iloc[0]

# La probabilité d'acceptation d'un client ciblé est le taux historique réel de
# l'offre la plus proche de son besoin (Card upgrade pour cross-sell carte) - pas
# un score prédictif par client, qu'aucun modèle de ce projet ne calcule
# A targeted customer's acceptance probability is the real historical rate of the
# closest matching offer (Card upgrade for card cross-sell) - not a per-customer
# predictive score, which no model in this project computes
taux_card_upgrade = historique_offres.loc[historique_offres["offer_type"] == "Card upgrade", "taux_acceptation"]
taux_card_upgrade = float(taux_card_upgrade.iloc[0]) if not taux_card_upgrade.empty else taux_moyen_global
valeur_card_upgrade = historique_offres.loc[historique_offres["offer_type"] == "Card upgrade", "valeur_moyenne"]
valeur_card_upgrade = float(valeur_card_upgrade.iloc[0]) if not valeur_card_upgrade.empty else 0

# --- KPIs --------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
nb_cross_sell = int(df["is_cross_sell_target"].sum())
nb_upsell = int(df["is_salary_upsell_opportunity"].sum())
potentiel_total = nb_cross_sell * valeur_card_upgrade * taux_card_upgrade + \
    nb_upsell * historique_offres["valeur_moyenne"].mean() * taux_moyen_global

with col1:
    afficher_carte_kpi(t("kpi_potentiel_cross_sell"), format_fcfa_compact(potentiel_total))
with col2:
    afficher_carte_kpi(t("kpi_clients_sans_carte"), str(nb_cross_sell))
with col3:
    afficher_carte_kpi(t("kpi_taux_conversion_moyen"), format_pct(100 * taux_moyen_global))
with col4:
    afficher_carte_kpi(
        t("kpi_meilleure_offre"), meilleure_offre["offer_type"], format_pct(100 * meilleure_offre["taux_acceptation"]),
    )

# --- Matrice de priorisation des types d'offres -------------------------------
afficher_entete_section(t("titre_matrice_opportunites"))

historique_offres["valeur_m"] = historique_offres["valeur_moyenne"] / 1_000_000
historique_offres["taux_pct"] = 100 * historique_offres["taux_acceptation"]

fig_matrice = px.scatter(
    historique_offres, x="taux_pct", y="valeur_m", size="n", color="offer_type", text="offer_type",
    color_discrete_sequence=PALETTE_CATEGORIELLE,
    labels={
        "taux_pct": t("axe_probabilite_acceptation"), "valeur_m": t("axe_valeur_potentielle"),
        "offer_type": t("col_type"),
    },
)
fig_matrice.update_traces(textposition="top center")
x_mid, y_mid = historique_offres["taux_pct"].mean(), historique_offres["valeur_m"].mean()
x_max = historique_offres["taux_pct"].max() * 1.2
y_max = historique_offres["valeur_m"].max() * 1.2
fig_matrice.add_shape(
    type="rect", x0=x_mid, x1=x_max, y0=y_mid, y1=y_max, fillcolor="#1E8449", opacity=0.07, line_width=0,
)
fig_matrice.add_shape(
    type="rect", x0=0, x1=x_mid, y0=y_mid, y1=y_max, fillcolor="#F39C12", opacity=0.07, line_width=0,
)
fig_matrice.add_shape(
    type="rect", x0=x_mid, x1=x_max, y0=0, y1=y_mid, fillcolor="#2E86C1", opacity=0.07, line_width=0,
)
fig_matrice.add_shape(
    type="rect", x0=0, x1=x_mid, y0=0, y1=y_mid, fillcolor="#6B6B6B", opacity=0.05, line_width=0,
)
fig_matrice.add_annotation(x=x_mid + (x_max - x_mid) / 2, y=y_max * 0.97, text=t("quadrant_priorite_absolue"),
                           showarrow=False, font=dict(color="#1E8449", size=11))
fig_matrice.add_annotation(x=x_mid / 2, y=y_max * 0.97, text=t("quadrant_valeur_elevee"),
                           showarrow=False, font=dict(color="#F39C12", size=11))
fig_matrice.add_annotation(x=x_mid + (x_max - x_mid) / 2, y=y_mid * 0.1, text=t("quadrant_volume_facile"),
                           showarrow=False, font=dict(color="#2E86C1", size=11))
fig_matrice.add_annotation(x=x_mid / 2, y=y_mid * 0.1, text=t("quadrant_non_prioritaire"),
                           showarrow=False, font=dict(color="#6B6B6B", size=11))
fig_matrice.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
st.plotly_chart(fig_matrice, width='stretch')
st.info(f"💡 {t('encadre_matrice_opportunites')}")

# --- Entonnoir de conversion ---------------------------------------------------
afficher_entete_section(t("titre_entonnoir_conversion"))
top3 = historique_offres.sort_values("n", ascending=False).head(3)
cols_entonnoir = st.columns(3)
for col, (_, ligne) in zip(cols_entonnoir, top3.iterrows()):
    with col:
        nb_acceptes = int(round(ligne["n"] * ligne["taux_acceptation"]))
        fig_funnel = go.Figure(go.Funnel(
            y=[t("funnel_cibles"), t("funnel_acceptes")],
            x=[int(ligne["n"]), nb_acceptes],
            marker=dict(color=[COULEUR_ACCENT, "#1E8449"]),
        ))
        fig_funnel.update_layout(
            title=str(ligne["offer_type"]), height=260, margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_funnel, width='stretch')
        st.caption(f"{format_pct(100 * ligne['taux_acceptation'])}")

if len(top3) >= 2:
    meilleur, second = top3.sort_values("taux_acceptation", ascending=False).iloc[0], \
        top3.sort_values("taux_acceptation", ascending=False).iloc[1]
    ratio = meilleur["taux_acceptation"] / second["taux_acceptation"] if second["taux_acceptation"] else 1
    st.caption(f"« {meilleur['offer_type']} » convertit {ratio:.1f}× mieux que « {second['offer_type']} ».")

# --- Liste des opportunités par client -----------------------------------------
afficher_entete_section(t("titre_liste_opportunites"))

col_filtre_segment, col_filtre_type = st.columns(2)
with col_filtre_segment:
    segments_filtre = st.multiselect(t("selectionner_segment"), sorted(df["segment"].unique().tolist()))
with col_filtre_type:
    type_filtre = st.selectbox(
        t("col_type"), [t("tous_les_segments")] + [t("cible_cross_sell"), t("opportunite_upsell_salaire")],
    )

opportunites = df[df["is_cross_sell_target"] | df["is_salary_upsell_opportunity"]].copy()
if segments_filtre:
    opportunites = opportunites[opportunites["segment"].isin(segments_filtre)]
if type_filtre == t("cible_cross_sell"):
    opportunites = opportunites[opportunites["is_cross_sell_target"]]
elif type_filtre == t("opportunite_upsell_salaire"):
    opportunites = opportunites[opportunites["is_salary_upsell_opportunity"]]

opportunites["offre_recommandee"] = opportunites.apply(
    lambda r: "Card upgrade" if r["is_cross_sell_target"] else t("opportunite_upsell_salaire"), axis=1,
)
opportunites["probabilite"] = opportunites["is_cross_sell_target"].apply(
    lambda cross: 100 * (taux_card_upgrade if cross else taux_moyen_global),
)
opportunites["valeur_potentielle"] = opportunites.apply(
    lambda r: valeur_card_upgrade if r["is_cross_sell_target"] else r["monthly_income_xof"] * 0.02, axis=1,
)

if not opportunites.empty:
    montant_total = opportunites["valeur_potentielle"].sum()
    st.info(f"💰 {t('kpi_potentiel_cross_sell')} : {format_fcfa_compact(montant_total)} "
            f"sur {len(opportunites)} clients ciblés.")

    tableau = pd.DataFrame({
        t("col_client"): opportunites["full_name"],
        t("segment_client"): opportunites["segment"],
        t("col_opportunite"): opportunites["offre_recommandee"],
        t("col_probabilite"): opportunites["probabilite"].apply(format_pct),
        t("col_valeur_potentielle"): opportunites["valeur_potentielle"].apply(format_fcfa),
        t("salaire_domicilie"): opportunites["salaire_domicilie"].map({True: "✅", False: "❌"}),
        t("canal_prefere"): opportunites["preferred_channel"],
    })
    proba_brute = opportunites["probabilite"].reset_index(drop=True)

    def _couleur_ligne(ligne: pd.Series) -> list:
        # Vert clair si forte probabilité, ambre si modérée, gris sinon
        # Light green if high probability, amber if moderate, gray otherwise
        proba = proba_brute.iloc[ligne.name]
        couleur = "#EAF7EF" if proba > 80 else "#FFFDF5" if proba >= 60 else "#F5F5F5"
        return [f"background-color: {couleur}"] * len(ligne)

    tableau_stylise = tableau.reset_index(drop=True).style.apply(_couleur_ligne, axis=1)
    st.dataframe(tableau_stylise, width='stretch', hide_index=True)
    st.download_button(
        t("exporter_liste_appels"), tableau.to_csv(index=False).encode("utf-8"),
        "opportunites_commerciales.csv", "text/csv",
    )
else:
    st.info(t("aucun_client_zone"))

afficher_pied_de_page()
