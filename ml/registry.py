# Sauvegarde et chargement des modèles et du préprocesseur (joblib)
# Saving and loading models and the preprocessor (joblib)

import os

import joblib

import config

MODEL_REGISTRY_DIR = os.path.join(config.PROJECT_ROOT, "ml", "artifacts")
PREPROCESSOR_PATH = os.path.join(MODEL_REGISTRY_DIR, "preprocessor.pkl")


def save_model(model, name: str) -> str:
    # Sauvegarde un modèle entraîné dans le registre local
    # Saves a trained model to the local registry
    os.makedirs(MODEL_REGISTRY_DIR, exist_ok=True)
    chemin = os.path.join(MODEL_REGISTRY_DIR, f"{name}.pkl")
    joblib.dump(model, chemin)
    return chemin


def load_model(name: str):
    # Recharge un modèle précédemment sauvegardé
    # Reloads a previously saved model
    chemin = os.path.join(MODEL_REGISTRY_DIR, f"{name}.pkl")
    return joblib.load(chemin)


def save_preprocessor(scaler) -> str:
    # Sauvegarde le préprocesseur ajusté sur le jeu d'entraînement
    # Saves the preprocessor fitted on the training set
    os.makedirs(MODEL_REGISTRY_DIR, exist_ok=True)
    joblib.dump(scaler, PREPROCESSOR_PATH)
    return PREPROCESSOR_PATH


def load_preprocessor():
    # Recharge le préprocesseur ajusté sur le jeu d'entraînement
    # Reloads the preprocessor fitted on the training set
    return joblib.load(PREPROCESSOR_PATH)
