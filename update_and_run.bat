@echo off
setlocal
cd /d "%~dp0"
title J-PRO Auto Updater & Launcher

:: 1. 관리자 권한 확인 및 자동 승격
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [J-PRO] 관리자 권한으로 자동 승격 실행 중...
    powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

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
    echo [경고] 로컬 변경사항으로 인해 최신 코드 병합에 실패했습니다.
    echo [경고] 로컬 작업을 복원하고 기존 코드로 서버를 가동합니다.
    git stash pop > nul 2>&1
) else (
    git stash pop > nul 2>&1
)

echo.
echo 3. 서버 재시작...
call "%~dp0run_all.bat"
