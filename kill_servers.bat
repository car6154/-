@echo off
setlocal
cd /d "%~dp0"
title J-PRO Clean Termination

:: 1. 관리자 권한 확인 및 자동 승격
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [J-PRO] 관리자 권한으로 자동 승격 실행 중...
    powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ========================================================
echo   [J-PRO] 전체 서버 및 프로세스 완전 종료 (Clean Kill)
echo   - Closing all Python, Node.js, CMD processes
echo ========================================================

:: 2. Python 및 Node.js 잔여 백그라운드 / 감시자 프로세스 일괄 전멸
taskkill /f /im python.exe > nul 2>&1
taskkill /f /im node.exe > nul 2>&1

:: 3. J-PRO 4대 전용 포트(8000, 3000, 8501, 8502)의 LISTENING 대기 프로세스 및 하위 트리 강제 확인사살
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":8000 :3000 :8501 :8502"') do (
    taskkill /f /t /pid %%a > nul 2>&1
)

:: 4. 관련 서버 콘솔 창 닫기 (JPRO_Watchdog 감시자는 보호)
taskkill /f /fi "WINDOWTITLE eq JPRO_FastAPI_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Frontend_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Streamlit_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *FastAPI*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *Streamlit*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *Integrated Launcher*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *Shopping*" > nul 2>&1

echo.
echo All Python, Node, and J-PRO servers have been terminated cleanly.
ping 127.0.0.1 -n 3 > nul
exit
