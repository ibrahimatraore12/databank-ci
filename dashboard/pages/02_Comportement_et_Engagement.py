# Engagement digital et comportement transactionnel des clients — répond à
# "qui s'engage et qui se désengage ?"
# Digital engagement and transaction behavior of customers — answers "who is
# engaging and who is disengaging?"

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from components.charts import (  # noqa: E402
    COULEUR_CRITIQUE, COULEUR_ORANGE_ACTION, COULEUR_SIDEBAR, RISK_COLOR_MAP, SEGMENT_COLOR_MAP,
)
from components.ui import (  # noqa: E402
    afficher_carte_kpi, afficher_entete, afficher_entete_section, afficher_guide, afficher_pied_de_page,
    format_fcfa_compact, format_pct, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="Comportement et Engagement", page_icon="🏦", layout="wide")

afficher_entete(t("nav_comportement"), t("soustitre_comportement"))
afficher_guide(t("guide_comportement"))

try:
    df = requete_duckdb("SELECT * FROM main_marts.customer_360")
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    afficher_pied_de_page()
    st.stop()

# --- KPIs ----------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    taux_digital = 100 * (
        df["mobile_app_active"] | df["internet_banking_active"] | df["mobile_money_linked"]
    ).mean()
    type_carte = "success" if taux_digital > 80 else "warning" if taux_digital >= 60 else "danger"
    afficher_carte_kpi(t("kpi_taux_adoption_digitale"), format_pct(taux_digital), "", type_carte)

with col2:
    afficher_carte_kpi(t("solde_moyen_90_jours"), format_fcfa_compact(df["avg_balance_90d_xof"].mean()))

with col3:
    nb_dormants = int((df["score_digital"] <= 1).sum())
    type_carte = "danger" if nb_dormants / len(df) > 0.3 else "warning" if nb_dormants / len(df) > 0.15 else "success"
    afficher_carte_kpi(t("kpi_clients_dormants_digitaux"), str(nb_dormants), "", type_carte)

with col4:
    try:
        derniere_date = requete_duckdb("SELECT max(txn_datetime) AS d FROM main_staging.stg_transactions")
        dernier_mois = pd.Timestamp(derniere_date["d"].iloc[0]).to_period("M")
        nb_txn_mois = requete_duckdb(
            f"SELECT count(*) AS n FROM main_staging.stg_transactions "
            f"WHERE date_trunc('month', txn_datetime) = DATE '{dernier_mois.start_time.date()}'"
        )["n"].iloc[0]
    except Exception:
        nb_txn_mois = 0
    afficher_carte_kpi(t("kpi_transactions_ce_mois"), f"{int(nb_txn_mois):,}".replace(",", " "))

onglet_canaux, onglet_activite, onglet_profil = st.tabs([
    t("onglet_canaux_digital"), t("onglet_activite_transactionnelle"), t("onglet_profil_segment"),
])

