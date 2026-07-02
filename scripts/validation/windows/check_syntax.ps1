# Script: check_syntax.ps1
# Meaning: Check Python syntax compilation, run Ruff for backend code quality, and ESLint for frontend.

Write-Host "=== [1/3] COMPILING PYTHON BACKEND (compileall) ===" -ForegroundColor Cyan
python -m compileall -q -f src/backend/app/
if ($LASTEXITCODE -ne 0) {
    Write-Error "Critical syntax error detected in Python backend!"
    exit 1
}
Write-Host "Compileall: OK." -ForegroundColor Green

Write-Host "=== [2/3] RUNNING RUFF CODE QUALITY GATE ===" -ForegroundColor Cyan
$ruffPath = ".\venv\Scripts\ruff.exe"
if (-Not (Test-Path $ruffPath)) {
    Write-Host "Ruff not found in venv, installing..." -ForegroundColor Yellow
    .\venv\Scripts\pip.exe install ruff
}

if (Test-Path $ruffPath) {
    Write-Host "Running ruff check & auto-fix..." -ForegroundColor Gray
    & $ruffPath check src/backend/app --show-fixes --fix
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Ruff found some warnings/errors that could not be auto-fixed!"
    } else {
        Write-Host "Ruff: OK." -ForegroundColor Green
    }
} else {
    Write-Error "Could not start Ruff linter!"
    exit 1
}

Write-Host "=== [3/3] RUNNING FRONTEND LINTER (ESLint) ===" -ForegroundColor Cyan
$currentDir = Get-Location
try {
    Set-Location src/frontend
    if (-Not (Test-Path "node_modules")) {
        Write-Host "node_modules not found, running npm install..." -ForegroundColor Yellow
        npm install
    }
    Write-Host "Running npm run lint..." -ForegroundColor Gray
    npm run lint
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Frontend Lint failed!"
        exit 1
    }
    Write-Host "Frontend Lint: OK." -ForegroundColor Green
} finally {
    Set-Location $currentDir
}

Write-Host "=== SYNTAX CHECK COMPLETED: SUCCESS ===" -ForegroundColor Green
exit 0
