$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$WebRoot = Join-Path $Root "web"

function Test-PortBindable {
    param([int]$Port)
    $listener = $null
    try {
        $address = [System.Net.IPAddress]::Parse("127.0.0.1")
        $listener = [System.Net.Sockets.TcpListener]::new($address, $Port)
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($listener -ne $null) {
            $listener.Stop()
        }
    }
}

$CandidatePorts = @(8000, 8010, 8011, 8012, 8013, 8014, 8015, 18080, 18081, 28080, 38080, 48080)
$BackendPort = $CandidatePorts | Where-Object { Test-PortBindable $_ } | Select-Object -First 1
if (-not $BackendPort) {
    $BackendPort = 18080
    Write-Host "Port probe was blocked or found no open port. Falling back to 127.0.0.1:$BackendPort." -ForegroundColor Yellow
}

$ApiBase = "http://127.0.0.1:$BackendPort/api"

Write-Host "Starting HK-JobMarket-Analyzer dev servers..." -ForegroundColor Cyan
Write-Host "Backend:  http://127.0.0.1:$BackendPort"
Write-Host "Frontend: http://127.0.0.1:5174"
Write-Host "API base: $ApiBase"
Write-Host ""

$BackendCommand = "Set-Location -LiteralPath '$Root'; python -m uvicorn api.main:app --reload --host 127.0.0.1 --port $BackendPort"
$FrontendCommand = "Set-Location -LiteralPath '$WebRoot'; `$env:VITE_API_BASE_URL='$ApiBase'; npm run dev -- --host 127.0.0.1 --port 5174"

Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $BackendCommand)
Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $FrontendCommand)

Write-Host "Started two terminal windows. Close them or press Ctrl+C in each window to stop." -ForegroundColor Green

