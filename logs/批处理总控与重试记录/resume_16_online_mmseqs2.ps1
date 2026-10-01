[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$GameRoot = '${PROJECT_ROOT}'
$OutputRoot = Join-Path $GameRoot '16'
$Project = Join-Path $GameRoot '_V2\ADAR2_SD40_linker_pipeline_V2'
$WslRunner = '${PACKAGE_ROOT}/02_原始记录/方法脚本与公共参考/src/run_single_span.sh'
$Python3 = '${USER_HOME}\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$Node = '${USER_HOME}\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$BuilderSource = Join-Path $Project 'tools\build_span_workbook.mjs'
$BuilderRuntime = Join-Path $GameRoot '_V2\scoring_report_build\build_span_workbook_runtime.mjs'
$StatusCsv = Join-Path $GameRoot 'remaining_spans_status.csv'
$RunLog = Join-Path $GameRoot '_batch_control\remaining_spans.log'
$Done = Join-Path $OutputRoot 'state\span.complete'

function Write-Status([string]$State, [string]$Stage, [string]$Message) {
    $rows = @()
    if (Test-Path -LiteralPath $StatusCsv) { $rows = @(Import-Csv -LiteralPath $StatusCsv) }
    $rows = @($rows | Where-Object { [int]$_.span_A -ne 16 })
    $rows += [pscustomobject]@{
        span_A = 16
        state = $State
        stage = $Stage
        updated = (Get-Date).ToString('s')
        message = $Message
    }
    $rows | Sort-Object { [int]$_.span_A } | Export-Csv -LiteralPath $StatusCsv -NoTypeInformation -Encoding utf8
}

function Invoke-Wsl([string[]]$Arguments) {
    & wsl.exe -d Ubuntu-22.04 -- @Arguments
    if ($LASTEXITCODE -ne 0) { throw "WSL命令失败，退出码 $LASTEXITCODE：$($Arguments -join ' ')" }
}

function Assert-Historical16Unchanged {
    $before = Join-Path $GameRoot '_batch_control\16A_protected_before.sha256'
    $current = Join-Path $GameRoot '_batch_control\16A_historical_after_online_msa.sha256'
    $command = "cd ${PROJECT_ROOT}/data && find 01_input 02_rfdiffusion_raw 03_rfdiffusion_validated 04_logs 06_proteinmpnn 07_sequence_qc 08_msa_online 08_boltz2_local 09_rmsd_gate_local 10_docking -type f -print0 2>/dev/null | sort -z | xargs -0 sha256sum > ${PROJECT_ROOT}/_batch_control/16A_historical_after_online_msa.sha256"
    Invoke-Wsl @('bash', '-lc', $command)
    if ((Get-Content -LiteralPath $before -Raw) -cne (Get-Content -LiteralPath $current -Raw)) {
        throw '历史16 Å目录哈希发生变化'
    }
}

try {
    if (Test-Path -LiteralPath $Done) {
        Write-Output "SPAN16_ONLINE_MSA_ALREADY_COMPLETE $(Get-Date -Format o)"
        exit 0
    }

    New-Item -ItemType Directory -Path (Join-Path $OutputRoot 'state') -Force | Out-Null
    Copy-Item -LiteralPath $BuilderSource -Destination $BuilderRuntime -Force
    Write-Status 'running' '在线MMseqs2 MSA/Boltz' '复用历史RF、MPNN和QC；在线重做MSA并在本机运行Boltz'
    "[$(Get-Date -Format s)] span 16 online MMseqs2 MSA + Boltz started" | Add-Content -LiteralPath $RunLog -Encoding utf8

    Invoke-Wsl @('bash', $WslRunner, '--span', '16', '--output-root', '${PACKAGE_ROOT}/02_原始记录/11-20A_在线MSA批次/16A', '--msa-mode', 'online', '--stage', 'boltz')

    Write-Status 'running' 'Vina' '在线MSA/Boltz完成；本机Windows Vina'
    & $Python3 (Join-Path $Project 'src\docking_helper.py') run-batch `
        --evaluations-dir (Join-Path $OutputRoot '09_rmsd_gate_local') `
        --ligand-pdb (Join-Path $Project 'references\prepared\8TNQ_MIQ_experimental.pdb') `
        --output-root (Join-Path $OutputRoot '10_docking') `
        --vina $(if ($env:VINA_EXE) { $env:VINA_EXE } else { 'vina' })
    if ($LASTEXITCODE -ne 0) { throw "Vina阶段失败，退出码 $LASTEXITCODE" }

    Write-Status 'running' 'Ranker/报告/总表' '方案B评分并生成16 Å在线MSA报告与11–20 Å总表'
    Invoke-Wsl @('bash', $WslRunner, '--span', '16', '--output-root', '${PACKAGE_ROOT}/02_原始记录/11-20A_在线MSA批次/16A', '--msa-mode', 'online', '--stage', 'ranker')
    Invoke-Wsl @('bash', $WslRunner, '--span', '16', '--output-root', '${PACKAGE_ROOT}/02_原始记录/11-20A_在线MSA批次/16A', '--msa-mode', 'online', '--stage', 'finalize')
    & $Node $BuilderRuntime span ($OutputRoot -replace '\\', '/') '16'
    if ($LASTEXITCODE -ne 0) { throw "16 Å Excel生成失败，退出码 $LASTEXITCODE" }
    & $Node $BuilderRuntime cross ($GameRoot -replace '\\', '/')
    if ($LASTEXITCODE -ne 0) { throw "跨距离总表生成失败，退出码 $LASTEXITCODE" }

    $summaryPath = Join-Path $OutputRoot '05_reports\span16A_summary.json'
    $summary = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
    if ($summary.rf_backbones -ne 3 -or $summary.mpnn_requested -ne 30 -or $summary.boltz_models -ne 60) {
        throw "验收失败：RF=$($summary.rf_backbones)，MPNN=$($summary.mpnn_requested)，Boltz=$($summary.boltz_models)"
    }
    Assert-Historical16Unchanged
    New-Item -ItemType File -Path $Done -Force | Out-Null
    Write-Status 'complete' 'online-MMseqs2-all' "在线MSA重算完成；RF=3; MPNN=30; QC通过=$($summary.qc_pass_design); Boltz模型=60; Vina通过=$($summary.vina_pass_design)"
    "[$(Get-Date -Format s)] span 16 online MMseqs2 complete; historical hashes unchanged; cross table rebuilt" | Add-Content -LiteralPath $RunLog -Encoding utf8
    Write-Output "SPAN16_ONLINE_MSA_COMPLETED $(Get-Date -Format o)"
} catch {
    Write-Status 'failed' 'online-MMseqs2-stopped' $_.Exception.Message
    "[$(Get-Date -Format s)] span 16 online MMseqs2 failed: $($_.Exception.Message)" | Add-Content -LiteralPath $RunLog -Encoding utf8
    Write-Error $_ -ErrorAction Continue
    Write-Output "SPAN16_ONLINE_MSA_FAILED $(Get-Date -Format o)"
    exit 1
}
