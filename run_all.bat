@echo off
setlocal
cd /d "%~dp0"
title J-PRO Integrated Launcher

REM Node.js 공식 경로 최우선 설정 (Antigravity IDE 임시 경로 충돌 방지 및 표준 설치 경로 지원)
if exist "%LOCALAPPDATA%\Programs\nodejs" (
    set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%"
)
if exist "C:\Program Files\nodejs" (
    set "PATH=C:\Program Files\nodejs;%PATH%"
)

echo ========================================================
echo   [J-PRO] 3 Servers Integrated Launcher
echo   - Port 8000 : FastAPI Backend (0.0.0.0)
echo   - Port 3000 : React Frontend Web (0.0.0.0)
echo   - Port 8501 : Streamlit Dashboard (0.0.0.0)
echo ========================================================

REM -1. 기존 J-PRO 서버 창 안전 종료 (중복 실행 방지)
taskkill /f /fi "WINDOWTITLE eq JPRO_FastAPI_8000*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Frontend_3000*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Streamlit_8501*" > nul 2>&1
timeout /t 2 /nobreak > nul

REM 0. Tailscale 수신 파일(다운로드 폴더) 자동 배치
if exist "%USERPROFILE%\Downloads\firebase-applet-config.json" (
    move /y "%USERPROFILE%\Downloads\firebase-applet-config.json" "%~dp0frontend\firebase-applet-config.json" > nul 2>&1
    echo [OK] firebase-applet-config.json 배치 완료
)
if exist "%USERPROFILE%\Downloads\.env" (
    move /y "%USERPROFILE%\Downloads\.env" "%~dp0.env" > nul 2>&1
    echo [OK] .env 배치 완료
)
if exist "%USERPROFILE%\Downloads\autoplus_cookie.txt" (
    move /y "%USERPROFILE%\Downloads\autoplus_cookie.txt" "%~dp0autoplus_cookie.txt" > nul 2>&1
    echo [OK] autoplus_cookie.txt 배치 완료
)

REM 1. Port 8000 FastAPI Backend (외부 접속 0.0.0.0 허용 및 소스 변경 자동 리로드)
start "JPRO_FastAPI_8000" cmd.exe /k "cd /d "%~dp0" & .venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload"

REM 2. Port 3000 Frontend Dev Server (외부 접속 0.0.0.0 허용)
start "JPRO_Frontend_3000" cmd.exe /k "cd /d "%~dp0frontend" & npm run dev -- --host 0.0.0.0"

REM 3. Port 8501 Streamlit Dashboard (외부 접속 0.0.0.0 및 이메일 프롬프트 스킵)
start "JPRO_Streamlit_8501" cmd.exe /k "cd /d "%~dp0" & .venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false"

echo.
echo All server windows have been launched successfully.
ping 127.0.0.1 -n 3 > nul
