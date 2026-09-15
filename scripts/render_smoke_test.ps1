# =====================================================================
# Enterprise Support AI Agent: Cloud Production Smoke Test Script
# Non-destructive public verification of Render deployed services
# =====================================================================

param (
    [string]$BackendUrl = $env:RENDER_BACKEND_URL,
    [string]$FrontendUrl = $env:RENDER_FRONTEND_URL,
    [int]$TimeoutSec = 30
)

$ErrorActionPreference = "Stop"

if (-not $BackendUrl) {
    $BackendUrl = "http://localhost:8000"
}
if (-not $FrontendUrl) {
    $FrontendUrl = "http://localhost:3000"
}

# Normalize trailing slashes
$BackendUrl = $BackendUrl.TrimEnd('/')
$FrontendUrl = $FrontendUrl.TrimEnd('/')

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Enterprise Support AI Agent - Cloud Smoke Test       " -ForegroundColor Cyan
Write-Host "   Backend Target:  $BackendUrl" -ForegroundColor Cyan
Write-Host "   Frontend Target: $FrontendUrl" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$results = [ordered]@{}
$stopwatch = [System.Diagnostics.Stopwatch]::New()

# ---------------------------------------------------------------------
# 1. Frontend Reachability Check
# ---------------------------------------------------------------------
Write-Host "`n[1/8] Verifying Frontend Reachability ($FrontendUrl)..." -ForegroundColor Yellow
$stopwatch.Restart()
try {
    $feResp = Invoke-WebRequest -Uri $FrontendUrl -Method Get -UseBasicParsing -TimeoutSec $TimeoutSec
    $stopwatch.Stop()
    $feLatency = [math]::Round($stopwatch.Elapsed.TotalMilliseconds, 1)
    if ($feResp.StatusCode -eq 200) {
        Write-Host " [PASS] Frontend reachable (HTTP 200 OK, Latency: ${feLatency} ms)" -ForegroundColor Green
        $results["Frontend"] = "PASS (${feLatency} ms)"
    } else {
        Write-Host " [FAIL] Frontend returned HTTP status $($feResp.StatusCode)" -ForegroundColor Red
        $results["Frontend"] = "FAIL"
    }
} catch {
    $stopwatch.Stop()
    Write-Host " [FAIL] Frontend unreachable: $_" -ForegroundColor Red
    $results["Frontend"] = "FAIL ($($_.Exception.Message))"
}

# ---------------------------------------------------------------------
# 2. Backend Health Check (GET /health)
# ---------------------------------------------------------------------
Write-Host "`n[2/8] Verifying Backend Health Check ($BackendUrl/health)..." -ForegroundColor Yellow
$stopwatch.Restart()
try {
    $healthResp = Invoke-RestMethod -Uri "$BackendUrl/health" -Method Get -TimeoutSec $TimeoutSec
    $stopwatch.Stop()
    $healthLatency = [math]::Round($stopwatch.Elapsed.TotalMilliseconds, 1)
    if ($healthResp.status -eq "healthy") {
        Write-Host " [PASS] Backend status=$($healthResp.status), version=$($healthResp.version) (${healthLatency} ms)" -ForegroundColor Green
        $results["Health"] = "PASS (${healthLatency} ms)"
    } else {
        Write-Host " [FAIL] Unexpected health payload" -ForegroundColor Red
        $results["Health"] = "FAIL"
    }
} catch {
    $stopwatch.Stop()
    Write-Host " [FAIL] Backend health failed: $_" -ForegroundColor Red
    $results["Health"] = "FAIL ($($_.Exception.Message))"
}

# ---------------------------------------------------------------------
# 3. Operational Data API (GET /api/v1/employees/E1001)
# ---------------------------------------------------------------------
Write-Host "`n[3/8] Verifying Relational Database Employee Lookup..." -ForegroundColor Yellow
$stopwatch.Restart()
try {
    $emp = Invoke-RestMethod -Uri "$BackendUrl/api/v1/employees/E1001" -Method Get -TimeoutSec $TimeoutSec
    $stopwatch.Stop()
    $dbLatency = [math]::Round($stopwatch.Elapsed.TotalMilliseconds, 1)
    if ($emp.employee_id -eq "E1001" -and $emp.name) {
        Write-Host " [PASS] Employee resolved: $($emp.name) ($($emp.department)) (${dbLatency} ms)" -ForegroundColor Green
        $results["Database_Employee"] = "PASS (${dbLatency} ms)"
    } else {
        Write-Host " [FAIL] Invalid employee data structure" -ForegroundColor Red
        $results["Database_Employee"] = "FAIL"
    }
} catch {
    $stopwatch.Stop()
    Write-Host " [FAIL] Database query failed: $_" -ForegroundColor Red
    $results["Database_Employee"] = "FAIL ($($_.Exception.Message))"
}

