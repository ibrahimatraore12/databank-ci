# Couche sémantique du dashboard : LABELS traduit chaque nom technique en clé
# métier stable, puis t() résout cette clé dans la langue active via i18n/
# Dashboard semantic layer: LABELS translates each technical name into a
# stable business key, then t() resolves that key in the active language via i18n/

import json
import os

import duckdb
import pandas as pd
import streamlit as st

import config
from src.logger import log_event

I18N_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "i18n")

# Aucun nom technique ne doit apparaître dans l'interface : toute colonne
# affichée passe par ce dictionnaire avant d'être traduite par t()
# No technical name should ever appear in the UI: every displayed column
# goes through this dictionary before being translated by t()
LABELS = {
    "score_digital": "score_adoption_digitale",
    "churn_flag": "risque_de_depart",
    "risk_band": "niveau_risque_credit",
    "nb_produits_total": "nombre_produits_detenus",
    "recency_jours": "jours_depuis_derniere_transaction",
    "nb_reclamations_ouvertes": "reclamations_en_cours",
    "nb_reclamations_total": "reclamations_en_cours",
    "next_best_action": "action_recommandee",
    "salaire_domicilie": "salaire_domicilie",
    "salary_domiciled_flag": "salaire_domicilie",
    "monthly_income_xof": "revenu_mensuel",
    "avg_balance_90d_xof": "solde_moyen_90_jours",
    "mobile_app_active": "application_mobile_activee",
    "internet_banking_active": "internet_banking_active",
    "mobile_money_linked": "mobile_money_lie",
    "risque_composite": "score_de_risque",
    "score_regles": "score_de_risque",
    "segment": "segment_client",
    "tendance_transactions": "tendance_activite",
    "nb_comptes": "nombre_comptes",
    "nb_cartes": "nombre_cartes",
    "is_high_value_at_risk": "client_forte_valeur_a_risque",
    "is_digitally_dormant_salary": "salaire_domicilie_digital_dormant",
    "is_complaints_churn_risk": "risque_reclamation",
    "is_cross_sell_target": "cible_cross_sell",
    "is_salary_upsell_opportunity": "opportunite_upsell_salaire",
    "nbi_estime_xof": "nbi_estime",
    "score_engagement": "score_engagement",
    "city": "ville",
    "district": "district",
    "full_name": "nom_complet",
    "customer_id": "identifiant_client",
    "preferred_channel": "canal_prefere",
    "solde_total_xof": "solde_total",
    "anciennete_jours": "anciennete_jours",
    "canal_majoritaire": "canal_bancaire_principal",
    "nb_txn_30j": "transactions_30_jours",
    "nb_txn_90j": "transactions_90_jours",
    "tendance_3m": "tendance_3_mois",
    "dpd_max": "retard_maximum_jours",
}

MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]

