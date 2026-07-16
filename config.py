# Constantes centralisées du projet dataBank CI Customer 360
# Centralized constants for the dataBank CI Customer 360 project

import os

# Chemins racine
# Root paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_ENRICHED_DIR = os.path.join(PROJECT_ROOT, "data", "enriched")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
LINEAGE_PATH = os.path.join(PROJECT_ROOT, "lineage.json")
PIPELINE_STATE_PATH = os.path.join(PROJECT_ROOT, "pipeline_state.json")

# Source des données
# Data source
SOURCE_EXCEL_PATH = os.path.join(DATA_RAW_DIR, "starter_dataset.xlsx")
DUCKDB_PATH = os.path.join(PROJECT_ROOT, "dbt_project", "databank_ci.duckdb")

SOURCE_SHEETS = [
    "Customers", "Accounts", "Transactions", "Loans", "Cards",
    "Branches", "Channels", "Interactions", "Complaints", "Offers",
]

# Incrémenter uniquement quand un changement de schéma dbt (nouvelle colonne
# dans un mart, etc.) rend un ancien pipeline_state.json/databank_ci.duckdb
# restauré depuis GCS incompatible avec le code courant — voir src/storage_sync.py
# Bump only when a dbt schema change (new mart column, etc.) makes an older
# pipeline_state.json/databank_ci.duckdb restored from GCS incompatible with
# the current code — see src/storage_sync.py
DATA_SCHEMA_VERSION = 1

# Idempotence : graine fixée partout (dbt seed, split ML, génération synthétique)
# Idempotence: seed fixed everywhere (dbt seed, ML split, synthetic generation)
RANDOM_SEED = 42

# Règles métier issues de l'EDA (voir docs/decisions.md)
# Business rules derived from the EDA (see docs/decisions.md)
LOAN_DPD_THRESHOLD_DAYS = 15
CHURN_RISK_RECENCY_THRESHOLD_DAYS = 90

# Pondération du score de règles métier (ml/rules.py) — Phase 1
# Business rule score weighting (ml/rules.py) — Phase 1
RULES_WEIGHT_RECENCY = 0.40
RULES_WEIGHT_COMPLAINTS = 0.30
RULES_WEIGHT_DIGITAL = 0.20
RULES_WEIGHT_TREND = 0.10

# Pondération du score d'engagement digital (src/data_enrichment.py)
# Digital engagement score weighting (src/data_enrichment.py)
ENGAGEMENT_WEIGHT_RECENCY = 0.30
ENGAGEMENT_WEIGHT_TRANSACTIONS = 0.25
ENGAGEMENT_WEIGHT_DIGITAL = 0.25
ENGAGEMENT_WEIGHT_PRODUCTS = 0.20

# Formule NBI estimé (standard UEMOA simplifié) — voir docs/decisions.md
# Estimated NBI formula (simplified UEMOA standard) — see docs/decisions.md
NBI_BALANCE_RATE = 0.035
NBI_PER_TRANSACTION_XOF = 500
NBI_PER_PRODUCT_XOF = 15000

# Génération synthétique
# Synthetic generation
SYNTHETIC_N_CUSTOMERS = 400
SYNTHETIC_CHURN_RATE = 0.10

# Formatage d'affichage (dashboard)
# Display formatting (dashboard)
CURRENCY_LABEL = "FCFA"

# Rotation des logs
# Log rotation
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5
