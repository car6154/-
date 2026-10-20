@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================================
echo  J-PRO 거래처 OCR 환경 구축 및 패키지 갱신 (RapidOCR OpenVINO)
echo ========================================================

set "VENV_DIR=.venv_ocr_spike"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [1/3] OCR 전용 가상환경(.venv_ocr_spike) 생성 중...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [오류] 가상환경 생성 실패. Python 설치 및 PATH 설정을 확인하세요.
        pause
        exit /b 1
    )
) else (
    echo [1/3] 기존 OCR 가상환경(.venv_ocr_spike) 확인 완료.
)

echo [2/3] RapidOCR 3.10.0 및 OpenVINO 백엔드 설치 중...
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install "rapidocr==3.10.0" "openvino"
if errorlevel 1 (
    echo [오류] 패키지 설치 실패.
    pause
    exit /b 1
)

echo [3/3] RapidOCR OpenVINO 모델 다운로드 및 사전 워밍업 중...
"%VENV_PY%" -c "from rapidocr import RapidOCR, EngineType, ModelType, OCRVersion; import numpy as np; engine=RapidOCR(params={'Global.use_cls':False,'Det.engine_type':EngineType.OPENVINO,'Det.ocr_version':OCRVersion.PPOCRV5,'Det.model_type':ModelType.MOBILE,'Det.limit_side_len':960,'Det.limit_type':'max','Det.unclip_ratio':2.0,'Det.box_thresh':0.5,'Rec.engine_type':EngineType.OPENVINO,'Rec.ocr_version':OCRVersion.PPOCRV5,'Rec.model_type':ModelType.MOBILE,'Rec.lang_type':'korean'}); dummy=np.ones((100,100,3),dtype=np.uint8)*255; engine(dummy); print('>> RapidOCR OpenVINO 모델 캐싱 및 워밍업 성공!')"

if errorlevel 1 (
    echo [경고] 워밍업 중 일부 경고 또는 오류가 발생했습니다.
) else (
    echo ========================================================
    echo  거래처 OCR 환경 구축 완료! 본 서버를 구동하십시오.
    echo ========================================================
)

pause
