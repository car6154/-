# settings.py
import json
from config import SETTINGS_PATH
from utils import logger

class SettingsManager:
    """사용자 환경 설정을 관리하는 클래스"""
    
    DEFAULT_SETTINGS = {
        "theme": "light",          # light or dark
        "recent_searches": [],     # 최근 검색어 리스트
        "auto_backup": True,       # 자동 백업 여부
        "window_size": [1280, 800] # 기본 창 크기
    }

    def __init__(self):
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load_settings()

    def load_settings(self):
        """설정 파일 로드"""
        if SETTINGS_PATH.exists():
            try:
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.settings.update(loaded_data)
                logger.info("설정 파일을 성공적으로 불러왔습니다.")
            except Exception as e:
                logger.error(f"설정 파일 로드 실패 (기본값 사용): {e}")
        else:
            self.save_settings()

    def save_settings(self):
        """현재 설정을 파일에 저장"""
        try:
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            logger.info("설정을 성공적으로 저장했습니다.")
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()