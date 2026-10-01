$ErrorActionPreference = 'Stop'
$scheduler = '${PACKAGE_ROOT}/02_原始记录/方法脚本与公共参考\src\run_remaining_spans.ps1'
try {
    & $scheduler -Spans @(13,14,15,17,18,19,20)
    Write-Output "RESUME_COMPLETED $(Get-Date -Format o)"
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    Write-Output "RESUME_FAILED $(Get-Date -Format o)"
    exit 1
}
