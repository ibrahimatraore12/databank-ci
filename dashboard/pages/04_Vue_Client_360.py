# Fiche client complète — prépare l'entretien conseiller avant un appel :
# score de risque expliqué, produits détenus, comportement récent, recommandation
# Full customer record — prepares the advisor's call: risk score explained,
# products held, recent behavior, recommendation

import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from components.charts import COULEUR_ACCENT, SEGMENT_COLOR_MAP  # noqa: E402
from components.ui import (  # noqa: E402
    afficher_alerte, afficher_barre_score, afficher_entete, afficher_entete_section, afficher_guide,
    afficher_pied_de_page, badge_segment, couleur_score, format_fcfa, label_technique, niveau_risque,
    requete_duckdb, t,
)
from ml.rules import decompose_risk_score  # noqa: E402

st.set_page_config(page_title="Vue Client 360", page_icon="🏦", layout="wide")

afficher_entete(t("nav_360"), t("soustitre_360"), "👤")
afficher_guide(t("guide_360"))

try:
    df = requete_duckdb(
        """
        SELECT c.*, n.next_best_action, sc.occupation
        FROM main_marts.customer_360 c
        LEFT JOIN main_marts.nba n ON c.customer_id = n.customer_id
        LEFT JOIN main_staging.stg_customers sc ON c.customer_id = sc.customer_id
        """
    )
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    afficher_pied_de_page()
    st.stop()


def _sans_accent(texte: str) -> str:
    # Recherche insensible aux accents : "Kone" doit trouver "Koné"
    # Accent-insensitive search: "Kone" must find "Koné"
    return "".join(c for c in unicodedata.normalize("NFD", str(texte)) if unicodedata.category(c) != "Mn").lower()


recherche = st.text_input(t("rechercher_client"), placeholder=t("rechercher_client_placeholder"))

resultats = df
if recherche:
    cle = _sans_accent(recherche)
    masque = (
        df["customer_id"].apply(_sans_accent).str.contains(cle)
        | df["full_name"].apply(_sans_accent).str.contains(cle)
        | df["city"].apply(_sans_accent).str.contains(cle)
        | df["segment"].apply(_sans_accent).str.contains(cle)
    )
    resultats = df[masque]

if resultats.empty:
    st.info(t("aucun_client_trouve"))
    afficher_pied_de_page()
    st.stop()

if len(resultats) == 1 or not recherche:
    if not recherche:
        st.caption(t("suggestion_clients_risque"))
        resultats = df.sort_values("risque_composite", ascending=False).head(10)
    client_id_choisi = resultats.iloc[0]["customer_id"] if len(resultats) == 1 else None
else:
    st.caption(t("plusieurs_resultats").format(n=len(resultats)))

apercu = resultats[["customer_id", "full_name", "segment", "city", "risque_composite"]].copy()
apercu["risque_composite"] = apercu["risque_composite"].round(0).astype(int)
apercu = apercu.rename(columns={c: label_technique(c) for c in apercu.columns if c != "risque_composite"})
apercu = apercu.rename(columns={"risque_composite": t("col_score_risque")})
ligne_selectionnee = st.dataframe(
    apercu, width='stretch', hide_index=True, on_select="rerun", selection_mode="single-row",
)

if ligne_selectionnee["selection"]["rows"]:
    client_id_choisi = resultats.iloc[ligne_selectionnee["selection"]["rows"][0]]["customer_id"]
elif len(resultats) == 1:
    client_id_choisi = resultats.iloc[0]["customer_id"]
else:
    client_id_choisi = None

if not client_id_choisi:
    st.info(t("selectionner_client_liste"))
    afficher_pied_de_page()
    st.stop()

client = df[df["customer_id"] == client_id_choisi].iloc[0]

st.divider()

# --- Bloc 1 : en-tête -------------------------------------------------------
initiales = "".join(p[0] for p in str(client["full_name"]).split()[:2]).upper()
couleur_avatar = SEGMENT_COLOR_MAP.get(client["segment"], COULEUR_ACCENT)
couleur_risque, libelle_risque = niveau_risque(client["risque_composite"])

col_identite, col_score = st.columns([2, 1])
with col_identite:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px;">
          <div style="width:56px;height:56px;border-radius:50%;background:{couleur_avatar};
                      color:#fff;display:flex;align-items:center;justify-content:center;
                      font-size:20px;font-weight:700;flex-shrink:0;">{initiales}</div>
          <div>
            <div style="font-size:20px;font-weight:700;color:#0D0D0D;">
              {client['full_name']} <span style="color:#6B6B6B;font-weight:400;font-size:14px;">
              — {client['customer_id']}</span>
            </div>
            <div style="margin-top:4px;">{badge_segment(client['segment'])}
              <span style="margin-left:6px;color:{couleur_risque};font-weight:600;font-size:12px;">
              ● {libelle_risque}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        f"📍 {client['city']} · {t('anciennete_jours')} : {int(client['anciennete_jours'])} j"
        + (f" · {client['occupation']}" if pd.notna(client.get("occupation")) else ""),
    )

