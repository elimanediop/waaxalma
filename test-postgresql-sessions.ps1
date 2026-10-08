$ErrorActionPreference = "Stop"

$baseUrl = "http://localhost:8000"
$clientA = "waaxalma-test-client-a"
$clientB = "waaxalma-test-client-b"
$headersA = @{ "X-Client-Id" = $clientA }
$headersB = @{ "X-Client-Id" = $clientB }

# 1. CREATE
$body = @{ agent_type = "interpreter"; source_language = "auto"; target_language = "French"; execution_mode = "standard" } | ConvertTo-Json
$created = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/sessions" -Headers $headersA -ContentType "application/json" -Body $body
$sessionId = $created.session_id
if (-not $sessionId) { throw "Session creation failed" }
Write-Host "CREATE OK: $sessionId"

# 2. READ
$session = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/sessions/$sessionId" -Headers $headersA
if ($session.owner_id -ne $clientA) { throw "Unexpected session owner" }
Write-Host "READ OK"

# 3. UPDATE
$update = @{ target_language = "English" } | ConvertTo-Json
$updated = Invoke-RestMethod -Method Patch -Uri "$baseUrl/api/sessions/$sessionId" -Headers $headersA -ContentType "application/json" -Body $update
if ($updated.target_language -ne "English") { throw "Update failed" }
Write-Host "UPDATE OK"

# 4. ISOLATION
try {
    $null = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/sessions/$sessionId" -Headers $headersB -ErrorAction Stop
    throw "SECURITY FAILURE: Client B accessed Client A session"
}
catch {
    if ($_.Exception.Message -like "SECURITY FAILURE:*") { throw }
    if (-not $_.Exception.Response) { throw }
    $status = [int]$_.Exception.Response.StatusCode
    if ($status -notin @(403, 404)) { throw "Unexpected isolation status: $status" }
    Write-Host "ISOLATION OK: HTTP $status"
}

# 5. CLOSE
$closed = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/sessions/$sessionId/close" -Headers $headersA
if ($closed.status -ne "closed") { throw "Session closure failed" }
Write-Host "CLOSE OK"

# 6. RESTART BACKEND
docker compose -f compose.yaml -f compose.postgres.yaml restart backend
if ($LASTEXITCODE -ne 0) { throw "Backend restart failed" }

# 7. WAIT FOR READINESS
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    try {
        $health = Invoke-RestMethod -Uri "$baseUrl/health/ready"
        if ($health.status -eq "ready") { $ready = $true; break }
    }
    catch {}
}
if (-not $ready) { throw "Backend did not become ready after restart" }
Write-Host "BACKEND READY"

# 8. PERSISTENCE
$persisted = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/sessions/$sessionId" -Headers $headersA
if ($persisted.status -ne "closed" -or $persisted.target_language -ne "English") { throw "Persistence verification failed" }
Write-Host "PERSISTENCE OK"
Write-Host "ALL POSTGRESQL SESSION TESTS PASSED" -ForegroundColor Green
