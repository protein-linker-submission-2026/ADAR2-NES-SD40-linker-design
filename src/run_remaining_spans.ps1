[CmdletBinding()]
param(
    [int[]]$Spans = @(11,12,13,14,15,17,18,19,20),
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$GameRoot = '${PROJECT_ROOT}'
$Project = '${PACKAGE_ROOT}/02_原始记录/方法脚本与公共参考'
$WslProject = '${PACKAGE_ROOT}/02_原始记录/方法脚本与公共参考'
$WslRunner = "$WslProject/src/run_single_span.sh"
$Python3 = '${USER_HOME}\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$Node = '${USER_HOME}\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$BuildDir = '${PROJECT_ROOT}\_V2\scoring_report_build'
$BuilderSource = Join-Path $Project 'tools\build_span_workbook.mjs'
$BuilderRuntime = Join-Path $BuildDir 'build_span_workbook_runtime.mjs'
$Control = Join-Path $GameRoot '_batch_control'
$StatusCsv = Join-Path $GameRoot 'remaining_spans_status.csv'
$Log = Join-Path $Control 'remaining_spans.log'
$Allowed = @(11,12,13,14,15,17,18,19,20)
$VinaExe = if ($env:VINA_EXE) { $env:VINA_EXE } else { 'vina' }

foreach ($span in $Spans) {
    if ($span -notin $Allowed) { throw "只允许11–15、17–20；16 Å受保护。收到：$span" }
}
if (-not (Test-Path -LiteralPath $Python3)) { throw "找不到Windows Python 3：$Python3" }
if (-not (Test-Path -LiteralPath $Node)) { throw "找不到Node.js：$Node" }
if (-not (Get-Command $VinaExe -ErrorAction SilentlyContinue) -and -not (Test-Path -LiteralPath $VinaExe)) {
    throw "找不到 AutoDock Vina。请将 vina 加入 PATH，或设置 VINA_EXE。当前值：$VinaExe"
}
New-Item -ItemType Directory -Path $Control -Force | Out-Null
Copy-Item -LiteralPath $BuilderSource -Destination $BuilderRuntime -Force

function Write-Status([int]$Span,[string]$State,[string]$Stage,[string]$Message) {
    $rows = @()
    if (Test-Path -LiteralPath $StatusCsv) { $rows = @(Import-Csv -LiteralPath $StatusCsv) }
    $rows = @($rows | Where-Object {[int]$_.span_A -ne $Span})
    $rows += [pscustomobject]@{span_A=$Span; state=$State; stage=$Stage; updated=(Get-Date).ToString('s'); message=$Message}
    $rows | Sort-Object {[int]$_.span_A} | Export-Csv -LiteralPath $StatusCsv -NoTypeInformation -Encoding utf8
}

function Invoke-Wsl([string[]]$Arguments) {
    & wsl.exe -d Ubuntu-22.04 -- @Arguments
    if ($LASTEXITCODE -ne 0) { throw "WSL命令失败，退出码 $LASTEXITCODE：$($Arguments -join ' ')" }
}

function Save-16Hash([string]$Target) {
    $protected = '01_input 02_rfdiffusion_raw 03_rfdiffusion_validated 04_logs 06_proteinmpnn 07_sequence_qc 08_msa_online 08_boltz2_local 09_rmsd_gate_local 10_docking'
    $cmd = "cd ${PROJECT_ROOT}/data && find $protected -type f -print0 | sort -z | xargs -0 sha256sum > '$Target'"
    Invoke-Wsl @('bash','-lc',$cmd)
}

function Invoke-16Rescore {
    $root = Join-Path $GameRoot 'data'
    $derived = Join-Path $root '05_reports\vina_rescored_minus6'
    $ranker = Join-Path $root '11_ranker_minus6'
    & $Python3 (Join-Path $Project 'src\rescore_existing_vina.py') --root $root --output-dir $derived
    if ($LASTEXITCODE -ne 0) { throw "16 Å重评分派生结果失败，退出码 $LASTEXITCODE" }
    & $Python3 (Join-Path $Project 'src\span_report.py') prepare-ranker --root $root --docking-dir $derived --ranker-dir $ranker
    if ($LASTEXITCODE -ne 0) { throw "16 Å重评分Ranker候选准备失败，退出码 $LASTEXITCODE" }
    $rankCmd = "cd ${PACKAGE_ROOT}/02_原始记录/方法脚本与公共参考/ranker/sd40_linker_ranker_v0_1 && export PYTHONPATH=${PACKAGE_ROOT}/02_原始记录/方法脚本与公共参考/ranker/sd40_linker_ranker_v0_1/src && /opt/adar2/envs/boltz/bin/python -m sd40_linker_ranker.cli rank --config config.yaml --candidates ${PROJECT_ROOT}/data/11_ranker_minus6/candidates --output ${PROJECT_ROOT}/data/11_ranker_minus6/ranking.csv"
    Invoke-Wsl @('bash','-lc',$rankCmd)
    & $Python3 (Join-Path $Project 'src\span_report.py') finalize --root $root --span 16 --docking-dir $derived --ranker-dir $ranker
    if ($LASTEXITCODE -ne 0) { throw "16 Å重评分报告失败，退出码 $LASTEXITCODE" }
    & $Node $BuilderRuntime span ($root -replace '\\','/') '16'
    if ($LASTEXITCODE -ne 0) { throw "16 Å中文表生成失败，退出码 $LASTEXITCODE" }
    Write-Status 16 'complete' 'rescored' '仅重读已有Vina分数；按−6.0门槛重评分，未重跑结构计算'
}

$beforeWsl='${PROJECT_ROOT}/_batch_control/16A_protected_before.sha256'
if (-not (Test-Path -LiteralPath (Join-Path $Control '16A_protected_before.sha256'))) { Save-16Hash $beforeWsl }

if ($DryRun) {
    foreach ($span in $Spans) {
        Invoke-Wsl @('bash',$WslRunner,'--span',"$span",'--output-root',"${PROJECT_ROOT}/$span",'--msa-mode','online','--dry-run')
    }
    Write-Output "DRY-RUN通过：$($Spans -join ', ')；未启动计算。"
    exit 0
}

"[$(Get-Date -Format s)] 开始剩余span批次：$($Spans -join ',')" | Add-Content -LiteralPath $Log -Encoding utf8
foreach ($span in $Spans) {
    if ($span -eq 17) { Invoke-16Rescore }
    $out = Join-Path $GameRoot "$span"
    $done = Join-Path $out 'state\span.complete'
    if (Test-Path -LiteralPath $done) { Write-Status $span 'complete' 'all' '已验收，跳过'; continue }
    try {
        Write-Status $span 'running' 'RF/MPNN/QC/MSA/Boltz' '本地计算；仅MSA联网'
        "[$(Get-Date -Format s)] span ${span}: WSL stages" | Add-Content -LiteralPath $Log -Encoding utf8
        Invoke-Wsl @('bash',$WslRunner,'--span',"$span",'--output-root',"${PROJECT_ROOT}/$span",'--msa-mode','online','--stage','all')

        Write-Status $span 'running' 'Vina' '本机Windows Vina；每模型动态36-aa SD40盒子'
        & $Python3 (Join-Path $Project 'src\docking_helper.py') run-batch `
            --evaluations-dir (Join-Path $out '09_rmsd_gate_local') `
            --ligand-pdb (Join-Path $Project 'references\prepared\8TNQ_MIQ_experimental.pdb') `
            --output-root (Join-Path $out '10_docking') `
            --vina $VinaExe
        if ($LASTEXITCODE -ne 0) { throw "Vina阶段失败，退出码 $LASTEXITCODE" }

        Write-Status $span 'running' 'Ranker/报告' '方案B评分并生成中文表格'
        Invoke-Wsl @('bash',$WslRunner,'--span',"$span",'--output-root',"${PROJECT_ROOT}/$span",'--msa-mode','online','--stage','ranker')
        Invoke-Wsl @('bash',$WslRunner,'--span',"$span",'--output-root',"${PROJECT_ROOT}/$span",'--msa-mode','online','--stage','finalize')
        & $Node $BuilderRuntime span ($out -replace '\\','/') "$span"
        if ($LASTEXITCODE -ne 0) { throw "Excel报告阶段失败，退出码 $LASTEXITCODE" }

        $summary = Get-Content -LiteralPath (Join-Path $out "05_reports\span${span}A_summary.json") -Raw | ConvertFrom-Json
        if ($summary.rf_backbones -ne 3 -or $summary.mpnn_requested -ne 30) { throw "验收失败：RF=$($summary.rf_backbones)，MPNN请求=$($summary.mpnn_requested)" }
        if (-not (Test-Path -LiteralPath (Join-Path $out "05_reports\ADAR2_SD40_${span}A_中文结果表.xlsx"))) { throw '验收失败：缺少中文Excel' }
        New-Item -ItemType File -Path $done -Force | Out-Null
        Write-Status $span 'complete' 'all' "RF=3; MPNN=30; QC通过=$($summary.qc_pass_design); Boltz模型=$($summary.boltz_models); Vina通过=$($summary.vina_pass_design)"
        "[$(Get-Date -Format s)] span $span complete" | Add-Content -LiteralPath $Log -Encoding utf8
    } catch {
        Write-Status $span 'failed' 'stopped' $_.Exception.Message
        "[$(Get-Date -Format s)] span $span failed: $($_.Exception.Message)" | Add-Content -LiteralPath $Log -Encoding utf8
        throw
    }
}

& $Node $BuilderRuntime cross ($GameRoot -replace '\\','/')
if ($LASTEXITCODE -ne 0) { throw "跨距离Excel生成失败，退出码 $LASTEXITCODE" }
Save-16Hash '${PROJECT_ROOT}/_batch_control/16A_protected_after.sha256'
$before = Get-Content -LiteralPath (Join-Path $Control '16A_protected_before.sha256') -Raw
$after = Get-Content -LiteralPath (Join-Path $Control '16A_protected_after.sha256') -Raw
if ($before -cne $after) { throw '16 Å目录内容发生变化，最终验收失败' }
"[$(Get-Date -Format s)] 全部span完成；16A哈希一致" | Add-Content -LiteralPath $Log -Encoding utf8
