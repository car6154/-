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

:: 8000번(백엔드) 또는 3000번(프론트엔드) 포트 LISTENING 상태 점검
set BACKEND_DOWN=0
set FRONTEND_DOWN=0

netstat -ano -p tcp | findstr "LISTENING" | findstr ":8000" > nul 2>&1
if %errorlevel% neq 0 set BACKEND_DOWN=1

netstat -ano -p tcp | findstr "LISTENING" | findstr ":3000" > nul 2>&1
if %errorlevel% neq 0 set FRONTEND_DOWN=1

if %BACKEND_DOWN% equ 1 (
    echo [%date% %time%] 8000번 백엔드 서버 다운 감지! 즉시 전체 서버를 자동 부활 기동합니다...
    start "" cmd.exe /c "cd /d "%~dp0" & run_all.bat"
    ping 127.0.0.1 -n 15 > nul
) else if %FRONTEND_DOWN% equ 1 (
    echo [%date% %time%] 3000번 프론트엔드 웹 서버 다운 감지! 즉시 재기동합니다...
    start "JPRO_Frontend_3000" cmd.exe /c "cd /d "%~dp0frontend" & npm run dev -- --host 0.0.0.0"
    ping 127.0.0.1 -n 10 > nul
)

goto LOOP
