# Intelligence Artificielle - transparence sur le calcul du score de risque :
# quelles variables comptent, comment le modèle a été évalué, quoi faire du résultat
# Artificial Intelligence - transparency on how the risk score is computed:
# which variables matter, how the model was evaluated, what to do with the result

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

import config  # noqa: E402
from components.charts import COULEUR_ACCENT, graphique_barres_horizontales  # noqa: E402
from components.ui import (  # noqa: E402
    afficher_carte_kpi, afficher_entete, afficher_guide, afficher_pied_de_page,
    format_fcfa_compact, format_pct, requete_duckdb, t,
)

st.set_page_config(page_title="Intelligence Artificielle", page_icon="🏦", layout="wide")

afficher_entete(t("nav_ia"), t("soustitre_ia"), "🤖")
afficher_guide(t("guide_ia"))

try:
    df = requete_duckdb("SELECT * FROM main_marts.customer_360")
except Exception:
    st.error(f"{t('erreur_donnees_titre')} {t('erreur_contact_admin')}")
    afficher_pied_de_page()
    st.stop()


@st.cache_resource
def _evaluer_modele_en_direct():
    # Rejoue le split déterministe (seed fixe) pour obtenir un vrai ROC/PSI sans
    # ré-entraîner - mis en cache process (une seule fois par instance, coûte
    # quelques centaines de ms) ; retourne None si le modèle n'est pas encore entraîné
    # Replays the deterministic split (fixed seed) to get a real ROC/PSI without
    # retraining - process-cached (once per instance, costs a few hundred ms);
    # returns None if the model isn't trained yet
    try:
        from ml.data import get_X_y, load_data, preprocess_data, split_data
        from ml.model import calculate_psi, compute_roc_data
        from ml.registry import load_model

        donnees = load_data(use_synthetic=True)
        X, y = get_X_y(donnees)
        X_train, X_test, y_train, y_test = split_data(X, y)
        X_train_prep = preprocess_data(X_train, fit=False)
        X_test_prep = preprocess_data(X_test, fit=False)

        modele = load_model("churn_scoring_logistic")
        roc = compute_roc_data(modele, X_test_prep, y_test)
        psi = calculate_psi(
            pd.Series(modele.predict_proba(X_train_prep)[:, 1]),
            pd.Series(modele.predict_proba(X_test_prep)[:, 1]),
        )
        coefficients = dict(zip(X.columns, modele.coef_[0]))
        return {"roc": roc, "psi": psi, "coefficients": coefficients, "n_test": len(y_test)}
    except Exception:
        return None


evaluation = _evaluer_modele_en_direct()

nb_synthetiques = int(df["is_synthetic"].sum())
auc_affiche = f"{evaluation['roc']['auc']:.3f}" if evaluation and evaluation["roc"]["auc"] else "-"
texte_transparence = t("encadre_transparence_ia").format(
    n=len(df), pct=format_pct(100 * nb_synthetiques / len(df)), auc=auc_affiche,
)
st.info(f"ℹ️ {texte_transparence}")

# --- KPIs --------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    afficher_carte_kpi(t("kpi_modele_actif"), "Logistic Regression")
with col2:
    auc = evaluation["roc"]["auc"] if evaluation else None
    type_carte = "success" if auc and auc > 0.75 else "warning" if auc else ""
    afficher_carte_kpi(t("kpi_auc"), f"{auc:.3f}" if auc else "-", "", type_carte)
with col3:
    recall = evaluation["roc"]["tpr_seuil"] if evaluation else None
    afficher_carte_kpi(t("kpi_recall_churners"), format_pct(100 * recall) if recall else "-")
with col4:
    psi = evaluation["psi"] if evaluation else None
    type_carte = "success" if psi is not None and psi < 0.2 else "warning" if psi is not None else ""
    afficher_carte_kpi(t("kpi_drift_psi"), f"{psi:.3f}" if psi is not None else "-", "", type_carte)

onglet_variables, onglet_performance, onglet_actions = st.tabs([
    t("onglet_variables_explicatives"), t("onglet_performance_modele"), t("onglet_actions_ia"),
])

with onglet_variables:
    poids = pd.DataFrame({
        "poids": [
            config.RULES_WEIGHT_RECENCY * 100, config.RULES_WEIGHT_COMPLAINTS * 100,
            config.RULES_WEIGHT_DIGITAL * 100, config.RULES_WEIGHT_TREND * 100,
        ],
        "facteur": [
            t("facteur_recence"), t("facteur_reclamations"), t("facteur_digital"), t("facteur_tendance"),
        ],
    }).sort_values("poids")
    st.plotly_chart(
        graphique_barres_horizontales(poids, "poids", "facteur", t("titre_feature_importance")),
        width='stretch',
    )
    variable_principale = poids.sort_values("poids", ascending=False).iloc[0]
    st.info(
        f"💡 {t('encadre_feature_importance').format(variable=variable_principale['facteur'])} "
        f"({variable_principale['poids']:.0f} %)",
    )
    st.caption(t("ia_intro_texte_1"))

