@echo off
setlocal EnableDelayedExpansion
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

REM 00. 재기동 도중 Watchdog 오폭(중복 실행 팀킬) 방지를 위해 기존 Watchdog 최우선 종료
taskkill /f /fi "WINDOWTITLE eq JPRO_Watchdog*" > nul 2>&1

echo [0/3] GitHub 최신 코드 동기화 중...
git stash push -u -m "auto-stash" > nul 2>&1
git fetch origin main > nul 2>&1
git merge --ff-only origin/main > nul 2>&1
if %errorlevel% neq 0 (
    echo [경고] 로컬 변경사항으로 인해 최신 코드 병합에 실패했습니다.
    echo [경고] 로컬 작업을 복원하고 기존 코드로 서버를 가동합니다.
    git stash pop > nul 2>&1
) else (
    git stash pop > nul 2>&1
)

echo [1/3] 기존 서버 프로세스 및 포트[8000, 3000, 8501] 완전 정리 중...

REM -0. 잔여 감시자 및 백그라운드 프로세스 일괄 완전 종료
taskkill /f /fi "WINDOWTITLE eq JPRO_Watchdog*" > nul 2>&1
taskkill /f /im python.exe > nul 2>&1
taskkill /f /im node.exe > nul 2>&1

REM -1. 기존 포트 8000, 3000, 8501, 8502 점유 프로세스[PID] 강제 종료
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":8000 :3000 :8501 :8502"') do (
    taskkill /f /t /pid %%a > nul 2>&1
)

REM -2. 기존 잔여 서버 콘솔 창 닫기 [자기 자신 Launcher 창은 보호]
taskkill /f /fi "WINDOWTITLE eq JPRO_FastAPI_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Frontend_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Streamlit_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Shopping_Web_6154*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq AI_Shopping_Bot*" > nul 2>&1
ping 127.0.0.1 -n 3 > nul

REM -3. 포트 잔여 PID 재확인 및 2차 강제 종료
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":8000 :3000 :8501"') do (
    taskkill /f /t /pid %%a > nul 2>&1
)
ping 127.0.0.1 -n 2 > nul

REM -4. 세 포트[8000, 3000, 8501] 완전 해제 여부 검증
set "PORTS_CLEAR=1"

netstat -ano -p tcp | findstr "LISTENING" | findstr ":8000" > nul 2>&1
if not errorlevel 1 (
    echo [경고] 8000번 포트 프로세스 종료 실패 - 포트가 여전히 점유 중입니다.
    set "PORTS_CLEAR=0"
)

netstat -ano -p tcp | findstr "LISTENING" | findstr ":3000" > nul 2>&1
if not errorlevel 1 (
    echo [경고] 3000번 포트 프로세스 종료 실패 - 포트가 여전히 점유 중입니다.
    set "PORTS_CLEAR=0"
)

netstat -ano -p tcp | findstr "LISTENING" | findstr ":8501" > nul 2>&1
if not errorlevel 1 (
    echo [경고] 8501번 포트 프로세스 종료 실패 - 포트가 여전히 점유 중입니다.
    set "PORTS_CLEAR=0"
)

if "!PORTS_CLEAR!"=="0" (
    echo.
    echo ========================================================
    echo   [치명적 오류] 기존 포트 정리에 실패하여 기동을 중단합니다.
    echo   중복 기동 방지를 위해 신규 서버를 띄우지 않습니다.
    echo ========================================================
    exit /b 1
)
echo [OK] 8000, 3000, 8501 세 포트 모두 정상 해제 확인 완료.

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

REM 1. Port 8000 FastAPI Backend (외부 접속 0.0.0.0 허용 및 소스 변경 자동 리로드, 셧다운 행 방지)
start "JPRO_FastAPI_8000" cmd.exe /c "cd /d "%~dp0" & .venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload --timeout-graceful-shutdown 1"

REM 2. Port 3000 Frontend Dev Server (외부 접속 0.0.0.0 허용)
start "JPRO_Frontend_3000" cmd.exe /c "cd /d "%~dp0frontend" & npm run dev -- --host 0.0.0.0"

REM 3. Port 8501 Streamlit Dashboard (외부 접속 0.0.0.0 및 이메일 프롬프트 스킵)
start "JPRO_Streamlit_8501" cmd.exe /c "cd /d "%~dp0" & .venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false"

REM 4. 쇼핑봇 자동 연동 가동 (C:\ai_shopping_bot\run_web.bat 존재 시 동시 가동)
if exist "C:\ai_shopping_bot\run_web.bat" (
    echo [*] ai_shopping_bot 동시 가동 중...
    start "Shopping_Web_6154" cmd.exe /c "cd /d C:\ai_shopping_bot & run_web.bat"
)

REM 5. 24시간 무인 자동 부활 감시자 (Watchdog) 가동
set "WD_ACTIVE=0"
(type nul > "%~dp0watchdog.lock") 2>nul
if errorlevel 1 set "WD_ACTIVE=1"
tasklist /fi "WINDOWTITLE eq JPRO_Watchdog*" 2>nul | findstr /i "cmd.exe" > nul 2>&1
if not errorlevel 1 set "WD_ACTIVE=1"

if "!WD_ACTIVE!"=="0" (
    echo [*] 24시간 자동 부활 감시자 가동 중...
    start "JPRO_Watchdog" /min cmd.exe /c "cd /d "%~dp0" & watchdog.bat"
) else (
    echo [*] 24시간 자동 부활 감시자가 이미 정상 가동 중입니다.
)

echo [3/3] 서버 가동 완료. 런처 창을 닫습니다.
ping 127.0.0.1 -n 3 > nul
exit
