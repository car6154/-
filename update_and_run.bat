@echo off
setlocal
cd /d "%~dp0"
title J-PRO Auto Updater & Launcher

echo ========================================================
echo   [J-PRO] 최신 코드 업데이트 및 통합 서버 재시작
echo ========================================================
echo.

echo 1. 기존 서버 프로세스 종료 중...
taskkill /f /im python.exe > nul 2>&1
taskkill /f /im node.exe > nul 2>&1
taskkill /f /im streamlit.exe > nul 2>&1

echo 2. GitHub 최신 코드 다운로드 중 (git pull)...
git stash push -u -m "auto-stash" > nul 2>&1
git fetch origin main > nul 2>&1
git merge --ff-only origin/main > nul 2>&1
if %errorlevel% neq 0 (
    echo [경고] 로컬 변경사항으로 인해 최신 코드 병합(ff-only)에 실패했습니다.
    echo [경고] 로컬 작업을 복원하고 실행을 중단합니다.
    git stash pop > nul 2>&1
    exit /b 1
)
git stash pop > nul 2>&1

echo.
echo 3. 서버 재시작...
call "%~dp0run_all.bat"
