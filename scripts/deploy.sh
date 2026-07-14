#!/usr/bin/env bash
# Validation complète avant déploiement : lint, tests, dbt, build Docker
# Full validation before deployment: lint, tests, dbt, Docker build
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> flake8"
flake8 .

echo "==> pytest"
pytest tests/ -v

echo "==> dbt run + dbt test"
cd dbt_project
export DBT_PROFILES_DIR="$(pwd)"
dbt run
dbt test
cd "$PROJECT_ROOT"

echo "==> docker build"
docker build -t databank-ci:latest .

echo "==> Validation complète : OK"
