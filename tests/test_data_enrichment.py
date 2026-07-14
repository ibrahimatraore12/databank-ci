# Tests de src/data_enrichment.py : score d'engagement, NBI estimé, risque composite
# Tests for src/data_enrichment.py: engagement score, estimated NBI, composite risk

import pandas as pd
import pytest

from src.data_enrichment import generate_nbi_estime, generate_risque_composite, generate_score_engagement
from src.ingest import load_source_tables


@pytest.fixture(scope="module")
def tables_reelles():
    return load_source_tables()


def test_generate_score_engagement_reste_dans_0_100(tables_reelles):
    resultat = generate_score_engagement(
        tables_reelles["Customers"], tables_reelles["Transactions"],
        tables_reelles["Accounts"], tables_reelles["Interactions"],
    )
    assert resultat["score_engagement"].between(0, 100).all()
    assert len(resultat) == len(tables_reelles["Customers"])


def test_generate_nbi_estime_marque_le_flag(tables_reelles):
    resultat = generate_nbi_estime(
        tables_reelles["Customers"], tables_reelles["Accounts"], tables_reelles["Transactions"],
    )
    assert (resultat["estimated_nbi_flag"]).all()
    assert (resultat["nbi_estime_xof"] >= 0).all()


def test_generate_risque_composite_leve_une_erreur_sans_colonnes_requises():
    df_incomplet = pd.DataFrame({"customer_id": ["C1"]})
    with pytest.raises(ValueError):
        generate_risque_composite(df_incomplet)


def test_generate_risque_composite_client_dormant_est_plus_risque():
    # Un client très inactif et sans digital doit avoir un risque plus élevé
    # qu'un client actif et bien équipé en digital
    # A very inactive, non-digital customer must score riskier than an
    # active, digitally well-equipped customer
    df = pd.DataFrame({
        "customer_id": ["C1", "C2"],
        "recency_jours": [400, 1],
        "nb_reclamations_ouvertes": [3, 0],
        "tendance_transactions": [-10, 10],
        "score_digital": [0, 3],
    })
    resultat = generate_risque_composite(df)
    risque_c1 = resultat.loc[resultat["customer_id"] == "C1", "risque_composite"].iloc[0]
    risque_c2 = resultat.loc[resultat["customer_id"] == "C2", "risque_composite"].iloc[0]
    assert risque_c1 > risque_c2
