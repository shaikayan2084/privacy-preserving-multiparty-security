# SMPC Shield - Security Verification Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SMPC Shield - Security Verification" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$baseUrl = "http://127.0.0.1:5000"
$allPassed = $true

# Test 1: Home page loads
Write-Host "[TEST 1] Home page loads..." -NoNewline
try {
    $resp = Invoke-WebRequest -Uri "$baseUrl/" -UseBasicParsing
    if ($resp.StatusCode -eq 200) {
        Write-Host " PASS" -ForegroundColor Green
    } else {
        Write-Host " FAIL (Status: $($resp.StatusCode))" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    $allPassed = $false
}

# Test 2: Login page loads
Write-Host "[TEST 2] Login page loads..." -NoNewline
try {
    $resp = Invoke-WebRequest -Uri "$baseUrl/auth/login" -UseBasicParsing
    if ($resp.StatusCode -eq 200) {
        Write-Host " PASS" -ForegroundColor Green
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    $allPassed = $false
}

# Test 3: Signup page loads
Write-Host "[TEST 3] Signup page loads..." -NoNewline
try {
    $resp = Invoke-WebRequest -Uri "$baseUrl/auth/signup" -UseBasicParsing
    if ($resp.StatusCode -eq 200) {
        Write-Host " PASS" -ForegroundColor Green
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    $allPassed = $false
}

# Test 4: 404 page works
Write-Host "[TEST 4] 404 error page works..." -NoNewline
try {
    $resp = Invoke-WebRequest -Uri "$baseUrl/nonexistent-page" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($resp.StatusCode -eq 404) {
        Write-Host " PASS" -ForegroundColor Green
    } else {
        Write-Host " FAIL (Status: $($resp.StatusCode))" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    $allPassed = $false
}

# Test 5: Security headers present
Write-Host "[TEST 5] Security headers present..." -NoNewline
try {
    $resp = Invoke-WebRequest -Uri "$baseUrl/" -UseBasicParsing
    $headers = $resp.Headers
    $requiredHeaders = @(
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
        "Strict-Transport-Security"
    )
    $missingHeaders = @()
    foreach ($h in $requiredHeaders) {
        if (-not $headers.ContainsKey($h)) {
            $missingHeaders += $h
        }
    }
    if ($missingHeaders.Count -eq 0) {
        Write-Host " PASS" -ForegroundColor Green
    } else {
        Write-Host " FAIL (Missing: $($missingHeaders -join ', '))" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    $allPassed = $false
}

# Test 6: CSP meta tag present
Write-Host "[TEST 6] CSP meta tag present..." -NoNewline
try {
    $resp = Invoke-WebRequest -Uri "$baseUrl/" -UseBasicParsing
    if ($resp.Content -match 'Content-Security-Policy') {
        Write-Host " PASS" -ForegroundColor Green
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    $allPassed = $false
}

# Test 7: Session cookie is HttpOnly
Write-Host "[TEST 7] Session cookie is HttpOnly..." -NoNewline
try {
    $resp = Invoke-WebRequest -Uri "$baseUrl/" -UseBasicParsing
    $cookies = $resp.Headers['Set-Cookie']
    if ($cookies -match 'HttpOnly') {
        Write-Host " PASS" -ForegroundColor Green
    } else {
        Write-Host " FAIL" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    $allPassed = $false
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "All security tests PASSED!" -ForegroundColor Green
} else {
    Write-Host "Some tests FAILED. Check above." -ForegroundColor Yellow
}
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Application is running at: $baseUrl" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server when done." -ForegroundColor Cyan
