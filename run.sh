#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
python3 predict.py --input results/all_candidate_records.csv --output results/results.csv
python3 validate_submission.py

