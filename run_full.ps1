[CmdletBinding()]
param(
    [int[]]$Spans = (11..20),
    [string]$OutputRoot,
    [string]$WslDistribution = 'Ubuntu-22.04',
    [string]$WindowsPython = 'py',
    [string]$VinaExe = 'vina',
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$forward = @{
    Spans = $Spans
    WslDistribution = $WslDistribution
    WindowsPython = $WindowsPython
    VinaExe = $VinaExe
    CheckOnly = $CheckOnly
}
if ($OutputRoot) { $forward.OutputRoot = $OutputRoot }
& (Join-Path $PSScriptRoot 'src\run_full_pipeline.ps1') @forward
exit $LASTEXITCODE
