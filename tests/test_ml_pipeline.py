# Tests du pipeline ML : chargement, split, entraînement, évaluation, score de règles
# ML pipeline tests: loading, split, training, evaluation, rule-based score

import pandas as pd
import pytest

from ml.data import get_X_y, load_data, preprocess_data, split_data
from ml.model import evaluate_model, train_model
from ml.rules import calculate_risk_score


@pytest.fixture(scope="module")
def df_reel():
    return load_data(use_synthetic=False)


def test_load_data_a_un_label_binaire(df_reel):
    assert set(df_reel["churn_flag"].unique()).issubset({0, 1})


def test_load_data_sans_synthetique_ne_contient_que_du_reel(df_reel):
    assert (~df_reel["is_synthetic"]).all()


def test_get_X_y_meme_nombre_de_lignes(df_reel):
    X, y = get_X_y(df_reel)
    assert len(X) == len(y) == len(df_reel)


def test_split_data_respecte_la_stratification(df_reel):
    X, y = get_X_y(df_reel)
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.2)
    taux_positifs_total = y.mean()
    taux_positifs_test = y_test.mean()
    assert abs(taux_positifs_total - taux_positifs_test) < 0.1


def test_preprocess_data_centre_reduit_les_features(df_reel):
    X, y = get_X_y(df_reel)
    X_train, X_test, _, _ = split_data(X, y, test_size=0.2)
    X_train_prep = preprocess_data(X_train, fit=True)
    assert abs(X_train_prep.mean().mean()) < 0.5


def test_train_model_logistic_produit_des_predictions(df_reel):
    X, y = get_X_y(df_reel)
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.2)
    X_train_prep = preprocess_data(X_train, fit=True)
    X_test_prep = preprocess_data(X_test, fit=False)

    model = train_model(X_train_prep, y_train, model_type="logistic")
    predictions = model.predict(X_test_prep)
    assert len(predictions) == len(y_test)


def test_evaluate_model_avertit_sur_petit_echantillon(df_reel):
    X, y = get_X_y(df_reel)
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.2)
    X_train_prep = preprocess_data(X_train, fit=True)
    X_test_prep = preprocess_data(X_test, fit=False)

    model = train_model(X_train_prep, y_train, model_type="logistic")
    metrics = evaluate_model(model, X_test_prep, y_test)
    assert "avertissement" in metrics


def test_calculate_risk_score_leve_une_erreur_sans_colonnes_requises():
    df_incomplet = pd.DataFrame({"customer_id": ["C1", "C2"]})
    with pytest.raises(ValueError):
        calculate_risk_score(df_incomplet)


def test_calculate_risk_score_reste_dans_0_100(df_reel):
    scores = calculate_risk_score(df_reel)
    assert scores["score_regles"].between(0, 100).all()
