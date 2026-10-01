$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python predict.py --input results/all_candidate_records.csv --output results/results.csv
python validate_submission.py

