# Zone réservée aux administrateurs — état technique du pipeline et des logs
# Administrator-only area — technical pipeline and log status

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import config  # noqa: E402
from components.ui import (  # noqa: E402
    afficher_entete, afficher_entete_section, afficher_etapes_pipeline, afficher_guide,
    afficher_pied_de_page, format_run_id, t,
)
from src.logger import log_event  # noqa: E402

st.set_page_config(page_title="Administration", page_icon="🏦", layout="wide")

afficher_entete(t("nav_admin"), t("page_admin_intro"), "🔧")
afficher_guide(t("guide_admin"))

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "databank-admin")

# Colonnes que dbt_project/models/staging/*.sql lit réellement dans chaque feuille
# (is_synthetic exclu : ajoutée automatiquement par pipelines/run_pipeline.py si
# absente, jamais attendue dans un fichier uploadé) — sert à détecter un fichier
# structurellement incompatible avec le pipeline avant de lancer quoi que ce soit
# Columns dbt_project/models/staging/*.sql actually reads from each sheet
# (is_synthetic excluded: added automatically by pipelines/run_pipeline.py when
# missing, never expected in an uploaded file) — used to detect a file that's
# structurally incompatible with the pipeline before running anything
COLONNES_ATTENDUES_PAR_FEUILLE = {
    "Customers": [
        "customer_id", "full_name", "gender", "date_of_birth", "city", "district", "occupation",
        "segment", "monthly_income_xof", "onboarding_date", "primary_branch_id", "preferred_channel",
        "mobile_app_active", "internet_banking_active", "mobile_money_linked", "kyc_level",
        "risk_band", "marketing_opt_in", "last_contact_date", "marital_status",
    ],
    "Accounts": [
        "account_id", "customer_id", "account_type", "currency", "open_date", "status", "branch_id",
        "avg_balance_90d_xof", "current_balance_xof", "salary_domiciled_flag", "overdraft_limit_xof",
    ],
    "Transactions": [
        "txn_id", "account_id", "customer_id", "txn_datetime", "txn_type", "channel_id",
        "merchant_category", "amount_xof", "direction", "counterparty_type", "city",
        "is_international", "is_disputed",
    ],
    "Loans": [
        "loan_id", "customer_id", "repayment_account_id", "loan_type", "origination_date",
        "principal_xof", "interest_rate_pct", "term_months", "monthly_installment_xof",
        "outstanding_balance_xof", "days_past_due", "status", "purpose", "collateral_flag",
        "next_due_date",
    ],
    "Cards": [
        "card_id", "customer_id", "account_id", "card_type", "card_tier", "network", "issue_date",
        "expiry_date", "status", "contactless_flag", "ecommerce_enabled", "monthly_spend_90d_xof",
    ],
    "Branches": ["branch_id", "branch_name", "city", "district", "branch_type"],
    "Channels": ["channel_id", "channel_name", "channel_group", "description"],
    "Interactions": [
        "interaction_id", "customer_id", "interaction_datetime", "channel", "interaction_type",
        "topic", "sentiment", "resolved_flag", "resolution_time_hours", "agent_team", "notes",
    ],
    "Complaints": [
        "complaint_id", "customer_id", "opened_date", "closed_date", "category", "severity",
        "status", "root_cause", "compensation_xof", "free_text",
    ],
    "Offers": [
        "offer_id", "customer_id", "offer_date", "offer_type", "channel", "accepted_flag",
        "product_target", "expected_value_xof",
    ],
}

# Fichiers modifiés par relancer_pipeline_complet : sauvegardés avant, restaurés si
# le pipeline échoue en cours de route (fichier incompatible détecté trop tard,
# panne dbt...), pour que l'instance ne reste jamais dans un état partiel/cassé
# Files modified by relancer_pipeline_complet: backed up before, restored if the
# pipeline fails partway (incompatible file caught too late, dbt failure...), so
# the instance never stays in a partial/broken state
FICHIERS_PROTEGES_AVANT_RECALCUL = [config.SOURCE_EXCEL_PATH, config.DUCKDB_PATH, config.PIPELINE_STATE_PATH]


def verifier_mot_de_passe() -> bool:
    # Contrôle d'accès simple par mot de passe pour la zone d'administration
    # Simple password gate for the administration area
    if st.session_state.get("admin_authentifie"):
        return True

    saisie = st.text_input(t("mot_de_passe"), type="password")
    if st.button(t("connexion")):
        if saisie == ADMIN_PASSWORD:
            st.session_state["admin_authentifie"] = True
            st.rerun()
        else:
            st.error(t("acces_refuse"))
    return False


def charger_json(chemin: str) -> dict:
    # Charge un fichier JSON d'état, retourne un dict vide s'il n'existe pas encore
    # Loads a JSON state file, returns an empty dict if it doesn't exist yet
    if not os.path.exists(chemin):
        return {}
    with open(chemin, "r") as f:
        return json.load(f)


