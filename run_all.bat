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

echo [0/3] GitHub 최신 코드 동기화 중...
git fetch origin main > nul 2>&1
git reset --hard origin/main > nul 2>&1

echo [1/3] 기존 서버 프로세스 및 포트(8000, 3000, 8501) 완전 정리 중...

REM -1. 기존 포트 8000, 3000, 8501 점유 프로세스(PID) 강제 종료
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr ":8000 "') do (
    taskkill /f /pid %%a > nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr ":3000 "') do (
    taskkill /f /pid %%a > nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr ":8501 "') do (
    taskkill /f /pid %%a > nul 2>&1
)

REM -2. 기존 잔여 JPRO 창 및 콘솔 안전 종료 (중복 창 방지)
taskkill /f /fi "WINDOWTITLE eq JPRO_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *JPRO*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *FastAPI*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *Streamlit*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *Integrated Launcher*" > nul 2>&1
timeout /t 1 /nobreak > nul

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

echo [2/3] 3대 서버 신규 가동 중...

REM 1. Port 8000 FastAPI Backend (외부 접속 0.0.0.0 허용 및 소스 변경 자동 리로드)
start "JPRO_FastAPI_8000" cmd.exe /c "cd /d "%~dp0" & .venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload"

REM 2. Port 3000 Frontend Dev Server (외부 접속 0.0.0.0 허용)
start "JPRO_Frontend_3000" cmd.exe /c "cd /d "%~dp0frontend" & npm run dev -- --host 0.0.0.0"

REM 3. Port 8501 Streamlit Dashboard (외부 접속 0.0.0.0 및 이메일 프롬프트 스킵)
start "JPRO_Streamlit_8501" cmd.exe /c "cd /d "%~dp0" & .venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false"

echo [3/3] 3대 서버 가동 완료. 런처 창을 닫습니다.
timeout /t 2 /nobreak > nul
exit