# CSS unique de la charte visuelle Artefact (noir #0D0D0D + orange #FF4500),
# injecté une seule fois depuis APP.py — s'applique à toutes les pages car
# Streamlit partage le même DOM de session entre les pages du routeur
# Single Artefact visual identity stylesheet (black #0D0D0D + orange #FF4500),
# injected once from APP.py — applies to every page since Streamlit shares the
# same session DOM across the router's pages
CSS_ARTEFACT = """
<style>
section[data-testid="stSidebar"] { background-color: #0D0D0D !important; border-right: 1px solid #2C2C2C; }
section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
section[data-testid="stSidebar"] .stRadio label { color: rgba(255,255,255,0.7) !important; font-size: 13px; }
section[data-testid="stSidebar"] .stRadio label:hover { color: #FF4500 !important; }

.stApp { background-color: #F5F5F5; }

.page-banner {
    background: linear-gradient(135deg, #0D0D0D 0%, #1A1A1A 100%);
    color: #FFFFFF; padding: 20px 24px; border-radius: 8px;
    margin-bottom: 20px; border-left: 5px solid #FF4500;
}
.page-banner h1 { margin: 0 0 4px 0; font-size: 22px; font-weight: 700; color: #FFFFFF; }
.page-banner p { margin: 0; font-size: 13px; color: rgba(255,255,255,0.7); }

.guide-box {
    background: #F8F8F8; border: 1px solid #E0E0E0; border-radius: 8px;
    padding: 14px 18px; margin-bottom: 16px; font-size: 13px; color: #444444; line-height: 1.6;
}
.guide-box strong { color: #0D0D0D; }

.section-header {
    background: #0D0D0D; color: #FFFFFF; padding: 10px 20px;
    border-left: 4px solid #FF4500; border-radius: 4px;
    margin: 16px 0 12px 0; font-size: 15px; font-weight: 600;
}

.alert-box { border-radius: 8px; padding: 14px 18px; margin-bottom: 14px; font-size: 14px; line-height: 1.5; }
.alert-box.critical { background: #FFF0ED; border: 1px solid #FF4500; }
.alert-box.danger   { background: #FDECEA; border: 1px solid #E74C3C; }
.alert-box.success  { background: #EAF7EF; border: 1px solid #1E8449; }
.alert-box.warning  { background: #FFFDF5; border: 1px solid #F39C12; }

.kpi-card {
    background: #FFFFFF; border-left: 4px solid #FF4500; border-radius: 8px;
    padding: 16px 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 8px; height: 100%;
}
.kpi-card.danger  { border-left-color: #E74C3C; background: #FFF8F8; }
.kpi-card.warning { border-left-color: #F39C12; background: #FFFDF5; }
.kpi-card.success { border-left-color: #1E8449; background: #F5FBF7; }
.kpi-label { font-size: 11px; color: #6B6B6B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.kpi-value { font-size: 28px; font-weight: 700; color: #0D0D0D; line-height: 1.2; }
.kpi-delta { font-size: 12px; margin-top: 4px; }
.kpi-delta.pos { color: #1E8449; } .kpi-delta.neg { color: #E74C3C; } .kpi-delta.neu { color: #6B6B6B; }

[data-testid="metric-container"] {
    background: #FFFFFF; border-left: 4px solid #FF4500; border-radius: 8px;
    padding: 12px 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
[data-testid="metric-container"] label {
    font-size: 11px !important; color: #6B6B6B !important; text-transform: uppercase;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 26px !important; font-weight: 700 !important; color: #0D0D0D !important;
}

.stDataFrame thead tr th {
    background-color: #0D0D0D !important; color: #FFFFFF !important; font-size: 12px !important;
    text-transform: uppercase; letter-spacing: 0.3px;
}
.stDataFrame tbody tr:nth-child(even) { background-color: #F9F9F9; }

.stTabs [data-baseweb="tab-list"] { background: #0D0D0D; border-radius: 8px 8px 0 0; padding: 4px 8px 0; }
.stTabs [data-baseweb="tab"] { color: rgba(255,255,255,0.6) !important; font-size: 13px; padding: 8px 16px; }
.stTabs [aria-selected="true"] {
    color: #FF4500 !important; border-bottom: 2px solid #FF4500 !important; font-weight: 600;
}

.stButton button[kind="primary"] {
    background: #FF4500 !important; border: none !important; color: white !important;
    font-weight: 600 !important; border-radius: 6px !important;
}
.stButton button[kind="primary"]:hover { background: #CC3700 !important; }

.badge-premier, .badge-affluent, .badge-mass, .badge-youth {
    color:#fff; padding:2px 10px; border-radius:10px; font-size:11px; font-weight:600;
}
.badge-premier  { background:#6C3483; }
.badge-affluent { background:#1A5276; }
.badge-mass     { background:#2980B9; }
.badge-youth    { background:#BA7517; }
.badge-action-danger  {
    background:#E74C3C; color:#fff; padding:2px 10px; border-radius:10px; font-size:11px; font-weight:600;
}
.badge-action-warning {
    background:#F39C12; color:#fff; padding:2px 10px; border-radius:10px; font-size:11px; font-weight:600;
}
.badge-action-success {
    background:#1E8449; color:#fff; padding:2px 10px; border-radius:10px; font-size:11px; font-weight:600;
}

details summary { font-weight: 600; color: #0D0D0D; font-size: 14px; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F5F5F5; }
::-webkit-scrollbar-thumb { background: #FF4500; border-radius: 3px; }
</style>
"""


def injecter_css_artefact() -> None:
    # Injecte le CSS de la charte Artefact une seule fois, depuis APP.py (routeur)
    # Injects the Artefact visual identity CSS once, from APP.py (router)
    st.markdown(CSS_ARTEFACT, unsafe_allow_html=True)


def charger_traductions(langue: str) -> dict:
    # Charge le dictionnaire de traduction pour une langue (mis en cache Streamlit)
    # Loads the translation dictionary for a language (cached by Streamlit)
    chemin = os.path.join(I18N_DIR, f"{langue}.json")
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)


def t(cle: str) -> str:
    # Résout une clé de traduction dans la langue active de la session
    # Resolves a translation key in the session's active language
    langue = st.session_state.get("langue", "fr")
    traductions = charger_traductions(langue)
    return traductions.get(cle, cle)


