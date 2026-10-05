@echo off
chcp 65001 > nul
title J-PRO Integrated Launcher (3000 / 8000 / 8501)
echo ========================================================
echo   [J-PRO] 3개 서버를 동시에 실행합니다.
echo   - Port 3000 : React / Express 웹 UI
echo   - Port 8000 : FastAPI 백엔드 (장부, 차얼마, 엔카 파이프라인)
echo   - Port 8501 : Streamlit 분석 대시보드
echo ========================================================

:: 1. Port 8000 (FastAPI Backend)
start "J-PRO [8000] FastAPI Backend" cmd /k "chcp 65001 > nul && .venv\Scripts\python -m uvicorn api_server:app --host 127.0.0.1 --port 8000"

:: 2. Port 3000 (Frontend Dev Server)
start "J-PRO [3000] Frontend Web" cmd /k "chcp 65001 > nul && cd frontend && npm run dev"

:: 3. Port 8501 (Streamlit Dashboard)
start "J-PRO [8501] Streamlit Dashboard" cmd /k "chcp 65001 > nul && .venv\Scripts\streamlit run app.py --server.port 8501"

echo 모든 서버 실행 명령이 전달되었습니다. 각 창에서 로그를 확인하실 수 있습니다.
timeout /t 3 > nul
