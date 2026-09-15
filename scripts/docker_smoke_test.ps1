# =====================================================================
# Enterprise Support AI Agent: Docker Release Smoke Test Script
# Non-destructive validation of running containers, endpoints & storage
# =====================================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Enterprise Support AI Agent - Docker Smoke Test      " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Check Docker CLI Availability
Write-Host "`n[1/7] Checking Docker CLI availability..." -ForegroundColor Yellow
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    # Check standard Docker Desktop paths on Windows
    $possiblePaths = @(
        "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin",
        "$env:ProgramFiles\Docker\Docker\resources\bin"
    )
    foreach ($path in $possiblePaths) {
        if (Test-Path "$path\docker.exe") {
            $env:Path = "$path;$env:Path"
            break
        }
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: Docker CLI not found. Ensure Docker Desktop is installed and running."
    exit 1
}

$dockerVer = (docker --version)
Write-Host " [PASS] Docker found: $dockerVer" -ForegroundColor Green

# 2. Check Docker Compose Configuration
Write-Host "`n[2/7] Checking Docker Compose configuration..." -ForegroundColor Yellow
$configCheck = docker compose config --quiet 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "ERROR: docker compose config failed: $configCheck"
    exit 1
}
Write-Host " [PASS] Compose syntax and interpolation valid" -ForegroundColor Green

# 3. Check Container Health Status
Write-Host "`n[3/7] Checking container status and health..." -ForegroundColor Yellow
$services = @("postgres", "backend", "frontend")
$allHealthy = $true

foreach ($svc in $services) {
    $psOut = docker compose ps $svc --format "{{.Name}} | {{.Status}}" 2>$null
    if (-not $psOut) {
        Write-Host " [FAIL] Service '$svc' is not running!" -ForegroundColor Red
        $allHealthy = $false
        continue
    }
    $psText = ($psOut -join " ")
    if ($psText -match "healthy") {
        Write-Host " [PASS] Service '$svc': $psText" -ForegroundColor Green
    } else {
        Write-Host " [WARN] Service '$svc' is running but not yet healthy: $psText" -ForegroundColor Yellow
    }
}

if (-not $allHealthy) {
    Write-Error "One or more required services are not running."
    exit 1
}

# 4. Check Backend Health Endpoint (GET /health)
Write-Host "`n[4/7] Checking backend GET /health..." -ForegroundColor Yellow
try {
    $healthResp = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 10
    if ($healthResp.status -eq "healthy") {
        Write-Host " [PASS] Backend health endpoint OK: status=$($healthResp.status), version=$($healthResp.version)" -ForegroundColor Green
    } else {
        Write-Host " [FAIL] Unexpected health payload: $($healthResp | ConvertTo-Json -Compress)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Error "Failed to connect to backend on http://localhost:8000/health: $_"
    exit 1
}

# 5. Check Frontend HTTP Reachability
Write-Host "`n[5/7] Checking frontend HTTP reachability (port 3000)..." -ForegroundColor Yellow
try {
    $frontendResp = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -UseBasicParsing -TimeoutSec 10
    if ($frontendResp.StatusCode -eq 200) {
        Write-Host " [PASS] Frontend reached: HTTP 200 OK (Content Length: $($frontendResp.RawContentLength) bytes)" -ForegroundColor Green
    } else {
        Write-Host " [FAIL] Frontend returned unexpected status: $($frontendResp.StatusCode)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Error "Failed to reach frontend at http://localhost:3000: $_"
    exit 1
}

# 6. Check Operational REST Endpoints
Write-Host "`n[6/7] Checking operational REST API endpoints..." -ForegroundColor Yellow

# Employee lookup
try {
    $emp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/employees/E1001" -Method Get -TimeoutSec 10
    Write-Host " [PASS] Employee lookup: $($emp.name) ($($emp.employee_id)), Dept: $($emp.department)" -ForegroundColor Green
} catch {
    Write-Host " [FAIL] Employee lookup failed: $_" -ForegroundColor Red
    exit 1
}

# Leave balance lookup
try {
    $leave = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/employees/E1001/leave" -Method Get -TimeoutSec 10
    Write-Host " [PASS] Leave balance lookup: Total remaining=$($leave.total_remaining_days) days" -ForegroundColor Green
} catch {
    Write-Host " [FAIL] Leave balance lookup failed: $_" -ForegroundColor Red
    exit 1
}

# Travel expense lookup
try {
    $travel = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/employees/E1001/travel" -Method Get -TimeoutSec 10
    Write-Host " [PASS] Travel expense lookup: Claims count=$($travel.total_claims), Total=$($travel.total_amount)" -ForegroundColor Green
} catch {
    Write-Host " [FAIL] Travel expense lookup failed: $_" -ForegroundColor Red
    exit 1
}

# 7. Check Storage Persistence & Security Non-Root Users
Write-Host "`n[7/7] Checking non-root users & persistent storage integrity..." -ForegroundColor Yellow

# Non-root user checks
$backendUser = (docker compose exec -T backend id 2>$null) -join " "
$frontendUser = (docker compose exec -T frontend id 2>$null) -join " "

if ($backendUser -match "appuser") {
    Write-Host " [PASS] Backend user: $backendUser" -ForegroundColor Green
} else {
    Write-Host " [WARN] Backend runtime user: $backendUser" -ForegroundColor Yellow
}

if ($frontendUser -match "nextjs") {
    Write-Host " [PASS] Frontend user: $frontendUser" -ForegroundColor Green
} else {
    Write-Host " [WARN] Frontend runtime user: $frontendUser" -ForegroundColor Yellow
}

# Database record count check
$dbCheck = docker compose exec -T postgres psql -U postgres -d enterprise_support -t -A -c "SELECT count(*) FROM employees;" 2>$null
$dbStr = ($dbCheck -join "").Trim()
if ($dbStr -match "^\d+$" -and [int]$dbStr -gt 0) {
    Write-Host " [PASS] PostgreSQL seeded records intact: $dbStr employees" -ForegroundColor Green
} else {
    Write-Host " [FAIL] PostgreSQL employees count check failed (result: '$dbStr')" -ForegroundColor Red
    exit 1
}

# ChromaDB collection chunk count check
$chromaCheck = docker compose exec -T backend python -c "
import chromadb, os
client = chromadb.PersistentClient(path=os.getenv('CHROMA_PATH', '/app/data/chroma'))
c = client.get_collection('company_documents')
print(c.count())
" 2>$null
$chromaStr = ($chromaCheck -join "").Trim()
if ($chromaStr -match "^\d+$" -and [int]$chromaStr -gt 0) {
    Write-Host " [PASS] ChromaDB vector embeddings intact: $chromaStr indexed policy chunks" -ForegroundColor Green
} else {
    Write-Host " [FAIL] ChromaDB chunk count check failed (result: '$chromaStr')" -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "   ALL SMOKE TESTS PASSED - DOCKER STACK IS GREEN!      " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
exit 0
