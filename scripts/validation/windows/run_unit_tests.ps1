# Script: run_unit_tests.ps1
# Meaning: Run pytest suite with fail-fast options and durations profiling.

Write-Host "=== LAUNCHING AUTOMATED UNIT TESTS (pytest) ===" -ForegroundColor Cyan

$pytestPath = ".\venv\Scripts\pytest.exe"
if (-Not (Test-Path $pytestPath)) {
    Write-Host "pytest not found in venv, installing..." -ForegroundColor Yellow
    .\venv\Scripts\pip.exe install pytest pytest-asyncio pytest-cov sse-starlette httpx
}

$currentDir = Get-Location
try {
    # Enter the backend directory containing pytest configurations
    Set-Location src/backend
    
    # Run pytest with:
    # -v: verbose execution
    # -x: exit first failure (Fail-Fast)
    # --tb=short: short traceback logs
    # --durations=5: print 5 slowest test cases
    Write-Host "Executing command: pytest -v -x --tb=short --durations=5" -ForegroundColor Gray
    
    $env:PYTHONPATH = "."
    
    if (Test-Path "..\..\venv\Scripts\pytest.exe") {
        & "..\..\venv\Scripts\pytest.exe" -v -x --tb=short --durations=5
    } else {
        pytest -v -x --tb=short --durations=5
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Unit tests failed!"
        exit 1
    }
    
    Write-Host "`n=== AUTOMATED TESTS PASSED (FAIL-FAST COMPLETE) ===" -ForegroundColor Green
} finally {
    $env:PYTHONPATH = ""
    Set-Location $currentDir
}

exit 0
