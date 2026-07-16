FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Construit les données au moment du build de l'image, pas au démarrage du
# conteneur : adapté au modèle scale-to-zero de Cloud Run, où chaque nouvelle
# instance doit démarrer instantanément plutôt que rejouer tout le pipeline
# Builds the data at image build time, not at container startup: fits Cloud
# Run's scale-to-zero model, where every new instance must start instantly
# instead of replaying the whole pipeline
RUN python3 pipelines/run_pipeline.py \
    && cd dbt_project && DBT_PROFILES_DIR=. dbt run && cd .. \
    && python3 pipelines/run_ml_pipeline.py

# Cloud Run injecte le port d'écoute via la variable PORT (8080 par défaut) ;
# en local (docker run sans PORT défini), on retombe sur 8501
# Cloud Run injects the listening port via the PORT variable (8080 by
# default); locally (docker run without PORT set), it falls back to 8501
ENV PORT=8501
EXPOSE 8501

CMD ["sh", "-c", "streamlit run dashboard/APP.py --server.address=0.0.0.0 --server.port=${PORT}"]