def valider_fichier_uploade(fichier) -> list:
    # Même contrôle que src/ingest.py::load_source_tables (feuille non vide,
    # taux de valeurs nulles), plus une vérification des colonnes attendues par
    # dbt (COLONNES_ATTENDUES_PAR_FEUILLE) — sans quoi un fichier avec les bons
    # noms de feuilles mais des colonnes incompatibles ne serait détecté qu'après
    # ~55 secondes de recalcul, au milieu de dbt run. Ne lève jamais : on veut le
    # rapport complet des 10 feuilles, pas un arrêt à la première erreur
    # Same check as src/ingest.py::load_source_tables (non-empty sheet, null
    # rate), plus a check of the columns dbt actually expects
    # (COLONNES_ATTENDUES_PAR_FEUILLE) — without it, a file with the right sheet
    # names but incompatible columns would only be caught ~55 seconds into the
    # recompute, mid-way through dbt run. Never raises: we want the full 10-sheet
    # report, not a stop at the first error
    rapports = []
    for nom_feuille in config.SOURCE_SHEETS:
        try:
            df = pd.read_excel(fichier, sheet_name=nom_feuille)
            taux_nuls = round(100 * df.isna().sum().sum() / max(df.size, 1), 2)
            erreurs = [t("feuille_vide")] if df.empty else []

            colonnes_attendues = COLONNES_ATTENDUES_PAR_FEUILLE.get(nom_feuille, [])
            colonnes_manquantes = [c for c in colonnes_attendues if c not in df.columns]
            if colonnes_manquantes:
                erreurs.append(t("colonnes_manquantes").format(colonnes=", ".join(colonnes_manquantes)))

            rapports.append({
                "table": nom_feuille, "lignes": len(df), "taux_nuls_pct": taux_nuls, "erreurs": ", ".join(erreurs),
            })
        except Exception as erreur:
            rapports.append({
                "table": nom_feuille, "lignes": 0, "taux_nuls_pct": None,
                "erreurs": f"{t('feuille_illisible')} : {erreur}",
            })
    return rapports


def _sauvegarder_avant_recalcul() -> dict:
    sauvegardes = {}
    for chemin in FICHIERS_PROTEGES_AVANT_RECALCUL:
        if os.path.exists(chemin):
            chemin_backup = chemin + ".backup_avant_recalcul"
            shutil.copy2(chemin, chemin_backup)
            sauvegardes[chemin] = chemin_backup
    return sauvegardes


def _restaurer_et_nettoyer(sauvegardes: dict, restaurer: bool) -> None:
    for chemin, chemin_backup in sauvegardes.items():
        if restaurer:
            shutil.copy2(chemin_backup, chemin)
        os.remove(chemin_backup)


def relancer_pipeline_complet(fichier) -> bool:
    # Écrit le fichier uploadé à la place du fichier source, puis rejoue tout le
    # pipeline dans le processus courant : ingestion+enrichissement (Python),
    # dbt run (sous-processus, même commande que le Dockerfile), puis ML.
    # Les fichiers touchés sont sauvegardés avant : si le pipeline échoue en
    # cours de route (fichier incompatible passé au travers de la validation,
    # panne dbt...), ils sont restaurés pour que cette instance ne reste pas
    # dans un état partiel — l'admin voit l'erreur, rien d'autre ne change.
    # Persiste ensuite le résultat sur GCS pour que ça survive au redémarrage de
    # cette instance et soit repris par les autres — un échec de cette dernière
    # étape est logué mais ne fait pas échouer le recalcul (déjà réel localement)
    # Writes the uploaded file over the source file, then replays the whole
    # pipeline in the current process: ingestion+enrichment (Python), dbt run
    # (subprocess, same command as the Dockerfile), then ML. The affected files
    # are backed up beforehand: if the pipeline fails partway (an incompatible
    # file slipping past validation, a dbt failure...), they're restored so
    # this instance doesn't stay in a partial state — the admin sees the
    # error, nothing else changes. Then persists the result to GCS so it
    # survives this instance's restart and is picked up by the others — a
    # failure of this last step is logged but doesn't fail the recompute
    # (already real locally)
    from pipelines.run_ml_pipeline import run_ml_pipeline
    from pipelines.run_pipeline import run_pipeline
    from src.storage_sync import televerser_vers_gcs

    sauvegardes = _sauvegarder_avant_recalcul()
    try:
        fichier.seek(0)
        with open(config.SOURCE_EXCEL_PATH, "wb") as f:
            f.write(fichier.read())

        run_pipeline()

        dbt_dir = os.path.join(config.PROJECT_ROOT, "dbt_project")
        resultat = subprocess.run(
            ["dbt", "run"], cwd=dbt_dir, env={**os.environ, "DBT_PROFILES_DIR": dbt_dir},
            capture_output=True, text=True, timeout=120,
        )
        if resultat.returncode != 0:
            raise RuntimeError(resultat.stderr[-1000:] or resultat.stdout[-1000:])

        run_ml_pipeline()
    except Exception:
        _restaurer_et_nettoyer(sauvegardes, restaurer=True)
        raise
    _restaurer_et_nettoyer(sauvegardes, restaurer=False)

    try:
        televerser_vers_gcs()
    except Exception as erreur:
        log_event("pipeline", "ERROR", "[GCS][SYNC] Persistance échouée après recalcul", {"erreur": str(erreur)})
        return False

    # Best-effort : l'Assistant IA (serveur MCP, processus séparé) ne relit GCS
    # qu'à son propre démarrage — on lui demande de le faire tout de suite plutôt
    # que d'attendre son prochain redémarrage naturel
    # Best-effort: the AI Assistant (MCP server, separate process) only re-reads
    # GCS at its own startup — ask it to do so right away instead of waiting for
    # its next natural restart
    from components.mcp_client import resynchroniser_mcp
    if not resynchroniser_mcp():
        log_event("pipeline", "ERROR", "[MCP][RESYNC] Échec — Assistant IA périmé jusqu'à son redémarrage", {})

    return True