with onglet_performance:
    col_roc, col_scenarios = st.columns(2)
    with col_roc:
        if evaluation:
            roc = evaluation["roc"]
            fig_roc = go.Figure()
            fig_roc.add_trace(go.Scatter(
                x=roc["fpr"], y=roc["tpr"], mode="lines", name="Logistic Regression",
                line=dict(color=COULEUR_ACCENT, width=2), fill="tozeroy", fillcolor="rgba(255,69,0,0.08)",
            ))
            fig_roc.add_trace(go.Scatter(
                x=[0, 1], y=[0, 1], mode="lines", name="Aléatoire (AUC=0.50)",
                line=dict(color="#999999", width=1, dash="dash"),
            ))
            fig_roc.add_trace(go.Scatter(
                x=[roc["fpr_seuil"]], y=[roc["tpr_seuil"]], mode="markers", name="Seuil retenu",
                marker=dict(color="#E74C3C", size=10),
            ))
            fig_roc.update_layout(
                title=t("titre_courbe_roc"), xaxis_title="Faux positifs", yaxis_title="Vrais positifs",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=380,
            )
            st.plotly_chart(fig_roc, width='stretch')
            st.info(t("encadre_roc").format(
                seuil=roc["seuil_retenu"], precision=format_pct(100 * roc["precision_seuil"]),
            ))
        else:
            st.info("-")

    with col_scenarios:
        st.markdown(f"**{t('titre_comparaison_scenarios')}**")
        chemin_rapport = os.path.join(config.PROJECT_ROOT, "docs", "model_comparison.md")
        try:
            with open(chemin_rapport, "r", encoding="utf-8") as f:
                contenu = f.read()
            debut = contenu.find("| scenario")
            fin = contenu.find("## Lecture")
            if debut != -1 and fin != -1:
                st.markdown(contenu[debut:fin].strip())
        except Exception:
            st.info("-")
        st.caption(t("note_scenarios"))

with onglet_actions:
    zone_rouge = df[df["risque_composite"] >= 70]
    zone_ambre = df[(df["risque_composite"] >= 40) & (df["risque_composite"] < 70)]
    zone_verte = df[df["risque_composite"] < 40]

    st.error(t("action_ia_rouge").format(
        n=len(zone_rouge), montant=format_fcfa_compact(zone_rouge["solde_total_xof"].sum()),
    ))
    st.page_link("pages/03_Retention_et_Risque.py", label=t("voir_les_alertes"))

    st.warning(t("action_ia_ambre").format(
        n=len(zone_ambre), montant=format_fcfa_compact(zone_ambre["solde_total_xof"].sum()),
    ))
    st.page_link("pages/03_Retention_et_Risque.py", label=t("voir_les_alertes"))

    st.success(t("action_ia_vert").format(
        n=len(zone_verte), montant=format_fcfa_compact(zone_verte["nbi_estime_xof"].sum()),
    ))
    st.page_link("pages/05_Opportunites_Commerciales.py", label=t("voir_les_alertes"))

    st.write("")
    st.markdown(f"**{t('titre_historique_mlflow')}**")
    try:
        import mlflow
        mlflow.set_tracking_uri(f"sqlite:///{os.path.join(config.PROJECT_ROOT, 'mlflow.db')}")
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name("databank_ci_churn_scoring")
        runs = client.search_runs(
            [experiment.experiment_id], order_by=["start_time DESC"], max_results=10,
        ) if experiment else []

        lignes = []
        for run in runs:
            dataset = run.data.tags.get("dataset", "-")
            modele = run.data.tags.get("model_type", "-")
            est_champion = modele == "LogisticRegression" and "540" in dataset
            lignes.append({
                t("col_version"): run.info.run_id[:8], t("col_date"): pd.Timestamp(
                    run.info.start_time, unit="ms",
                ).strftime("%d/%m/%Y %H:%M"),
                t("kpi_auc"): run.data.metrics.get("auc", "-"), t("kpi_recall_churners"): run.data.metrics.get(
                    "recall", "-",
                ),
                t("col_dataset"): dataset, t("col_statut"): f"🏆 {t('badge_champion')}" if est_champion else modele,
            })
        if lignes:
            st.dataframe(pd.DataFrame(lignes), width='stretch', hide_index=True)
        else:
            st.info("-")
    except Exception:
        st.info("-")

afficher_pied_de_page()
