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

    @staticmethod
    def filter_strictly_by_submodel(df: pd.DataFrame, target_car_name: str = "", target_sub_model: str = "") -> pd.DataFrame:
        """
        엔카 실시간 수집 데이터에서 세부모델/파생트림(스페셜, 에디션, N Line, 유종/배기량/구동방식 불일치 등)을
        엄격하게 배제하여 정밀 비교군만 추출합니다. (8501과 3000 단일 공통 기준)
        """
        if df.empty or not target_sub_model or target_sub_model == "전체" or '세부모델' not in df.columns:
            return df
        
        sub_raw = str(target_sub_model).strip()
        sub_clean = sub_raw.lower().replace(" ", "")
        sub_parts = [p for p in sub_raw.split() if len(p) >= 2]
        
        encar_full_clean = (df['차량명'].astype(str) + " " + df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
        
        all_matched = pd.Series(True, index=df.index)
        for part in sub_parts:
            part_clean = part.replace(" ", "").lower()
            all_matched = all_matched & encar_full_clean.str.contains(part_clean, na=False, regex=False)
        
        cand_df = df[all_matched] if all_matched.any() else df.copy()
        
        # 1. 🚗 파생 바디/타입 배제
        BODY_TYPE_KEYWORDS = [
            '살룬', '왜건', '해치백', '하이리무진', '리무진', '밴', '카고', 
            '쿠페', '컨버터블', '카브리올레', '로드스터', '그란쿠페', 
            '칸', '크로스오버', '아웃도어'
        ]
        target_all_text = (str(target_car_name or '') + " " + sub_raw).lower()
        cand_full_clean = (cand_df['차량명'].astype(str) + " " + cand_df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
        
        for b_kw in BODY_TYPE_KEYWORDS:
            if b_kw in target_all_text:
                has_b = cand_full_clean.str.contains(b_kw, na=False)
                if has_b.any():
                    cand_df = cand_df[has_b]
                    cand_full_clean = (cand_df['차량명'].astype(str) + " " + cand_df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
            else:
                has_b = cand_full_clean.str.contains(b_kw, na=False)
                if has_b.any() and (~has_b).any():
                    cand_df = cand_df[~has_b]
                    cand_full_clean = (cand_df['차량명'].astype(str) + " " + cand_df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
                    
        # 2. ⛽ 유종 엄격 상호 배제
        diesel_kws = ['vgt', 'crdi', '디젤', 'diesel', 'dci', 'cdi', 'tdi', 'e-vgt']
        gas_kws = ['gdi', '가솔린', 'gasoline', 'gde', 't-gdi', 'mpi', 'cvvl']
        lpg_kws = ['lpi', 'lpg', 'lpe']
        
        is_q_diesel = any(k in sub_clean for k in diesel_kws)
        is_q_gas = any(k in sub_clean for k in gas_kws)
        is_q_lpg = any(k in sub_clean for k in lpg_kws)
        
        cand_full_clean = (cand_df['차량명'].astype(str) + " " + cand_df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
        if is_q_diesel:
            bad_fuel = cand_full_clean.str.contains('gdi|가솔린|gde|lpi|lpg|lpe', na=False)
            if (~bad_fuel).any():
                cand_df = cand_df[~bad_fuel]
        elif is_q_gas:
            bad_fuel = cand_full_clean.str.contains('vgt|crdi|디젤|diesel|dci|cdi|tdi|lpi|lpg|lpe', na=False)
            if (~bad_fuel).any():
                cand_df = cand_df[~bad_fuel]
        elif is_q_lpg:
            lpg_mask = cand_full_clean.str.contains('lpi|lpg|lpe', na=False)
            if lpg_mask.any():
                cand_df = cand_df[lpg_mask]
                
        # 3. 🔍 배기량 엄격 일치
        disp_m = re.search(r'(\d\.\d)', sub_raw)
        if disp_m:
            disp_val = disp_m.group(1)
            cand_full_clean = (cand_df['차량명'].astype(str) + " " + cand_df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
            disp_mask = cand_full_clean.str.contains(disp_val, na=False)
            if disp_mask.any():
                cand_df = cand_df[disp_mask]
        
        # 4. ⚙️ 구동방식 (2WD vs 4WD/AWD)
        is_target_4wd = any(x in sub_clean for x in ['4wd', '4륜', 'awd'])
        cand_sub_col = cand_df['세부모델'].astype(str)
        if not is_target_4wd:
            non_4wd = ~cand_sub_col.str.contains(r'4wd|4륜|awd', case=False, regex=True, na=False)
            if non_4wd.any():
                cand_df = cand_df[non_4wd]
        else:
            is_4wd = cand_sub_col.str.contains(r'4wd|4륜|awd', case=False, regex=True, na=False)
            if is_4wd.any():
                cand_df = cand_df[is_4wd]
                
        # 5. ✨ 서브 키워드 (스페셜, 플러스, 에디션, 마스터, n line 등) 배제
        for sub_kw in ['스페셜', '플러스', '에디션', '마스터', 'n line', 'nline']:
            if sub_kw not in sub_clean:
                has_kw = cand_df['세부모델'].astype(str).str.lower().str.contains(sub_kw, na=False)
                if (~has_kw).any():
                    cand_df = cand_df[~has_kw]
            else:
                has_kw = cand_df['세부모델'].astype(str).str.lower().str.contains(sub_kw, na=False)
                if has_kw.any():
                    cand_df = cand_df[has_kw]
                    
        return cand_df.reset_index(drop=True)

    @staticmethod
    def sort_by_price_year_perf(df: pd.DataFrame) -> pd.DataFrame:
        """
        사용자 승인 정렬 기준 (2번):
        1. 가격 낮은순 (오름차순)
        2. 연식 최신순 (내림차순)
        3. 성능점검 완료 우선 및 점검일 최신순 (내림차순)
        """
        if df.empty:
            return df
        
        res_df = df.copy()
        if "판매가" in res_df.columns:
            res_df["_sort_price"] = pd.to_numeric(res_df["판매가"], errors='coerce').fillna(999999)
        else:
            res_df["_sort_price"] = 999999

        def _parse_year(val):
            m = re.search(r'(\d+)', str(val))
            return int(m.group(1)) if m else 0

        res_df['_sort_year'] = res_df['연식'].apply(_parse_year) if "연식" in res_df.columns else 0
        
        if "성능일" in res_df.columns:
            res_df['_has_perf'] = res_df['성능일'].astype(str).apply(
                lambda x: 1 if re.match(r'^\d{2}-\d{2}-\d{2}', str(x)) and str(x) not in ['미검사/사진', '⚠️미등록', '⚠️조회실패', '-'] else 0
            )
            res_df['_sort_perf'] = res_df['성능일'].astype(str).apply(
                lambda x: x if re.match(r'^\d{2}-\d{2}-\d{2}', str(x)) and str(x) not in ['미검사/사진', '⚠️미등록', '⚠️조회실패', '-'] else '00-00-00'
            )
        else:
            res_df['_has_perf'] = 0
            res_df['_sort_perf'] = '00-00-00'

        res_df = res_df.sort_values(
            by=['_sort_price', '_sort_year', '_has_perf', '_sort_perf'],
            ascending=[True, False, False, False]
        ).drop(columns=['_sort_price', '_sort_year', '_has_perf', '_sort_perf']).reset_index(drop=True)
        
        return res_df

    @staticmethod
    def sort_by_perf_and_year(df: pd.DataFrame) -> pd.DataFrame:
        """
        8501 콕핏 확정 정렬 기준:
        1. 성능점검 등록 여부 (점검 완료 우선)
        2. 연식 최신순 (내림차순)
        3. 성능점검일 최신순 (내림차순)
        """
        if df.empty:
            return df
        
        res_df = df.copy()
        if "주행거리" in res_df.columns:
            res_df["주행거리"] = pd.to_numeric(res_df["주행거리"], errors='coerce').fillna(0)
            
        def _parse_year(val):
            m = re.search(r'(\d+)', str(val))
            return int(m.group(1)) if m else 0

        if "성능일" in res_df.columns and "연식" in res_df.columns:
            res_df['_has_perf'] = res_df['성능일'].astype(str).apply(
                lambda x: 1 if re.match(r'^\d{2}-\d{2}-\d{2}', str(x)) and str(x) not in ['미검사/사진', '⚠️미등록', '⚠️조회실패', '-'] else 0
            )
            res_df['_sort_perf'] = res_df['성능일'].astype(str).apply(
                lambda x: x if re.match(r'^\d{2}-\d{2}-\d{2}', str(x)) and str(x) not in ['미검사/사진', '⚠️미등록', '⚠️조회실패', '-'] else '00-00-00'
            )
            res_df['_sort_year'] = res_df['연식'].apply(_parse_year)
            res_df = res_df.sort_values(
                by=['_has_perf', '_sort_year', '_sort_perf'],
                ascending=[False, False, False]
            ).drop(columns=['_has_perf', '_sort_perf', '_sort_year']).reset_index(drop=True)
            
        return res_df
