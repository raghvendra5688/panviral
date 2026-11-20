#!/usr/bin/env bash
# End-to-end panviral pipeline.
#
#   bash scripts/run_pipeline.sh              # models -> screening -> aggregation
#   bash scripts/run_pipeline.sh aggregate    # only re-aggregate the shipped results (no GPU, no DeepPurpose)
#
# Run from anywhere; paths are resolved relative to the repository root.
# Optional: set PYTHON=/path/to/env/bin/python to choose the interpreter.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python}"
cd "$ROOT"
mkdir -p logs

case "${1:-all}" in
  aggregate)
    "$PY" scripts/03_aggregate_ranks.py --compare-with results/panviral_drug_protein_ranks.csv \
      --out logs/ranks_reproduced.csv
    ;;
  all)
    "$PY" scripts/00_download_models.py
    "$PY" scripts/02_run_virtual_screening.py
    "$PY" scripts/03_aggregate_ranks.py
    ;;
  *)
    echo "usage: $0 [all|aggregate]" >&2; exit 2 ;;
esac
