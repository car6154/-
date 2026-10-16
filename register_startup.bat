@echo off
setlocal
cd /d "%~dp0"
title J-PRO Register Startup

set "TARGET_BAT=C:\jpro\run_all.bat"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_VBS=%TEMP%\CreateShortcut.vbs"

echo ========================================================
echo   [J-PRO] 윈도우 부팅 시 자동 시작 등록
echo   - 노트북 전원만 켜지면 전체 서버가 자동으로 가동됩니다.
echo ========================================================
echo.

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%SHORTCUT_VBS%"
echo sLinkFile = "%STARTUP_FOLDER%\JPRO_AutoStart.lnk" >> "%SHORTCUT_VBS%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%SHORTCUT_VBS%"
echo oLink.TargetPath = "%TARGET_BAT%" >> "%SHORTCUT_VBS%"
echo oLink.WorkingDirectory = "C:\jpro" >> "%SHORTCUT_VBS%"
echo oLink.WindowStyle = 1 >> "%SHORTCUT_VBS%"
echo oLink.Description = "J-PRO Auto Launcher on Windows Startup" >> "%SHORTCUT_VBS%"
echo oLink.Save >> "%SHORTCUT_VBS%"

cscript /nologo "%SHORTCUT_VBS%"
del "%SHORTCUT_VBS%" > nul 2>&1

echo [성공] 윈도우 부팅 시 자동 실행 등록이 완료되었습니다!
echo 등록 위치: %STARTUP_FOLDER%\JPRO_AutoStart.lnk
echo.
ping 127.0.0.1 -n 3 > nul
exit
