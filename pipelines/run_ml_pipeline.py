# Orchestration ML : entraîne le modèle de production et lance l'étude comparative
# ML orchestration: trains the production model and runs the comparative study

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.comparison import run_comparison  # noqa: E402
from ml.data import get_X_y, load_data, preprocess_data, split_data  # noqa: E402
from ml.model import evaluate_model, train_model  # noqa: E402
from ml.registry import save_model  # noqa: E402
from src.logger import log_event  # noqa: E402
from pipelines.run_pipeline import update_pipeline_state  # noqa: E402

PRODUCTION_MODEL_NAME = "churn_scoring_logistic"


def train_production_model() -> dict:
    # Entraîne le modèle de référence mis à disposition du dashboard et du MCP server
    # Trains the reference model made available to the dashboard and the MCP server
    df = load_data(use_synthetic=True)
    X, y = get_X_y(df)
    X_train, X_test, y_train, y_test = split_data(X, y)

    X_train_prep = preprocess_data(X_train, fit=True)
    X_test_prep = preprocess_data(X_test, fit=False)

    model = train_model(X_train_prep, y_train, model_type="logistic")
    metrics = evaluate_model(model, X_test_prep, y_test)

    save_model(model, PRODUCTION_MODEL_NAME)
    log_event("ml", "INFO", "[ML][PRODUCTION_MODEL] OK", {"nom": PRODUCTION_MODEL_NAME, **metrics})
    return metrics


def run_ml_pipeline() -> None:
    # Point d'entrée de l'orchestration ML complète
    # Entry point for the full ML orchestration
    try:
        metrics = train_production_model()
        update_pipeline_state("ml_production_model", "OK")

        run_comparison()
        update_pipeline_state("ml_comparison", "OK")

        log_event("ml", "INFO", "[ML][PIPELINE] OK", {"statut": "SUCCESS", **metrics})
    except Exception as error:
        update_pipeline_state("ml_pipeline", "FAILED")
        log_event("ml", "ERROR", "[ML][PIPELINE] ECHEC", {"erreur": str(error)})
        raise


if __name__ == "__main__":
    run_ml_pipeline()
