@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title JPRO_Watchdog

REM Node.js 공식 경로 최우선 설정 (run_all.bat와 100% 대칭 유지)
if exist "%LOCALAPPDATA%\Programs\nodejs" (
    set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%"
)
if exist "C:\Program Files\nodejs" (
    set "PATH=C:\Program Files\nodejs;%PATH%"
)

REM 0. 워치도그 중복 실행 원천 차단 (락 파일 점유 검사)
(type nul > "%~dp0watchdog.lock") 2>nul
if errorlevel 1 (
    echo [%date% %time%] 이미 다른 JPRO_Watchdog 인스턴스가 실행 중입니다. 중복 기동 방지를 위해 종료합니다.
    exit /b 0
)

(
    echo ========================================================
    echo   [J-PRO] 24시간 무인 자동 부활 감시자 [Watchdog]
    echo   - 8000[백엔드] / 3000[프론트] / 8501[스트림릿] 개별 핀셋 부활
    echo   - 연속 3회 점검 실패 시에만 부활 및 포트 실측 해제 후 기동
    echo   - 다른 정상 서버는 절대 종료하지 않음 [무충돌 보장]
    echo ========================================================

    echo [*] 초기 서버 부팅 대기 중 [60초]...
    ping 127.0.0.1 -n 61 > nul

    set "FAIL_8000=0"
    set "FAIL_3000=0"
    set "FAIL_8501=0"

    :LOOP
    ping 127.0.0.1 -n 6 > nul

    :: 1. 8000번 포트 (FastAPI Backend) LISTENING 및 HTTP 응답 점검
    set "BACKEND_OK=0"
    netstat -ano -p tcp | findstr "LISTENING" | findstr ":8000" > nul 2>&1
    if not errorlevel 1 (
        curl.exe -s -m 5 -o nul http://127.0.0.1:8000/api/health > nul 2>&1
        if not errorlevel 1 set "BACKEND_OK=1"
    )
    if "!BACKEND_OK!"=="1" (
        set "FAIL_8000=0"
    ) else (
        set /a FAIL_8000+=1
        echo [%date% %time%] 8000번 백엔드 점검 실패 !FAIL_8000!/3회
        if !FAIL_8000! geq 3 (
            echo [%date% %time%] 8000번 백엔드 3회 연속 실패 감지. 포트 LISTENING PID 강제 종료...
            for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":8000"') do (
                taskkill /f /t /pid %%a > nul 2>&1
            )
            ping 127.0.0.1 -n 3 > nul
            set "PORT_8000_BUSY=0"
            netstat -ano -p tcp | findstr "LISTENING" | findstr ":8000" > nul 2>&1
            if not errorlevel 1 set "PORT_8000_BUSY=1"
            if "!PORT_8000_BUSY!"=="1" (
                echo [%date% %time%] [경고] 8000번 포트 프로세스 종료 실패로 포트가 비지 않음. 기동 중단.
            ) else (
                echo [%date% %time%] 8000번 포트 해제 확인 완료. FastAPI 개별 부활 기동...
                start "JPRO_FastAPI_8000" cmd.exe /c "cd /d "%~dp0" & .venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload --timeout-graceful-shutdown 1"
                set "FAIL_8000=0"
                ping 127.0.0.1 -n 10 > nul
            )
        )
    )

    :: 2. 3000번 포트 (React Frontend) LISTENING 및 HTTP 응답 점검
    set "FRONTEND_OK=0"
    netstat -ano -p tcp | findstr "LISTENING" | findstr ":3000" > nul 2>&1
    if not errorlevel 1 (
        curl.exe -s -m 5 -o nul http://127.0.0.1:3000/ > nul 2>&1
        if not errorlevel 1 set "FRONTEND_OK=1"
    )
    if "!FRONTEND_OK!"=="1" (
        set "FAIL_3000=0"
    ) else (
        set /a FAIL_3000+=1
        echo [%date% %time%] 3000번 프론트엔드 점검 실패 !FAIL_3000!/3회
        if !FAIL_3000! geq 3 (
            echo [%date% %time%] 3000번 프론트엔드 3회 연속 실패 감지. 포트 LISTENING PID 강제 종료...
            for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":3000"') do (
                taskkill /f /t /pid %%a > nul 2>&1
            )
            ping 127.0.0.1 -n 3 > nul
            set "PORT_3000_BUSY=0"
            netstat -ano -p tcp | findstr "LISTENING" | findstr ":3000" > nul 2>&1
            if not errorlevel 1 set "PORT_3000_BUSY=1"
            if "!PORT_3000_BUSY!"=="1" (
                echo [%date% %time%] [경고] 3000번 포트 프로세스 종료 실패로 포트가 비지 않음. 기동 중단.
            ) else (
                echo [%date% %time%] 3000번 포트 해제 확인 완료. Frontend 개별 부활 기동...
                start "JPRO_Frontend_3000" cmd.exe /c "cd /d "%~dp0frontend" & npm run dev -- --host 0.0.0.0"
                set "FAIL_3000=0"
                ping 127.0.0.1 -n 10 > nul
            )
        )
    )

    :: 3. 8501번 포트 (Streamlit Dashboard) LISTENING 및 HTTP 응답 점검
    set "STREAMLIT_OK=0"
    netstat -ano -p tcp | findstr "LISTENING" | findstr ":8501" > nul 2>&1
    if not errorlevel 1 (
        curl.exe -s -m 5 -o nul http://127.0.0.1:8501/_stcore/health > nul 2>&1
        if not errorlevel 1 set "STREAMLIT_OK=1"
    )
    if "!STREAMLIT_OK!"=="1" (
        set "FAIL_8501=0"
    ) else (
        set /a FAIL_8501+=1
        echo [%date% %time%] 8501번 스트림릿 점검 실패 !FAIL_8501!/3회
        if !FAIL_8501! geq 3 (
            echo [%date% %time%] 8501번 스트림릿 3회 연속 실패 감지. 포트 LISTENING PID 강제 종료...
            for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":8501"') do (
                taskkill /f /t /pid %%a > nul 2>&1
            )
            ping 127.0.0.1 -n 3 > nul
            set "PORT_8501_BUSY=0"
            netstat -ano -p tcp | findstr "LISTENING" | findstr ":8501" > nul 2>&1
            if not errorlevel 1 set "PORT_8501_BUSY=1"
            if "!PORT_8501_BUSY!"=="1" (
                echo [%date% %time%] [경고] 8501번 포트 프로세스 종료 실패로 포트가 비지 않음. 기동 중단.
            ) else (
                echo [%date% %time%] 8501번 포트 해제 확인 완료. Streamlit 개별 부활 기동...
                start "JPRO_Streamlit_8501" cmd.exe /c "cd /d "%~dp0" & .venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --browser.gatherUsageStats false"
                set "FAIL_8501=0"
                ping 127.0.0.1 -n 10 > nul
            )
        )
    )

    goto LOOP
) 9>"%~dp0watchdog.lock"
