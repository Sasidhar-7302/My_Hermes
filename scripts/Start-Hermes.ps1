# Hermes Agent - one-click launcher
# Ensures the persistent Telegram gateway and local dashboard are running.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Host.UI.RawUI.WindowTitle = "Hermes Agent"
$env:HERMES_HOME = "C:\Users\yepur\Desktop\My_Projects\Hermes agent"
$hermesExe = Join-Path $env:HERMES_HOME "app\venv\Scripts\hermes.exe"

if (-not (Test-Path -LiteralPath $hermesExe)) {
    throw "Hermes executable not found at: $hermesExe"
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "       Hermes Agent - Starting Services" -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "  [1/3] Ensuring Telegram gateway is running..." -ForegroundColor Yellow
& $hermesExe gateway start

Write-Host "  [2/3] Warming local AI models..." -ForegroundColor Yellow
$warmupScript = Join-Path $env:HERMES_HOME "Warm-Hermes-Models.ps1"
if (Test-Path -LiteralPath $warmupScript) {
    Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$warmupScript`"" `
        -WindowStyle Hidden
}

Write-Host "  [3/4] Ensuring dashboard is running..." -ForegroundColor Yellow
$dashboardListener = Get-NetTCPConnection -State Listen -LocalPort 9119 -ErrorAction SilentlyContinue
if (-not $dashboardListener) {
    Start-Process -FilePath $hermesExe -ArgumentList "dashboard" -WindowStyle Hidden
    Start-Sleep -Seconds 5
    $dashboardListener = Get-NetTCPConnection -State Listen -LocalPort 9119 -ErrorAction SilentlyContinue
}
if (-not $dashboardListener) {
    throw "Hermes dashboard did not start on http://127.0.0.1:9119"
}

Write-Host "  [4/4] Starting Employee Dashboard API (Port 8000)..." -ForegroundColor Yellow
$empListener = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $empListener) {
    Start-Process -FilePath "python" -ArgumentList "-X utf8 local_model_lab\company_dashboard.py" -WindowStyle Hidden
}

Write-Host ""
Write-Host "  Dashboard: http://127.0.0.1:9119" -ForegroundColor Green
Write-Host "  Telegram:  https://t.me/Hermes_persaiassist_bot" -ForegroundColor Green
Write-Host ""
& $hermesExe gateway status
Write-Host "  Dashboard process is listening on port 9119." -ForegroundColor Green
Write-Host ""
Write-Host "  Hermes will continue running in the background." -ForegroundColor DarkGray
