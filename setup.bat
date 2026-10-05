@echo off
chcp 65001 > nul
title J-PRO 최초 환경 자동 설치기 (사무실 노트북용)
echo ========================================================
echo   [J-PRO] 사무실 노트북 최초 자동 설정을 시작합니다.
echo   - 파이썬 가상환경 생성 (.venv)
echo   - 필수 라이브러리 일괄 설치 (requirements.txt)
echo   - 웹 화면 구성요소 설치 (npm install)
echo ========================================================

echo [1/3] 파이썬 가상환경(.venv) 생성 중...
python -m venv .venv
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되어 있지 않거나 경로에 등록되지 않았습니다. Python 3.10 이상을 먼저 설치해주세요.
    pause
    exit /b
)

echo [2/3] 필수 파이썬 패키지 일괄 설치 중...
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt

echo [3/3] 프론트엔드 웹 패키지 설치 중...
cd frontend
call npm install
cd ..

echo ========================================================
echo   ✅ 모든 설치와 세팅이 완벽하게 끝났습니다!
echo   이제 [run_all.bat]을 더블클릭하시면 바로 실행됩니다.
echo ========================================================
pause
