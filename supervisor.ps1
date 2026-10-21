# ==============================================================================
# J-PRO Unified Supervisor (PowerShell)
# - Single instance enforcement via Named Mutex
# - Direct child process supervision (No uvicorn --reload, No tsx watch)
# - 5-second health loop: Process alive + TCP LISTENING check
# - 3 consecutive failures threshold with 30-second initial grace period
# - Clean tree-kill & port-clear on failure & supervisor.stop
# ==============================================================================

# 0. Host Guard
if ($env:COMPUTERNAME -ne "DESKTOP-809DDGE") {
    Write-Host "[ERROR] Invalid host: $env:COMPUTERNAME. Expected DESKTOP-809DDGE."
    exit 1
}

# 1. Base Directory Setup
$baseDir = "C:\jpro"
Set-Location -Path $baseDir

$logsDir = Join-Path $baseDir "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

$supervisorLog = Join-Path $logsDir "supervisor.log"
$stopFile = Join-Path $baseDir "supervisor.stop"

function Write-SupervisorLog([string]$message) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $logLine = "[$timestamp] $message"
    Write-Host $logLine
    try {
        Add-Content -Path $supervisorLog -Value $logLine -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {}
}

# 2. Named Mutex for Single Instance
$mutexName = "Global\JPRO_Supervisor_Mutex"
$createdNew = $false
$mutex = $null
$hasHandle = $false

try {
    $mutex = New-Object System.Threading.Mutex($false, $mutexName, [ref]$createdNew)
} catch {
    Write-SupervisorLog "[FATAL] Failed to create mutex: $_"
    exit 1
}

try {
    $hasHandle = $mutex.WaitOne(0, $false)
} catch [System.Threading.AbandonedMutexException] {
    # Previous process was killed abruptly; ownership acquired
    $hasHandle = $true
} catch {
    Write-SupervisorLog "[FATAL] Failed to acquire mutex: $_"
    exit 1
}

if (-not $hasHandle) {
    Write-SupervisorLog "[INFO] JPRO_Supervisor is already running. Exiting immediately."
    exit 0
}

