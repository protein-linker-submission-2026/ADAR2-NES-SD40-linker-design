[CmdletBinding()]
param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& $Python predict.py --input results/all_candidate_records.csv --output results/results.csv
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python validate_submission.py
exit $LASTEXITCODE

