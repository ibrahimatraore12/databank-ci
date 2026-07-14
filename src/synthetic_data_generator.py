# Génération de clients synthétiques par bootstrap métier, en respectant les
# distributions réelles observées en EDA. Toute ligne produite est marquée
# is_synthetic=True pour ne jamais être confondue avec de la donnée réelle.
# Synthetic customer generation via business bootstrap, respecting the real
# distributions observed in EDA. Every produced row is flagged is_synthetic=True
# so it can never be confused with real data.

import numpy as np
import pandas as pd
from scipy import stats

import config
from src.logger import log_event

# Tables liées uniquement par customer_id (pas de dépendance à account_id)
# Tables linked only by customer_id (no dependency on account_id)
TABLES_LIEES_CLIENT = {
    "Loans": ("loan_id", "SYN-LOAN"),
    "Interactions": ("interaction_id", "SYN-INT"),
    "Complaints": ("complaint_id", "SYN-CMP"),
    "Offers": ("offer_id", "SYN-OFF"),
}


def _tirer_clients_source(df_customers: pd.DataFrame, n: int, rng: np.random.Generator) -> pd.DataFrame:
    # Tire n clients réels avec remise (bootstrap) comme base des clients synthétiques
    # Draws n real customers with replacement (bootstrap) as the synthetic customer base
    indices = rng.integers(0, len(df_customers), size=n)
    return df_customers.iloc[indices].reset_index(drop=True)


def _remapper_comptes(df_accounts: pd.DataFrame, ancien_id_client, nouvel_id_client, compteur: dict) -> tuple:
    # Copie les comptes d'un client réel et construit la correspondance ancien->nouveau account_id
    # Copies a real customer's accounts and builds the old->new account_id mapping
    comptes = df_accounts[df_accounts["customer_id"] == ancien_id_client].copy()
    mapping_comptes = {}
    nouveaux_ids = []
    for ancien_account_id in comptes["account_id"]:
        compteur["SYN-ACC"] = compteur.get("SYN-ACC", 0) + 1
        nouvel_account_id = f"SYN-ACC-{compteur['SYN-ACC']:05d}"
        mapping_comptes[ancien_account_id] = nouvel_account_id
        nouveaux_ids.append(nouvel_account_id)

    comptes["account_id"] = nouveaux_ids
    comptes["customer_id"] = nouvel_id_client
    comptes["is_synthetic"] = True
    return comptes, mapping_comptes


def _remapper_avec_compte(
    df_table: pd.DataFrame, cle_id: str, prefixe: str, nouvel_id_client, mapping_comptes: dict, compteur: dict,
) -> pd.DataFrame:
    # Copie les lignes liées à un compte (transactions, cartes) en remappant customer_id et account_id
    # Copies rows linked to an account (transactions, cards), remapping customer_id and account_id
    lignes = df_table[df_table["account_id"].isin(mapping_comptes.keys())].copy()
    if lignes.empty:
        return lignes

    nouveaux_ids = []
    for _ in range(len(lignes)):
        compteur[prefixe] = compteur.get(prefixe, 0) + 1
        nouveaux_ids.append(f"{prefixe}-{compteur[prefixe]:05d}")

    lignes[cle_id] = nouveaux_ids
    lignes["account_id"] = lignes["account_id"].map(mapping_comptes)
    lignes["customer_id"] = nouvel_id_client
    lignes["is_synthetic"] = True
    return lignes


def _remapper_table_client(
    df_table: pd.DataFrame, cle_id: str, prefixe: str, ancien_id_client, nouvel_id_client, compteur: dict,
) -> pd.DataFrame:
    # Copie les lignes liées uniquement par customer_id (prêts, interactions, réclamations, offres)
    # Copies rows linked only by customer_id (loans, interactions, complaints, offers)
    lignes = df_table[df_table["customer_id"] == ancien_id_client].copy()
    if lignes.empty:
        return lignes

    nouveaux_ids = []
    for _ in range(len(lignes)):
        compteur[prefixe] = compteur.get(prefixe, 0) + 1
        nouveaux_ids.append(f"{prefixe}-{compteur[prefixe]:05d}")

    lignes[cle_id] = nouveaux_ids
    lignes["customer_id"] = nouvel_id_client
    lignes["is_synthetic"] = True
    return lignes


