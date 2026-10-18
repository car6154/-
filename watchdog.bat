@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title JPRO_Watchdog

echo ========================================================
echo   [J-PRO] 24시간 무인 자동 부활 감시자 (Watchdog)
echo   - 8000번 백엔드 서버 다운 시 3회 연속 확인 후 자동 부활
echo   - 초기 부팅 안전 대기(15초) 후 백그라운드 항시 감시
echo ========================================================

:: 서버 최초 부팅 안전 대기 (run_all.bat 실행 직후 간섭 방지)
ping 127.0.0.1 -n 15 > nul

set FAIL_COUNT_8000=0
set FAIL_COUNT_3000=0

:LOOP
ping 127.0.0.1 -n 8 > nul

:: 8000번(백엔드) 포트 LISTENING 상태 점검
netstat -ano -p tcp | findstr "LISTENING" | findstr ":8000" > nul 2>&1
if !errorlevel! neq 0 (
    set /a FAIL_COUNT_8000+=1
) else (
    set FAIL_COUNT_8000=0
)

:: 3000번(프론트엔드) 포트 LISTENING 상태 점검
netstat -ano -p tcp | findstr "LISTENING" | findstr ":3000" > nul 2>&1
if !errorlevel! neq 0 (
    set /a FAIL_COUNT_3000+=1
) else (
    set FAIL_COUNT_3000=0
)

:: 백엔드가 연속 3회(약 20초 이상) 다운된 경우에만 전체 부활 기동
if !FAIL_COUNT_8000! geq 3 (
    echo [%date% %time%] 8000번 백엔드 3회 연속 다운 감지! 전체 서버를 자동 부활 기동합니다...
    set FAIL_COUNT_8000=0
    set FAIL_COUNT_3000=0
    start "" cmd.exe /c "cd /d "%~dp0" & run_all.bat"
    ping 127.0.0.1 -n 25 > nul
    goto LOOP
)

:: 백엔드는 정상인데 프론트엔드만 연속 3회 다운된 경우
if !FAIL_COUNT_3000! geq 3 (
    echo [%date% %time%] 3000번 프론트엔드 웹 서버 다운 감지! 프론트엔드만 재기동합니다...
    set FAIL_COUNT_3000=0
    taskkill /f /fi "WINDOWTITLE eq JPRO_Frontend_*" > nul 2>&1
    start "JPRO_Frontend_3000" cmd.exe /c "cd /d "%~dp0frontend" & npm run dev -- --host 0.0.0.0"
    ping 127.0.0.1 -n 15 > nul
    goto LOOP
)

goto LOOP
