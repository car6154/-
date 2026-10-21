@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion
title JPRO_Server_Cleanup

REM ========================================================
REM   1. 자기 보호 [jpro 서버 머신 외 실행 절대 금지]
REM ========================================================
if /i not "%COMPUTERNAME%"=="jpro" (
    echo [차단] 이 PC에서는 실행할 수 없습니다. 호스트명: %COMPUTERNAME%
    echo 이 스크립트는 실제 서버 [jpro] 전용 정리 도구입니다.
    pause
    exit /b 1
)

REM ========================================================
REM   2. 관리자 권한 자동 승격 [더블클릭 실행 지원]
REM ========================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 관리자 권한으로 자동 승격 실행 중...
    powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c', '\"\"%~f0\"\"' -Verb RunAs"
    exit /b 0
)

cd /d "%~dp0"

echo ========================================================
echo   [J-PRO] 서버 감시 체계 및 프로세스 전면 제거 도구
echo   - 대상 머신: jpro [확인 완료]
echo   - schtasks 등록 작업 삭제, 시작 프로그램 제거, 프로세스/포트 전면 종료
echo ========================================================
echo.

REM ========================================================
REM   3. 자동 실행 등록 제거 [schtasks 및 시작 프로그램]
REM ========================================================
echo [1/3] 자동 실행 등록 제거 중...

schtasks /delete /tn "JPRO_Guard_Logon" /f > nul 2>&1
if errorlevel 1 (
    echo   - JPRO_Guard_Logon: 미등록 상태 또는 삭제 완료
) else (
    echo   - JPRO_Guard_Logon: 작업 삭제 완료
)

schtasks /delete /tn "JPRO_Guard_5Min" /f > nul 2>&1
if errorlevel 1 (
    echo   - JPRO_Guard_5Min: 미등록 상태 또는 삭제 완료
) else (
    echo   - JPRO_Guard_5Min: 작업 삭제 완료
)

set "STARTUP_LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\JPRO_AutoStart.lnk"
if exist "%STARTUP_LNK%" (
    del /f /q "%STARTUP_LNK%" > nul 2>&1
    echo   - 시작 프로그램 바로가기 JPRO_AutoStart.lnk 삭제 완료
) else (
    echo   - 시작 프로그램 바로가기 JPRO_AutoStart.lnk 없음 [정상]
)

REM ========================================================
REM   4. 프로세스 및 포트[8000, 3000, 8501, 8502] 전면 종료
REM ========================================================
echo.
echo [2/3] 가동 중 프로세스 및 포트 점유 전면 종료 중...

REM (1) 창 제목 기준 콘솔 창 닫기
taskkill /f /fi "WINDOWTITLE eq JPRO_Watchdog*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Guard_Watchdog*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_FastAPI_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Frontend_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq JPRO_Streamlit_*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Shopping_Web_6154*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq AI_Shopping_Bot*" > nul 2>&1
taskkill /f /fi "WINDOWTITLE eq *Integrated Launcher*" > nul 2>&1

REM (2) 백그라운드 프로세스 전면 종료
taskkill /f /im python.exe > nul 2>&1
taskkill /f /im node.exe > nul 2>&1

REM (3) 8000, 3000, 8501, 8502 포트 점유 PID 강제 종료
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr "LISTENING" ^| findstr ":8000 :3000 :8501 :8502"') do (
    taskkill /f /t /pid %%a > nul 2>&1
)

REM (4) 잔여 락 파일 정리
if exist "%~dp0watchdog.lock" del /f /q "%~dp0watchdog.lock" > nul 2>&1
if exist "%~dp0guard.lock" del /f /q "%~dp0guard.lock" > nul 2>&1

echo   - 프로세스 및 포트 종료 명령 전달 완료.

REM ========================================================
REM   5. 검증: 120초 대기 후 잔존/부활 여부 전수 실측
REM ========================================================
echo.
echo [3/3] 종료 후 부활 여부 실측 검증 대기 중 [120초]...
ping 127.0.0.1 -n 121 > nul

echo.
echo ========================================================
echo   [검증 결과 보고서]
echo ========================================================

REM 5-1. 포트 LISTENING 잔존 여부 확인
echo [*] 포트 LISTENING 상태 점검:
set "PORT_8000_FOUND=0"
set "PORT_3000_FOUND=0"
set "PORT_8501_FOUND=0"
set "PORT_8502_FOUND=0"

netstat -ano -p tcp | findstr "LISTENING" | findstr ":8000" > nul 2>&1
if not errorlevel 1 set "PORT_8000_FOUND=1"

netstat -ano -p tcp | findstr "LISTENING" | findstr ":3000" > nul 2>&1
if not errorlevel 1 set "PORT_3000_FOUND=1"

netstat -ano -p tcp | findstr "LISTENING" | findstr ":8501" > nul 2>&1
if not errorlevel 1 set "PORT_8501_FOUND=1"

netstat -ano -p tcp | findstr "LISTENING" | findstr ":8502" > nul 2>&1
if not errorlevel 1 set "PORT_8502_FOUND=1"

if "!PORT_8000_FOUND!"=="1" (
    echo   - Port 8000 [FastAPI]: [경고] 여전히 LISTENING 중
) else (
    echo   - Port 8000 [FastAPI]: [정상] 비어있음
)

if "!PORT_3000_FOUND!"=="1" (
    echo   - Port 3000 [Frontend]: [경고] 여전히 LISTENING 중
) else (
    echo   - Port 3000 [Frontend]: [정상] 비어있음
)

if "!PORT_8501_FOUND!"=="1" (
    echo   - Port 8501 [Streamlit]: [경고] 여전히 LISTENING 중
) else (
    echo   - Port 8501 [Streamlit]: [정상] 비어있음
)

if "!PORT_8502_FOUND!"=="1" (
    echo   - Port 8502 [쇼핑봇]: [경고] 여전히 LISTENING 중
) else (
    echo   - Port 8502 [쇼핑봇]: [정상] 비어있음
)

REM 5-2. 작업 스케줄러 JPRO 작업 잔존 여부 확인
echo.
echo [*] 작업 스케줄러 [schtasks] JPRO 잔존 작업 점검:
schtasks /query /fo table 2>nul | findstr /i "JPRO" > nul 2>&1
if not errorlevel 1 (
    echo   [경고] schtasks에 잔존 JPRO 작업이 발견되었습니다:
    schtasks /query /fo table 2>nul | findstr /i "JPRO"
) else (
    echo   - JPRO 관련 등록 작업: 0건 [완전 제거 확인]
)

REM 5-3. JPRO 관련 창 잔존 여부 확인
echo.
echo [*] JPRO 관련 프로세스/창 잔존 점검:
tasklist /fi "WINDOWTITLE eq JPRO_*" 2>nul | findstr /i "cmd.exe" > nul 2>&1
if not errorlevel 1 (
    echo   [경고] JPRO 관련 창이 여전히 실행 중입니다:
    tasklist /fi "WINDOWTITLE eq JPRO_*" 2>nul
) else (
    echo   - JPRO 관련 창: 0개 [완전 종료 확인]
)

echo.
echo ========================================================
echo   정리 및 검증이 완료되었습니다. 창을 닫으려면 아무 키나 누르세요.
echo ========================================================
pause
exit /b 0
