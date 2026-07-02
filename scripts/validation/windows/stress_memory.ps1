# Script: stress_memory.ps1
# Meaning: Simulate Redis connection drop, automate benchmark traffic, and record metrics (RAM, CPU) into a CSV file to verify LRU Cache limit.

$CSV_FILE = "ram_profile.csv"
$BENCHMARK_URL = "http://localhost:8000/api/search?start=Q5&target=Q42&mode=deep"
$DURATION_SECS = 30
$CONCURRENT_CONN = 50

# 1. Detect environment and check Docker
$dockerAvailable = $false
try {
    docker compose version > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerAvailable = $true
    }
} catch {}

if ($dockerAvailable) {
    Write-Host "Docker Compose is available. Pausing Redis container to simulate connection loss..." -ForegroundColor Yellow
    docker compose pause redis
} else {
    Write-Host "Docker not detected. Assuming Redis is stopped manually or running in background." -ForegroundColor Yellow
}

# 2. Identify Backend Process for RAM Monitoring
$isDockerBackend = $false
$backendContainerId = ""
$localProcess = $null

if ($dockerAvailable) {
    $backendContainerId = (docker compose ps -q backend)
    if ($backendContainerId) {
        $isDockerBackend = $true
        Write-Host "Monitoring Backend Container ID: $backendContainerId" -ForegroundColor Gray
    }
}

if (-not $isDockerBackend) {
    # Find local python process running uvicorn
    $localProcess = Get-Process -Name python | Where-Object { 
        $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*app.main:app*" -or $_.Path -like "*name-related-searching*"
    } | Select-Object -First 1
    
    if ($localProcess) {
        Write-Host "Monitoring Local Python Backend PID: $($localProcess.Id)" -ForegroundColor Gray
    } else {
        Write-Warning "Backend process not found! Make sure backend is running on port 8000 before running stress tests."
    }
}

# 3. Prepare CSV log file
Write-Host "Initializing resource log file: $CSV_FILE" -ForegroundColor Gray
"Timestamp,Source,Memory_Usage,CPU_Percentage" | Out-File -FilePath $CSV_FILE -Encoding utf8

# Resource sampling function
function Get-ResourceSample {
    $ts = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    if ($isDockerBackend) {
        $stats = docker stats $backendContainerId --no-stream --format "{{.MemUsage}},{{.CPUPerc}}"
        if ($stats) {
            $parts = $stats -split ","
            $mem = $parts[0].Trim()
            $cpu = $parts[1].Trim()
            return "$ts,DockerContainer,$mem,$cpu"
        }
    } elseif ($localProcess) {
        try {
            $proc = Get-Process -Id $localProcess.Id -ErrorAction Stop
            $memBytes = $proc.WorkingSet64
            $memMB = [Math]::Round($memBytes / 1MB, 2)
            $cpuTime = $proc.CPU
            return "$ts,LocalProcess,$($memMB)MB,$cpuTime"
        } catch {
            return "$ts,LocalProcess,Stopped,0%"
        }
    }
    return "$ts,Unknown,0,0"
}

# 4. Start background monitoring job (every 2 seconds)
Write-Host "Starting background memory monitoring..." -ForegroundColor Gray
$monitorJob = Start-ThreadJob -ScriptBlock {
    param($csvPath)
    while ($true) {
        $sample = & $using:Get-ResourceSample
        $sample | Out-File -Append -FilePath $csvPath -Encoding utf8
        Start-Sleep -Seconds 2
    }
} -ArgumentList $CSV_FILE

# 5. Run stress test via autocannon
Write-Host "=== STARTING STRESS TEST (autocannon) ===" -ForegroundColor Cyan
Write-Host "Endpoint: $BENCHMARK_URL" -ForegroundColor Gray
Write-Host "Duration: $DURATION_SECS seconds | Concurrent Connections: $CONCURRENT_CONN" -ForegroundColor Gray

npx autocannon -c $CONCURRENT_CONN -d $DURATION_SECS -m GET $BENCHMARK_URL

# 6. Cleanup and terminate
Write-Host "Stopping background monitoring job..." -ForegroundColor Gray
$monitorJob | Stop-Job
$monitorJob | Remove-Job

if ($dockerAvailable) {
    Write-Host "Resuming Redis container..." -ForegroundColor Yellow
    docker compose unpause redis
}

# Print the last few lines of the resource log
Write-Host "`n=== RESOURCE LOG RECAP ($CSV_FILE) ===" -ForegroundColor Cyan
if (Test-Path $CSV_FILE) {
    Get-Content $CSV_FILE | Select-Object -Last 10
}

Write-Host "`nOOM Stress Test completed!" -ForegroundColor Green
exit 0
