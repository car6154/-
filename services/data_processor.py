# services/data_processor.py
import re
import pandas as pd

class DataProcessor:
    @staticmethod
    def infer_brand(car_name):
        name = str(car_name).strip().upper()
        if any(x in name for x in ['G70', 'G80', 'G90', 'GV70', 'GV80', 'GV60', '제네시스', 'EQ900']): return "제네시스"
        elif any(x in name for x in ['쏘나타', '그랜저', '아반떼', '싼타페', '투싼', '팰리세이드', '캐스퍼', '포터', '스타리아', '스타렉스', '코나', '아이오닉', '베뉴']): return "현대"
        elif any(x in name for x in ['K3', 'K5', 'K7', 'K8', 'K9', '쏘렌토', '스포티지', '카니발', '레이', '모닝', '봉고', '셀토스', '니로', '모하비', 'EV6', 'EV9']): return "기아"
        elif any(x in name for x in ['스파크', '말리부', '트레일블레이저', '트래버스', '콜로라도', '이쿼녹스', '볼트']): return "쉐보레"
        elif any(x in name for x in ['SM3', 'SM5', 'SM6', 'QM3', 'QM6', 'XM3']): return "르노코리아"
        elif any(x in name for x in ['티볼리', '코란도', '렉스턴', '토레스']): return "KG모빌리티"
        elif any(x in name for x in ['E클래스', 'S클래스', 'C클래스', '벤츠', 'GLC', 'GLE', 'GLA', 'GLB', 'AMG']): return "벤츠"
        elif any(x in name for x in ['3시리즈', '5시리즈', '7시리즈', 'BMW', 'X3', 'X4', 'X5', 'X6', 'X7', 'M3', 'M4', 'M5']): return "BMW"
        elif any(x in name for x in ['아우디', 'A4', 'A6', 'A7', 'A8', 'Q5', 'Q7', 'Q8']): return "아우디"
        elif any(x in name for x in ['렉서스', 'ES', 'RX', 'NX', 'LS']): return "렉서스"
        elif any(x in name for x in ['볼보', 'XC60', 'XC90', 'S90']): return "볼보"
        elif any(x in name for x in ['포르쉐', '카이엔', '파나메라', '마칸', '911']): return "포르쉐"
        elif any(x in name for x in ['미니', 'MINI', '클럽맨', '컨트리맨']): return "미니"
        elif any(x in name for x in ['포드', '익스플로러', '머스탱']): return "포드"
        elif any(x in name for x in ['테슬라', '모델3', '모델Y', '모델S', '모델X']): return "테슬라"
        return "기타"

    @staticmethod
    def standardize(df):
        if df.empty: return df
        df = df.copy()
        df = df.loc[:, ~df.columns.duplicated()]
        
        rename_dict = {}
        price_candidates = {"할인적용가": 1, "지점판매가": 2, "판매가": 3, "가격": 4, "매입가": 5}
        best_price_col = None
        best_price_rank = 99
        
        for col in df.columns:
            clean_col = str(col).replace(" ", "").lower()
            
            if "세부모델" in clean_col: rename_dict[col] = "세부모델"
            elif any(x in clean_col for x in ["제조사", "브랜드", "메이커"]): rename_dict[col] = "제조사"
            elif any(x in clean_col for x in ["차종", "차량명", "모델"]): rename_dict[col] = "차량명"
            elif "상태" in clean_col: rename_dict[col] = "상태"
            elif any(x in clean_col for x in ["등록일", "연식"]): rename_dict[col] = "연식"
            elif "주행거리" in clean_col: rename_dict[col] = "주행거리"
            elif any(x in clean_col for x in ["경과일", "재고"]): rename_dict[col] = "재고" 
            elif "성능" in clean_col: rename_dict[col] = "성능일"
            elif any(x in clean_col for x in ["url", "링크", "웹페이지", "사이트", "link"]): rename_dict[col] = "링크"
            
            for cand, rank in price_candidates.items():
                if cand in clean_col and rank < best_price_rank:
                    best_price_col = col
                    best_price_rank = rank
                    
        if best_price_col:
            rename_dict[best_price_col] = "판매가"

        df = df.rename(columns=rename_dict)
        df = df.loc[:, ~df.columns.duplicated()]
        
        if "차량명" in df.columns:
            df["차량명"] = df["차량명"].astype(str).str.replace(" ", "", regex=False)
        if "세부모델" in df.columns:
            df["세부모델"] = df["세부모델"].astype(str).str.replace(" ", "", regex=False)
            
        if "제조사" not in df.columns: df["제조사"] = ""
        if "차량명" in df.columns:
            df["제조사"] = df.apply(lambda row: DataProcessor.infer_brand(row["차량명"]) if pd.isna(row["제조사"]) or str(row["제조사"]).strip() == "" else row["제조사"], axis=1)
        
        if "_carid" not in df.columns: df["_carid"] = ""
        df["_carid"] = df["_carid"].astype(str)
        
        target_columns = ['상태', '성능일', '링크', '차량명', '세부모델', '연식', '주행거리', '판매가', '재고', '사고유무', '외장컬러', '추가옵션', '제조사', '_carid']
        for col in target_columns:
            if col not in df.columns:
                if col in ['사고유무', '추가옵션', '성능일', '재고', '외장컬러']: df[col] = "-"
                elif col == '상태': df[col] = "자사재고"
                else: df[col] = ""
                
        df["상태"] = df["상태"].fillna("자사재고").replace("", "자사재고")
                
        ordered_df = df[target_columns].copy()

        if "링크" in ordered_df.columns:
            def fix_url(url):
                u = str(url).strip()
                if not u or u.lower() in ["nan", "-", "none", ""] or "javascript" in u.lower(): return None
                if not u.startswith("http"): return f"https://{u}"
                return u
            ordered_df["링크"] = ordered_df["링크"].apply(fix_url)

        if "연식" in ordered_df.columns:
            def format_year(y):
                y = str(y).strip()
                if len(y) >= 7 and y[4] == '-': return y[2:7] 
                if len(y) == 6 and y.isdigit(): return f"{y[2:4]}-{y[4:6]}" 
                if len(y) == 4 and y.isdigit(): return y[2:4] 
                return y
            ordered_df["연식"] = ordered_df["연식"].apply(format_year)
            
        if "주행거리" in ordered_df.columns:
            ordered_df["주행거리"] = ordered_df["주행거리"].astype(str).str.replace(r'[^\d.]', '', regex=True)
            ordered_df["주행거리"] = pd.to_numeric(ordered_df["주행거리"], errors='coerce')
        
        if "판매가" in ordered_df.columns:
            ordered_df["판매가"] = ordered_df["판매가"].astype(str).str.replace(r'[^\d.]', '', regex=True)
            ordered_df["판매가"] = pd.to_numeric(ordered_df["판매가"], errors='coerce')
            ordered_df["판매가"] = ordered_df["판매가"].apply(lambda x: x / 10000 if pd.notna(x) and x >= 100000 else x)
            
            valid_prices = ordered_df["판매가"].dropna()
            if len(valid_prices) > 10:
                low_bound = valid_prices.quantile(0.01)
                high_bound = valid_prices.quantile(0.99)
                ordered_df = ordered_df[(ordered_df["판매가"].isna()) | ((ordered_df["판매가"] >= low_bound) & (ordered_df["판매가"] <= high_bound))]

        if "사고유무" in ordered_df.columns:
            def clean_acc_col(val):
                s = str(val).strip()
                if not s or s in ("-", "정보없음", "기록부(사진)", "⚠️조회실패"):
                    return s
                s = s.replace("⚠️", "").replace("✅", "").replace("🟢", "").replace("🟡", "").replace("🔴", "").strip()
                s = s.replace("(사고/판금)", "사고").replace("(사고/단순)", "사고")
                s = s.replace("(판금)", "단순교환").replace("(단순)", "단순교환")
                s = s.replace("사고/판금", "사고").replace("사고/단순", "사고")
                s = re.sub(r'\s*/\s*판금:0', '', s)
                s = re.sub(r'교환:0\s*/\s*', '', s)
                s = re.sub(r'\[교환:0\]', '', s)
                s = re.sub(r'\[판금:0\]', '', s)
                s = re.sub(r'\[\s*\]', '', s)
                if '교환:' in s and '판금:' not in s:
                    s = re.sub(r'단순\s*\([^)]*\)|단순판금', '단순교환', s)
                    s = re.sub(r'사고\s*\([^)]*\)', '사고', s)
                elif '판금:' in s and '교환:' not in s:
                    s = re.sub(r'단순\s*\([^)]*\)|단순교환', '단순판금', s)
                    s = re.sub(r'사고\s*\([^)]*\)', '사고', s)
                elif '교환:' in s and '판금:' in s:
                    s = re.sub(r'단순\s*\([^)]*\)|단순교환|단순판금', '단순(교환/판금)', s)
                    s = re.sub(r'사고\s*\([^)]*\)', '사고', s)
                return s.strip()
            ordered_df["사고유무"] = ordered_df["사고유무"].apply(clean_acc_col)

        ordered_df = ordered_df.fillna("")
        if "링크" in ordered_df.columns:
            ordered_df["링크"] = ordered_df["링크"].replace("", None)
            
        return ordered_df
