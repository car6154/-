# database.py
import sqlite3
import pandas as pd
from contextlib import contextmanager
from config import DB_PATH
from utils import logger

class DatabaseManager:
    """SQLite 데이터베이스 관리 클래스"""

    def __init__(self):
        self.db_path = str(DB_PATH)
        self.init_database()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row 
        try:
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_database(self):
        """테이블 및 인덱스 생성"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT, model TEXT, sub_model TEXT, grade TEXT,
            year INTEGER, mileage INTEGER, fuel TEXT, transmission TEXT,
            color TEXT, accident TEXT, options TEXT, price REAL, registration_date TEXT
        )
        """
        create_index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_brand_model ON cars (brand, model);",
            "CREATE INDEX IF NOT EXISTS idx_year_mileage ON cars (year, mileage);",
            "CREATE INDEX IF NOT EXISTS idx_price ON cars (price);"
        ]
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_table_query)
                for idx_query in create_index_queries:
                    cursor.execute(idx_query)
                conn.commit()
            logger.info("데이터베이스 초기화 및 인덱스 생성이 완료되었습니다.")
        except Exception as e:
            logger.critical(f"데이터베이스 초기화 중 오류 발생: {e}")

    # ===== [새로 추가된 기능] =====
    def save_raw_data(self, df):
        """화면에 있는 데이터를 DB(cars_raw 테이블)에 그대로 안전하게 저장"""
        try:
            with self.get_connection() as conn:
                # pandas의 to_sql을 이용하면 수만 건의 데이터도 1초 만에 DB로 들어갑니다.
                df.to_sql('cars_raw', conn, if_exists='append', index=False)
            logger.info(f"DB에 {len(df)}건의 데이터를 성공적으로 저장했습니다.")
            return True
        except Exception as e:
            logger.error(f"DB 저장 실패: {e}")
            return False

    def load_all_data(self):
        """DB에 저장된 데이터를 다시 가져오기"""
        try:
            with self.get_connection() as conn:
                # cars_raw 테이블이 존재하는지 먼저 확인
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cars_raw'")
                if not cursor.fetchone():
                    return pd.DataFrame() # 테이블이 없으면 빈 데이터 반환
                
                query = "SELECT * FROM cars_raw"
                df = pd.read_sql_query(query, conn)
            return df
        except Exception as e:
            logger.error(f"DB 데이터 불러오기 실패: {e}")
            return pd.DataFrame()

# 전역에서 사용할 수 있도록 인스턴스화
db = DatabaseManager()