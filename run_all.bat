@echo off
setlocal
cd /d "%~dp0"
title J-PRO Integrated Launcher

REM Node.js 공식 경로 최우선 설정 (Antigravity IDE 임시 경로 충돌 방지)
if exist "%LOCALAPPDATA%\Programs\nodejs" (
    set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%"
)

echo ========================================================
echo   [J-PRO] 3 Servers Integrated Launcher
echo   - Port 8000 : FastAPI Backend
echo   - Port 3000 : React Frontend Web
echo   - Port 8501 : Streamlit Dashboard
echo ========================================================

REM 1. Port 8000 FastAPI Backend
start "JPRO_FastAPI_8000" cmd.exe /k "cd /d "%~dp0" & .venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000"

REM 2. Port 3000 Frontend Dev Server
start "JPRO_Frontend_3000" cmd.exe /k "cd /d "%~dp0frontend" & set "PATH=%LOCALAPPDATA%\Programs\nodejs;%%PATH%%" & npm run dev"

REM 3. Port 8501 Streamlit Dashboard
start "JPRO_Streamlit_8501" cmd.exe /k "cd /d "%~dp0" & .venv\Scripts\streamlit.exe run app.py --server.port 8501"

echo.
echo All server windows have been launched successfully.
ping 127.0.0.1 -n 3 > nul