with col_score:
    afficher_barre_score(client["risque_composite"], t("score_de_risque"))
    if client["risque_composite"] >= 70:
        afficher_alerte(t("recommandation_appel_urgent"), "danger", "🚨")
    elif client["risque_composite"] >= 40:
        afficher_alerte(t("recommandation_offre_fidelisation"), "warning", "⚠️")
    else:
        offre = (
            t("offre_carte") if client["nb_cartes"] == 0
            else t("offre_domiciliation_salaire") if not client["salaire_domicilie"]
            else t("offre_epargne")
        )
        afficher_alerte(t("recommandation_opportunite").format(offre=offre), "success", "💡")

st.divider()

# --- Bloc 2 : onglets --------------------------------------------------------
onglet_profil, onglet_transactions, onglet_interactions, onglet_ia = st.tabs([
    t("onglet_profil_financier"), t("onglet_transactions"), t("onglet_interactions"), t("onglet_recommandation_ia"),
])

with onglet_profil:
    col1, col2, col3 = st.columns(3)
    with col1, st.container(border=True):
        st.metric(t("solde_total"), format_fcfa(client["solde_total_xof"]))
    with col2, st.container(border=True):
        st.metric(t("revenu_mensuel"), format_fcfa(client["monthly_income_xof"]))
    with col3, st.container(border=True):
        st.metric(t("nbi_estime"), format_fcfa(client["nbi_estime_xof"]))

    st.write("")
    try:
        carte = requete_duckdb(
            f"SELECT card_tier, status FROM main_staging.stg_cards "
            f"WHERE customer_id = '{client_id_choisi}' ORDER BY issue_date DESC LIMIT 1",
        )
        compte = requete_duckdb(
            f"SELECT account_type, current_balance_xof FROM main_staging.stg_accounts "
            f"WHERE customer_id = '{client_id_choisi}' ORDER BY current_balance_xof DESC LIMIT 1",
        )
        pret = requete_duckdb(
            f"SELECT outstanding_balance_xof, status_corrige FROM main_staging.stg_loans "
            f"WHERE customer_id = '{client_id_choisi}' ORDER BY origination_date DESC LIMIT 1",
        )
        epargne = requete_duckdb(
            f"SELECT current_balance_xof FROM main_staging.stg_accounts "
            f"WHERE customer_id = '{client_id_choisi}' AND account_type = 'Savings' LIMIT 1",
        )
    except Exception:
        carte = compte = pret = epargne = pd.DataFrame()

    col_carte, col_compte, col_pret, col_epargne = st.columns(4)
    with col_carte, st.container(border=True):
        texte = (
            f"{carte.iloc[0]['card_tier']} · {carte.iloc[0]['status']}" if not carte.empty
            else t("opportunite_carte")
        )
        st.markdown(f"**💳 {t('produit_carte')}**")
        st.write(texte)
    with col_compte, st.container(border=True):
        texte = (
            f"{compte.iloc[0]['account_type']} · {format_fcfa(compte.iloc[0]['current_balance_xof'])}"
            if not compte.empty else "—"
        )
        st.markdown(f"**🏦 {t('produit_compte')}**")
        st.write(texte)
    with col_pret, st.container(border=True):
        texte = (
            f"{format_fcfa(pret.iloc[0]['outstanding_balance_xof'])} · {pret.iloc[0]['status_corrige']}"
            if not pret.empty else t("opportunite_pret")
        )
        st.markdown(f"**💰 {t('produit_pret')}**")
        st.write(texte)
    with col_epargne, st.container(border=True):
        texte = format_fcfa(epargne.iloc[0]["current_balance_xof"]) if not epargne.empty else t("opportunite_epargne")
        st.markdown(f"**📈 {t('produit_epargne')}**")
        st.write(texte)

    st.write("")
    if client["salaire_domicilie"]:
        st.success(f"✅ {t('salaire_domicilie')} : {t('salaire_domicilie_oui')}")
    else:
        st.warning(f"⚠️ {t('salaire_domicilie')} : {t('salaire_domicilie_non')}")

