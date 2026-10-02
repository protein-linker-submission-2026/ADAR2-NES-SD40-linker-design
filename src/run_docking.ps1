[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Evaluations,
    [Parameter(Mandatory=$true)][string]$Output,
    [string]$Ligand,
    [string]$VinaExe = $(if ($env:VINA_EXE) { $env:VINA_EXE } else { 'vina' }),
    [string]$WindowsPython = 'py'
)
$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $PSScriptRoot
if (-not $Ligand) { $Ligand = Join-Path $PackageRoot 'references\prepared\8TNQ_MIQ_experimental.pdb' }
if (-not (Test-Path -LiteralPath $Evaluations -PathType Container)) { throw "Boltz evaluations not found: $Evaluations" }
$leaf = Split-Path -Leaf $WindowsPython
if ($leaf -in @('py','py.exe')) {
    & $WindowsPython -3 (Join-Path $PSScriptRoot 'docking_helper.py') run-batch --evaluations-dir $Evaluations --ligand-pdb $Ligand --output-root $Output --vina $VinaExe
} else {
    & $WindowsPython (Join-Path $PSScriptRoot 'docking_helper.py') run-batch --evaluations-dir $Evaluations --ligand-pdb $Ligand --output-root $Output --vina $VinaExe
}
if ($LASTEXITCODE -ne 0) { throw "Docking failed with exit code $LASTEXITCODE" }
