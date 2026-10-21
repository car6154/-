@echo off
setlocal
cd /d "%~dp0"
title J-PRO Register Guard Watchdog

echo ========================================================
echo   [J-PRO] 24시간 무인 가드 스케줄러 등록 및 절전 방지 설정
echo   - 윈도우 스케줄러(schtasks) 등록: 로그온 시 1회 + 1분 주기 무기한 반복
echo   - AC 전원 시 절전/최대절전 해제 (powercfg)
echo   * 안내: powercfg 및 schtasks의 시스템 수준 등록을 위해 관리자 권한 실행 권장
echo ========================================================
echo.

:: 1. AC 전원 시 절전 및 최대절전 비활성화 (서버 노트북 상시 가동 보장)
echo [*] AC 전원 연결 시 절전 및 최대절전 모드 해제 중...
powercfg /change standby-timeout-ac 0 > nul 2>&1
powercfg /change hibernate-timeout-ac 0 > nul 2>&1
powercfg /change monitor-timeout-ac 15 > nul 2>&1
echo [OK] 절전 모드 해제 완료 (대기시간 0분 설정)

:: 2. 대상 가드 배치 파일 경로 확정
set "GUARD_BAT=%~dp0guard_watchdog.bat"
if not exist "%GUARD_BAT%" (
    set "GUARD_BAT=C:\jpro\guard_watchdog.bat"
)

:: 3. schtasks (a) 로그온 시 1회 실행 작업 등록
echo [*] 윈도우 로그온 시 자동 가드 작업 등록 중...
schtasks /create /tn "JPRO_Guard_Logon" /tr "\"%GUARD_BAT%\"" /sc onlogon /rl highest /f > nul 2>&1
if %errorlevel% neq 0 (
    schtasks /create /tn "JPRO_Guard_Logon" /tr "\"%GUARD_BAT%\"" /sc onlogon /f > nul 2>&1
)

:: 4. schtasks (b) 1분 간격 무기한 반복 작업 등록
echo [*] 1분 간격 무기한 반복 가드 작업 등록 중...
schtasks /create /tn "JPRO_Guard_5Min" /tr "\"%GUARD_BAT%\"" /sc minute /mo 1 /rl highest /f > nul 2>&1
if %errorlevel% neq 0 (
    schtasks /create /tn "JPRO_Guard_5Min" /tr "\"%GUARD_BAT%\"" /sc minute /mo 1 /f > nul 2>&1
)

:: 5. 즉시 1회 가드 실행하여 현재 감시자 가동 보장
echo [*] 가드 즉시 1회 기동...
call "%GUARD_BAT%"

echo.
echo ========================================================
echo   [성공] J-PRO 무인 복구 가드 등록이 완료되었습니다!
echo   - 작업 1: JPRO_Guard_Logon (로그온 시 즉시 가동)
echo   - 작업 2: JPRO_Guard_5Min (1분마다 감시자 생존 확인 및 부활)
echo   - 전원: AC 전원 연결 시 절전 모드 자동 차단
echo ========================================================
ping 127.0.0.1 -n 3 > nul
exit /b 0