with onglet_transactions:
    try:
        historique = requete_duckdb(
            f"""
            SELECT date_trunc('month', txn_datetime) as mois, count(*) as nb_txn
            FROM main_staging.stg_transactions
            WHERE customer_id = '{client_id_choisi}'
            GROUP BY 1 ORDER BY 1 DESC LIMIT 6
            """,
        ).sort_values("mois")
        dernieres = requete_duckdb(
            f"""
            SELECT t.txn_datetime, t.txn_type, t.amount_xof, ch.channel_name
            FROM main_staging.stg_transactions t
            LEFT JOIN main_staging.stg_channels ch ON t.channel_id = ch.channel_id
            WHERE t.customer_id = '{client_id_choisi}'
            ORDER BY t.txn_datetime DESC LIMIT 5
            """,
        )
    except Exception:
        historique = dernieres = pd.DataFrame()

    if not historique.empty:
        tendance_hausse = historique["nb_txn"].iloc[-1] >= historique["nb_txn"].iloc[0]
        r, g, b = (30, 132, 73) if tendance_hausse else (231, 76, 60)
        fig = go.Figure(go.Scatter(
            x=historique["mois"], y=historique["nb_txn"], mode="lines+markers",
            line=dict(color=f"rgb({r},{g},{b})", width=2), fill="tozeroy",
            fillcolor=f"rgba({r},{g},{b},0.12)",
        ))
        fig.update_layout(
            title=t("titre_sparkline_transactions"), height=220, showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info(t("aucune_transaction"))

    if not dernieres.empty:
        st.metric(t("canal_le_plus_utilise"), client["canal_majoritaire"] or "—")
        dernieres_affichees = dernieres.rename(columns={
            "txn_datetime": t("col_date"), "txn_type": t("col_type"),
            "amount_xof": t("col_montant"), "channel_name": t("col_canal"),
        })
        dernieres_affichees[t("col_montant")] = dernieres_affichees[t("col_montant")].apply(format_fcfa)
        st.dataframe(dernieres_affichees, width='stretch', hide_index=True)

with onglet_interactions:
    try:
        interactions = requete_duckdb(
            f"""
            SELECT interaction_datetime, interaction_type, sentiment
            FROM main_staging.stg_interactions
            WHERE customer_id = '{client_id_choisi}'
            ORDER BY interaction_datetime DESC LIMIT 5
            """,
        )
        reclamations_client = requete_duckdb(
            f"""
            SELECT category, severity, opened_date, status
            FROM main_staging.stg_complaints
            WHERE customer_id = '{client_id_choisi}' AND status = 'Open'
            ORDER BY opened_date DESC
            """,
        )
    except Exception:
        interactions = reclamations_client = pd.DataFrame()

    st.markdown(f"**{t('dernieres_interactions')}**")
    if interactions.empty:
        st.info(t("aucune_interaction"))
    else:
        icones_sentiment = {"Positive": "🟢", "Neutral": "⚪", "Negative": "🔴"}
        for _, ligne in interactions.iterrows():
            icone = icones_sentiment.get(ligne["sentiment"], "⚪")
            st.markdown(f"{icone} **{ligne['interaction_type']}** — {str(ligne['interaction_datetime'])[:10]}")

    st.write("")
    if reclamations_client.empty:
        st.success(f"✅ {t('aucune_reclamation_ouverte_client')}")
    else:
        st.error(t("alerte_reclamations_client").format(n=len(reclamations_client)))
        st.dataframe(
            reclamations_client.rename(columns={
                "category": t("col_categorie"), "severity": t("col_severite"),
                "opened_date": t("col_date_ouverture"), "status": t("col_statut"),
            }),
            width='stretch', hide_index=True,
        )

with onglet_ia:
    afficher_entete_section(t("detail_score_titre"))
    try:
        contributions = decompose_risk_score(df, client_id_choisi)
        signaux = [
            (t("signal_h1_recency"), contributions["recency"], 40),
            (t("signal_h2_reclamations"), contributions["reclamations"], 30),
            (t("signal_h3_tendance"), contributions["tendance"], 10),
            (t("signal_h4_digital"), contributions["digital"], 20),
        ]
        for libelle, valeur, maximum in signaux:
            couleur = couleur_score(100 * valeur / maximum) if maximum else "#6B6B6B"
            st.markdown(
                f"""
                <div style="margin-bottom:8px;">
                  <div style="display:flex;justify-content:space-between;font-size:0.85rem;">
                    <span>{libelle}</span><span>{valeur:.1f} / {maximum} pts</span>
                  </div>
                  <div style="background:#e0e0e0;border-radius:4px;height:8px;width:100%;">
                    <div style="background:{couleur};width:{100 * valeur / maximum if maximum else 0}%;
                                height:8px;border-radius:4px;"></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        afficher_barre_score(client["risque_composite"], t("score_total"))
    except Exception:
        st.info("—")

    st.write("")
    afficher_entete_section(t("prochaine_action_titre"))
    if client["risque_composite"] >= 70:
        script = t("script_appel_urgent").format(nom=client["full_name"], jours=int(client["recency_jours"]))
        afficher_alerte(script, "critical", "📞")
    elif client["risque_composite"] >= 40:
        script = t("script_appel_fidelisation").format(nom=client["full_name"])
        afficher_alerte(script, "warning", "📞")
    else:
        offre = (
            t("offre_carte") if client["nb_cartes"] == 0
            else t("offre_domiciliation_salaire") if not client["salaire_domicilie"]
            else t("offre_epargne")
        )
        script = t("script_appel_opportunite").format(nom=client["full_name"], offre=offre)
        afficher_alerte(script, "success", "📞")

afficher_pied_de_page()
