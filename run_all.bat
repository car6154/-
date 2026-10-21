@echo off
setlocal
cd /d "%~dp0"
title J-PRO Launcher

echo ========================================================
echo   [J-PRO] Unified Supervisor Launcher
echo ========================================================

REM 0. Remove supervisor.stop if exists
if exist "%~dp0supervisor.stop" (
    echo [*] Removing supervisor.stop...
    del /f /q "%~dp0supervisor.stop" > nul 2>&1
)

REM 1. Start unified supervisor in background (Single instance enforced by Mutex)
echo [*] Starting JPRO Unified Supervisor (PowerShell)...
start "JPRO_Supervisor" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0supervisor.ps1"

echo [*] JPRO Supervisor launched successfully.
exit /b 0
