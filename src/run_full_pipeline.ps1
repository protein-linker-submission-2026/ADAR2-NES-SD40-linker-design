[CmdletBinding()]
param(
    [int[]]$Spans = (11..20),
    [string]$OutputRoot,
    [string]$WslDistribution = 'Ubuntu-22.04',
    [string]$WindowsPython = 'py',
    [string]$VinaExe = $(if ($env:VINA_EXE) { $env:VINA_EXE } else { 'vina' }),
    [switch]$SmokeTest,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputRoot) { $OutputRoot = Join-Path $RepoRoot 'reproduction_runs' }
$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)

foreach ($span in $Spans) {
    if ($span -lt 11 -or $span -gt 20) { throw "Span must be between 11 and 20 A: $span" }
}
if ($Spans.Count -eq 0) { throw 'At least one span is required.' }
if ($SmokeTest -and $Spans.Count -ne 1) { throw 'SmokeTest requires exactly one span.' }
if ($RepoRoot.Contains("'") -or $OutputRoot.Contains("'")) { throw 'Apostrophes in paths are unsupported; use another directory.' }

function Invoke-Wsl([string[]]$Arguments) {
    & wsl.exe -d $WslDistribution -- @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "WSL command failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

function Convert-ToWslPath([string]$Path) {
    $value = & wsl.exe -d $WslDistribution --exec wslpath -a ($Path.Replace('\', '/'))
    if ($LASTEXITCODE -ne 0 -or -not $value) { throw "Cannot convert to WSL path: $Path" }
    return $value.Trim()
}

function Invoke-Python([string[]]$Arguments) {
    $leaf = Split-Path -Leaf $WindowsPython
    if ($leaf -in @('py','py.exe')) { & $WindowsPython -3 @Arguments }
    else { & $WindowsPython @Arguments }
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

Get-Command wsl.exe -ErrorAction Stop | Out-Null
Get-Command $WindowsPython -ErrorAction Stop | Out-Null
Get-Command $VinaExe -ErrorAction Stop | Out-Null
if (-not $env:ADT_PYTHON) { throw 'Set ADT_PYTHON to MGLTools pythonsh.exe before docking.' }
if (-not $env:ADT_UTILITIES) { throw 'Set ADT_UTILITIES to the MGLTools Utilities24 directory before docking.' }
if (-not (Test-Path -LiteralPath $env:ADT_PYTHON -PathType Leaf)) { throw "ADT_PYTHON not found: $env:ADT_PYTHON" }
if (-not (Test-Path -LiteralPath $env:ADT_UTILITIES -PathType Container)) { throw "ADT_UTILITIES not found: $env:ADT_UTILITIES" }
foreach ($script in @('prepare_receptor4.py', 'prepare_ligand4.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $env:ADT_UTILITIES $script))) { throw "Missing AutoDockTools script: $script" }
}
Invoke-Python @('-c', 'import numpy, yaml, openpyxl')
& $env:ADT_PYTHON -c 'import AutoDockTools, MolKit'
if ($LASTEXITCODE -ne 0) { throw 'AutoDockTools import failed.' }
& $VinaExe --version
if ($LASTEXITCODE -ne 0) { throw 'Vina executable cannot run.' }

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
Invoke-Python @(
    (Join-Path $PSScriptRoot 'capture_runtime.py'), '--label', 'windows_tools',
    '--output', (Join-Path $OutputRoot 'runtime_windows_tools.json'),
    '--vina', $VinaExe, '--adt-python', $env:ADT_PYTHON
)
$WslRepo = Convert-ToWslPath $RepoRoot
$WslOutput = Convert-ToWslPath $OutputRoot
$WslRunner = "$WslRepo/src/run_single_span.sh"

foreach ($span in $Spans) {
    $SpanRoot = Join-Path $OutputRoot "$span"
    $WslSpanRoot = "$WslOutput/$span"
    $WslPrefix = "export RUN_ROOT='$WslOutput'; bash '$WslRunner' --span $span --output-root '$WslSpanRoot' --msa-mode online"
    if ($SmokeTest) { $WslPrefix += ' --smoke-test' }

    if ($CheckOnly) {
        Invoke-Wsl @('bash','-lc',"$WslPrefix --dry-run")
        continue
    }

    Write-Host "[$span A] RFdiffusion, ProteinMPNN, sequence QC, online MSA, Boltz-2 and linker RMSD"
    Invoke-Wsl @('bash','-lc',"$WslPrefix --stage all")

    Write-Host "[$span A] AutoDock Vina"
    $env:VINA_EXE = $VinaExe
    Invoke-Python @(
        (Join-Path $PSScriptRoot 'docking_helper.py'),
        'run-batch',
        '--evaluations-dir', (Join-Path $SpanRoot '09_rmsd_gate_local'),
        '--ligand-pdb', (Join-Path $RepoRoot 'references\prepared\8TNQ_MIQ_experimental.pdb'),
        '--output-root', (Join-Path $SpanRoot '10_docking'),
        '--vina', $VinaExe
    )

    Write-Host "[$span A] Geometry ranker and per-span report"
    Invoke-Wsl @('bash','-lc',"$WslPrefix --stage ranker")
    Invoke-Wsl @('bash','-lc',"$WslPrefix --stage finalize")
    New-Item -ItemType File -Path (Join-Path $SpanRoot 'state\span.complete') -Force | Out-Null
}

if ($CheckOnly) {
    Write-Host 'PREFLIGHT PASS: imports, executables, GPU and references checked; no model inference executed.'
    exit 0
}

Write-Host 'Collecting standardized final tables'
Invoke-Python @(
    (Join-Path $PSScriptRoot 'collect_reproduction_results.py'),
    '--run-root', $OutputRoot,
    '--spans', ($Spans -join ','),
    '--output-dir', (Join-Path $OutputRoot 'final')
)
Write-Host "FULL PIPELINE COMPLETE: $(Join-Path $OutputRoot 'final\results.csv')"
