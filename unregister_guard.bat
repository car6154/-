@echo off
setlocal
cd /d "%~dp0"
title J-PRO Unregister Guard Watchdog

echo ========================================================
echo   [J-PRO] 24시간 무인 가드 스케줄러 등록 해제
echo ========================================================
echo.

echo [*] 등록된 가드 스케줄러 작업 삭제 중...
schtasks /delete /tn "JPRO_Guard_Logon" /f > nul 2>&1
schtasks /delete /tn "JPRO_Guard_5Min" /f > nul 2>&1

echo [성공] JPRO_Guard_Logon 및 JPRO_Guard_5Min 스케줄 작업이 정상 해제되었습니다.
echo.
ping 127.0.0.1 -n 3 > nul
exit /b 0
