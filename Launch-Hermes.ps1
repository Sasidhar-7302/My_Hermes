# Hermes Agent - Universal One-Click Launcher (Windows)
# Launches:
#   1. Persistent Telegram Gateway (@Hermes_persaiassist_bot)
#   2. Local Model Pre-warming (Qwen 9B & FunctionGemma)
#   3. Hermes Native Dashboard (http://127.0.0.1:9119)
#   4. Multi-Agent Company Roster API (http://localhost:8000)
#   5. Windows Desktop Shell & System Tray Daemon (Global Hotkeys & Panic Stop)

param(
    [switch]$NoTray,
    [switch]$Stop,
    [switch]$Status
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
if (-not $repoRoot) {
    $repoRoot = "C:\Users\yepur\Desktop\My_Projects\Hermes agent"
}

$hermesExe = Join-Path $repoRoot "app\venv\Scripts\hermes.exe"
$pythonExe = Join-Path $repoRoot "app\venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $hermesExe)) {
    throw "Hermes executable not found at: $hermesExe"
}

if ($Stop) {
    Write-Host "Stopping Hermes desktop services..." -ForegroundColor Yellow
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*shell_daemon.py*" -or $_.CommandLine -like "*company_dashboard.py*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    & $hermesExe gateway stop
    Write-Host "All Hermes background services stopped." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "       Hermes Agent - Starting Services" -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# [1/5] Ensuring Telegram gateway is running
Write-Host "  [1/5] Ensuring Telegram gateway is running..." -ForegroundColor Yellow
& $hermesExe gateway start

# [2/5] Warming local AI models
Write-Host "  [2/5] Warming local AI models..." -ForegroundColor Yellow
$warmupScript = Join-Path $repoRoot "Warm-Hermes-Models.ps1"
if (Test-Path -LiteralPath $warmupScript) {
    Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$warmupScript`"" `
        -WindowStyle Hidden
}

# [3/5] Ensuring Native Web Dashboard is running (Port 9119)
Write-Host "  [3/5] Ensuring native dashboard is running (Port 9119)..." -ForegroundColor Yellow
$dashboardListener = Get-NetTCPConnection -State Listen -LocalPort 9119 -ErrorAction SilentlyContinue
if (-not $dashboardListener) {
    Start-Process -FilePath $hermesExe -ArgumentList "dashboard" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# [4/5] Starting Multi-Agent Company Dashboard (Port 8000)
Write-Host "  [4/5] Starting Employee Dashboard API (Port 8000)..." -ForegroundColor Yellow
$empListener = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $empListener) {
    $dashboardScript = Join-Path $repoRoot "local_model_lab\company_dashboard.py"
    Start-Process -FilePath $pythonExe -ArgumentList "-X utf8 `"$dashboardScript`"" -WindowStyle Hidden
}

# [5/5] Starting Windows Desktop Shell & System Tray Daemon
if (-not $NoTray) {
    Write-Host "  [5/5] Starting Desktop Shell & System Tray Daemon..." -ForegroundColor Yellow
    $trayRunning = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*shell_daemon.py*" }
    if (-not $trayRunning) {
        $shellScript = Join-Path $repoRoot "local_model_lab\shell_daemon.py"
        Start-Process -FilePath $pythonExe -ArgumentList "`"$shellScript`" --start" -WindowStyle Hidden
    }
}

Write-Host ""
Write-Host "  ✓ Native Dashboard:   http://127.0.0.1:9119" -ForegroundColor Green
Write-Host "  ✓ Company Roster:     http://localhost:8000" -ForegroundColor Green
Write-Host "  ✓ Telegram Gateway:   Active" -ForegroundColor Green
Write-Host "  ✓ Global Hotkeys:     Ctrl+Alt+Space (Summon), Ctrl+Alt+C (Assist), Ctrl+Esc (Emergency Stop)" -ForegroundColor Green
Write-Host ""
