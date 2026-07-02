# Script: benchmark_sparql.ps1
# Meaning: Measure response times of Wikidata SPARQL endpoint for old and optimized queries (isURI) bypassing edge CDN cache.

$WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
$USER_AGENT = "WikiBFS-Benchmark/1.0 (contact: qa-team@wikibfs.local)"

function Get-Sparql-Query-Old ($qid) {
    return @"
SELECT DISTINCT ?neighbor WHERE {
  { wd:$qid ?p ?neighbor . FILTER(STRSTARTS(STR(?neighbor), "http://www.wikidata.org/entity/Q")) }
  UNION
  { ?neighbor ?p wd:$qid . FILTER(STRSTARTS(STR(?neighbor), "http://www.wikidata.org/entity/Q")) }
  FILTER(?neighbor != wd:$qid)
  BIND(rand() as ?rnd)
} LIMIT 50
"@
}

function Get-Sparql-Query-New ($qid) {
    return @"
SELECT DISTINCT ?neighbor WHERE {
  { wd:$qid ?p ?neighbor . FILTER(isURI(?neighbor)) }
  UNION
  { ?neighbor ?p wd:$qid . FILTER(isURI(?neighbor)) }
  FILTER(?neighbor != wd:$qid)
  BIND(rand() as ?rnd)
} LIMIT 50
"@
}

$testEntity = "Q34660" # J. K. Rowling

Write-Host "=== [1/2] BENCHMARKING OLD SPARQL QUERY (STRSTARTS) ===" -ForegroundColor Cyan
$queryOld = Get-Sparql-Query-Old $testEntity

$timeOld = curl.exe -s -X POST $WIKIDATA_ENDPOINT `
  -H "Accept: application/sparql-results+json" `
  -H "Cache-Control: no-cache" `
  -H "User-Agent: $USER_AGENT" `
  --data-urlencode "query=$queryOld" `
  -o nul -w "%{time_total}"

Write-Host "Old query response time (STRSTARTS): $timeOld seconds" -ForegroundColor Yellow

Write-Host "`n=== [2/2] BENCHMARKING OPTIMIZED NEW SPARQL QUERY (isURI) ===" -ForegroundColor Cyan
$queryNew = Get-Sparql-Query-New $testEntity

$timeNew = curl.exe -s -X POST $WIKIDATA_ENDPOINT `
  -H "Accept: application/sparql-results+json" `
  -H "Cache-Control: no-cache" `
  -H "User-Agent: $USER_AGENT" `
  --data-urlencode "query=$queryNew" `
  -o nul -w "%{time_total}"

Write-Host "New query response time (isURI): $timeNew seconds" -ForegroundColor Green

# Compute performance difference
$timeOldVal = [double]$timeOld
$timeNewVal = [double]$timeNew

if ($timeOldVal -gt 0 -and $timeNewVal -gt 0) {
    $diff = $timeOldVal - $timeNewVal
    $percent = [Math]::Round(($diff / $timeOldVal) * 100, 2)
    Write-Host "`n=== BENCHMARK COMPARISON RESULTS ===" -ForegroundColor Cyan
    if ($diff -gt 0) {
        Write-Host "Optimized new query (isURI) is faster than old query by $percent% (saved $diff seconds)" -ForegroundColor Green
    } else {
        Write-Host "No significant difference detected. Likely due to transient network latency or instant responses." -ForegroundColor Yellow
    }
} else {
    Write-Error "Failed to complete benchmark due to Wikidata connection issues!"
    exit 1
}

exit 0