def _injecter_desengagement(tables: dict, taux_churn: float, rng: np.random.Generator) -> dict:
    # Dégrade artificiellement les signaux d'engagement d'une fraction des clients synthétiques
    # (transactions plus anciennes) pour approcher le taux de positifs cible du label enrichi
    # Artificially degrades engagement signals for a share of synthetic customers (older
    # transactions) to approach the enriched label's target positive rate
    ids_clients = tables["Customers"]["customer_id"].tolist()
    n_churn = max(1, int(len(ids_clients) * taux_churn))
    clients_a_degrader = rng.choice(ids_clients, size=n_churn, replace=False)

    transactions = tables["Transactions"]
    masque = transactions["customer_id"].isin(clients_a_degrader)
    transactions.loc[masque, "txn_datetime"] = transactions.loc[masque, "txn_datetime"] - pd.Timedelta(days=180)
    tables["Transactions"] = transactions
    return tables


def _valider_distributions_ks(df_reel: pd.DataFrame, df_synthetique: pd.DataFrame, colonne: str) -> float:
    # Test de Kolmogorov-Smirnov : compare la distribution réelle et synthétique d'une colonne
    # Kolmogorov-Smirnov test: compares the real vs. synthetic distribution of a column
    statistique, p_value = stats.ks_2samp(df_reel[colonne].dropna(), df_synthetique[colonne].dropna())
    log_event("pipeline", "INFO", f"[SYNTHETIC][KS-TEST][{colonne}]",
              {"statistique": round(float(statistique), 3), "p_value": round(float(p_value), 3)})
    return float(p_value)


def generate_synthetic_customers(
    df_real: dict, n: int = config.SYNTHETIC_N_CUSTOMERS,
    churn_rate: float = config.SYNTHETIC_CHURN_RATE, seed: int = config.RANDOM_SEED,
) -> dict:
    # Génère n clients synthétiques et toutes leurs tables liées par bootstrap métier
    # Generates n synthetic customers and all their linked tables via business bootstrap
    try:
        rng = np.random.default_rng(seed)
        clients_source = _tirer_clients_source(df_real["Customers"], n, rng)

        collectes = {nom: [] for nom in TABLES_LIEES_CLIENT}
        collectes.update({"Customers": [], "Accounts": [], "Transactions": [], "Cards": []})
        compteur_ids = {}

        for i, (_, client_reel) in enumerate(clients_source.iterrows(), start=1):
            ancien_id = client_reel["customer_id"]
            nouvel_id = f"SYN-{i:04d}"

            client_copie = client_reel.copy()
            client_copie["customer_id"] = nouvel_id
            client_copie["is_synthetic"] = True
            collectes["Customers"].append(client_copie.to_frame().T)

            comptes, mapping_comptes = _remapper_comptes(df_real["Accounts"], ancien_id, nouvel_id, compteur_ids)
            if not comptes.empty:
                collectes["Accounts"].append(comptes)

            txns = _remapper_avec_compte(
                df_real["Transactions"], "txn_id", "SYN-TXN", nouvel_id, mapping_comptes, compteur_ids,
            )
            if not txns.empty:
                collectes["Transactions"].append(txns)

            cartes = _remapper_avec_compte(
                df_real["Cards"], "card_id", "SYN-CARD", nouvel_id, mapping_comptes, compteur_ids,
            )
            if not cartes.empty:
                collectes["Cards"].append(cartes)

            for nom_table, (cle_id, prefixe) in TABLES_LIEES_CLIENT.items():
                lignes = _remapper_table_client(
                    df_real[nom_table], cle_id, prefixe, ancien_id, nouvel_id, compteur_ids,
                )
                if not lignes.empty:
                    collectes[nom_table].append(lignes)

        tables_synthetiques = {}
        for nom, morceaux in collectes.items():
            if morceaux:
                tables_synthetiques[nom] = pd.concat(morceaux, ignore_index=True)
            else:
                tables_synthetiques[nom] = df_real[nom].iloc[0:0].copy()

        # Branches et Channels sont des référentiels partagés, pas des données par client :
        # on les reprend tels quels, non marqués synthétiques
        # Branches and Channels are shared reference data, not per-customer data:
        # reused as-is, not flagged synthetic
        tables_synthetiques["Branches"] = df_real["Branches"].copy()
        tables_synthetiques["Channels"] = df_real["Channels"].copy()

        tables_synthetiques = _injecter_desengagement(tables_synthetiques, churn_rate, rng)

        p_value = _valider_distributions_ks(
            df_real["Customers"], tables_synthetiques["Customers"], "monthly_income_xof",
        )
        if p_value < 0.05:
            log_event("pipeline", "ERROR", "[SYNTHETIC][KS-TEST] distribution divergente", {"p_value": p_value})

        log_event("pipeline", "INFO", "[SYNTHETIC][GENERATION] OK", {"clients_generes": n, "churn_rate": churn_rate})
        return tables_synthetiques
    except Exception as error:
        log_event("pipeline", "ERROR", "[SYNTHETIC][GENERATION] ECHEC", {"erreur": str(error)})
        raise
