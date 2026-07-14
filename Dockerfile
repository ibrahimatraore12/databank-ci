FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# Le pipeline de données doit être rejoué avant le premier démarrage du dashboard
# The data pipeline must be replayed before the dashboard's first startup
CMD ["sh", "-c", "python3 pipelines/run_pipeline.py && cd dbt_project && DBT_PROFILES_DIR=. dbt run && cd .. && python3 pipelines/run_ml_pipeline.py && streamlit run dashboard/APP.py --server.address=0.0.0.0 --server.port=8501"]
