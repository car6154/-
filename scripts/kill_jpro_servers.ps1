# J-PRO 전용 서버 프로세스 정밀 타겟 종료 스크립트
# 쇼핑봇(Telegram, 6154 포트) 등 다른 Python/Node 프로세스는 100% 안전하게 보호하고
# J-PRO 백엔드(api_server), 프론트엔드(server.ts / tsx), 스트림릿(app.py) 관련 프로세스만 안전하게 종료합니다.

# 1. CommandLine 기반 정밀 필터링 종료 (부모 uvicorn, server.ts, tsx, streamlit, 부모 cmd 창)
$targetProcesses = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -in @('python.exe', 'node.exe', 'cmd.exe')) -and (
        $_.CommandLine -like '*api_server*' -or
        $_.CommandLine -like '*server.ts*' -or
        $_.CommandLine -like '*tsx*' -or
        $_.CommandLine -like '*streamlit run app.py*' -or
        $_.CommandLine -like '*vite*' -or
        $_.CommandLine -like '*JPRO_*'
    )
}

if ($targetProcesses) {
    foreach ($proc in $targetProcesses) {
        try {
            Write-Host "[Kill Process] PID: $($proc.ProcessId) ($($proc.Name))"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        } catch {}
    }
}

# 2. J-PRO 고유 포트 (8000, 3000, 8501, 8502) 점유 PID netstat 파싱 강제 종료
try {
    $portsPattern = ":(8000|3000|8501|8502)\s+"
    $netstatLines = netstat -ano -p tcp | Select-String $portsPattern
    foreach ($line in $netstatLines) {
        $tokens = ($line.Line.Trim() -split '\s+')
        $pidToKill = $tokens[-1]
        if ($pidToKill -match '^\d+$' -and [int]$pidToKill -gt 0) {
            try {
                Write-Host "[Kill Port PID] $pidToKill"
                taskkill /f /t /pid $pidToKill 2>$null
            } catch {}
        }
    }
} catch {}
