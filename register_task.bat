@echo off
setlocal
cd /d "%~dp0"
title JPRO_Register_Task

REM 관리자 권한 확인 및 자동 승격
openfiles >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 관리자 권한으로 승격을 요청합니다...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ========================================================
echo   [J-PRO] Unified Supervisor Task Scheduler Registration
echo ========================================================

schtasks /create /tn "JPRO_Supervisor" /tr "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\jpro\supervisor.ps1" /sc minute /mo 1 /rl highest /f
schtasks /create /tn "JPRO_Supervisor_Logon" /tr "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\jpro\supervisor.ps1" /sc onlogon /rl highest /f

if %errorlevel% equ 0 (
    echo [OK] JPRO_Supervisor (1분 주기 및 로그온 트리거) 작업이 작업 스케줄러에 성공적으로 등록되었습니다.
    echo [*] 스케줄러 작업을 즉시 1회 기동합니다...
    schtasks /run /tn "JPRO_Supervisor"
) else (
    echo [ERROR] 작업 등록에 실패했습니다. (ErrorLevel: %errorlevel%)
)

timeout /t 3
exit /b %errorlevel%
