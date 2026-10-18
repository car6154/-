@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title JPRO_Watchdog

echo ========================================================
echo   [J-PRO] 24시간 무인 자동 부활 감시자 (Smart Watchdog)
echo   - 8000번 백엔드 다운 시 플래그 확인 후 즉각 자동 부활
echo   - server_booting.lock / server_paused.lock 기반 스마트 제어
echo ========================================================

:: 초기 기동 대기 (3초)
ping 127.0.0.1 -n 3 > nul

set FAIL_COUNT_8000=0
set FAIL_COUNT_3000=0

:LOOP
ping 127.0.0.1 -n 5 > nul

:: 1. 수동 종료 상태 점검 (kill_servers.bat 실행 시 감시 일시 정지)
if exist "%~dp0server_paused.lock" (
    set FAIL_COUNT_8000=0
    set FAIL_COUNT_3000=0
    goto LOOP
)

:: 2. 서버 부팅 진행 상태 점검 (run_all.bat 실행 중 중복 기동 간섭 방지)
if exist "%~dp0server_booting.lock" (
    set FAIL_COUNT_8000=0
    set FAIL_COUNT_3000=0
    goto LOOP
)

:: 3. 8000번(백엔드) 포트 LISTENING 상태 점검
netstat -ano -p tcp | findstr "LISTENING" | findstr ":8000" > nul 2>&1
if !errorlevel! neq 0 (
    set /a FAIL_COUNT_8000+=1
) else (
    set FAIL_COUNT_8000=0
)

:: 4. 3000번(프론트엔드) 포트 LISTENING 상태 점검
netstat -ano -p tcp | findstr "LISTENING" | findstr ":3000" > nul 2>&1
if !errorlevel! neq 0 (
    set /a FAIL_COUNT_3000+=1
) else (
    set FAIL_COUNT_3000=0
)

:: 백엔드가 연속 2회(약 6~10초) 다운 확인 시 즉시 전체 서버 자동 부활
if !FAIL_COUNT_8000! geq 2 (
    echo [%date% %time%] 8000번 백엔드 다운 감지! 전체 서버를 자동 부활 기동합니다...
    set FAIL_COUNT_8000=0
    set FAIL_COUNT_3000=0
    start "" cmd.exe /c "cd /d "%~dp0" & run_all.bat"
    ping 127.0.0.1 -n 10 > nul
    goto LOOP
)

:: 백엔드는 정상인데 프론트엔드만 연속 2회 다운된 경우
if !FAIL_COUNT_3000! geq 2 (
    echo [%date% %time%] 3000번 프론트엔드 웹 서버 다운 감지! 프론트엔드만 재기동합니다...
    set FAIL_COUNT_3000=0
    taskkill /f /fi "WINDOWTITLE eq JPRO_Frontend_*" > nul 2>&1
    start "JPRO_Frontend_3000" cmd.exe /c "cd /d "%~dp0frontend" & npm run dev -- --host 0.0.0.0"
    ping 127.0.0.1 -n 8 > nul
    goto LOOP
)

goto LOOP
