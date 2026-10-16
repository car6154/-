@echo off
setlocal
cd /d "%~dp0"
title JPRO_Watchdog

echo ========================================================
echo   [J-PRO] 24시간 무인 자동 부활 감시자 (Watchdog)
echo   - 8000번 백엔드 서버 다운 시 3초 내 자동 재기동
echo   - 윈도우 최소화 상태로 백그라운드 항시 감시
echo ========================================================

:LOOP
ping 127.0.0.1 -n 5 > nul

:: 8000번 포트 LISTENING 상태 점검
netstat -ano -p tcp | findstr "LISTENING" | findstr ":8000" > nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] 8000번 백엔드 서버 다운 감지! 즉시 자동 부활 기동합니다...
    call "%~dp0run_all.bat"
    ping 127.0.0.1 -n 10 > nul
)

goto LOOP