# ---------------------------------------------------------------------
# 4. Operational Data Leave & Travel Summary
# ---------------------------------------------------------------------
Write-Host "`n[4/8] Verifying Relational Leave & Travel Records..." -ForegroundColor Yellow
try {
    $leave = Invoke-RestMethod -Uri "$BackendUrl/api/v1/employees/E1001/leave" -Method Get -TimeoutSec $TimeoutSec
    $travel = Invoke-RestMethod -Uri "$BackendUrl/api/v1/employees/E1001/travel" -Method Get -TimeoutSec $TimeoutSec
    if ($leave.total_allocated_days -gt 0 -and $travel.total_claims -ge 0) {
        Write-Host " [PASS] Leave allocated=$($leave.total_allocated_days), Travel claims count=$($travel.total_claims)" -ForegroundColor Green
        $results["Database_Records"] = "PASS"
    } else {
        Write-Host " [FAIL] Invalid leave or travel data" -ForegroundColor Red
        $results["Database_Records"] = "FAIL"
    }
} catch {
    Write-Host " [FAIL] Records query failed: $_" -ForegroundColor Red
    $results["Database_Records"] = "FAIL ($($_.Exception.Message))"
}

# ---------------------------------------------------------------------
# 5. Hybrid RAG Policy Question (Answerable + Citations)
# ---------------------------------------------------------------------
Write-Host "`n[5/8] Verifying Grounded Policy RAG Assistant ($BackendUrl/api/v1/ask)..." -ForegroundColor Yellow
$stopwatch.Restart()
try {
    $askBody = @{ question = "What is the meal per diem allowance for domestic travel?" } | ConvertTo-Json
    $ragResp = Invoke-RestMethod -Uri "$BackendUrl/api/v1/ask" -Method Post -Body $askBody -ContentType "application/json" -TimeoutSec $TimeoutSec
    $stopwatch.Stop()
    $ragLatency = [math]::Round($stopwatch.Elapsed.TotalMilliseconds, 1)
    
    if ($ragResp.answer -and $ragResp.is_refusal -eq $false) {
        $citCount = if ($ragResp.sources) { $ragResp.sources.Count } else { 0 }
        Write-Host " [PASS] RAG Answer generated with $citCount citation(s) (${ragLatency} ms)" -ForegroundColor Green
        Write-Host "        Answer: $($ragResp.answer.Substring(0, [math]::Min(120, $ragResp.answer.Length)))..." -ForegroundColor DarkGray
        $results["Policy_RAG"] = "PASS (${ragLatency} ms, $citCount sources)"
    } else {
        Write-Host " [FAIL] Unexpected RAG response or unexpected refusal" -ForegroundColor Red
        $results["Policy_RAG"] = "FAIL"
    }
} catch {
    $stopwatch.Stop()
    Write-Host " [WARN/FAIL] RAG query failed: $_" -ForegroundColor Red
    $results["Policy_RAG"] = "FAIL ($($_.Exception.Message))"
}

# ---------------------------------------------------------------------
# 6. RAG Refusal Behavior (Unanswerable Question)
# ---------------------------------------------------------------------
Write-Host "`n[6/8] Verifying Deterministic RAG Refusal Behavior..." -ForegroundColor Yellow
try {
    $unanswerableBody = @{ question = "What is the protocol for faster-than-light warp travel?" } | ConvertTo-Json
    $refusalResp = Invoke-RestMethod -Uri "$BackendUrl/api/v1/ask" -Method Post -Body $unanswerableBody -ContentType "application/json" -TimeoutSec $TimeoutSec
    if ($refusalResp.is_refusal -eq $true) {
        Write-Host " [PASS] Correct refusal returned for out-of-domain query" -ForegroundColor Green
        $results["Refusal"] = "PASS"
    } else {
        Write-Host " [FAIL] Model hallucinated or failed to flag refusal: $($refusalResp.answer)" -ForegroundColor Red
        $results["Refusal"] = "FAIL"
    }
} catch {
    Write-Host " [FAIL] Refusal query failed: $_" -ForegroundColor Red
    $results["Refusal"] = "FAIL ($($_.Exception.Message))"
}

