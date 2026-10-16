@echo off
setlocal
cd /d "%~dp0"
title J-PRO Unregister Startup

set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\JPRO_AutoStart.lnk"

echo ========================================================
echo   [J-PRO] 윈도우 부팅 시 자동 시작 해제
echo ========================================================
echo.

if exist "%SHORTCUT_PATH%" (
    del /f /q "%SHORTCUT_PATH%" > nul 2>&1
    echo [성공] 윈도우 시작 프로그램에서 J-PRO가 제거되었습니다.
) else (
    echo [안내] 등록된 시작 프로그램 바로가기가 없습니다.
)

echo.
ping 127.0.0.1 -n 3 > nul
exit
