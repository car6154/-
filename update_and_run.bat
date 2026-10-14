@echo off
setlocal
cd /d "%~dp0"
title J-PRO Auto Updater & Launcher

echo ========================================================
echo   [J-PRO] 최신 코드 업데이트 및 통합 서버 재시작
echo ========================================================
echo.

echo 1. 기존 서버 프로세스 종료 중...
taskkill /f /im node.exe > nul 2>&1
taskkill /f /im streamlit.exe > nul 2>&1

echo 2. GitHub 최신 코드 다운로드 중 (git pull)...
git fetch origin main
git reset --hard origin/main

echo.
echo 3. 서버 재시작...
call "%~dp0run_all.bat"
