$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $PSScriptRoot
$Evaluations = Join-Path $PackageRoot 'results_v2\boltz\evaluations'
$Ligand = Join-Path $PackageRoot 'references\prepared\8TNQ_MIQ_experimental.pdb'
$Output = Join-Path $PackageRoot 'results_v2\docking'
$VinaExe = if ($env:VINA_EXE) { $env:VINA_EXE } else { 'vina' }
if (-not (Test-Path -LiteralPath $Evaluations -PathType Container)) { throw "Boltz evaluations not found: $Evaluations" }
py -3 (Join-Path $PSScriptRoot 'docking_helper.py') run-batch --evaluations-dir $Evaluations --ligand-pdb $Ligand --output-root $Output --vina $VinaExe
if ($LASTEXITCODE -ne 0) { throw "Docking failed with exit code $LASTEXITCODE" }
