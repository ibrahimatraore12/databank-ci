# Tests de src/synthetic_data_generator.py : intégrité référentielle et marquage is_synthetic
# Tests for src/synthetic_data_generator.py: referential integrity and is_synthetic flagging

import pytest

from src.ingest import load_source_tables
from src.synthetic_data_generator import generate_synthetic_customers


@pytest.fixture(scope="module")
def tables_synthetiques():
    tables_reelles = load_source_tables()
    return generate_synthetic_customers(tables_reelles, n=50, churn_rate=0.10, seed=42)


def test_generate_synthetic_customers_produit_le_bon_volume(tables_synthetiques):
    assert len(tables_synthetiques["Customers"]) == 50


def test_generate_synthetic_customers_marque_is_synthetic(tables_synthetiques):
    assert tables_synthetiques["Customers"]["is_synthetic"].all()
    assert tables_synthetiques["Accounts"]["is_synthetic"].all()


def test_generate_synthetic_customers_integrite_transactions_comptes(tables_synthetiques):
    comptes_ids = set(tables_synthetiques["Accounts"]["account_id"])
    transactions_comptes_ids = set(tables_synthetiques["Transactions"]["account_id"])
    assert transactions_comptes_ids.issubset(comptes_ids)


def test_generate_synthetic_customers_est_idempotent():
    tables_reelles = load_source_tables()
    resultat_1 = generate_synthetic_customers(tables_reelles, n=30, churn_rate=0.10, seed=42)
    resultat_2 = generate_synthetic_customers(tables_reelles, n=30, churn_rate=0.10, seed=42)
    assert resultat_1["Customers"]["customer_id"].tolist() == resultat_2["Customers"]["customer_id"].tolist()
