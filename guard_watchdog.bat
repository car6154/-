@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
title JPRO_Guard_Watchdog

REM Check if JPRO_Watchdog is running
tasklist /fi "WINDOWTITLE eq JPRO_Watchdog*" 2>nul | findstr /i "cmd.exe" > nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] JPRO_Watchdog is not running. Starting watchdog.bat in background...
    start "JPRO_Watchdog" /min cmd.exe /c "cd /d "%~dp0" & watchdog.bat"
) else (
    echo [%date% %time%] JPRO_Watchdog is already running normally.
)

exit /b 0
