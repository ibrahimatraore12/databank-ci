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
    # Palette RAG : rouge (critique), ambre (attention), vert (positif)
    # RAG palette: red (critical), amber (attention), green (positive)
    if score >= 66:
        return "#E74C3C"
    if score >= 33:
        return "#F39C12"
    return "#1E8449"


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


def afficher_entete(titre: str, sous_titre: str = "") -> None:
    # Titre centré avec encadré dégradé, charte visuelle du projet — dégradé
    # navy vers violet (couleur du segment Premier) avec un fin liseré accent,
    # plus chaleureux que l'ancien dégradé navy-sur-navy
    # Centered title with a gradient banner, project visual identity — navy to
    # purple gradient (Premier segment color) with a thin accent underline,
    # warmer than the previous navy-on-navy gradient
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#1A1A2E,#3B1F5C);
                    padding:24px;border-radius:10px;text-align:center;margin-bottom:20px;
                    border-bottom:3px solid #FF4500;">
          <h1 style="color:white;margin:0;">{titre}</h1>
          <p style="color:#dddddd;margin:6px 0 0 0;">{sous_titre}</p>
        </div>
        """,
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


def afficher_pied_de_page() -> None:
    # Signature d'auteur, sobre, identique sur chaque page
    # Author signature, sober, identical on every page
    st.markdown(
        """
        <div style="text-align:center;color:#888;font-size:0.8rem;
                    margin-top:32px;padding-top:12px;border-top:1px solid rgba(128,128,128,0.3);">
          Ibrahima TRAORE — Analytics Engineer
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
