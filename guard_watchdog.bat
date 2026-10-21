@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title JPRO_Guard_Watchdog

REM 0. Guard 자체의 중복 실행 방지 (락 파일 검사)
(type nul > "%~dp0guard.lock") 2>nul
if errorlevel 1 (
    echo [%date% %time%] JPRO_Guard_Watchdog is already running. Exiting.
    exit /b 0
)

(
    REM 1. Watchdog 활성 상태 검사 (락 파일 점유 확인 + 창 제목 확인)
    set "WD_RUNNING=0"

    REM (1) watchdog.lock 점유 확인: 열려 있으면(에러코드 1) 이미 워치도그 실행 중
    (type nul > "%~dp0watchdog.lock") 2>nul
    if errorlevel 1 set "WD_RUNNING=1"

    REM (2) 창 제목 확인: 보조 안전장치
    tasklist /fi "WINDOWTITLE eq JPRO_Watchdog*" 2>nul | findstr /i "cmd.exe" > nul 2>&1
    if not errorlevel 1 set "WD_RUNNING=1"

    REM 2. 워치도그가 1개라도 실행 중이면 절대 추가 기동하지 않음
    if "!WD_RUNNING!"=="1" (
        echo [%date% %time%] JPRO_Watchdog is already running normally.
    ) else (
        echo [%date% %time%] JPRO_Watchdog is not running. Starting watchdog.bat in background...
        start "JPRO_Watchdog" /min cmd.exe /c "cd /d "%~dp0" & watchdog.bat"
    )
) 9>"%~dp0guard.lock"

exit /b 0
