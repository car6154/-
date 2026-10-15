@echo off
setlocal
cd /d "%~dp0"
title J-PRO Clean Termination

echo ========================================================
echo   [J-PRO] 3 Servers Complete Clean Termination
echo   - Closing Port 8000, 3000, 8501
echo   - Closing all console windows
echo ========================================================

REM 1. 포트 8000, 3000, 8501 점유 프로세스(PID) 강제 종료
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr ":8000 "') do (
    echo [Kill] Port 8000 (PID: %%a)
    taskkill /f /t /pid %%a > nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr ":3000 "') do (
    echo [Kill] Port 3000 (PID: %%a)
    taskkill /f /t /pid %%a > nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr ":8501 "') do (
    echo [Kill] Port 8501 (PID: %%a)
    taskkill /f /t /pid %%a > nul 2>&1
)

REM 2. 관련 모든 CMD 창 종료
taskkill /f /fi "WINDOWTITLE eq JPRO_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *JPRO*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *FastAPI*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *Streamlit*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *Integrated Launcher*" > nul 2>&1

echo.
echo All J-PRO servers and console windows have been terminated cleanly.
timeout /t 2 /nobreak > nul
exit
