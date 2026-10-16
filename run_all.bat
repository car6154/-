@echo off
setlocal
cd /d "%~dp0"
title J-PRO Integrated Launcher

:: 1. 관리자 권한 확인 및 자동 승격 (포트 해제 및 프로세스 종료 액세스 거부 원천 방지)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [J-PRO] 관리자 권한으로 자동 승격 실행 중...
    powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

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

REM -0. 잔여 백그라운드 / 감시자 프로세스(python, node) 일괄 완전 종료
taskkill /f /im python.exe > nul 2>&1
taskkill /f /im node.exe > nul 2>&1

REM -1. 기존 포트 8000, 3000, 8501, 8502 점유 프로세스(PID) 강제 확인사살
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":8000 :3000 :8501 :8502"') do (
    taskkill /f /t /pid %%a > nul 2>&1
)

REM -2. 기존 잔여 서버 콘솔 창 닫기 (자기 자신 Launcher 창은 보호)
taskkill /f /fi "WINDOWTITLE eq JPRO_FastAPI_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Frontend_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Streamlit_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Shopping_Web_6154*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq AI_Shopping_Bot*" > nul 2>&1
ping 127.0.0.1 -n 2 > nul

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

REM 4. 쇼핑봇 자동 연동 가동 (C:\ai_shopping_bot\run_web.bat 존재 시 동시 가동)
if exist "C:\ai_shopping_bot\run_web.bat" (
    echo [*] ai_shopping_bot 동시 가동 중...
    start "Shopping_Web_6154" cmd.exe /c "cd /d C:\ai_shopping_bot & run_web.bat"
)

echo [3/3] 서버 가동 완료. 런처 창을 닫습니다.
ping 127.0.0.1 -n 3 > nul
exit
