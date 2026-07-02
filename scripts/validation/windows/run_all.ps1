# Script: run_all.ps1
# Meaning: Master orchestrator script to sequentially run syntax, unit tests, SPARQL performance, SSE leaks, and memory stress tests.

Clear-Host
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   STARTING WIKIBFS SYSTEM VALIDATION RUNNER            " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Run-SubScript ($scriptName) {
    Write-Host "`n>>> RUNNING: $scriptName..." -ForegroundColor Green
    $path = Join-Path $scriptDir $scriptName
    & $path
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Subscript $scriptName failed! Aborting entire validation run."
        exit 1
    }
}

# Run tests in logical order (fail early)
Run-SubScript "check_syntax.ps1"
Run-SubScript "run_unit_tests.ps1"
Run-SubScript "benchmark_sparql.ps1"
Run-SubScript "detect_sse_leaks.ps1"
Run-SubScript "stress_memory.ps1"

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "   ALL SYSTEM VALIDATIONS COMPLETED SUCCESSFULLY!       " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
exit 0