# --- Onglet 1 : canaux et digital ------------------------------------------------
with onglet_canaux:
    afficher_entete_section(t("titre_heatmap_canaux"))

    canaux_cibles = {
        "Mobile App": t("canal_app_mobile"),
        "Internet Banking": t("canal_internet_banking"),
        "ATM": t("canal_agence_dab"),
        "Branch": t("canal_agence_dab"),
        "Agent / Mobile Money": t("canal_mobile_money"),
    }
    try:
        adoption = requete_duckdb(
            """
            WITH cust_channel AS (
                SELECT c.customer_id, c.segment, ch.channel_name
                FROM main_marts.customer_360 c
                JOIN main_staging.stg_transactions t ON t.customer_id = c.customer_id
                JOIN main_staging.stg_channels ch ON ch.channel_id = t.channel_id
                WHERE ch.channel_name IN ('Mobile App', 'Internet Banking', 'ATM', 'Agent / Mobile Money')
                GROUP BY 1, 2, 3
            ),
            segment_totals AS (
                SELECT segment, COUNT(DISTINCT customer_id) AS nb_clients
                FROM main_marts.customer_360 GROUP BY 1
            )
            SELECT cc.segment, cc.channel_name, 100.0 * COUNT(DISTINCT cc.customer_id) / st.nb_clients AS taux
            FROM cust_channel cc JOIN segment_totals st ON st.segment = cc.segment
            GROUP BY 1, 2, st.nb_clients
            """
        )
        adoption["channel_label"] = adoption["channel_name"].map(canaux_cibles)
        matrice = adoption.pivot_table(index="segment", columns="channel_label", values="taux", aggfunc="mean")
        ordre_segments = [s for s in ["Mass", "Affluent", "Premier", "Youth"] if s in matrice.index]
        ordre_canaux = [
            t("canal_app_mobile"), t("canal_internet_banking"), t("canal_agence_dab"), t("canal_mobile_money"),
        ]
        ordre_canaux = [c for c in ordre_canaux if c in matrice.columns]
        matrice = matrice.reindex(index=ordre_segments, columns=ordre_canaux)

        fig_heatmap = go.Figure(go.Heatmap(
            z=matrice.values, x=matrice.columns, y=matrice.index,
            colorscale=[[0, COULEUR_CRITIQUE], [0.5, "#FFFFFF"], [1, RISK_COLOR_MAP["Low"]]],
            zmin=0, zmax=100,
            text=[[f"{v:.0f} %" for v in row] for row in matrice.values],
            texttemplate="%{text}", hovertemplate="%{y} · %{x} : %{z:.1f} %<extra></extra>",
        ))
        fig_heatmap.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_heatmap, width='stretch')
        st.caption(t("soustitre_heatmap_canaux"))

        idx_min = np.unravel_index(np.nanargmin(matrice.values), matrice.values.shape)
        segment_min, canal_min, valeur_min = (
            matrice.index[idx_min[0]], matrice.columns[idx_min[1]], matrice.values[idx_min],
        )
        # Le "paradoxe Premier" (fort revenu, faible adoption mobile) n'est affiché que
        # s'il est réellement observé dans les données — jamais affirmé par défaut
        # The "Premier paradox" (high income, low mobile adoption) is only shown if
        # it actually holds in the data — never asserted by default
        if segment_min == "Premier" and canal_min == t("canal_app_mobile"):
            st.info(t("paradoxe_premier_digital").format(pct=format_pct(valeur_min)))
        else:
            st.info(f"**{segment_min} · {canal_min}** : {format_pct(valeur_min)} — {t('insight_canal_plus_faible')}")
    except Exception as error:
        st.warning(f"{t('erreur_donnees_titre')} ({error})")

    afficher_entete_section(t("titre_score_digital_segment"))
    score_par_segment = df.groupby("segment")["score_digital"].mean().reset_index()
    score_par_segment = score_par_segment.sort_values("score_digital", ascending=True)
    fig_score_digital = px.bar(
        score_par_segment, x="score_digital", y="segment", orientation="h", color="segment",
        color_discrete_map=SEGMENT_COLOR_MAP, labels={"score_digital": t("axe_score_digital"), "segment": ""},
    )
    fig_score_digital.update_layout(
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_score_digital, width='stretch')

# --- Onglet 2 : activité transactionnelle ----------------------------------------
with onglet_activite:
    afficher_entete_section(t("titre_evolution_transactions"))
    try:
        mensuel = requete_duckdb(
            """
            SELECT date_trunc('month', txn_datetime) AS mois, sum(amount_xof) AS volume
            FROM main_staging.stg_transactions
            WHERE txn_datetime >= (SELECT max(txn_datetime) FROM main_staging.stg_transactions) - INTERVAL 12 MONTH
            GROUP BY 1 ORDER BY 1
            """
        )
        mensuel["volume_M"] = mensuel["volume"] / 1_000_000
        x_num = np.arange(len(mensuel))
        pente, ordonnee = np.polyfit(x_num, mensuel["volume_M"], 1)
        tendance = pente * x_num + ordonnee

        fig_mensuel = go.Figure()
        fig_mensuel.add_trace(go.Scatter(
            x=mensuel["mois"], y=mensuel["volume_M"], mode="lines+markers", fill="tozeroy",
            line=dict(color=COULEUR_SIDEBAR, width=2), name=t("titre_evolution_transactions"),
        ))
        fig_mensuel.add_trace(go.Scatter(
            x=mensuel["mois"], y=tendance, mode="lines", line=dict(color=COULEUR_ORANGE_ACTION, dash="dash"),
            name="Tendance",
        ))
        idx_creux = mensuel["volume_M"].idxmin()
        fig_mensuel.add_trace(go.Scatter(
            x=[mensuel.loc[idx_creux, "mois"]], y=[mensuel.loc[idx_creux, "volume_M"]],
            mode="markers", marker=dict(color=COULEUR_CRITIQUE, size=12), showlegend=False,
        ))
        fig_mensuel.update_layout(
            showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis_title="M FCFA",
        )
        st.plotly_chart(fig_mensuel, width='stretch')

        variation = 100 * (mensuel["volume_M"].iloc[-1] - mensuel["volume_M"].iloc[0]) / mensuel["volume_M"].iloc[0]
        tendance_libelle = (
            t("tendance_hausse") if variation > 5 else t("tendance_baisse") if variation < -5 else t("tendance_stable")
        )
        st.info(t("encadre_tendance_generale").format(
            tendance=tendance_libelle, variation=f"{variation:+.1f} %",
        ))
    except Exception as error:
        st.warning(f"{t('erreur_donnees_titre')} ({error})")

    afficher_entete_section(t("titre_types_transactions"))
    try:
        types_txn = requete_duckdb(
            """
            SELECT txn_type, sum(amount_xof) AS volume, avg(amount_xof) AS montant_moyen
            FROM main_staging.stg_transactions GROUP BY 1 ORDER BY 2 DESC LIMIT 5
            """
        )
        fig_types = px.bar(
            types_txn.sort_values("volume"), x="volume", y="txn_type", orientation="h", color="txn_type",
            color_discrete_map={"salary_credit": COULEUR_ORANGE_ACTION},
            labels={"volume": t("solde_total") + " (FCFA)", "txn_type": ""},
        )
        for trace in fig_types.data:
            if trace.name != "salary_credit":
                trace.marker.color = COULEUR_SIDEBAR
        fig_types.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_types, width='stretch')
        if "salary_credit" in types_txn["txn_type"].values:
            st.caption(t("annotation_salaire_credit"))
    except Exception as error:
        st.warning(f"{t('erreur_donnees_titre')} ({error})")

