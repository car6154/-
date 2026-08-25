# utils.py
import logging
import sys
from logging.handlers import RotatingFileHandler
from config import LOG_DIR, APP_NAME

class AppLogger:
    """애플리케이션 전역 로깅 클래스 (싱글톤 패턴)"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppLogger, cls).__new__(cls)
            cls._instance._setup_logger()
        return cls._instance

    def _setup_logger(self):
        self.logger = logging.getLogger(APP_NAME)
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )

        # 1. 파일 핸들러 (최대 5MB, 백업 3개)
        log_file = LOG_DIR / "app.log"
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        # 2. 콘솔 핸들러 (개발용)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger

# 전역에서 쉽게 사용할 수 있도록 인스턴스화
logger = AppLogger().get_logger()