try {
    Write-SupervisorLog "=================================================="
    Write-SupervisorLog "  [J-PRO] Unified Supervisor Started (PID: $PID)"
    Write-SupervisorLog "=================================================="

    # Node.js PATH setup
    if (Test-Path "$env:LOCALAPPDATA\Programs\nodejs") {
        $env:PATH = "$env:LOCALAPPDATA\Programs\nodejs;$env:PATH"
    }
    if (Test-Path "C:\Program Files\nodejs") {
        $env:PATH = "C:\Program Files\nodejs;$env:PATH"
    }

    # Tailscale sync
    function Sync-Downloads() {
        $dl = "$env:USERPROFILE\Downloads"
        $moves = @(
            @{ Src = "$dl\firebase-applet-config.json"; Dst = "$baseDir\frontend\firebase-applet-config.json" },
            @{ Src = "$dl\.env"; Dst = "$baseDir\.env" },
            @{ Src = "$dl\autoplus_cookie.txt"; Dst = "$baseDir\autoplus_cookie.txt" }
        )
        foreach ($m in $moves) {
            if (Test-Path $m.Src) {
                try {
                    Move-Item -Path $m.Src -Destination $m.Dst -Force -ErrorAction SilentlyContinue
                    Write-SupervisorLog "[OK] Moved $($m.Src) to $($m.Dst)"
                } catch {}
            }
        }
    }
    Sync-Downloads

    # 3. Find Node.js
    $nodeExe = "C:\Program Files\nodejs\node.exe"
    if (-not (Test-Path $nodeExe)) {
        $nodeCmd = Get-Command node.exe -ErrorAction SilentlyContinue
        if ($nodeCmd) { $nodeExe = $nodeCmd.Source }
    }

    # 4. Define 4 services
    $services = @(
        @{
            Name = "FastAPI Backend"
            ShortName = "backend"
            Port = 8000
            SecondaryPort = $null
            WorkDir = $baseDir
            FilePath = "$baseDir\.venv\Scripts\python.exe"
            ArgumentList = "-m uvicorn api_server:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 1"
            StdOut = "$logsDir\fastapi.log"
            StdErr = "$logsDir\fastapi_err.log"
            Process = $null
            Pid = $null
            StartedAt = [DateTime]::MinValue
            FailCount = 0
            Enabled = $true
        },
        @{
            Name = "Frontend Server"
            ShortName = "frontend"
            Port = 3000
            SecondaryPort = 8502
            WorkDir = "$baseDir\frontend"
            FilePath = $nodeExe
            ArgumentList = "`"$baseDir\frontend\node_modules\tsx\dist\cli.mjs`" server.ts"
            StdOut = "$logsDir\frontend.log"
            StdErr = "$logsDir\frontend_err.log"
            Process = $null
            Pid = $null
            StartedAt = [DateTime]::MinValue
            FailCount = 0
            Enabled = $true
        },
        @{
            Name = "Streamlit Dashboard"
            ShortName = "streamlit"
            Port = 8501
            SecondaryPort = $null
            WorkDir = $baseDir
            FilePath = "$baseDir\.venv\Scripts\python.exe"
            ArgumentList = "-m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false"
            StdOut = "$logsDir\streamlit.log"
            StdErr = "$logsDir\streamlit_err.log"
            Process = $null
            Pid = $null
            StartedAt = [DateTime]::MinValue
            FailCount = 0
            Enabled = $true
        },
        @{
            Name = "Shopping Bot Web"
            ShortName = "shopping"
            Port = 6154
            SecondaryPort = $null
            WorkDir = "C:\ai_shopping_bot"
            FilePath = "C:\ai_shopping_bot\.venv\Scripts\python.exe"
            ArgumentList = "web_server.py"
            StdOut = "$logsDir\shopping.log"
            StdErr = "$logsDir\shopping_err.log"
            Process = $null
            Pid = $null
            StartedAt = [DateTime]::MinValue
            FailCount = 0
            Enabled = (Test-Path "C:\ai_shopping_bot\web_server.py")
        }
    )

    function Get-ListeningProcesses() {
        $map = @{}
        $lines = netstat -ano -p tcp
        foreach ($line in $lines) {
            if ($line -match '^\s*TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$') {
                $p = [int]$matches[1]
                $pidVal = [int]$matches[2]
                if (-not $map.ContainsKey($p)) {
                    $map[$p] = [System.Collections.Generic.List[int]]::new()
                }
                if (-not $map[$p].Contains($pidVal)) {
                    $map[$p].Add($pidVal)
                }
            }
        }
        return $map
    }

    function Stop-ServiceTree($svc) {
        Write-SupervisorLog "[$($svc.Name)] Stopping process tree (PID: $($svc.Pid), Port: $($svc.Port))..."
        if ($svc.Pid) {
            try {
                taskkill /f /t /pid $svc.Pid 2>&1 | Out-Null
            } catch {}
        }
        
        $ports = @($svc.Port)
        if ($svc.SecondaryPort) { $ports += $svc.SecondaryPort }
        
        foreach ($prt in $ports) {
            $listenMap = Get-ListeningProcesses
            if ($listenMap.ContainsKey($prt)) {
                foreach ($p in $listenMap[$prt]) {
                    if ($p -gt 0 -and $p -ne $PID) {
                        Write-SupervisorLog "[$($svc.Name)] Killing lingering port $prt listener PID $p..."
                        try { taskkill /f /t /pid $p 2>&1 | Out-Null } catch {}
                    }
                }
            }
        }
        $svc.Process = $null
        $svc.Pid = $null
    }

    function Wait-PortClear([int]$port, [int]$timeoutSec = 10) {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        while ($sw.Elapsed.TotalSeconds -lt $timeoutSec) {
            $listenMap = Get-ListeningProcesses
            if (-not $listenMap.ContainsKey($port)) {
                return $true
            }
            Start-Sleep -Milliseconds 500
        }
        return $false
    }

    function Start-SingleService($svc) {
        if (-not $svc.Enabled) {
            Write-SupervisorLog "[$($svc.Name)] Service is disabled. Skipping."
            return
        }

        $ports = @($svc.Port)
        if ($svc.SecondaryPort) { $ports += $svc.SecondaryPort }
        foreach ($prt in $ports) {
            $listenMap = Get-ListeningProcesses
            if ($listenMap.ContainsKey($prt)) {
                foreach ($p in $listenMap[$prt]) {
                    if ($p -gt 0 -and $p -ne $PID) {
                        Write-SupervisorLog "[$($svc.Name)] Pre-clearing occupied port $prt (PID $p)..."
                        try { taskkill /f /t /pid $p 2>&1 | Out-Null } catch {}
                    }
                }
            }
            Wait-PortClear $prt 5 | Out-Null
        }

        Write-SupervisorLog "[$($svc.Name)] Starting: $($svc.FilePath) $($svc.ArgumentList) in $($svc.WorkDir)..."
        try {
            $proc = Start-Process -FilePath $svc.FilePath `
                                  -ArgumentList $svc.ArgumentList `
                                  -WorkingDirectory $svc.WorkDir `
                                  -RedirectStandardOutput $svc.StdOut `
                                  -RedirectStandardError $svc.StdErr `
                                  -NoNewWindow `
                                  -PassThru
            $svc.Process = $proc
            $svc.Pid = $proc.Id
            $svc.StartedAt = [DateTime]::Now
            $svc.FailCount = 0
            Write-SupervisorLog "[$($svc.Name)] Started successfully. (PID: $($svc.Pid))"
        } catch {
            Write-SupervisorLog "[$($svc.Name)] [ERROR] Failed to start: $_"
            $svc.Process = $null
            $svc.Pid = $null
        }
    }

    # 4-1. Clear stale stop file on startup
    if (Test-Path $stopFile) {
        try {
            Remove-Item -Path $stopFile -Force -ErrorAction SilentlyContinue
            Write-SupervisorLog "[STARTUP] Stale supervisor.stop removed. Continuing normal startup."
        } catch {}
    }

    # 5. Start all services initially
    foreach ($svc in $services) {
        Start-SingleService $svc
    }

    # 6. Health check loop (5s interval)
    Write-SupervisorLog "[LOOP] Entering health check loop (5s interval, 30s grace period, threshold 3)..."
    $gracePeriodSec = 30
    $failThreshold = 3

    while ($true) {
        Start-Sleep -Seconds 5

        # (1) Check supervisor.stop
        if (Test-Path $stopFile) {
            Write-SupervisorLog "[STOP] supervisor.stop detected! Terminating all child services and shutting down supervisor..."
            foreach ($svc in $services) {
                Stop-ServiceTree $svc
            }
            $allPorts = @(8000, 3000, 8501, 8502, 6154)
            $listenMap = Get-ListeningProcesses
            foreach ($prt in $allPorts) {
                if ($listenMap.ContainsKey($prt)) {
                    foreach ($p in $listenMap[$prt]) {
                        if ($p -gt 0 -and $p -ne $PID) {
                            try { taskkill /f /t /pid $p 2>&1 | Out-Null } catch {}
                        }
                    }
                }
            }
            Write-SupervisorLog "[STOP] All child services stopped. Supervisor exiting cleanly."
            break
        }

        # (2) Health check
        $listenMap = Get-ListeningProcesses

        foreach ($svc in $services) {
            if (-not $svc.Enabled) { continue }

            $now = [DateTime]::Now
            $uptimeSec = ($now - $svc.StartedAt).TotalSeconds

            # 30s initial grace period
            if ($uptimeSec -lt $gracePeriodSec) {
                $svc.FailCount = 0
                continue
            }

            # Process alive check
            $procAlive = $false
            if ($svc.Process -and -not $svc.Process.HasExited) {
                $procAlive = $true
            } elseif ($svc.Pid) {
                $p = Get-Process -Id $svc.Pid -ErrorAction SilentlyContinue
                if ($p) { $procAlive = $true }
            }

            # Port listening check
            $portListening = $listenMap.ContainsKey($svc.Port)

            if ($procAlive -and $portListening) {
                if ($svc.FailCount -gt 0) {
                    Write-SupervisorLog "[$($svc.Name)] Health restored (PID: $($svc.Pid), Port: $($svc.Port)). Resetting fail count."
                }
                $svc.FailCount = 0
            } else {
                $svc.FailCount++
                Write-SupervisorLog "[$($svc.Name)] Check FAILED ($($svc.FailCount)/$failThreshold). [ProcessAlive: $procAlive, Port $($svc.Port) Listening: $portListening]"
                
                # 3 consecutive failures threshold
                if ($svc.FailCount -ge $failThreshold) {
                    Write-SupervisorLog "[$($svc.Name)] Reached $failThreshold consecutive failures. Initiating restart..."
                    Stop-ServiceTree $svc
                    if (-not (Wait-PortClear $svc.Port 10)) {
                        Write-SupervisorLog "[$($svc.Name)] [WARNING] Port $($svc.Port) not cleared after tree kill."
                    }
                    Start-SingleService $svc
                }
            }
        }
    }
} finally {
    if ($mutex) {
        try {
            $mutex.ReleaseMutex()
        } catch {}
        $mutex.Dispose()
    }
    Write-SupervisorLog "[INFO] JPRO_Supervisor process terminated. Mutex released."
}
