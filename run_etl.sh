#!/usr/bin/env bash
# Convenience wrapper: run the ETL pipeline end to end.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

python -m src.pipeline --config config/config.yaml