# --- Onglet 3 : profil par segment ------------------------------------------------
with onglet_profil:
    afficher_entete_section(t("titre_engagement_digital_vs_activite"))
    fig_engagement = px.scatter(
        df, x="recency_jours", y="score_digital", color="segment", color_discrete_map=SEGMENT_COLOR_MAP,
        labels={"recency_jours": label_technique("recency_jours"), "score_digital": label_technique("score_digital")},
        title=t("titre_engagement_digital_vs_activite"),
    )
    fig_engagement.add_vrect(x0=0, x1=30, fillcolor=RISK_COLOR_MAP["Low"], opacity=0.08, line_width=0)
    fig_engagement.add_vrect(x0=30, x1=60, fillcolor=RISK_COLOR_MAP["Medium"], opacity=0.08, line_width=0)
    borne = max(float(df["recency_jours"].max()), 61)
    fig_engagement.add_vrect(x0=60, x1=borne, fillcolor=RISK_COLOR_MAP["High"], opacity=0.08, line_width=0)
    fig_engagement.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_engagement, width='stretch')

    afficher_entete_section(t("titre_profil_moyen_segment"))
    try:
        interactions = requete_duckdb(
            """
            SELECT c.segment, i.sentiment, count(*) AS n
            FROM main_staging.stg_interactions i
            JOIN main_marts.customer_360 c ON c.customer_id = i.customer_id
            WHERE i.sentiment IN ('Positive', 'Negative')
            GROUP BY 1, 2
            """
        )
        satisfaction = interactions.pivot_table(index="segment", columns="sentiment", values="n", fill_value=0)
        satisfaction["taux_positif"] = 100 * satisfaction.get("Positive", 0) / (
            satisfaction.get("Positive", 0) + satisfaction.get("Negative", 0)
        ).replace(0, np.nan)
    except Exception:
        satisfaction = pd.DataFrame({"taux_positif": []})

    def normaliser(serie: pd.Series, inverse: bool = False) -> pd.Series:
        # Ramène une série sur 0-100 (min-max) pour les axes du profil moyen
        # Rescales a series onto 0-100 (min-max) for the average-profile axes
        m, mx = serie.min(), serie.max()
        if mx == m:
            return pd.Series(50.0, index=serie.index)
        base = (serie - m) / (mx - m) * 100
        return 100 - base if inverse else base

    profil = df.groupby("segment").agg(
        activite=("nb_txn_90j", "mean"),
        digital=("score_digital", "mean"),
        fidelite=("anciennete_jours", "mean"),
        valeur=("solde_total_xof", "mean"),
    )
    profil["activite"] = normaliser(profil["activite"])
    profil["digital"] = profil["digital"] / 3 * 100
    profil["fidelite"] = normaliser(profil["fidelite"])
    profil["valeur"] = normaliser(profil["valeur"])
    profil["satisfaction"] = satisfaction["taux_positif"].reindex(profil.index).fillna(50)

    axes = ["activite", "digital", "fidelite", "valeur", "satisfaction"]
    libelles_axes = [t("axe_activite"), t("axe_digital"), t("axe_fidelite"), t("axe_valeur"), t("axe_satisfaction")]

    fig_radar = go.Figure()
    for segment in profil.index:
        valeurs = profil.loc[segment, axes].tolist()
        fig_radar.add_trace(go.Scatterpolar(
            r=valeurs + [valeurs[0]], theta=libelles_axes + [libelles_axes[0]], fill="toself",
            name=segment, line=dict(color=SEGMENT_COLOR_MAP.get(segment)),
            opacity=0.7,
        ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_radar, width='stretch')

afficher_pied_de_page()
