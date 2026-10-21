@echo off
setlocal
cd /d "%~dp0"
title J-PRO Clean Termination

echo ========================================================
echo   [J-PRO] Unified Supervisor Stop Request
echo ========================================================

echo [*] Requesting supervisor shutdown via supervisor.stop...
echo stop > "%~dp0supervisor.stop"

echo [*] supervisor.stop created.
echo [*] Supervisor will terminate all child services and exit cleanly.
exit /b 0
