# J-PRO 전용 서버 프로세스 정밀 타겟 종료 스크립트
# 쇼핑봇(Telegram, 6154 포트) 등 다른 Python/Node 프로세스는 100% 안전하게 보호하고
# J-PRO 백엔드(api_server), 스트림릿(app.py), 프론트엔드(Vite dev) 관련 프로세스만 안전하게 종료합니다.

# 1. CommandLine 기반 정밀 필터링 종료
$targetProcesses = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -in @('python.exe', 'node.exe', 'cmd.exe')) -and (
        $_.CommandLine -like '*api_server*' -or
        $_.CommandLine -like '*streamlit run app.py*' -or
        ($_.CommandLine -like '*frontend*' -and $_.CommandLine -like '*npm run dev*') -or
        $_.CommandLine -like '*vite*'
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

# 2. J-PRO 고유 포트 (8000, 3000, 8501) 점유 PID 추가 정리
$targetPorts = @(8000, 3000, 8501)
foreach ($port in $targetPorts) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            if ($conn.OwningProcess -and $conn.OwningProcess -gt 0) {
                try {
                    Write-Host "[Kill Port $port] PID: $($conn.OwningProcess)"
                    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
                } catch {}
            }
        }
    }
}