def afficher_derniere_lignes_log(chemin: str, n: int = 20) -> None:
    # Affiche les dernières lignes d'un fichier de log
    # Displays the last lines of a log file
    if not os.path.exists(chemin):
        st.caption("—")
        return
    with open(chemin, "r") as f:
        lignes = f.readlines()
    st.code("".join(lignes[-n:]) or "—", language="text")


if not verifier_mot_de_passe():
    afficher_pied_de_page()
    st.stop()

st.success(t("acces_autorise"))

etat_pipeline = charger_json(config.PIPELINE_STATE_PATH)
lineage = charger_json(config.LINEAGE_PATH)

afficher_entete_section(t("etat_pipeline"))
if etat_pipeline:
    run_id = etat_pipeline.get("last_updated", "—")
    st.caption(f"run_id : {format_run_id(run_id)}")
    afficher_etapes_pipeline(etat_pipeline)
else:
    st.info("—")

afficher_entete_section(t("titre_lineage"))
st.json(lineage) if lineage else st.info("—")

afficher_entete_section(t("titre_logs"))
onglet_pipeline, onglet_ml, onglet_api, onglet_errors = st.tabs(["pipeline.log", "ml.log", "api.log", "errors.log"])
with onglet_pipeline:
    afficher_derniere_lignes_log(os.path.join(config.LOGS_DIR, "pipeline.log"))
with onglet_ml:
    afficher_derniere_lignes_log(os.path.join(config.LOGS_DIR, "ml.log"))
with onglet_api:
    afficher_derniere_lignes_log(os.path.join(config.LOGS_DIR, "api.log"))
with onglet_errors:
    afficher_derniere_lignes_log(os.path.join(config.LOGS_DIR, "errors.log"))

afficher_entete_section(t("titre_etude_modeles"))
chemin_rapport = os.path.join(config.PROJECT_ROOT, "docs", "model_comparison.md")
try:
    with open(chemin_rapport, "r", encoding="utf-8") as f:
        st.markdown(f.read())
except Exception:
    st.info("—")

afficher_entete_section(t("titre_upload"))
st.caption(t("upload_intro"))
fichier_uploade = st.file_uploader(t("uploader_label"), type=["xlsx"])
if fichier_uploade is not None:
    rapports_feuilles = valider_fichier_uploade(fichier_uploade)
    nb_erreurs = sum(1 for r in rapports_feuilles if r["erreurs"])

    if nb_erreurs == 0:
        st.success(t("upload_valide"))
    else:
        st.error(t("upload_invalide").format(n=nb_erreurs))

    tableau_validation = pd.DataFrame(rapports_feuilles).rename(columns={
        "table": t("col_feuille"), "lignes": t("col_lignes"),
        "taux_nuls_pct": t("col_taux_nuls"), "erreurs": t("col_erreurs"),
    })
    st.dataframe(tableau_validation, width='stretch', hide_index=True)

    if nb_erreurs == 0:
        st.info(t("upload_instructions"))
        if st.button(t("recalculer_maintenant")):
            try:
                with st.spinner(t("recalcul_en_cours")):
                    persiste = relancer_pipeline_complet(fichier_uploade)
                if persiste:
                    st.success(t("recalcul_succes"))
                else:
                    st.warning(t("recalcul_succes_local_seulement"))
            except Exception as erreur:
                st.error(t("recalcul_echec"))
                st.code(str(erreur)[:1000], language="text")

afficher_pied_de_page()