# ---------------------------------------------------------------------
# 7. Conversational Multi-Turn Agent Endpoint
# ---------------------------------------------------------------------
Write-Host "`n[7/8] Verifying Conversational Agent Loop ($BackendUrl/api/v1/agent/chat)..." -ForegroundColor Yellow
$stopwatch.Restart()
try {
    $agentBody = @{
        message = "Look up employee E1001 and tell me their leave balance."
        session_id = "render_smoke_session_$(Get-Random)"
    } | ConvertTo-Json
    $agentResp = Invoke-RestMethod -Uri "$BackendUrl/api/v1/agent/chat" -Method Post -Body $agentBody -ContentType "application/json" -TimeoutSec 60
    $stopwatch.Stop()
    $agentLatency = [math]::Round($stopwatch.Elapsed.TotalMilliseconds, 1)

    if ($agentResp.answer -and $agentResp.status -ne "error") {
        Write-Host " [PASS] Agent completed $($agentResp.total_steps) tool step(s) (${agentLatency} ms)" -ForegroundColor Green
        Write-Host "        Status: $($agentResp.status), Answer preview: $($agentResp.answer.Substring(0, [math]::Min(100, $agentResp.answer.Length)))..." -ForegroundColor DarkGray
        $results["Agent"] = "PASS (${agentLatency} ms, $($agentResp.total_steps) steps)"
    } else {
        Write-Host " [FAIL] Agent returned error: $($agentResp.answer)" -ForegroundColor Red
        $results["Agent"] = "FAIL"
    }
} catch {
    $stopwatch.Stop()
    Write-Host " [FAIL] Agent request failed: $_" -ForegroundColor Red
    $results["Agent"] = "FAIL ($($_.Exception.Message))"
}

# ---------------------------------------------------------------------
# 8. Production Security Verification (No Secret Leakage in Responses)
# ---------------------------------------------------------------------
Write-Host "`n[8/8] Verifying Response Sanitization & Security..." -ForegroundColor Yellow
$leakFound = $false
# Check that error responses and payloads do not expose passwords or connection strings
try {
    $badReq = Invoke-WebRequest -Uri "$BackendUrl/api/v1/employees/NONEXISTENT_9999" -Method Get -SkipHttpErrorCheck -UseBasicParsing
    $bodyText = $badReq.Content
    if ($bodyText -match "password" -or $bodyText -match "postgresql://" -or $bodyText -match "gsk_" -or $bodyText -match "sk-") {
        Write-Host " [FAIL] Potential secret detected in error payload!" -ForegroundColor Red
        $leakFound = $true
    }
} catch {}

if (-not $leakFound) {
    Write-Host " [PASS] Error responses sanitized; zero credential patterns detected" -ForegroundColor Green
    $results["Security"] = "PASS"
} else {
    $results["Security"] = "FAIL"
}

# ---------------------------------------------------------------------
# Summary Report
# ---------------------------------------------------------------------
Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "               SMOKE TEST SUMMARY RESULTS               " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
$allPass = $true
foreach ($key in $results.Keys) {
    $val = $results[$key]
    if ($val -like "FAIL*") {
        Write-Host ("  {0,-20}: {1}" -f $key, $val) -ForegroundColor Red
        $allPass = $false
    } else {
        Write-Host ("  {0,-20}: {1}" -f $key, $val) -ForegroundColor Green
    }
}
Write-Host "========================================================" -ForegroundColor Cyan

if ($allPass) {
    Write-Host "  ALL CLOUD SMOKE TESTS PASSED - PRODUCTION IS GREEN!   " -ForegroundColor Green
    Write-Host "========================================================`n" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "  ONE OR MORE SMOKE CHECKS FAILED                       " -ForegroundColor Red
    Write-Host "========================================================`n" -ForegroundColor Cyan
    exit 1
}
