$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$WebRoot = Join-Path $Root "web"

# Docker Desktop 程序位置
$DockerDesktopPath = "D:\Users\c4018\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"
# docker-compose.yml 中定义的 MongoDB 容器名
$MongoContainerName = "hk-job-mongo"

# 单实例锁：防止脚本被重复触发（快速双击、并发执行等场景）
$ScriptMutex = New-Object System.Threading.Mutex($false, "Global\HK-JobMarket-Analyzer-Dev-Lock")
if (-not $ScriptMutex.WaitOne(0, $false)) {
    Write-Host "开发启动脚本已在运行中，请勿重复启动。" -ForegroundColor Yellow
    Write-Host "如需重启，请先关闭已有的启动窗口，再运行本脚本。" -ForegroundColor Yellow
    exit 1
}

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

# 检测 Docker 引擎是否已运行
function Test-DockerRunning {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        docker info 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

# 检测指定容器是否处于 running 状态
function Test-ContainerRunning {
    param([string]$Name)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $status = docker inspect --type=container --format='{{.State.Status}}' $Name 2>$null
        return ($LASTEXITCODE -eq 0 -and $status -eq "running")
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

# TCP 端口连接探测（服务已监听则可连，用于判断就绪）
function Test-PortOpen {
    param([int]$Port)
    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect("127.0.0.1", $Port)
        return $true
    }
    catch { return $false }
    finally {
        if ($client -ne $null) { $client.Close() }
    }
}

# 按已读行数增量读取日志（避免文件锁冲突）
function Read-LogDelta {
    param([string]$Path, [ref]$ReadCount)
    if (-not (Test-Path $Path)) { return @() }
    $all = @(Get-Content -Path $Path -ErrorAction SilentlyContinue)
    if ($all.Count -le $ReadCount.Value) { return @() }
    $new = $all | Select-Object -Skip $ReadCount.Value
    $ReadCount.Value = $all.Count
    return $new
}

# 单实例检测：前端固定端口 5174 若已被占用，说明前后端开发服务器已在运行
if (-not (Test-PortBindable 5174)) {
    Write-Host "检测到 5174 端口已被占用，前后端开发服务器可能已在运行。" -ForegroundColor Yellow
    Write-Host "如需重启，请先关闭已有的前后端窗口，再运行本脚本。" -ForegroundColor Yellow
    exit 1
}

$CandidatePorts = @(8000, 8010, 8011, 8012, 8013, 8014, 8015, 18080, 18081, 28080, 38080, 48080)
$BackendPort = $CandidatePorts | Where-Object { Test-PortBindable $_ } | Select-Object -First 1
if (-not $BackendPort) {
    $BackendPort = 18080
    Write-Host "Port probe was blocked or found no open port. Falling back to 127.0.0.1:$BackendPort." -ForegroundColor Yellow
}

$ApiBase = "http://127.0.0.1:$BackendPort/api"

# ===== Docker & MongoDB 容器检查 =====
Write-Host "Checking Docker environment..." -ForegroundColor Cyan

# 1. 检测 Docker 引擎是否已启动
if (-not (Test-DockerRunning)) {
    if (-not (Test-Path $DockerDesktopPath)) {
        Write-Host "未找到 Docker Desktop: $DockerDesktopPath" -ForegroundColor Red
        Write-Host "请确认 Docker Desktop 安装路径，或手动启动后重试。" -ForegroundColor Red
        exit 1
    }
    Write-Host "Docker 未运行，正在启动 Docker Desktop..." -ForegroundColor Yellow
    Start-Process -FilePath $DockerDesktopPath
    Write-Host "等待 Docker 引擎就绪" -NoNewline -ForegroundColor Cyan
    $DockerTimeout = 120
    $DockerElapsed = 0
    while (-not (Test-DockerRunning) -and $DockerElapsed -lt $DockerTimeout) {
        Start-Sleep -Seconds 3
        $DockerElapsed += 3
        Write-Host "." -NoNewline
    }
    Write-Host ""
    if (-not (Test-DockerRunning)) {
        Write-Host "Docker 引擎启动超时（${DockerTimeout}s），请手动确认 Docker Desktop 已完全启动后重试。" -ForegroundColor Red
        exit 1
    }
    Write-Host "Docker 已启动。" -ForegroundColor Green
} else {
    Write-Host "Docker 已运行。" -ForegroundColor Green
}

# 2. 检测 MongoDB 容器是否正常运行
if (-not (Test-ContainerRunning -Name $MongoContainerName)) {
    Write-Host "MongoDB 容器 ($MongoContainerName) 未运行，正在通过 docker compose 启动..." -ForegroundColor Yellow
    Push-Location $Root
    try {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        docker compose up -d mongo
        $composeExit = $LASTEXITCODE
        $ErrorActionPreference = $prevEap
        if ($composeExit -ne 0) {
            Write-Host "docker compose 启动 MongoDB 失败，请检查 docker-compose.yml 配置。" -ForegroundColor Red
            exit 1
        }
        $MongoTimeout = 60
        $MongoElapsed = 0
        while (-not (Test-ContainerRunning -Name $MongoContainerName) -and $MongoElapsed -lt $MongoTimeout) {
            Start-Sleep -Seconds 2
            $MongoElapsed += 2
        }
        if (-not (Test-ContainerRunning -Name $MongoContainerName)) {
            Write-Host "MongoDB 容器启动超时（${MongoTimeout}s），请用 'docker logs $MongoContainerName' 排查。" -ForegroundColor Red
            exit 1
        }
        Write-Host "MongoDB 容器已启动。" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "MongoDB 容器 ($MongoContainerName) 运行正常。" -ForegroundColor Green
}
Write-Host ""
Write-Host "Starting HK-JobMarket-Analyzer dev servers..." -ForegroundColor Cyan

# 设置前端环境变量（隐藏子进程将继承父进程环境）
$env:VITE_API_BASE_URL = $ApiBase

# 日志目录
$LogDir = Join-Path $Root ".dev-logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$BackendLog = Join-Path $LogDir "backend.log"
$FrontendLog = Join-Path $LogDir "frontend.log"

# 以隐藏窗口方式启动后端（输出重定向到日志文件，不弹窗）
Write-Host "Starting backend (hidden)..." -ForegroundColor Cyan
$BackendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "python -m uvicorn api.main:app --reload --host 127.0.0.1 --port $BackendPort 2>&1" -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $BackendLog

# 以隐藏窗口方式启动前端
Write-Host "Starting frontend (hidden)..." -ForegroundColor Cyan
$FrontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev -- --host 127.0.0.1 --port 5174 2>&1" -WorkingDirectory $WebRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $FrontendLog

$BackendReady = $false
$FrontendReady = $false
$BackendRead = 0
$FrontendRead = 0
$SummaryPrinted = $false
$TimeoutWarned = $false
$StartupTimeout = 90
$StartTime = Get-Date

Write-Host ""
Write-Host "Waiting for services to be ready... (Ctrl+C to stop)" -ForegroundColor Cyan
Write-Host ""

# 主循环放宽错误处理，避免原生命令/日志读取的 stderr 中断脚本
$LoopEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    while ($true) {
        # 转发后端日志新增行
        $bDelta = Read-LogDelta $BackendLog ([ref]$BackendRead)
        foreach ($line in $bDelta) { Write-Host "[Backend]  $line" -ForegroundColor DarkGray }

        # 转发前端日志新增行
        $fDelta = Read-LogDelta $FrontendLog ([ref]$FrontendRead)
        foreach ($line in $fDelta) { Write-Host "[Frontend] $line" -ForegroundColor DarkCyan }

        # 后端就绪检测（端口可连）
        if (-not $BackendReady -and (Test-PortOpen $BackendPort)) {
            $BackendReady = $true
            Write-Host "[OK] Backend ready  -> http://127.0.0.1:$BackendPort" -ForegroundColor Green
        }
        # 前端就绪检测（端口可连）
        if (-not $FrontendReady -and (Test-PortOpen 5174)) {
            $FrontendReady = $true
            Write-Host "[OK] Frontend ready -> http://127.0.0.1:5174" -ForegroundColor Green
        }

        # 全部就绪后打印汇总（仅一次）
        if (-not $SummaryPrinted -and $BackendReady -and $FrontendReady) {
            $SummaryPrinted = $true
            Write-Host ""
            Write-Host "All services ready. API base: $ApiBase" -ForegroundColor Green
            Write-Host "Press Ctrl+C in this window to stop all services." -ForegroundColor Cyan
            Write-Host ""
        }

        # 进程异常退出检测
        if ($BackendProc.HasExited) {
            Write-Host "[FAIL] Backend exited (code $($BackendProc.ExitCode))." -ForegroundColor Red
            break
        }
        if ($FrontendProc.HasExited) {
            Write-Host "[FAIL] Frontend exited (code $($FrontendProc.ExitCode))." -ForegroundColor Red
            break
        }

        # 超时提示（仅一次）
        if (-not $TimeoutWarned -and -not ($BackendReady -and $FrontendReady)) {
            $elapsed = [int]((Get-Date) - $StartTime).TotalSeconds
            if ($elapsed -gt $StartupTimeout) {
                $TimeoutWarned = $true
                Write-Host "[WARN] Still waiting after ${StartupTimeout}s, continuing..." -ForegroundColor Yellow
            }
        }

        Start-Sleep -Milliseconds 800
    }
}
finally {
    $ErrorActionPreference = $LoopEap
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Cyan
    foreach ($procId in @($FrontendProc.Id, $BackendProc.Id)) {
        if ($procId) {
            # /T 杀掉整个进程树（cmd 及其子进程 python/node）
            try { taskkill /PID $procId /T /F 2>&1 | Out-Null } catch {}
        }
    }
    Write-Host "All services stopped." -ForegroundColor Green
}