def label_technique(nom_technique: str) -> str:
    # Traduit un nom de colonne technique en libellé métier affichable
    # Translates a technical column name into a displayable business label
    cle = LABELS.get(nom_technique, nom_technique)
    return t(cle)


def format_fcfa(valeur) -> str:
    # "3 320 273 FCFA" — espace comme séparateur de milliers
    # "3 320 273 FCFA" — space as thousands separator
    if pd.isna(valeur):
        return "—"
    entier = int(round(float(valeur)))
    formate = f"{entier:,}".replace(",", " ")
    return f"{formate} {config.CURRENCY_LABEL}"


def format_fcfa_compact(valeur) -> str:
    # "4,2 M FCFA" au-delà d'1 million, sinon identique à format_fcfa
    # "4.2 M FCFA" above 1 million, otherwise same as format_fcfa
    if pd.isna(valeur):
        return "—"
    valeur = float(valeur)
    if abs(valeur) >= 1_000_000:
        return f"{valeur / 1_000_000:.1f}".replace(".", ",") + f" M {config.CURRENCY_LABEL}"
    return format_fcfa(valeur)


def format_pct(valeur) -> str:
    # "22,9 %" — virgule décimale et espace avant le symbole
    # "22.9 %" — decimal comma and space before the symbol
    if pd.isna(valeur):
        return "—"
    return f"{float(valeur):.1f}".replace(".", ",") + " %"


def format_date_longue(valeur) -> str:
    # "8 juillet 2026 à 21h34" en français, format anglais équivalent sinon
    # "8 juillet 2026 à 21h34" in French, equivalent English format otherwise
    if pd.isna(valeur):
        return "—"
    dt = pd.Timestamp(valeur)
    if st.session_state.get("langue", "fr") == "fr":
        return f"{dt.day} {MOIS_FR[dt.month - 1]} {dt.year} à {dt.hour:02d}h{dt.minute:02d}"
    return dt.strftime("%B %d, %Y at %I:%M %p")


def format_run_id(run_id) -> str:
    # N'affiche jamais plus que les 8 premiers caractères d'un run_id
    # Never displays more than the first 8 characters of a run_id
    return str(run_id)[:8]


def couleur_score(score: float) -> str:
    # Palette RAG : rouge (>=70, critique), ambre (>=40, attention), vert (positif) —
    # seuils alignés sur la règle métier (voir docs/decisions.md)
    # RAG palette: red (>=70, critical), amber (>=40, attention), green (positive) —
    # thresholds aligned with the business rule (see docs/decisions.md)
    if score >= 70:
        return "#E74C3C"
    if score >= 40:
        return "#F39C12"
    return "#1E8449"


def niveau_risque(score: float) -> tuple:
    # Retourne (couleur RAG, libellé traduit) pour un score 0-100
    # Returns (RAG color, translated label) for a 0-100 score
    if score >= 70:
        return "#E74C3C", t("libelle_risque_eleve")
    if score >= 40:
        return "#F39C12", t("libelle_risque_modere")
    return "#1E8449", t("libelle_risque_faible")


def badge_segment(segment: str) -> str:
    # Pastille HTML colorée par segment (Premier/Affluent/Mass/Youth)
    # HTML pill colored by segment (Premier/Affluent/Mass/Youth)
    classe = {"Premier": "badge-premier", "Affluent": "badge-affluent",
              "Mass": "badge-mass", "Youth": "badge-youth"}.get(segment, "badge-mass")
    return f'<span class="{classe}">{segment}</span>'


def badge_action(texte: str, type_action: str = "warning") -> str:
    # Pastille HTML pour une action recommandée (danger/warning/success)
    # HTML pill for a recommended action (danger/warning/success)
    return f'<span class="badge-action-{type_action}">{texte}</span>'


