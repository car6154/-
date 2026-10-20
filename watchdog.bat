@echo off
setlocal
cd /d "%~dp0"
title JPRO_Watchdog

REM Node.js 공식 경로 최우선 설정 (run_all.bat와 100% 대칭 유지)
if exist "%LOCALAPPDATA%\Programs\nodejs" (
    set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%"
)
if exist "C:\Program Files\nodejs" (
    set "PATH=C:\Program Files\nodejs;%PATH%"
)

echo ========================================================
echo   [J-PRO] 24시간 무인 자동 부활 감시자 (Watchdog)
echo   - 8000(백엔드) / 3000(프론트) / 8501(스트림릿) 개별 핀셋 부활
echo   - 다른 정상 서버는 절대 종료하지 않음 (무충돌 보장)
echo ========================================================

echo [*] 초기 서버 부팅 완료 대기 중 (20초)...
ping 127.0.0.1 -n 20 > nul

:LOOP
ping 127.0.0.1 -n 6 > nul

:: 1. 8000번 포트 (FastAPI Backend) LISTENING 및 HTTP 응답 점검
set "BACKEND_OK=0"
netstat -ano -p tcp | findstr "LISTENING" | findstr ":8000" > nul 2>&1
if %errorlevel% equ 0 (
    curl.exe -s -m 5 -o nul http://127.0.0.1:8000/ > nul 2>&1
    if %errorlevel% equ 0 set "BACKEND_OK=1"
)
if "%BACKEND_OK%"=="0" (
    echo [%date% %time%] 8000번 백엔드 이상 감지 (다운 또는 무응답 Hang)! FastAPI 개별 부활 기동...
    taskkill /f /fi "WINDOWTITLE eq JPRO_FastAPI_*" > nul 2>&1
    for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":8000"') do (
        taskkill /f /t /pid %%a > nul 2>&1
    )
    start "JPRO_FastAPI_8000" cmd.exe /c "cd /d "%~dp0" & .venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload --timeout-graceful-shutdown 1"
    ping 127.0.0.1 -n 10 > nul
)

:: 2. 3000번 포트 (React Frontend) LISTENING 및 HTTP 응답 점검
set "FRONTEND_OK=0"
netstat -ano -p tcp | findstr "LISTENING" | findstr ":3000" > nul 2>&1
if %errorlevel% equ 0 (
    curl.exe -s -m 5 -o nul http://127.0.0.1:3000/ > nul 2>&1
    if %errorlevel% equ 0 set "FRONTEND_OK=1"
)
if "%FRONTEND_OK%"=="0" (
    echo [%date% %time%] 3000번 프론트엔드 이상 감지 (다운 또는 무응답 Hang)! Frontend 개별 부활 기동...
    taskkill /f /fi "WINDOWTITLE eq JPRO_Frontend_*" > nul 2>&1
    for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":3000"') do (
        taskkill /f /t /pid %%a > nul 2>&1
    )
    start "JPRO_Frontend_3000" cmd.exe /c "cd /d "%~dp0frontend" & npm run dev -- --host 0.0.0.0"
    ping 127.0.0.1 -n 10 > nul
)

:: 3. 8501번 포트 (Streamlit Dashboard) LISTENING 및 HTTP 응답 점검
set "STREAMLIT_OK=0"
netstat -ano -p tcp | findstr "LISTENING" | findstr ":8501" > nul 2>&1
if %errorlevel% equ 0 (
    curl.exe -s -m 5 -o nul http://127.0.0.1:8501/_stcore/health > nul 2>&1
    if %errorlevel% equ 0 set "STREAMLIT_OK=1"
)
if "%STREAMLIT_OK%"=="0" (
    echo [%date% %time%] 8501번 스트림릿 이상 감지 (다운 또는 무응답 Hang)! Streamlit 개별 부활 기동...
    taskkill /f /fi "WINDOWTITLE eq JPRO_Streamlit_*" > nul 2>&1
    for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":8501"') do (
        taskkill /f /t /pid %%a > nul 2>&1
    )
    start "JPRO_Streamlit_8501" cmd.exe /c "cd /d "%~dp0" & .venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false"
    ping 127.0.0.1 -n 10 > nul
)

goto LOOP
