$ErrorActionPreference = "Stop"

$HermesHome = "C:\Users\yepur\Desktop\My_Projects\Hermes agent"
$LogPath = Join-Path $HermesHome "logs\model-warmup.log"
$OllamaBase = "http://127.0.0.1:11434"

function Write-WarmLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $LogPath -Value "$timestamp $Message" -Encoding UTF8
}

$ready = $false
for ($attempt = 1; $attempt -le 18; $attempt++) {
    try {
        Invoke-RestMethod -Uri "$OllamaBase/api/version" -TimeoutSec 3 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 5
    }
}

if (-not $ready) {
    Write-WarmLog "Ollama was not ready after 90 seconds; skipping warm-up."
    exit 0
}

try {
    $embedBody = @{
        model = "embeddinggemma:300m"
        input = "Hermes memory warm-up"
        keep_alive = "24h"
    } | ConvertTo-Json
    Invoke-RestMethod `
        -Uri "$OllamaBase/api/embed" `
        -Method Post `
        -ContentType "application/json" `
        -Body $embedBody `
        -TimeoutSec 120 | Out-Null
    Write-WarmLog "Loaded embeddinggemma:300m."
} catch {
    Write-WarmLog "Embedding warm-up failed: $($_.Exception.Message)"
}

try {
    $chatBody = @{
        model = "hermes-local:latest"
        messages = @(@{ role = "user"; content = "Reply OK." })
        stream = $false
        think = $false
        keep_alive = "24h"
        options = @{ num_predict = 2; temperature = 0 }
    } | ConvertTo-Json -Depth 5
    Invoke-RestMethod `
        -Uri "$OllamaBase/api/chat" `
        -Method Post `
        -ContentType "application/json" `
        -Body $chatBody `
        -TimeoutSec 240 | Out-Null
    Write-WarmLog "Loaded hermes-local:latest."
} catch {
    Write-WarmLog "Local model warm-up failed: $($_.Exception.Message)"
}

