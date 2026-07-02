# Script: detect_sse_leaks.ps1
# Meaning: Check thread leaks and outbound connection leaks (port 443 to Wikidata) on backend after clients abruptly drop SSE connections.

$STREAM_URL = "http://localhost:8000/api/search/stream?start=Q5&target=Q42&mode=deep"
$CLIENTS_COUNT = 5

# 1. Detect Python Backend Process
$backendProc = Get-Process -Name python | Where-Object { 
    $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*app.main:app*" -or $_.Path -like "*name-related-searching*"
} | Select-Object -First 1

if (-not $backendProc) {
    Write-Error "Backend Python/Uvicorn process not found! Start backend on port 8000 first."
    exit 1
}

$backendPid = $backendProc.Id
Write-Host "Detected Backend Python PID: $backendPid" -ForegroundColor Gray

# Retrieve threads and outbound connections metrics
function Get-SystemMetrics {
    $proc = Get-Process -Id $backendPid -ErrorAction SilentlyContinue
    $threadCount = 0
    if ($proc) {
        $threadCount = $proc.Threads.Count
    }
    
    $outboundConns = Get-NetTCPConnection -RemotePort 443 -ErrorAction SilentlyContinue | Where-Object { 
        $_.OwningProcess -eq $backendPid -and $_.State -eq "Established"
    }
    $outboundCount = ($outboundConns | Measure-Object).Count
    
    return [PSCustomObject]@{
        Threads     = $threadCount
        Connections = $outboundCount
    }
}

# --- STEP 1: BASELINE MEASUREMENT ---
Write-Host "`n=== STEP 1: BASELINE MEASUREMENT ===" -ForegroundColor Cyan
$baseline = Get-SystemMetrics
Write-Host "Baseline Threads: $($baseline.Threads)" -ForegroundColor Gray
Write-Host "Baseline Outbound HTTPS (443): $($baseline.Connections)" -ForegroundColor Gray

# --- STEP 2: LAUNCH CONCURRENT SSE TRAFFIC & ABORT ---
Write-Host "`n=== STEP 2: LAUNCH CONCURRENT SSE TRAFFIC & ABORT ===" -ForegroundColor Cyan
Write-Host "Starting $CLIENTS_COUNT concurrent SSE connections..." -ForegroundColor Gray

$jobs = @()
for ($i = 1; $i -le $CLIENTS_COUNT; $i++) {
    $job = Start-Job -ScriptBlock {
        param($url)
        curl.exe -s -N -H "Accept: text/event-stream" $url > $null
    } -ArgumentList $STREAM_URL
    $jobs += $job
}

Write-Host "Holding connections for 2 seconds to trigger BFS thread pools..." -ForegroundColor Gray
Start-Sleep -Seconds 2

$activeMetrics = Get-SystemMetrics
Write-Host "Active Threads: $($activeMetrics.Threads)" -ForegroundColor Yellow
Write-Host "Active Outbound HTTPS (443): $($activeMetrics.Connections)" -ForegroundColor Yellow

Write-Host "Forcibly terminating all $CLIENTS_COUNT connections (Client Abort)..." -ForegroundColor Red
foreach ($job in $jobs) {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -ErrorAction SilentlyContinue
}

$postAbortMetrics = Get-SystemMetrics
Write-Host "Post-Abort Threads: $($postAbortMetrics.Threads)" -ForegroundColor Gray
Write-Host "Post-Abort Outbound HTTPS (443): $($postAbortMetrics.Connections)" -ForegroundColor Gray

# --- STEP 3: COOLDOWN & LEAK DETECTION ---
$cooldownSecs = 10
Write-Host "`n=== STEP 3: COOLDOWN & LEAK DETECTION ===" -ForegroundColor Cyan
Write-Host "Waiting $cooldownSecs seconds for worker threads to resolve and close sockets..." -ForegroundColor Gray
Start-Sleep -Seconds $cooldownSecs

$cooldownMetrics = Get-SystemMetrics
Write-Host "Cooldown Threads: $($cooldownMetrics.Threads)" -ForegroundColor Green
Write-Host "Cooldown Outbound HTTPS (443): $($cooldownMetrics.Connections)" -ForegroundColor Green

# --- REPORT ---
Write-Host "`n=== RESOURCE LEAK REPORT ===" -ForegroundColor Cyan
$threadLeak = $cooldownMetrics.Threads - $baseline.Threads
$connLeak = $cooldownMetrics.Connections - $baseline.Connections

$leakDetected = $false

if ($threadLeak -gt 2) {
    Write-Warning "WARNING: Thread Leak detected! System did not return to baseline thread count (Leak: $threadLeak threads)."
    $leakDetected = $true
} else {
    Write-Host "Thread GC / Worker thread termination: PASS" -ForegroundColor Green
}

if ($connLeak -gt 1) {
    Write-Warning "WARNING: Outbound Connection Leak detected! Wikidata connections remained hanging (Leak: $connLeak sockets)."
    $leakDetected = $true
} else {
    Write-Host "Outbound Socket Cleanup (Port 443): PASS" -ForegroundColor Green
}

if ($leakDetected) {
    Write-Host "`nResult: System validation failed due to SSE thread/socket leaks!" -ForegroundColor Red
    exit 1
} else {
    Write-Host "`nResult: No leaks detected. SSE connection management is robust." -ForegroundColor Green
    exit 0
}
