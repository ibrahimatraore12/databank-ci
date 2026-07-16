# Tests des outils MCP : lecture seule, formats de retour attendus
# MCP tool tests: read-only, expected return formats

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp_server"))

from tools.complaints import get_complaint_analysis  # noqa: E402
from tools.customers import get_at_risk_customers, get_customer_profile  # noqa: E402
from tools.portfolio import get_cross_sell_candidates, get_portfolio_kpis  # noqa: E402


def test_get_at_risk_customers_respecte_la_limite():
    resultat = get_at_risk_customers(limit=5)
    assert len(resultat) <= 5
    assert all("risque_composite" in ligne for ligne in resultat)


def test_get_at_risk_customers_est_trie_par_risque_decroissant():
    resultat = get_at_risk_customers(limit=10)
    scores = [ligne["risque_composite"] for ligne in resultat]
    assert scores == sorted(scores, reverse=True)


def test_get_customer_profile_client_inconnu_renvoie_vide():
    profil = get_customer_profile("CLIENT_INEXISTANT")
    assert profil == {}


def test_get_customer_profile_client_connu_a_une_action_recommandee():
    top = get_at_risk_customers(limit=1)
    profil = get_customer_profile(top[0]["customer_id"])
    assert "next_best_action" in profil


def test_get_cross_sell_candidates_respecte_la_limite():
    resultat = get_cross_sell_candidates(limit=5)
    assert len(resultat) <= 5


def test_get_portfolio_kpis_global_a_les_cles_attendues():
    kpis = get_portfolio_kpis()
    for cle in ["nb_clients", "risque_composite_moyen", "taux_salaire_domicilie_pct"]:
        assert cle in kpis


def test_get_portfolio_kpis_par_segment():
    kpis = get_portfolio_kpis(segment="Premier")
    assert kpis.get("segment") == "Premier"


def test_get_complaint_analysis_total_coherent_avec_le_detail():
    analyse = get_complaint_analysis()
    assert analyse["total"] == sum(d["nb_reclamations"] for d in analyse["detail"])
