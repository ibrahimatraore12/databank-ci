# Ingestion des données sources (Excel) vers la couche Bronze
# Ingestion of source data (Excel) into the Bronze layer

import duckdb
import pandas as pd

import config
from src.lineage import update_lineage
from src.logger import log_event
from src.validation import validate_dataframe


def load_source_tables(path: str = config.SOURCE_EXCEL_PATH) -> dict:
    # Charge chaque feuille Excel source, la valide, et met à jour le lignage
    # Loads each source Excel sheet, validates it, and updates lineage
    try:
        tables = {}
        for sheet_name in config.SOURCE_SHEETS:
            df = pd.read_excel(path, sheet_name=sheet_name)
            validate_dataframe(df, sheet_name)
            update_lineage(sheet_name, source=path, row_count=len(df), is_synthetic=False)
            tables[sheet_name] = df

        log_event("pipeline", "INFO", "[BRONZE][INGESTION] OK", {"tables": len(tables)})
        return tables
    except Exception as error:
        log_event("pipeline", "ERROR", "[BRONZE][INGESTION] ECHEC", {"erreur": str(error)})
        raise


def load_tables_to_duckdb(tables: dict, db_path: str = config.DUCKDB_PATH) -> None:
    # Écrit chaque table Bronze dans DuckDB pour que dbt puisse les lire en sources
    # Writes each Bronze table into DuckDB so dbt can read them as sources
    try:
        connection = duckdb.connect(db_path)
        for table_name, df in tables.items():
            bronze_name = f"bronze_{table_name.lower()}"
            connection.execute(f"CREATE OR REPLACE TABLE {bronze_name} AS SELECT * FROM df")
            log_event("pipeline", "INFO", f"[BRONZE][{bronze_name}] OK", {"lignes": len(df)})
        connection.close()
    except Exception as error:
        log_event("pipeline", "ERROR", "[BRONZE][DUCKDB] ECHEC", {"erreur": str(error)})
        raise
