@echo off
setlocal
cd /d "%~dp0"
title J-PRO Clean Termination

:: 1. 관리자 권한 확인 및 자동 승격 (액세스 거부 원천 방지)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [J-PRO] 관리자 권한으로 자동 승격 실행 중...
    powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ========================================================
echo   [J-PRO] 3 Servers Complete Clean Termination
echo   - Closing Port 8000, 3000, 8501, 8502 (Admin Mode)
echo   - Safe termination (protecting shopping bot 6154)
echo   - Closing all console windows
echo ========================================================

:: 2. J-PRO 4대 전용 포트(8000, 3000, 8501, 8502)의 LISTENING 대기 프로세스 및 하위 트리 강제 종료
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":8000 :3000 :8501 :8502"') do (
    echo [Kill] Port Process PID: %%a
    taskkill /f /t /pid %%a > nul 2>&1
)

:: 3. 관련 모든 CMD 콘솔 창 닫기
taskkill /f /fi "WINDOWTITLE eq JPRO_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *JPRO*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *FastAPI*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *Streamlit*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *Integrated Launcher*" > nul 2>&1

echo.
echo All J-PRO servers and console windows have been terminated cleanly.
timeout /t 2 /nobreak > nul
exit
