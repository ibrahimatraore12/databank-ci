# Fiche complète d'un client : profil, comportement, risque, actions recommandées
# Full customer record: profile, behavior, risk, recommended actions

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st  # noqa: E402

from components.ui import (  # noqa: E402
    afficher_barre_score, afficher_entete, afficher_pied_de_page,
    format_fcfa, label_technique, requete_duckdb, t,
)

st.set_page_config(page_title="Vue Client 360", page_icon="🏦", layout="wide")

afficher_entete(t("nav_360"), t("page_360_intro"))

try:
    df = requete_duckdb(
        """
        SELECT c.*, n.next_best_action
        FROM main_marts.customer_360 c
        LEFT JOIN main_marts.nba n ON c.customer_id = n.customer_id
        """
    )
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    afficher_pied_de_page()
    st.stop()

recherche = st.text_input(t("rechercher_client"), placeholder="C0001 ou nom du client")

resultats = df
if recherche:
    resultats = df[
        df["customer_id"].str.contains(recherche, case=False, na=False)
        | df["full_name"].str.contains(recherche, case=False, na=False)
    ]

if resultats.empty:
    st.info(t("aucun_client_trouve"))
    afficher_pied_de_page()
    st.stop()

client = resultats.iloc[0]

st.subheader(f"{client['full_name']} — {client['customer_id']}")
col_gauche, col_milieu, col_droite = st.columns(3)

with col_gauche:
    st.markdown(f"**{t('segment_client')}** : {client['segment']}")
    st.markdown(f"**{t('niveau_risque_credit')}** : {client['risk_band']}")
    st.markdown(f"**{t('ville')}** : {client['city']} ({client['district']})")
    st.markdown(f"**{t('canal_prefere')}** : {client['preferred_channel']}")

with col_milieu:
    st.markdown(f"**{t('revenu_mensuel')}** : {format_fcfa(client['monthly_income_xof'])}")
    st.markdown(f"**{t('salaire_domicilie')}** : {'✅' if client['salaire_domicilie'] else '❌'}")
    st.markdown(f"**{t('nombre_produits_detenus')}** : {int(client['nb_produits_total'])}")
    st.markdown(f"**{t('nombre_cartes')}** : {int(client['nb_cartes'])}")

with col_droite:
    st.markdown(f"**{t('application_mobile_activee')}** : {'✅' if client['mobile_app_active'] else '❌'}")
    st.markdown(f"**{t('internet_banking_active')}** : {'✅' if client['internet_banking_active'] else '❌'}")
    st.markdown(f"**{t('mobile_money_lie')}** : {'✅' if client['mobile_money_linked'] else '❌'}")
    st.markdown(f"**{t('reclamations_en_cours')}** : {int(client['nb_reclamations_ouvertes'])}")

st.divider()
col_score, col_action = st.columns([1, 2])
with col_score:
    afficher_barre_score(client["risque_composite"], label_technique("risque_composite"))
    st.caption(f"{t('jours_depuis_derniere_transaction')} : {int(client['recency_jours'])}")
with col_action:
    st.info(f"**{t('action_recommandee_titre')}** : {client['next_best_action']}")

st.divider()
st.subheader(t("kpis_portefeuille"))
badges = {
    t("client_forte_valeur_a_risque"): client["is_high_value_at_risk"],
    t("salaire_domicilie_digital_dormant"): client["is_digitally_dormant_salary"],
    t("risque_reclamation"): client["is_complaints_churn_risk"],
    t("cible_cross_sell"): client["is_cross_sell_target"],
    t("opportunite_upsell_salaire"): client["is_salary_upsell_opportunity"],
}
colonnes_badges = st.columns(len(badges))
for colonne, (libelle, valeur) in zip(colonnes_badges, badges.items()):
    with colonne, st.container(border=True):
        st.metric(libelle, "Oui" if valeur else "Non")

afficher_pied_de_page()
