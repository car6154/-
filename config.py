# config.py
import os
from pathlib import Path

# 애플리케이션 기본 정보
APP_NAME = "UsedCarAnalyzer_Pro"
VERSION = "1.0.0"

# 디렉토리 설정
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# 파일 경로
DB_PATH = DATA_DIR / "used_cars.db"
SETTINGS_PATH = DATA_DIR / "settings.json"

# 초기화: 필요한 폴더 자동 생성
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)