# excel.py
import pandas as pd
from utils import logger

class DataLoader:
    """엑셀 및 CSV 데이터를 불러오는 전담 클래스"""
    
    @staticmethod
    def load_file(file_path):
        try:
            # 파일 확장자에 따라 다르게 읽기
            if file_path.endswith('.csv'):
                # 한글 깨짐 방지를 위해 cp949 인코딩 시도, 안되면 utf-8
                try:
                    df = pd.read_csv(file_path, encoding='cp949')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='utf-8')
            elif file_path.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                raise ValueError("지원하지 않는 파일 형식입니다.")
            
            # [수정된 부분] 숫자/텍스트 충돌 방지를 위해 데이터를 object 타입으로 변환 후 빈칸 처리
            df = df.astype(object)
            df.fillna("", inplace=True)
            
            logger.info(f"성공적으로 데이터를 불러왔습니다. (총 {len(df)}건): {file_path}")
            return df
            
        except Exception as e:
            logger.error(f"파일 불러오기 실패 - {file_path}: {e}")
            return None