def afficher_barre_score(score: float, label: str = "") -> None:
    # Barre de progression colorée verte/ambre/rouge selon le score 0-100
    # Green/amber/red progress bar based on the 0-100 score
    couleur = couleur_score(score)
    st.markdown(
        f"""
        <div style="margin-bottom: 10px;">
          <div style="display:flex;justify-content:space-between;font-size:0.85rem;">
            <span>{label}</span><span>{score:.0f}/100</span>
          </div>
          <div style="background:#e0e0e0;border-radius:4px;height:10px;width:100%;">
            <div style="background:{couleur};width:{max(0, min(score, 100))}%;height:10px;border-radius:4px;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def afficher_entete(titre: str, sous_titre: str = "", emoji: str = "") -> None:
    # Bandeau de page : fond noir dégradé, liseré orange, emoji optionnel — charte Artefact
    # Page banner: black gradient, orange left border, optional emoji — Artefact identity
    prefixe = f"{emoji} " if emoji else ""
    st.markdown(
        f'<div class="page-banner"><h1>{prefixe}{titre}</h1><p>{sous_titre}</p></div>',
        unsafe_allow_html=True,
    )


def afficher_guide(texte: str) -> None:
    # Boîte grise d'explication en haut de page, sous le bandeau — répond à
    # "quelle question décisionnelle cette page résout-elle ?"
    # Grey explanation box at the top of the page, under the banner — answers
    # "what decision question does this page solve?"
    st.markdown(f'<div class="guide-box">{texte}</div>', unsafe_allow_html=True)


def afficher_entete_section(titre: str) -> None:
    # En-tête de section : fond noir, liseré orange à gauche
    # Section header: black background, orange left border
    st.markdown(f'<div class="section-header">{titre}</div>', unsafe_allow_html=True)


def afficher_alerte(texte: str, type_alerte: str = "danger", icone: str = "🚨") -> None:
    # Boîte d'alerte RAG — danger/critical pour les risques à traiter, success pour
    # les signaux positifs (le dashboard doit aussi montrer ce qui va bien)
    # RAG alert box — danger/critical for risks to act on, success for positive
    # signals (the dashboard must also surface what's going well)
    st.markdown(f'<div class="alert-box {type_alerte}">{icone} {texte}</div>', unsafe_allow_html=True)


def afficher_carte_kpi(label: str, valeur: str, delta: str = "", type_carte: str = "") -> None:
    # Carte KPI stylisée ; type_carte ∈ {"", "success", "warning", "danger"} pilote la couleur RAG
    # Styled KPI card; type_carte drives the RAG color
    classe = f"kpi-card {type_carte}" if type_carte else "kpi-card"
    delta_html = ""
    if delta:
        sens = "pos" if delta.startswith("+") else "neg" if delta.startswith("-") else "neu"
        delta_html = f'<div class="kpi-delta {sens}">{delta}</div>'
    st.markdown(
        f'<div class="{classe}"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{valeur}</div>{delta_html}</div>',
        unsafe_allow_html=True,
    )


def afficher_etapes_pipeline(etat: dict) -> None:
    # Liste ✅/❌ des étapes du pipeline, dans le corps de la page (pas la sidebar)
    # ✅/❌ list of pipeline steps, in the page body (not the sidebar)
    if not etat:
        st.info("—")
        return
    for etape, statut in etat.get("steps", {}).items():
        icone = "✅" if statut == "OK" else "❌"
        st.markdown(f"{icone} {etape}")
    st.caption(f"{t('derniere_execution')} : {etat.get('last_updated', '—')[:19]}")


def afficher_pied_de_page(date_maj: str = "") -> None:
    # Signature d'auteur sur chaque page, avec date de dernière MAJ optionnelle (accueil)
    # Author signature on every page, with optional last-update date (home page)
    ligne_date = f'<div style="margin-bottom:4px;">{date_maj}</div>' if date_maj else ""
    st.markdown(
        f"""
        <div style="text-align:center;color:#6B6B6B;font-size:0.8rem;
                    margin-top:32px;padding-top:12px;border-top:2px solid #FF4500;">
          {ligne_date}Ibrahima TRAORÉ — Analytics Engineer
        </div>
        """,
        unsafe_allow_html=True,
    )


def afficher_selecteur_langue() -> None:
    # Bouton radio horizontal FR | EN — jamais de liste déroulante
    # Horizontal FR | EN radio button — never a dropdown
    if "langue" not in st.session_state:
        st.session_state["langue"] = "fr"

    choix = st.radio(
        label="FR | EN", options=["fr", "en"], horizontal=True,
        format_func=lambda x: x.upper(), label_visibility="collapsed",
        index=0 if st.session_state["langue"] == "fr" else 1,
        key="selecteur_langue",
    )
    st.session_state["langue"] = choix


def requete_duckdb(sql: str) -> pd.DataFrame:
    # Exécute une requête en lecture seule sur DuckDB ; logge et relève toute erreur
    # Executes a read-only query on DuckDB; logs and raises any error
    try:
        connection = duckdb.connect(config.DUCKDB_PATH, read_only=True)
        resultat = connection.execute(sql).fetchdf()
        connection.close()
        return resultat
    except Exception as error:
        log_event("api", "ERROR", "[DASHBOARD][DUCKDB] ECHEC", {"erreur": str(error), "sql": sql[:200]})
        raise
