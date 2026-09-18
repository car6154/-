# sales_analysis.py
"""
J-PRO 빅데이터 실거래 판매 분석 및 추천 입찰/엔카 시세 연동 모듈
- 7,493건 이상의 완판 실거래 데이터를 분석하여 차종별 평균 재고일수(회전율), 실현 마진, 고객 수요도를 산출
- 3단계 추천 입찰가(공격적/표준/방어적) 산정
- 엔카 실시간 동급 매물 검색 URL 생성
"""

import os
import re
import json
import urllib.parse
import pandas as pd
import numpy as np

SALES_DATA_FILES = [
    "autoplus_inventory.csv",
    "20260917_sales_car_datalist.csv",
    "20260813_sales_car_datalist.csv"
]

class SalesDataAnalyzer:
    _instance = None

    def __init__(self):
        self.df = pd.DataFrame()
        self.raw_df = pd.DataFrame()
        self.retail_sales_df = pd.DataFrame()
        self.auction_sales_df = pd.DataFrame()
        self.inventory_df = pd.DataFrame()
        self.pure_sales_count = 0
        self.auction_filtered_count = 0
        self.inventory_count = 0
        self.load_data()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_data(self):
        """판매 데이터셋 로드 및 전처리 (autoplus_inventory.csv 최우선, 없을 시 다운로드 폴더 자동 감지)"""
        candidates = list(SALES_DATA_FILES)
        
        # 다운로드 폴더의 최신 sales_car_datalist 파일도 후보에 추가
        downloads_dir = os.path.expanduser(r"~\Downloads")
        if os.path.exists(downloads_dir):
            for f in sorted(os.listdir(downloads_dir), reverse=True):
                if "sales_car_datalist" in f and f.endswith(".csv"):
                    candidates.append(os.path.join(downloads_dir, f))

        for filename in candidates:
            if os.path.exists(filename):
                try:
                    try:
                        loaded = pd.read_csv(filename, encoding='utf-8-sig')
                    except UnicodeDecodeError:
                        try:
                            loaded = pd.read_csv(filename, encoding='utf-8')
                        except UnicodeDecodeError:
                            loaded = pd.read_csv(filename, encoding='cp949')
                    
                    if not loaded.empty and len(loaded) > 50:
                        self.raw_df = loaded
                        self._preprocess_data()
                        print(f"[SalesDataAnalyzer] 로드 완료: 순수 소매 완판 {self.pure_sales_count:,}건 (경매 제외 {self.auction_filtered_count:,}건), 현재 재고 {self.inventory_count:,}건 ({filename})")
                        break
                except Exception as e:
                    print(f"[SalesDataAnalyzer] {filename} 로드 실패: {e}")

    def _preprocess_data(self):
        """데이터 정규화, 경매/도매 판매 제외 및 자사 보유재고 분리"""
        if not hasattr(self, 'raw_df') or self.raw_df.empty:
            if self.df.empty:
                return
            self.raw_df = self.df.copy()

        df_work = self.raw_df.copy()

        # 컬럼 매핑 (중복 컬럼 방지)
        col_map = {}
        for c in df_work.columns:
            clean = str(c).strip().replace(" ", "").lower()
            if clean in ["차량명", "차종"]:
                col_map[c] = "차량명"
            elif "세부모델" in clean or "세부 모델" in clean:
                col_map[c] = "세부모델"
            elif "최초등록일" in clean:
                col_map[c] = "최초등록일"
            elif "경과일수" in clean:
                col_map[c] = "경과일수"
            elif "예상매출이익" in clean:
                col_map[c] = "예상매출이익"
            elif clean == "지점판매가":
                col_map[c] = "지점판매가"
            elif "할인적용가" in clean:
                col_map[c] = "할인적용가"
            elif clean == "매입가":
                col_map[c] = "매입가"
            elif clean in ["지점", "전시장"]:
                col_map[c] = "지점"
            elif clean in ["담당자명", "판매담당자"]:
                col_map[c] = "담당자명"
            elif "eurl" in clean or "e url" in clean:
                col_map[c] = "E URL"
            elif "rb찜수" in clean:
                col_map[c] = "RB찜수"
            elif "rb조회수" in clean:
                col_map[c] = "RB조회수"
            elif "rb상담수" in clean:
                col_map[c] = "RB상담수"
            elif "e찜수" in clean:
                col_map[c] = "E찜수"
            elif "e조회수" in clean:
                col_map[c] = "E조회수"
            elif "e상담수" in clean:
                col_map[c] = "E상담수"
            elif "홈페이지상태" in clean:
                col_map[c] = "홈페이지상태"
            elif "주행거리" in clean or clean == "주행":
                col_map[c] = "주행거리"

        df_work = df_work.rename(columns=col_map)

        # 필수 컬럼 기본값 처리
        for req in ["차량명", "세부모델", "경과일수", "예상매출이익", "지점판매가", "할인적용가", "매입가"]:
            if req not in df_work.columns:
                df_work[req] = 0

        for col, default_val in [('담당자명', np.nan), ('E URL', ''), ('홈페이지상태', '판매완료'), ('지점', ''), ('주행거리', 0)]:
            if col not in df_work.columns:
                df_work[col] = default_val

        # 경과일수 및 등록연도 수치화
        df_work['경과일수_num'] = pd.to_numeric(df_work['경과일수'], errors='coerce').fillna(0)
        df_work['주행거리_num'] = pd.to_numeric(df_work['주행거리'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
        df_work['등록연도_num'] = pd.to_numeric(df_work['최초등록일'].astype(str).str.extract(r'(\d{4})')[0], errors='coerce').fillna(0).astype(int)

        # 예상매출이익: 원 단위 -> 만원 단위 변환 (예: 2,000,000원 -> 200만원)
        profit_num = pd.to_numeric(df_work['예상매출이익'], errors='coerce').fillna(0)
        df_work['이익_만원'] = profit_num.apply(lambda x: round(x / 10000, 1) if abs(x) >= 10000 else x)

        # 판매가 (할인적용가 우선, 없으면 지점판매가)
        sell_p = pd.to_numeric(df_work['할인적용가'], errors='coerce').fillna(0)
        sell_branch = pd.to_numeric(df_work['지점판매가'], errors='coerce').fillna(0)
        sell_final = np.where(sell_p > 0, sell_p, sell_branch)
        df_work['판매가_만원'] = pd.Series(sell_final).apply(lambda x: round(x / 10000, 1) if x >= 10000 else x)

        # 차량명 정규화 (검색 최적화)
        df_work['차량명_clean'] = df_work['차량명'].astype(str).str.replace(" ", "").str.lower()
        df_work['세부모델_clean'] = df_work['세부모델'].astype(str).str.replace(" ", "").str.lower()

        # 🚨 경매 / 도매 출고 차량 판별
        # 1. 담당자명이 공란(NaN)인 경우 (소매 영업사원 미배정 경매/도매 출고)
        # 2. E URL이 비어있거나 javascript:; 인 경우 (엔카 소매 광고 미진행)
        is_auction = (
            df_work['담당자명'].isna() |
            df_work['E URL'].isna() |
            df_work['E URL'].astype(str).str.strip().str.startswith('javascript')
        )
        df_work['is_auction'] = is_auction

        # 데이터셋 분리
        # 1) 순수 내수 소매 완판 실적 (경매/도매 제외)
        self.retail_sales_df = df_work[(df_work['홈페이지상태'] == '판매완료') & (~df_work['is_auction'])].copy()
        # 2) 경매/도매 출고 차량
        self.auction_sales_df = df_work[(df_work['홈페이지상태'] == '판매완료') & (df_work['is_auction'])].copy()
        # 3) 현재 자사 보유재고 (판매중 / 계약중)
        self.inventory_df = df_work[df_work['홈페이지상태'].isin(['판매중', '계약중'])].copy()

        self.pure_sales_count = len(self.retail_sales_df)
        self.auction_filtered_count = len(self.auction_sales_df)
        self.inventory_count = len(self.inventory_df)

        # 기본 분석 대상을 순수 소매 완판 데이터셋으로 지정 (회전율 왜곡 원천 차단)
        self.df = self.retail_sales_df

    # 헤이딜러 <-> 오토플러스 사내 표기 간의 차종명 별칭(Synonym) 매핑 테이블 (세대 엄격 분리)
    SYNONYM_MAP = {
        # --- 기아 ---
        "신형카니발": ["카니발4세대", "카니발ka4"],
        "카니발4세대": ["신형카니발", "카니발ka4"],
        "더뉴카니발4세대": ["카니발4세대", "더뉴카니발"],
        "더뉴카니발": ["올뉴카니발", "카니발yp"],
        "올뉴카니발": ["더뉴카니발", "카니발yp"],
        "신형쏘렌토": ["쏘렌토4세대", "쏘렌토mq4"],
        "쏘렌토4세대": ["신형쏘렌토", "쏘렌토mq4"],
        "더뉴쏘렌토4세대": ["신형쏘렌토", "쏘렌토mq4"],
        "더뉴쏘렌토": ["올뉴쏘렌토", "쏘렌토um"],
        "올뉴쏘렌토": ["더뉴쏘렌토", "쏘렌토um"],
        "디올뉴스포티지": ["스포티지5세대", "스포티지nq5"],
        "스포티지5세대": ["디올뉴스포티지", "스포티지nq5"],
        "스포티지4세대": ["신형스포티지", "스포티지더볼드", "스포티지ql"],
        "신형스포티지": ["스포티지4세대", "스포티지ql"],
        "스포티지더볼드": ["스포티지4세대"],
        "k52세대": ["신형k5", "뉴신형k5", "k5jf"],
        "신형k5": ["k52세대", "뉴신형k5"],
        "뉴신형k5": ["k52세대", "신형k5"],
        "k53세대": ["신형k5(dl3)", "k5dl3", "더뉴k5(dl3)"],
        "k5dl3": ["신형k5(dl3)", "k53세대", "더뉴k5(dl3)"],
        "신형k5(dl3)": ["k53세대", "k5dl3", "더뉴k5(dl3)"],
        "더뉴k5": ["k52세대", "신형k5"],
        "더뉴k3": ["올뉴k3", "k32세대"],
        "올뉴k3": ["더뉴k3", "k32세대"],
        "더뉴k7": ["올뉴k7"],
        "올뉴k7": ["k7프리미어", "더뉴k7"],
        "k7프리미어": ["올뉴k7"],
        "더뉴k9": ["더k9", "k92세대"],
        "더k9": ["더뉴k9", "k92세대"],
        "더뉴레이": ["더뉴기아레이", "레이"],
        "더뉴기아레이": ["더뉴레이", "레이"],
        "모닝어반": ["올뉴모닝", "더뉴모닝"],
        "올뉴모닝": ["더뉴모닝", "모닝어반"],
        "더뉴모닝": ["올뉴모닝", "모닝어반"],
        "더뉴셀토스": ["셀토스"],
        "셀토스": ["더뉴셀토스"],
        "디올뉴니로": ["니로2세대", "니로sg2"],
        "더뉴니로": ["니로"],
        "니로": ["더뉴니로"],
        "모하비더마스터": ["더뉴모하비", "모하비"],
        "더뉴모하비": ["모하비더마스터", "모하비"],

        # --- 현대 ---
        "디올뉴그랜저": ["그랜저gn7", "그랜저7세대"],
        "그랜저gn7": ["디올뉴그랜저"],
        "더뉴그랜저ig": ["더뉴그랜저", "그랜저ig"],
        "그랜저ig": ["더뉴그랜저ig", "더뉴그랜저"],
        "그랜저hg": ["그랜저5세대"],
        "디올뉴싼타페": ["싼타페mx5", "싼타페5세대"],
        "더뉴싼타페": ["신형싼타페", "싼타페tm"],
        "신형싼타페": ["더뉴싼타페", "싼타페tm"],
        "싼타페tm": ["신형싼타페", "더뉴싼타페"],
        "싼타페더프라임": ["싼타페dm"],
        "디올뉴투싼": ["투싼nx4", "투싼4세대"],
        "투싼nx4": ["디올뉴투싼"],
        "더뉴투싼": ["올뉴투싼", "신형투싼", "투싼tl"],
        "신형투싼": ["올뉴투싼", "더뉴투싼", "투싼tl"],
        "올뉴투싼": ["더뉴투싼", "신형투싼", "투싼tl"],
        "더뉴아반떼cn7": ["아반떼cn7", "올뉴아반떼"],
        "아반떼cn7": ["더뉴아반떼cn7", "올뉴아반떼"],
        "더뉴아반떼ad": ["아반떼ad"],
        "아반떼ad": ["더뉴아반떼ad"],
        "쏘나타디엣지": ["쏘나타dn8"],
        "쏘나타dn8": ["쏘나타디엣지"],
        "lf쏘나타뉴라이즈": ["lf쏘나타"],
        "lf쏘나타": ["lf쏘나타뉴라이즈"],
        "더뉴팰리세이드": ["팰리세이드"],
        "팰리세이드": ["더뉴팰리세이드"],
        "디올뉴코나": ["코나sx2", "코나2세대"],
        "더뉴코나": ["코나"],
        "코나": ["더뉴코나"],
        "더뉴그랜드스타렉스": ["그랜드스타렉스"],
        "그랜드스타렉스": ["더뉴그랜드스타렉스"],
        "더뉴맥스크루즈": ["맥스크루즈"],
        "맥스크루즈": ["더뉴맥스크루즈"],

        # --- 제네시스 ---
        "더올뉴g80": ["g80rg3", "신형g80"],
        "g80rg3": ["더올뉴g80"],
        "신형g80": ["더올뉴g80", "g80rg3"],
        "뉴g80": ["g80"],
        "더뉴g70": ["g70"],
        "g70": ["더뉴g70"],
        "신형g90": ["g90rs4"],
        "g90": ["신형g90", "eq900"],
        "더뉴gv80": ["gv80"],
        "gv80": ["더뉴gv80"],
        "신형gv70": ["gv70"],
        "gv70": ["신형gv70"],

        # --- 르노코리아 / 쉐보레 / KGM ---
        "더뉴qm6": ["뉴qm6", "신형qm6", "qm6"],
        "뉴qm6": ["더뉴qm6", "신형qm6", "qm6"],
        "신형qm6": ["더뉴qm6", "뉴qm6", "qm6"],
        "qm6": ["더뉴qm6", "뉴qm6"],
        "더뉴sm6": ["sm6"],
        "sm6": ["더뉴sm6"],
        "xm3": ["아르카나"],
        "아르카나": ["xm3"],
        "더뉴트랙스": ["트랙스"],
        "트랙스크로스오버": ["트랙스"],
        "더뉴말리부": ["올뉴말리부", "말리부"],
        "올뉴말리부": ["더뉴말리부", "말리부"],
        "더뉴트레일블레이저": ["트레일블레이저"],
        "트레일블레이저": ["더뉴트레일블레이저"],
        "더뉴스파크": ["더넥스트스파크", "스파크"],
        "더넥스트스파크": ["더뉴스파크", "스파크"],
        "뷰티풀코란도": ["올뉴코란도", "코란도"],
        "올뉴코란도": ["뷰티풀코란도", "코란도"],
        "더뉴티볼리": ["베리뉴티볼리", "티볼리아머", "티볼리"],
        "베리뉴티볼리": ["더뉴티볼리", "티볼리아머", "티볼리"],
        "티볼리아머": ["티볼리", "베리뉴티볼리"],
        "더뉴렉스턴스포츠": ["렉스턴스포츠"],
        "렉스턴스포츠": ["더뉴렉스턴스포츠"],
        "더뉴토레스": ["토레스"],
        "토레스": ["더뉴토레스"],
    }

    CORE_CAR_NAMES = [
        '코란도', '카니발', '쏘렌토', '그랜저', '투싼', '스포티지', 'k5', 'k3', 'k7', 'k8', 'k9',
        '아반떼', '쏘나타', 'g80', 'g70', 'gv70', 'gv80', '레이', '모닝', '스파크', '캐스퍼',
        '셀토스', '니로', '팰리세이드', '티볼리', 'qm6', 'xm3', 'sm6', '맥스크루즈', '산타페', '싼타페'
    ]

    def find_matches(self, car_name, sub_model="", year="", target_df=None):
        """헤이딜러 및 엔카 차량명과 오토플러스 실거래 DB 간의 지능형 매칭 (동의어 + 연식 세대 구분 + 토큰 기반)"""
        if not car_name and sub_model:
            car_name = sub_model
            sub_model = ""

        search_df = self.df if target_df is None else target_df
        if search_df.empty or not car_name:
            return pd.DataFrame()

        c_clean = str(car_name).replace(" ", "").lower()
        # 브랜드명 제거 ('현대', '기아', '제네시스', '쉐보레', '르노코리아', '쌍용', 'kg모빌리티' 등)
        for b in ['현대', '기아', '제네시스', '쉐보레', '르노코리아', '르노삼성', '쌍용', 'kg모빌리티', '벤츠', 'bmw', '아우디', '폭스바겐', '볼보']:
            if c_clean.startswith(b) and len(c_clean) > len(b):
                c_clean = c_clean[len(b):]

        # 연식 파싱 (예: '2016', '16', '16년' -> 2016)
        target_year = None
        if year:
            y_digits = re.findall(r'\d+', str(year))
            if y_digits:
                y_val = int(y_digits[0])
                if y_val < 100:
                    y_val += 2000
                target_year = y_val

        full_query_text = f"{c_clean} {str(sub_model).lower()}"

        # =========================================================================
        # 🚗 [세대 및 형식(페이스리프트 vs 풀체인지) 정밀 식별 엔진]
        # 원칙: 1순위(섀시코드/명시적 세대명) > 2순위(세대 고유 트림명) > 3순위(연식 기준)
        # =========================================================================
        # 1. K5 (2세대 JF/신형K5 vs 3세대 DL3)
        is_k5 = 'k5' in full_query_text
        is_k5_gen2 = False
        is_k5_gen3 = False
        if is_k5:
            # 1순위: 섀시코드 및 세대명
            if any(k in full_query_text for k in ['3세대', 'dl3']):
                is_k5_gen3 = True
            elif any(k in full_query_text for k in ['2세대', 'jf', '신형k5', '뉴신형k5', '더뉴k52세대']):
                is_k5_gen2 = True
            # 2순위: 세대 고유 트림명 (과도기 2019~2020년식 판별)
            elif any(k in full_query_text for k in ['mx', 'sx', '인텔리전트']):
                is_k5_gen2 = True
            elif any(k in full_query_text for k in ['시그니처']):
                is_k5_gen3 = True
            # 3순위: 단서가 전혀 없을 때만 연식 기반 분기
            elif target_year:
                if target_year <= 2019:
                    is_k5_gen2 = True
                elif target_year >= 2020:
                    is_k5_gen3 = True

        # 2. 카니발 (3세대 YP 올뉴/더뉴 vs 4세대 KA4)
        is_carnival = '카니발' in full_query_text
        is_carnival_gen4 = False
        is_carnival_old = False
        if is_carnival:
            if any(k in full_query_text for k in ['4세대', 'ka4']):
                is_carnival_gen4 = True
            elif any(k in full_query_text for k in ['3세대', 'yp', '올뉴', '더뉴']):
                is_carnival_old = True
            elif target_year:
                if target_year >= 2021:
                    is_carnival_gen4 = True
                elif target_year <= 2020:
                    is_carnival_old = True

        # 3. 쏘렌토 (2세대 전기 쏘렌토R vs 2세대 후기 뉴쏘렌토R vs 3세대 UM 올뉴/더뉴 vs 4세대 MQ4)
        is_sorento = '쏘렌토' in full_query_text
        is_sorento_gen4 = False
        is_sorento_um = False
        is_sorento_new_r = False
        is_sorento_r = False
        if is_sorento:
            if any(k in full_query_text for k in ['4세대', 'mq4', '신형쏘렌토', '그래비티']):
                is_sorento_gen4 = True
            elif any(k in full_query_text for k in ['3세대', 'um', '올뉴', '더뉴', '마스터']):
                is_sorento_um = True
            elif any(k in full_query_text for k in ['뉴쏘렌토r', '뉴쏘렌토']):
                is_sorento_new_r = True
            elif '쏘렌토r' in full_query_text:
                is_sorento_r = True
            elif target_year:
                if target_year >= 2021:
                    is_sorento_gen4 = True
                elif target_year >= 2015:
                    is_sorento_um = True
                elif target_year >= 2012:
                    is_sorento_new_r = True
                elif target_year >= 2009:
                    is_sorento_r = True

        # 4. 그랜저 (5세대 HG vs 6세대 전기 IG vs 6세대 후기 더뉴그랜저IG vs 7세대 GN7 디올뉴)
        is_grandeur = '그랜저' in full_query_text
        is_grandeur_gn7 = False
        is_grandeur_new_ig = False
        is_grandeur_ig = False
        is_grandeur_hg = False
        if is_grandeur:
            if any(k in full_query_text for k in ['gn7', '디올뉴', '7세대']):
                is_grandeur_gn7 = True
            elif any(k in full_query_text for k in ['더뉴그랜저', '르블랑']) or (target_year and 2020 <= target_year <= 2022 and 'hg' not in full_query_text):
                is_grandeur_new_ig = True
            elif any(k in full_query_text for k in ['그랜저ig', 'ig']) or (target_year and 2017 <= target_year <= 2019 and 'hg' not in full_query_text):
                is_grandeur_ig = True
            elif any(k in full_query_text for k in ['hg', '5세대']) or (target_year and target_year <= 2016):
                is_grandeur_hg = True
            elif target_year:
                if target_year >= 2023:
                    is_grandeur_gn7 = True
                elif target_year >= 2020:
                    is_grandeur_new_ig = True
                elif target_year >= 2017:
                    is_grandeur_ig = True
                else:
                    is_grandeur_hg = True

        # 5. 스포티지 (4세대 전기 QL/신형스포티지 vs 4세대 페이스리프트 더볼드 vs 5세대 NQ5 디올뉴)
        is_sportage = '스포티지' in full_query_text
        is_sportage_gen4_early = False
        is_sportage_thebold = False
        is_sportage_gen5 = False
        if is_sportage:
            if any(k in full_query_text for k in ['5세대', 'nq5', '디올뉴']):
                is_sportage_gen5 = True
            elif any(k in full_query_text for k in ['더볼드', '스포티지더볼드']):
                is_sportage_thebold = True
            elif any(k in full_query_text for k in ['4세대', '신형스포티지', '스포티지ql', 'thesuv']):
                if target_year and target_year >= 2019:
                    is_sportage_thebold = True
                else:
                    is_sportage_gen4_early = True
            elif target_year:
                if target_year >= 2021:
                    is_sportage_gen5 = True
                elif target_year >= 2019:
                    is_sportage_thebold = True
                elif target_year >= 2015:
                    is_sportage_gen4_early = True

        # 2. 동의어/별칭 후보군 확장
        candidates = [c_clean]
        if is_k5_gen2:
            candidates.extend(["신형k5", "뉴신형k5", "k52세대"])
        elif is_k5_gen3:
            candidates.extend(["신형k5(dl3)", "더뉴k5(dl3)", "k53세대", "k5dl3"])
        elif is_grandeur_gn7:
            candidates.extend(["그랜저gn7", "디올뉴그랜저"])
        elif is_grandeur_new_ig:
            candidates.extend(["더뉴그랜저", "더뉴그랜저ig"])
        elif is_grandeur_ig:
            candidates.extend(["그랜저ig"])
        elif is_grandeur_hg:
            candidates.extend(["그랜저hg"])
        elif is_sportage_gen4_early:
            candidates.extend(["신형스포티지", "스포티지4세대"])
        elif is_sportage_thebold:
            candidates.extend(["스포티지더볼드"])
        elif is_sportage_gen5:
            candidates.extend(["디올뉴스포티지", "스포티지5세대"])
        elif is_sorento_r:
            candidates.extend(["쏘렌토r"])
        elif is_sorento_new_r:
            candidates.extend(["뉴쏘렌토r", "뉴쏘렌토"])
        elif is_sorento_um:
            candidates.extend(["올뉴쏘렌토", "더뉴쏘렌토", "쏘렌토um"])
        elif is_sorento_gen4:
            candidates.extend(["쏘렌토4세대", "디올뉴쏘렌토", "쏘렌토mq4"])
        elif c_clean in self.SYNONYM_MAP:
            candidates.extend(self.SYNONYM_MAP[c_clean])

        for k, v in self.SYNONYM_MAP.items():
            if (k in c_clean or c_clean in k) and not (is_k5_gen2 and 'dl3' in k) and not (is_k5_gen3 and k in ('k52세대', '신형k5')):
                if is_sorento_r and ('뉴' in k or '올뉴' in k or '더뉴' in k or 'mq4' in k):
                    continue
                candidates.extend(v)

        # 코어 차종군 탐색 (예: 코란도, 카니발 등)
        core = None
        for cc in self.CORE_CAR_NAMES:
            if cc in c_clean:
                core = cc
                break

        # 1차: 차량명 또는 별칭 포함 검색
        mask = pd.Series(False, index=search_df.index)
        for cand in set(candidates):
            mask = mask | search_df['차량명_clean'].str.contains(cand, na=False, regex=False) | \
                          search_df['차량명_clean'].apply(lambda x: cand in str(x) or str(x) in cand)

        sub_df = search_df[mask]

        # 3. 세대 오매칭 엄격 분리 및 필터링
        if is_k5_gen2 and not sub_df.empty:
            # 2세대 K5 검색 시 3세대 DL3 실적 배제
            filtered_k5_g2 = sub_df[~sub_df['차량명_clean'].str.contains('dl3', na=False)]
            if not filtered_k5_g2.empty:
                sub_df = filtered_k5_g2
        elif is_k5_gen3 and not sub_df.empty:
            # 3세대 K5 검색 시 DL3 실적 우선
            filtered_k5_g3 = sub_df[sub_df['차량명_clean'].str.contains('dl3', na=False)]
            if not filtered_k5_g3.empty:
                sub_df = filtered_k5_g3

        if is_carnival_gen4 and not sub_df.empty:
            filtered_c4 = sub_df[sub_df['차량명_clean'].str.contains('4세대|ka4', na=False)]
            if not filtered_c4.empty: sub_df = filtered_c4
        elif is_carnival_old and not sub_df.empty:
            filtered_co = sub_df[~sub_df['차량명_clean'].str.contains('4세대|ka4', na=False)]
            if not filtered_co.empty: sub_df = filtered_co

        if is_sorento_r and not sub_df.empty:
            # 쏘렌토 R (2009~2012) 검색 시 뉴쏘렌토R, 올뉴, 더뉴, 4세대 절대 배제
            filtered_sr = sub_df[sub_df['차량명_clean'].str.contains('^쏘렌토r', na=False) & ~sub_df['차량명_clean'].str.contains('뉴|올뉴|더뉴|4세대|mq4', na=False)]
            sub_df = filtered_sr
        elif is_sorento_new_r and not sub_df.empty:
            filtered_snr = sub_df[sub_df['차량명_clean'].str.contains('뉴쏘렌토', na=False) & ~sub_df['차량명_clean'].str.contains('올뉴|더뉴|4세대|mq4', na=False)]
            sub_df = filtered_snr
        elif is_sorento_um and not sub_df.empty:
            filtered_sum = sub_df[sub_df['차량명_clean'].str.contains('올뉴|더뉴|um', na=False) & ~sub_df['차량명_clean'].str.contains('4세대|mq4', na=False)]
            sub_df = filtered_sum
        elif is_sorento_gen4 and not sub_df.empty:
            filtered_s4 = sub_df[sub_df['차량명_clean'].str.contains('4세대|mq4', na=False)]
            if not filtered_s4.empty: sub_df = filtered_s4

        if is_sportage_gen4_early and not sub_df.empty:
            filtered_sp_g4 = sub_df[sub_df['차량명_clean'].str.contains('신형스포티지', na=False)]
            if not filtered_sp_g4.empty: sub_df = filtered_sp_g4
        elif is_sportage_thebold and not sub_df.empty:
            filtered_sp_tb = sub_df[sub_df['차량명_clean'].str.contains('더볼드', na=False)]
            if not filtered_sp_tb.empty: sub_df = filtered_sp_tb
        elif is_sportage_gen5 and not sub_df.empty:
            filtered_sp_g5 = sub_df[sub_df['차량명_clean'].str.contains('디올뉴', na=False)]
            if not filtered_sp_g5.empty: sub_df = filtered_sp_g5

        if is_grandeur_ig and not sub_df.empty:
            filtered_gig = sub_df[sub_df['차량명_clean'].str.contains('그랜저ig', na=False) & ~sub_df['차량명_clean'].str.contains('더뉴', na=False)]
            if not filtered_gig.empty: sub_df = filtered_gig
        elif is_grandeur_new_ig and not sub_df.empty:
            filtered_gnig = sub_df[sub_df['차량명_clean'].str.contains('더뉴그랜저', na=False)]
            if not filtered_gnig.empty: sub_df = filtered_gnig
        elif is_grandeur_gn7 and not sub_df.empty:
            filtered_ggn7 = sub_df[sub_df['차량명_clean'].str.contains('디올뉴', na=False)]
            if not filtered_ggn7.empty: sub_df = filtered_ggn7
        elif is_grandeur_hg and not sub_df.empty:
            filtered_ghg = sub_df[sub_df['차량명_clean'].str.contains('그랜저hg', na=False)]
            if not filtered_ghg.empty: sub_df = filtered_ghg

        # 만약 결과가 없거나 부족하면 코어 차종으로 확장 (단, 세대 필터 유지 및 세대 불일치 강제 확장 금지)
        # 사용자 원칙: "없으면 표시 안 해도 돼, 혼란만 줄 뿐이야" -> 다른 세대나 다른 차종 강제 유입 금지
        if (sub_df.empty or len(sub_df) < 3) and core and not is_sorento_r:
            core_sub = search_df[search_df['차량명_clean'].str.contains(core, na=False, regex=False)]
            if is_k5_gen2:
                core_sub = core_sub[~core_sub['차량명_clean'].str.contains('dl3', na=False)]
            elif is_k5_gen3:
                core_sub = core_sub[core_sub['차량명_clean'].str.contains('dl3', na=False)]
            elif is_sorento_new_r:
                core_sub = core_sub[core_sub['차량명_clean'].str.contains('뉴쏘렌토', na=False)]
            elif is_sorento_um:
                core_sub = core_sub[core_sub['차량명_clean'].str.contains('올뉴|더뉴', na=False)]
            elif is_sorento_gen4:
                core_sub = core_sub[core_sub['차량명_clean'].str.contains('4세대|mq4', na=False)]
            elif is_grandeur_ig:
                core_sub = core_sub[core_sub['차량명_clean'].str.contains('그랜저ig', na=False) & ~core_sub['차량명_clean'].str.contains('더뉴', na=False)]
            elif is_grandeur_new_ig:
                core_sub = core_sub[core_sub['차량명_clean'].str.contains('더뉴그랜저', na=False)]
            elif is_grandeur_gn7:
                core_sub = core_sub[core_sub['차량명_clean'].str.contains('디올뉴', na=False)]
            if not core_sub.empty:
                sub_df = core_sub

        # =========================================================================
        # 🎯 [2단계: 차종·등급(유종/배기량/트림)·연식(±1년) 정밀 매칭 엔진]
        # =========================================================================
        base_car_title = str(sub_df['차량명'].iloc[0]) if not sub_df.empty else str(car_name)
        matched_tier = "차종 전체 매칭"
        matched_name = f"{base_car_title} (전체)"
        year_band_desc = ""

        if not sub_df.empty:
            # 1. 유종(Fuel) 분리 필터
            is_query_hybrid = any(k in full_query_text for k in ['하이브리드', 'hybrid', 'hev'])
            is_query_lpi = any(k in full_query_text for k in ['lpi', 'lpg', '렌터카', '장애인'])
            is_query_diesel = any(k in full_query_text for k in ['디젤', 'diesel', 'crdi', 'vgt'])
            is_query_ev = any(k in full_query_text for k in ['전기', 'ev', 'electric'])
            is_query_gasoline = any(k in full_query_text for k in ['가솔린', 'gasoline', 'gdi', 't-gdi', '터보', 'turbo'])

            fuel_filtered = sub_df.copy()
            fuel_label = ""
            if is_query_hybrid:
                f_mask = fuel_filtered['차량명_clean'].str.contains('하이브리드', na=False) | fuel_filtered['세부모델_clean'].str.contains('hev', na=False)
                if f_mask.any():
                    fuel_filtered = fuel_filtered[f_mask]
                    fuel_label = "하이브리드"
            elif is_query_lpi:
                f_mask = fuel_filtered['세부모델_clean'].str.contains('lpi|lpg|렌터카|장애인', na=False)
                if f_mask.any():
                    fuel_filtered = fuel_filtered[f_mask]
                    fuel_label = "LPi"
            elif is_query_diesel:
                f_mask = fuel_filtered['차량명_clean'].str.contains('디젤', na=False) | fuel_filtered['세부모델_clean'].str.contains('디젤|crdi|vgt', na=False)
                if f_mask.any():
                    fuel_filtered = fuel_filtered[f_mask]
                    fuel_label = "디젤"
            elif is_query_ev:
                f_mask = fuel_filtered['차량명_clean'].str.contains('ev|전기', na=False) | fuel_filtered['세부모델_clean'].str.contains('ev|전기', na=False)
                if f_mask.any():
                    fuel_filtered = fuel_filtered[f_mask]
                    fuel_label = "전기"
            else:
                f_mask = ~fuel_filtered['차량명_clean'].str.contains('하이브리드', na=False) & ~fuel_filtered['세부모델_clean'].str.contains('hev|lpi|lpg|디젤', na=False)
                if f_mask.any():
                    fuel_filtered = fuel_filtered[f_mask]
                    fuel_label = "가솔린"

            # 2. 배기량(Displacement) 추출 및 필터
            disp_match = re.search(r'(\d\.\d)', str(sub_model) + " " + str(car_name))
            disp_val = disp_match.group(1) if disp_match else ""
            disp_filtered = fuel_filtered.copy()
            if disp_val:
                d_mask = disp_filtered['세부모델_clean'].str.contains(disp_val, na=False)
                if d_mask.any():
                    disp_filtered = disp_filtered[d_mask]

            # 3. 연식 밴드(Year Band: 기준 연식 ±1년) 필터 풀 생성
            has_year_col = '등록연도_num' in disp_filtered.columns
            year_pool = disp_filtered.copy()
            year_band_active = False
            if target_year and target_year >= 2000 and has_year_col:
                y_min = target_year - 1
                y_max = target_year + 1
                y_mask = disp_filtered['등록연도_num'].between(y_min, y_max)
                if y_mask.any():
                    year_pool = disp_filtered[y_mask]
                    year_band_desc = f"{y_min}~{y_max}년식"
                    year_band_active = True

            # 4. 세부 트림(Trim) 정밀 매칭
            sub_tokens = re.findall(r'[a-zA-Z0-9\.]+|[가-힣]+', str(sub_model).lower())
            stop_words = {'가솔린', '디젤', '하이브리드', 'hev', 'lpi', 'lpg', '2wd', '4wd', 'awd', 'auto', 'a/t', '오토'}
            meaningful_tokens = [t for t in sub_tokens if t not in stop_words and (len(t) >= 2 or t.isalnum())]

            best_subset = pd.DataFrame()
            matched_trim_title = ""

            if meaningful_tokens:
                def score_row(row_val):
                    rv = str(row_val).lower()
                    return sum(1 for t in meaningful_tokens if t in rv)

                # A) 연식 밴드가 적용된 풀에서 세부 트림 검색 (Tier 1 후보)
                scores_year = year_pool['세부모델_clean'].apply(score_row)
                max_s_year = scores_year.max() if not scores_year.empty else 0
                if max_s_year >= 1:
                    cand_trim_year = year_pool[scores_year == max_s_year]
                    if len(cand_trim_year) >= 3:
                        best_subset = cand_trim_year
                        matched_tier = "🎯 정밀 등급·연식 매칭"
                        matched_trim_title = str(best_subset['세부모델'].iloc[0])

                # B) 연식 밴드에서 표본 부족 시, 연식 제한을 푼 disp_filtered에서 동일 세부 트림 검색 (Tier 3 후보)
                if best_subset.empty:
                    scores_all = disp_filtered['세부모델_clean'].apply(score_row)
                    max_s_all = scores_all.max() if not scores_all.empty else 0
                    if max_s_all >= 1:
                        cand_trim_all = disp_filtered[scores_all == max_s_all]
                        if len(cand_trim_all) >= 3:
                            best_subset = cand_trim_all
                            matched_tier = "🏷️ 동일 등급 전체연식 매칭"
                            matched_trim_title = str(best_subset['세부모델'].iloc[0])
                            year_band_active = False
                            year_band_desc = "전체연식"

                # C) 세부 트림 표본이 부족한 경우: 동급 배기량/유종 + 연식군 풀 활용 (Tier 2)
                if best_subset.empty and len(year_pool) >= 3:
                    best_subset = year_pool
                    matched_tier = "📊 동급 배기량/연식군 매칭"
                    fuel_disp_part = f"{fuel_label} {disp_val}".strip()
                    matched_trim_title = f"{fuel_disp_part}군" if fuel_disp_part else "동급 표준형"

            # 5. 최종 풀 및 표시 명칭 결정
            if not best_subset.empty:
                final_df = best_subset
            elif not year_pool.empty and len(year_pool) >= 3:
                final_df = year_pool
                matched_tier = "📊 동급 배기량/연식군 매칭"
                matched_trim_title = f"{fuel_label} {disp_val}".strip()
            else:
                final_df = sub_df
                matched_tier = "🚗 차종 전체 매칭"
                matched_trim_title = ""

            # 최종 안내명 조립
            name_parts = [base_car_title]
            if matched_trim_title:
                name_parts.append(matched_trim_title)
            if year_band_desc:
                name_parts.append(f"({year_band_desc})")
            matched_name = " ".join(name_parts)

            final_df = final_df.copy()
            final_df.attrs['matched_name'] = matched_name
            final_df.attrs['matched_tier'] = matched_tier
            final_df.attrs['year_band'] = year_band_desc
            return final_df

        sub_df = sub_df.copy()
        sub_df.attrs['matched_name'] = matched_name
        sub_df.attrs['matched_tier'] = matched_tier
        return sub_df

    def find_inventory_matches(self, car_name, sub_model="", year=""):
        """현재 자사 보유재고(판매중/계약중) 중에서 동일/동급 차량 검색"""
        if not hasattr(self, 'inventory_df') or self.inventory_df.empty:
            return pd.DataFrame()
        return self.find_matches(car_name, sub_model, year, target_df=self.inventory_df)

    def get_market_stats(self, car_name, sub_model="", year="", current_retail=0):
        """차종별 회전율, 마진, 수요 통계 및 자사 재고 현황 산출 (경매 제외 순수 소매 완판 기준)"""
        matches = self.find_matches(car_name, sub_model, year)
        inv_matches = self.find_inventory_matches(car_name, sub_model, year)

        # 현재 자사 보유재고(판매중/계약중) 현황 분석
        current_stock_count = len(inv_matches)
        if current_stock_count > 0:
            current_stock_avg_days = float(round(inv_matches['경과일수_num'].mean(), 1))
            branch_series = inv_matches.get('지점', pd.Series(dtype=str)).dropna()
            branch_counts = branch_series[branch_series.astype(str).str.strip().ne('')].value_counts()
            top_branches = [f"{b} {c}대" for b, c in branch_counts.head(2).items()]
            branch_summary = ", ".join(top_branches)
            if branch_summary:
                current_stock_desc = f"평균 {current_stock_avg_days}일 보유 ({branch_summary})"
            else:
                current_stock_desc = f"평균 {current_stock_avg_days}일 보유 중"
            stock_color = "#f59e0b" if current_stock_count >= 10 else "#38bdf8"
        else:
            current_stock_avg_days = 0
            current_stock_desc = "현재 자사 미보유 (재고부담 0)"
            stock_color = "#4ade80"

        if matches.empty:
            return {
                "has_data": False,
                "pure_sales_count": getattr(self, 'pure_sales_count', 0),
                "auction_filtered_count": getattr(self, 'auction_filtered_count', 0),
                "current_stock_count": current_stock_count,
                "current_stock_avg_days": current_stock_avg_days,
                "current_stock_desc": current_stock_desc,
                "stock_color": stock_color,
                "total_count": 0,
                "avg_days": 0,
                "median_days": 0,
                "turnover_grade": "-",
                "turnover_desc": "과거 소매 완판 데이터 없음",
                "avg_profit": 0,
                "profit_rate": 0,
                "avg_mileage": 0,
                "avg_sell_price": 0,
                "under_30_pct": 0,
                "over_60_pct": 0,
                "demand_level": "보통",
                "demand_badge": "⚪ 보통",
                "aggressive_margin": 100,
                "standard_margin": 180,
                "defensive_margin": 280,
                "aggressive_bid": int(current_retail - 100) if current_retail > 100 else 0,
                "standard_bid": int(current_retail - 180) if current_retail > 180 else 0,
                "defensive_bid": int(current_retail - 280) if current_retail > 280 else 0,
                "sample_desc": f"'{car_name}' 관련 최근 소매 완판 실적 데이터가 부족합니다."
            }

        total_count = len(matches)
        days_series = matches['경과일수_num']
        profit_series = matches['이익_만원']
        sell_p_series = matches['판매가_만원']

        avg_days = float(round(days_series.mean(), 1))
        median_days = int(round(days_series.median()))
        under_30_pct = int(round(((days_series <= 30).sum() / total_count) * 100))
        over_60_pct = int(round(((days_series >= 60).sum() / total_count) * 100))

        avg_profit = float(round(profit_series.mean(), 1))
        avg_sell_p = float(sell_p_series.mean()) if sell_p_series.mean() > 0 else 1
        profit_rate = float(round((avg_profit / avg_sell_p) * 100, 1)) if avg_sell_p > 0 else 0
        avg_sell_price = int(round(avg_sell_p))

        mileage_series = pd.to_numeric(matches.get('주행거리_num', matches.get('주행거리', 0)), errors='coerce').fillna(0)
        valid_mileage = mileage_series[mileage_series >= 1000]
        avg_mileage = int(round(valid_mileage.mean())) if not valid_mileage.empty else int(round(mileage_series.mean()))

        # 회전율 등급 평가 (순수 소매 완판 기준)
        if avg_days <= 30 or under_30_pct >= 60:
            turnover_grade = "S (초고속 완판)"
            turnover_color = "#38bdf8"
            turnover_desc = f"순수 소매 평균 {avg_days}일 만에 완판! 30일 이내 회전율 {under_30_pct}%로 회전이 극도로 빠른 효자 차종입니다."
            rec_strategy = "공격적 입찰 추천 (마진 80~100만 원만 잡고 높은 입찰가로 매입 성공률 극대화)"
            agg_m = 90
            std_m = 160
            def_m = 250
        elif avg_days <= 45 or under_30_pct >= 40:
            turnover_grade = "A (빠른 회전)"
            turnover_color = "#4ade80"
            turnover_desc = f"순수 소매 평균 {avg_days}일 소요. 45일 이내 매각 확률이 높아 안정적 마진 확보가 가능합니다."
            rec_strategy = "표준 입찰 추천 (기본 기대 마진 150~180만 원 확보)"
            agg_m = 110
            std_m = 180
            def_m = 280
        elif avg_days <= 60:
            turnover_grade = "B (보통 회전)"
            turnover_color = "#facc15"
            turnover_desc = f"순수 소매 평균 {avg_days}일 소요. 60일 이상 장기재고 비율({over_60_pct}%)을 고려하여 적정 마진을 유지하세요."
            rec_strategy = "신중 입찰 (마진 200만 원 이상 권장)"
            agg_m = 130
            std_m = 210
            def_m = 320
        else:
            turnover_grade = "C (장기재고 주의)"
            turnover_color = "#ef4444"
            turnover_desc = f"순수 소매 평균 재고일 {avg_days}일, 60일 초과 비율이 {over_60_pct}%에 달합니다. 소매 장기화 주의가 필요합니다."
            rec_strategy = "방어적 입찰 필수 (안전 마진 280~350만 원 이상 확보하여 가격 하락 방어)"
            agg_m = 160
            std_m = 250
            def_m = 350

        # 자사 보유재고 상황에 따른 추가 비딩 조언
        if current_stock_count >= 10:
            rec_strategy += f" (⚠️ 현재 자사 보유재고 {current_stock_count}대로 과밀 상태)"
        elif current_stock_count == 0:
            rec_strategy += f" (✨ 현재 자사 미보유 모델로 빠른 전시/판매 유리)"

        # 수요 지수 산출 (찜수, 조회수, 상담수)
        views = pd.to_numeric(matches.get('RB조회수', 0), errors='coerce').fillna(0) + \
                pd.to_numeric(matches.get('E조회수', 0), errors='coerce').fillna(0)
        likes = pd.to_numeric(matches.get('RB찜수', 0), errors='coerce').fillna(0) + \
                pd.to_numeric(matches.get('E찜수', 0), errors='coerce').fillna(0)
        inquiries = pd.to_numeric(matches.get('RB상담수', 0), errors='coerce').fillna(0) + \
                    pd.to_numeric(matches.get('E상담수', 0), errors='coerce').fillna(0)

        avg_likes = likes.mean()
        avg_inq = inquiries.mean()

        if avg_likes >= 8 or avg_inq >= 2.0 or total_count >= 100:
            demand_level = "최상 (초인기 차종)"
            demand_badge = "🔥 폭발적 수요"
        elif avg_likes >= 4 or avg_inq >= 1.0 or total_count >= 50:
            demand_level = "높음 (인기 차종)"
            demand_badge = "✨ 높은 수요"
        else:
            demand_level = "보통"
            demand_badge = "☕ 보통 수요"

        # 입찰가 산출 (소매가가 주어진 경우)
        current_retail = float(current_retail) if current_retail else 0
        aggressive_bid = int(round(current_retail - agg_m)) if current_retail > agg_m else 0
        standard_bid = int(round(current_retail - std_m)) if current_retail > std_m else 0
        defensive_bid = int(round(current_retail - def_m)) if current_retail > def_m else 0

        # 대표 모델명 및 정밀 매칭 메타데이터
        matched_model_name = matches.attrs.get('matched_name') if hasattr(matches, 'attrs') and matches.attrs.get('matched_name') else matches['차량명'].iloc[0]
        matched_tier = matches.attrs.get('matched_tier', '정밀 매칭') if hasattr(matches, 'attrs') and matches.attrs.get('matched_tier') else '정밀 매칭'
        matched_year_band = matches.attrs.get('year_band', '') if hasattr(matches, 'attrs') else ''

        return {
            "has_data": True,
            "matched_name": matched_model_name,
            "matched_tier": matched_tier,
            "matched_year_band": matched_year_band,
            "pure_sales_count": getattr(self, 'pure_sales_count', 0),
            "auction_filtered_count": getattr(self, 'auction_filtered_count', 0),
            "current_stock_count": current_stock_count,
            "current_stock_avg_days": current_stock_avg_days,
            "current_stock_desc": current_stock_desc,
            "stock_color": stock_color,
            "total_count": total_count,
            "avg_days": avg_days,
            "median_days": median_days,
            "under_30_pct": under_30_pct,
            "over_60_pct": over_60_pct,
            "turnover_grade": turnover_grade,
            "turnover_color": turnover_color,
            "turnover_desc": turnover_desc,
            "avg_profit": avg_profit,
            "profit_rate": profit_rate,
            "avg_mileage": avg_mileage,
            "avg_sell_price": avg_sell_price,
            "demand_level": demand_level,
            "demand_badge": demand_badge,
            "rec_strategy": rec_strategy,
            "aggressive_margin": agg_m,
            "standard_margin": std_m,
            "defensive_margin": def_m,
            "aggressive_bid": aggressive_bid,
            "standard_bid": standard_bid,
            "defensive_bid": defensive_bid,
            "sample_desc": f"과거 순수 소매 완판 {total_count:,}대 실거래 기준: 평균 재고 {avg_days}일, 평균 실현마진 +{int(avg_profit):,}만 원 (마진율 {profit_rate}%)"
        }

    # 오토플러스 표기 -> 엔카(Encar) 공식 제조사 및 대표 모델그룹 매핑 데이터베이스
    ENCA_BRAND_MODELS = [
        # 제네시스
        ("제네시스", ["eq900"], "EQ900"),
        ("제네시스", ["gv60"], "GV60"),
        ("제네시스", ["gv70"], "GV70"),
        ("제네시스", ["gv80"], "GV80"),
        ("제네시스", ["g70"], "G70"),
        ("제네시스", ["g80"], "G80"),
        ("제네시스", ["g90"], "G90"),
        
        # 현대
        ("현대", ["그랜저", "그랜져"], "그랜저"),
        ("현대", ["아반떼", "아반테"], "아반떼"),
        ("현대", ["쏘나타", "소나타"], "쏘나타"),
        ("현대", ["투싼"], "투싼"),
        ("현대", ["싼타페", "산타페"], "싼타페"),
        ("현대", ["팰리세이드", "펠리세이드"], "팰리세이드"),
        ("현대", ["캐스퍼"], "캐스퍼"),
        ("현대", ["코나"], "코나"),
        ("현대", ["베뉴"], "베뉴"),
        ("현대", ["스타리아"], "스타리아"),
        ("현대", ["스타렉스"], "스타렉스"),
        ("현대", ["포터", "포터2", "포터ii"], "포터"),
        ("현대", ["아이오닉5", "아이오닉6", "아이오닉"], "아이오닉"),
        ("현대", ["맥스크루즈"], "맥스크루즈"),
        ("현대", ["벨로스터"], "벨로스터"),
        ("현대", ["i30"], "i30"),
        ("현대", ["i40"], "i40"),
        ("현대", ["에쿠스"], "에쿠스"),
        ("현대", ["엑센트"], "엑센트"),
        ("현대", ["넥쏘"], "넥쏘"),
        ("현대", ["아슬란"], "아슬란"),
        ("현대", ["쏠라티"], "쏠라티"),
        ("현대", ["마이티"], "마이티"),
        ("현대", ["제네시스dh", "제네시스쿠페", "제네시스프라다"], "제네시스"),

        # 기아
        ("기아", ["카니발"], "카니발"),
        ("기아", ["쏘렌토", "소렌토"], "쏘렌토"),
        ("기아", ["스포티지"], "스포티지"),
        ("기아", ["k3"], "K3"),
        ("기아", ["k5"], "K5"),
        ("기아", ["k7"], "K7"),
        ("기아", ["k8"], "K8"),
        ("기아", ["k9"], "K9"),
        ("기아", ["레이"], "레이"),
        ("기아", ["모닝"], "모닝"),
        ("기아", ["셀토스"], "셀토스"),
        ("기아", ["니로"], "니로"),
        ("기아", ["모하비"], "모하비"),
        ("기아", ["봉고", "봉고3", "봉고iii"], "봉고"),
        ("기아", ["ev3"], "EV3"),
        ("기아", ["ev5"], "EV5"),
        ("기아", ["ev6"], "EV6"),
        ("기아", ["ev9"], "EV9"),
        ("기아", ["스팅어"], "스팅어"),
        ("기아", ["스토닉"], "스토닉"),
        ("기아", ["오피러스"], "오피러스"),
        ("기아", ["프라이드"], "프라이드"),
        ("기아", ["카렌스"], "카렌스"),
        ("기아", ["쏘울"], "쏘울"),
        ("기아", ["포르테"], "포르테"),
        ("기아", ["로체"], "로체"),
        ("기아", ["타스만"], "타스만"),

        # 쉐보레(GM대우)
        ("쉐보레(GM대우)", ["스파크"], "스파크"),
        ("쉐보레(GM대우)", ["트레일블레이저"], "트레일블레이저"),
        ("쉐보레(GM대우)", ["트랙스"], "트랙스"),
        ("쉐보레(GM대우)", ["말리부"], "말리부"),
        ("쉐보레(GM대우)", ["볼트"], "볼트"),
        ("쉐보레(GM대우)", ["임팔라"], "임팔라"),
        ("쉐보레(GM대우)", ["크루즈"], "크루즈"),
        ("쉐보레(GM대우)", ["올란도"], "올란도"),
        ("쉐보레(GM대우)", ["이쿼녹스"], "이쿼녹스"),
        ("쉐보레(GM대우)", ["콜로라도"], "콜로라도"),
        ("쉐보레(GM대우)", ["트래버스"], "트래버스"),
        ("쉐보레(GM대우)", ["캡티바"], "캡티바"),
        ("쉐보레(GM대우)", ["알페온"], "알페온"),
        ("쉐보레(GM대우)", ["카마로"], "카마로"),
        ("쉐보레(GM대우)", ["다마스"], "다마스"),
        ("쉐보레(GM대우)", ["라보"], "라보"),

        # 르노코리아(삼성)
        ("르노코리아(삼성)", ["qm6"], "QM6"),
        ("르노코리아(삼성)", ["xm3"], "XM3"),
        ("르노코리아(삼성)", ["sm6"], "SM6"),
        ("르노코리아(삼성)", ["sm5"], "SM5"),
        ("르노코리아(삼성)", ["sm3"], "SM3"),
        ("르노코리아(삼성)", ["sm7"], "SM7"),
        ("르노코리아(삼성)", ["qm3"], "QM3"),
        ("르노코리아(삼성)", ["qm5"], "QM5"),
        ("르노코리아(삼성)", ["그랑콜레오스", "콜레오스"], "그랑 콜레오스"),
        ("르노코리아(삼성)", ["아르카나"], "아르카나"),
        ("르노코리아(삼성)", ["캡처", "캡쳐"], "캡처"),
        ("르노코리아(삼성)", ["클리오"], "클리오"),
        ("르노코리아(삼성)", ["마스터"], "마스터"),

        # KG모빌리티(쌍용)
        ("KG모빌리티(쌍용)", ["티볼리"], "티볼리"),
        ("KG모빌리티(쌍용)", ["토레스"], "토레스"),
        ("KG모빌리티(쌍용)", ["렉스턴"], "렉스턴"),
        ("KG모빌리티(쌍용)", ["코란도"], "코란도"),
        ("KG모빌리티(쌍용)", ["액티언"], "액티언"),
        ("KG모빌리티(쌍용)", ["투리스모"], "투리스모"),
        ("KG모빌리티(쌍용)", ["체어맨"], "체어맨"),

        # 벤츠
        ("벤츠", ["cls-클래스", "cls클래스", "cls"], "CLS-클래스"),
        ("벤츠", ["cla-클래스", "cla클래스", "cla"], "CLA-클래스"),
        ("벤츠", ["cle-클래스", "cle클래스", "cle"], "CLE"),
        ("벤츠", ["glc-클래스", "glc클래스", "glc"], "GLC-클래스"),
        ("벤츠", ["gle-클래스", "gle클래스", "gle"], "GLE-클래스"),
        ("벤츠", ["gla-클래스", "gla클래스", "gla"], "GLA-클래스"),
        ("벤츠", ["glb-클래스", "glb클래스", "glb"], "GLB-클래스"),
        ("벤츠", ["gls-클래스", "gls클래스", "gls"], "GLS-클래스"),
        ("벤츠", ["glk-클래스", "glk클래스", "glk"], "GLK-클래스"),
        ("벤츠", ["g-클래스", "g클래스", "g바겐"], "G-클래스"),
        ("벤츠", ["e-클래스", "e클래스", "e class"], "E-클래스"),
        ("벤츠", ["c-클래스", "c클래스", "c class"], "C-클래스"),
        ("벤츠", ["s-클래스", "s클래스", "s class"], "S-클래스"),
        ("벤츠", ["a-클래스", "a클래스"], "A-클래스"),
        ("벤츠", ["b-클래스", "b클래스"], "B-클래스"),
        ("벤츠", ["eqe"], "EQE"),
        ("벤츠", ["eqs"], "EQS"),
        ("벤츠", ["eqa"], "EQA"),
        ("벤츠", ["eqb"], "EQB"),

        # BMW
        ("BMW", ["1시리즈", "1er"], "1시리즈"),
        ("BMW", ["2시리즈", "2er"], "2시리즈"),
        ("BMW", ["3시리즈", "3er"], "3시리즈"),
        ("BMW", ["4시리즈", "4er"], "4시리즈"),
        ("BMW", ["5시리즈", "5er"], "5시리즈"),
        ("BMW", ["6시리즈", "6er"], "6시리즈"),
        ("BMW", ["7시리즈", "7er"], "7시리즈"),
        ("BMW", ["8시리즈", "8er"], "8시리즈"),
        ("BMW", ["x1"], "X1"),
        ("BMW", ["x2"], "X2"),
        ("BMW", ["x3"], "X3"),
        ("BMW", ["x4"], "X4"),
        ("BMW", ["x5"], "X5"),
        ("BMW", ["x6"], "X6"),
        ("BMW", ["x7"], "X7"),
        ("BMW", ["z4"], "Z4"),
        ("BMW", ["ix"], "iX"),
        ("BMW", ["i4"], "i4"),

        # 아우디
        ("아우디", ["a3"], "A3"),
        ("아우디", ["a4"], "A4"),
        ("아우디", ["a5"], "A5"),
        ("아우디", ["a6"], "A6"),
        ("아우디", ["a7"], "A7"),
        ("아우디", ["a8"], "A8"),
        ("아우디", ["q2"], "Q2"),
        ("아우디", ["q3"], "Q3"),
        ("아우디", ["q5"], "Q5"),
        ("아우디", ["q7"], "Q7"),
        ("아우디", ["q8"], "Q8"),
        ("아우디", ["e-트론", "etron"], "e-트론"),

        # 폭스바겐
        ("폭스바겐", ["골프"], "골프"),
        ("폭스바겐", ["티구안"], "티구안"),
        ("폭스바겐", ["아테온"], "아테온"),
        ("폭스바겐", ["제타"], "제타"),
        ("폭스바겐", ["파사트"], "파사트"),
        ("폭스바겐", ["투아렉"], "투아렉"),

        # 볼보
        ("볼보", ["xc40"], "XC40"),
        ("볼보", ["xc60"], "XC60"),
        ("볼보", ["xc90"], "XC90"),
        ("볼보", ["s60"], "S60"),
        ("볼보", ["s90"], "S90"),
        ("볼보", ["v60"], "V60"),
        ("볼보", ["v90"], "V90"),

        # 포르쉐
        ("포르쉐", ["카이엔"], "카이엔"),
        ("포르쉐", ["파나메라"], "파나메라"),
        ("포르쉐", ["타이칸"], "타이칸"),
        ("포르쉐", ["마칸"], "마칸"),
        ("포르쉐", ["911"], "911"),
        ("포르쉐", ["박스터"], "박스터"),
        ("포르쉐", ["카이맨"], "카이맨"),

        # 테슬라
        ("테슬라", ["모델y", "modely"], "모델 Y"),
        ("테슬라", ["모델3", "model3"], "모델 3"),
        ("테슬라", ["모델s", "models"], "모델 S"),
        ("테슬라", ["모델x", "modelx"], "모델 X"),

        # 포드 / 링컨
        ("포드", ["익스플로러"], "익스플로러"),
        ("포드", ["머스탱"], "머스탱"),
        ("링컨", ["에비에이터"], "에비에이터"),
        ("링컨", ["코세어"], "코세어"),
        ("링컨", ["mkz"], "MKZ"),

        # 혼다 / 닛산 / 토요타 / 렉서스
        ("혼다", ["어코드"], "어코드"),
        ("혼다", ["cr-v", "crv"], "CR-V"),
        ("닛산", ["알티마"], "알티마"),
        ("토요타", ["알파드"], "알파드"),
        ("토요타", ["캠리"], "캠리"),
        ("토요타", ["라브4", "rav4"], "RAV4"),
        ("토요타", ["프리우스"], "프리우스"),
        ("렉서스", ["es"], "ES"),
        ("렉서스", ["ls"], "LS"),
        ("렉서스", ["ct"], "CT"),
        ("렉서스", ["nx"], "NX"),
        ("렉서스", ["rx"], "RX"),

        # 지프 / 랜드로버 / 미니 / 푸조 / 폴스타 / 마세라티 / 재규어 / 볼보 / BYD
        ("지프", ["레니게이드"], "레니게이드"),
        ("지프", ["체로키"], "체로키"),
        ("지프", ["컴패스"], "컴패스"),
        ("지프", ["랭글러"], "랭글러"),
        ("지프", ["그랜드체로키"], "그랜드 체로키"),
        ("랜드로버", ["디스커버리"], "디스커버리"),
        ("랜드로버", ["레인지로버"], "레인지로버"),
        ("미니", ["컨트리맨"], "미니"),
        ("미니", ["클럽맨"], "미니"),
        ("미니", ["미니", "쿠퍼"], "미니"),
        ("볼보", ["c40"], "C40"),
        ("마세라티", ["기블리"], "기블리"),
        ("재규어", ["xf"], "XF"),
        ("BYD", ["아토", "atto"], "아토 3"),
        ("푸조", ["508"], "508"),
        ("푸조", ["2008"], "2008"),
        ("푸조", ["5008"], "5008"),
        ("폴스타", ["폴스타2", "폴스타 2"], "폴스타 2"),
    ]

    # 엔카 공식 세부모델(세부 세대) 매핑 테이블
    ENCA_SUB_MODELS = [
        # --- 기아 ---
        (r'더\s*뉴\s*기아\s*레이|더\s*뉴\s*레이|더뉴레이', '레이', '더 뉴 레이'),
        (r'올\s*뉴\s*레이|올뉴레이', '레이', '더 뉴 레이'),
        (r'레이\s*ev|더\s*기아\s*레이\s*ev', '레이', '더 기아 레이 EV'),
        (r'\b레이\b', '레이', '레이'),

        (r'더\s*뉴\s*카니발\s*4세대', '카니발', '더 뉴 카니발 4세대'),
        (r'카니발\s*4세대|신형\s*카니발|ka4|4세대\s*카니발', '카니발', '카니발 4세대'),
        (r'더\s*뉴\s*카니발|더뉴카니발', '카니발', '더 뉴 카니발'),
        (r'올\s*뉴\s*카니발|올뉴카니발', '카니발', '올 뉴 카니발'),

        (r'더\s*뉴\s*k5\s*3세대', 'K5', '더 뉴 K5 3세대'),
        (r'k5\s*3세대|k5\s*dl3|dl3', 'K5', 'K5 3세대'),
        (r'더\s*뉴\s*k5\s*2세대', 'K5', '더 뉴 K5 2세대'),
        (r'k5\s*2세대|신형\s*k5|신형k5|올\s*뉴\s*k5|올뉴k5|\bmx\b|\bsx\b', 'K5', 'K5 2세대'),
        (r'더\s*뉴\s*k5|더뉴k5', 'K5', '더 뉴 K5'),

        (r'더\s*뉴\s*k3|더뉴k3|올\s*뉴\s*k3|올뉴k3', 'K3', '더 뉴 K3 2세대'),
        (r'k3\s*2세대|올\s*뉴\s*k3|올뉴k3', 'K3', '올 뉴 K3'),
        (r'\bk3\b', 'K3', 'K3'),

        (r'k7\s*프리미어|k7프리미어', 'K7', 'K7 프리미어'),
        (r'올\s*뉴\s*k7|올뉴k7', 'K7', '올 뉴 K7'),
        (r'더\s*뉴\s*k7|더뉴k7', 'K7', '더 뉴 K7'),

        (r'더\s*뉴\s*k8|더뉴k8', 'K8', '더 뉴 K8'),
        (r'\bk8\b', 'K8', 'K8'),

        (r'더\s*뉴\s*k9|더뉴k9', 'K9', '더 뉴 K9 (RJ)'),
        (r'더\s*k9|더k9|k9\s*\(rj\)', 'K9', '더 K9 (RJ)'),
        (r'\bk9\b', 'K9', 'K9'),

        (r'더\s*뉴\s*쏘렌토\s*4세대', '쏘렌토', '더 뉴 쏘렌토 4세대'),
        (r'쏘렌토\s*4세대|신형\s*쏘렌토|신형쏘렌토|쏘렌토\s*mq4|mq4', '쏘렌토', '쏘렌토 4세대'),
        (r'더\s*뉴\s*쏘렌토|더뉴쏘렌토', '쏘렌토', '더 뉴 쏘렌토'),
        (r'올\s*뉴\s*쏘렌토|올뉴쏘렌토', '쏘렌토', '올 뉴 쏘렌토'),

        (r'스포티지\s*5세대|디\s*올\s*뉴\s*스포티지|스포티지\s*nq5|nq5', '스포티지', '스포티지 5세대'),
        (r'스포티지\s*더\s*볼드|더볼드', '스포티지', '스포티지 더 볼드'),
        (r'스포티지\s*4세대|스포티지4세대|the\s*suv\s*스포티지|더\s*suv\s*스포티지|신형\s*스포티지|스포티지ql|ql', '스포티지', 'The SUV 스포티지'),
        (r'더\s*뉴\s*스포티지\s*r|더뉴스포티지r', '스포티지', '더 뉴 스포티지 R'),
        (r'스포티지\s*r|스포티지r', '스포티지', '스포티지 R'),

        (r'더\s*뉴\s*셀토스|더뉴셀토스', '셀토스', '더 뉴 셀토스'),
        (r'\b셀토스\b', '셀토스', '셀토스'),

        (r'모닝\s*어반|모닝어반', '모닝', '모닝 어반'),
        (r'더\s*뉴\s*모닝|더뉴모닝', '모닝', '더 뉴 모닝'),
        (r'올\s*뉴\s*모닝|올뉴모닝', '모닝', '올 뉴 모닝 (JA)'),

        (r'디\s*올\s*뉴\s*니로|디올뉴니로', '니로', '디 올 뉴 니로'),
        (r'더\s*뉴\s*니로|더뉴니로', '니로', '더 뉴 니로'),
        (r'\b니로\b', '니로', '니로'),

        (r'모하비\s*더\s*마스터|모하비더마스터', '모하비', '모하비 더 마스터'),
        (r'더\s*뉴\s*모하비|더뉴모하비', '모하비', '더 뉴 모하비'),

        # --- 현대 ---
        (r'디\s*올\s*뉴\s*그랜저|그랜저\s*gn7|gn7', '그랜저', '그랜저 (GN7)'),
        (r'더\s*뉴\s*그랜저\s*ig|더\s*뉴\s*그랜저|더뉴그랜저', '그랜저', '더 뉴 그랜저 IG'),
        (r'그랜저\s*ig|그랜저ig', '그랜저', '그랜저 IG'),
        (r'그랜저\s*hg|그랜저hg', '그랜저', '그랜저 HG'),

        (r'디\s*올\s*뉴\s*싼타페|싼타페\s*mx5|mx5', '싼타페', '디 올 뉴 싼타페'),
        (r'더\s*뉴\s*싼타페|더뉴싼타페', '싼타페', '더 뉴 싼타페'),
        (r'신형\s*싼타페|싼타페\s*tm|싼타페tm', '싼타페', '싼타페 TM'),
        (r'싼타페\s*더\s*프라임|싼타페더프라임', '싼타페', '싼타페 더 프라임'),
        (r'싼타페\s*dm|싼타페\(dm\)', '싼타페', '싼타페 DM'),

        (r'디\s*올\s*뉴\s*투싼|투싼\s*nx4|nx4', '투싼', '디 올 뉴 투싼'),
        (r'더\s*뉴\s*투싼|더뉴투싼', '투싼', '더 뉴 투싼'),
        (r'올\s*뉴\s*투싼|올뉴투싼|신형\s*투싼|신형투싼', '투싼', '올 뉴 투싼'),
        (r'투싼\s*ix|투싼ix|뉴투싼ix', '투싼', '투싼 ix'),

        (r'더\s*뉴\s*팰리세이드|더뉴팰리세이드', '팰리세이드', '더 뉴 팰리세이드'),
        (r'\b팰리세이드\b', '팰리세이드', '팰리세이드'),

        (r'더\s*뉴\s*아반떼\s*cn7|더\s*뉴\s*아반떼\s*\(cn7\)', '아반떼', '더 뉴 아반떼 (CN7)'),
        (r'아반떼\s*cn7|아반떼\(cn7\)|cn7', '아반떼', '아반떼 (CN7)'),
        (r'더\s*뉴\s*아반떼\s*ad|더뉴아반떼ad', '아반떼', '더 뉴 아반떼 AD'),
        (r'아반떼\s*ad|아반떼ad', '아반떼', '아반떼 AD'),
        (r'아반떼\s*md|아반떼md', '아반떼', '아반떼 MD'),

        (r'쏘나타\s*디\s*엣지|디\s*엣지', '쏘나타', '쏘나타 디 엣지(DN8)'),
        (r'쏘나타\s*dn8|쏘나타\(dn8\)|dn8', '쏘나타', '쏘나타 (DN8)'),
        (r'쏘나타\s*뉴\s*라이즈|뉴\s*라이즈', '쏘나타', '쏘나타 뉴 라이즈'),
        (r'lf\s*쏘나타|lf쏘나타', '쏘나타', 'LF 쏘나타'),
        (r'yf\s*쏘나타|yf쏘나타', '쏘나타', 'YF 쏘나타'),

        (r'디\s*올\s*뉴\s*코나|디올뉴코나', '코나', '디 올 뉴 코나'),
        (r'더\s*뉴\s*코나|더뉴코나', '코나', '더 뉴 코나'),
        (r'\b코나\b', '코나', '코나'),

        (r'캐스퍼\s*일렉트릭|캐스퍼일렉트릭', '캐스퍼', '캐스퍼 일렉트릭'),
        (r'\b캐스퍼\b', '캐스퍼', '캐스퍼'),

        (r'더\s*뉴\s*그랜드\s*스타렉스|더뉴그랜드스타렉스', '스타렉스', '더 뉴 그랜드 스타렉스'),
        (r'그랜드\s*스타렉스|그랜드스타렉스', '스타렉스', '그랜드 스타렉스'),
        (r'스타리아', '스타리아', '스타리아'),
        (r'포터\s*ii|포터2|포터ii', '포터', '포터 II'),

        # --- 제네시스 ---
        (r'더\s*올\s*뉴\s*g80|신형\s*g80|g80\s*rg3|rg3', 'G80', 'G80 (RG3)'),
        (r'뉴\s*g80|뉴g80', 'G80', 'G80'),
        (r'\bg80\b', 'G80', 'G80'),

        (r'더\s*뉴\s*g70|더뉴g70', 'G70', '더 뉴 G70'),
        (r'\bg70\b', 'G70', 'G70'),

        (r'신형\s*g90|신형g90|g90\s*\(rs4\)', 'G90', 'G90 (RS4)'),
        (r'\bg90\b', 'G90', 'G90'),

        (r'신형\s*gv70|신형gv70', 'GV70', 'GV70'),
        (r'\bgv70\b', 'GV70', 'GV70'),

        (r'뉴\s*gv80|뉴gv80', 'GV80', 'GV80'),
        (r'\bgv80\b', 'GV80', 'GV80'),

        # --- 르노코리아 / 쉐보레 / KGM ---
        (r'더\s*뉴\s*qm6|더뉴qm6|뉴\s*qm6|신형\s*qm6', 'QM6', '더 뉴 QM6'),
        (r'\bqm6\b', 'QM6', 'QM6'),
        (r'더\s*뉴\s*sm6|더뉴sm6', 'SM6', '더 뉴 SM6'),
        (r'\bsm6\b', 'SM6', 'SM6'),
        (r'xm3\s*하이브리드|xm3', 'XM3', 'XM3'),

        (r'트랙스\s*크로스오버|트랙스크로스오버', '트랙스', '트랙스 크로스오버'),
        (r'더\s*뉴\s*트랙스|더뉴트랙스', '트랙스', '더 뉴 트랙스'),
        (r'\b트랙스\b', '트랙스', '트랙스'),

        (r'더\s*뉴\s*트레일블레이저|더뉴트레일블레이저', '트레일블레이저', '더 뉴 트레일블레이저'),
        (r'\b트레일블레이저\b', '트레일블레이저', '트레일블레이저'),

        (r'더\s*뉴\s*말리부|더뉴말리부', '말리부', '더 뉴 말리부'),
        (r'올\s*뉴\s*말리부|올뉴말리부', '말리부', '올 뉴 말리부'),
        (r'\b말리부\b', '말리부', '말리부'),

        (r'더\s*넥스트\s*스파크|더넥스트스파크', '스파크', '더 넥스트 스파크'),
        (r'더\s*뉴\s*스파크|더뉴스파크', '스파크', '더 뉴 스파크'),
        (r'\b스파크\b', '스파크', '스파크'),

        (r'더\s*뉴\s*토레스|더뉴토레스', '토레스', '더 뉴 토레스'),
        (r'\b토레스\b', '토레스', '토레스'),

        (r'더\s*뉴\s*티볼리|더뉴티볼리|베리\s*뉴\s*티볼리|베리뉴티볼리', '티볼리', '베리 뉴 티볼리'),
        (r'티볼리\s*아머|티볼리아머', '티볼리', '티볼리 아머'),
        (r'\b티볼리\b', '티볼리', '티볼리'),

        (r'더\s*뉴\s*렉스턴\s*스포츠\s*칸', '렉스턴', '더 뉴 렉스턴 스포츠 칸'),
        (r'더\s*뉴\s*렉스턴\s*스포츠', '렉스턴', '더 뉴 렉스턴 스포츠'),
        (r'렉스턴\s*스포츠', '렉스턴', '렉스턴 스포츠'),
        (r'올\s*뉴\s*렉스턴|g4\s*렉스턴', '렉스턴', '올 뉴 렉스턴'),

        (r'더\s*뉴\s*맥스크루즈|더뉴맥스크루즈', '맥스크루즈', '더 뉴 맥스크루즈'),
        (r'\b맥스크루즈\b', '맥스크루즈', '맥스크루즈'),

        # --- 수입차 및 잔여 차종 ---
        (r'e-?클래스\s*\(5세대\)|e클래스\(5세대\)|w213', 'E-클래스', 'E-클래스 W213'),
        (r'e-?클래스\s*\(4세대\)|e클래스\(4세대\)|w212', 'E-클래스', 'E-클래스 W212'),
        (r's-?클래스\s*\(7세대\)|s클래스\(7세대\)|w223', 'S-클래스', 'S-클래스 W223'),
        (r's-?클래스\s*\(6세대\)|s클래스\(6세대\)|w222', 'S-클래스', 'S-클래스 W222'),
        (r'5시리즈\s*\(7세대\)|5시리즈\(7세대\)|g30', '5시리즈', '5시리즈 (G30)'),
        (r'5시리즈\s*\(6세대\)|5시리즈\(6세대\)|f10', '5시리즈', '5시리즈 (F10)'),
        (r'쿠퍼\s*\(3세대\)|쿠퍼\(3세대\)|미니\s*쿠퍼', '미니', '쿠퍼'),
        (r'\bev6\b', 'EV6', 'EV6'),
        (r'\b베뉴\b', '베뉴', '베뉴'),
        (r'\b넥쏘\b', '넥쏘', '넥쏘'),
        (r'올\s*뉴\s*코란도|뷰티풀\s*코란도', '코란도', '뷰티풀 코란도'),
        (r'\b코란도\b', '코란도', '코란도'),
    ]

    @staticmethod
    def generate_encar_url(car_name, sub_model="", year="", mileage=0):
        """
        오토플러스/차얼마 사내 차량명을 엔카(Encar) PC 딜러 전용 데스크톱 검색 화면으로 100% 매칭
        - 엔카 공식 PC 규격: www.encar.com/dc/dc_carsearchlist.do
        - 왼쪽 필터 사이드바(제조사 > 모델그룹 > 세부모델)가 완벽하게 체크된 고정밀 딜러 화면 제공
        """
        full_text = f"{car_name or ''} {sub_model or ''}".strip()
        if not full_text:
            return "https://www.encar.com/dc/dc_carsearchlist.do?carType=kor&searchType=model"

        # 연식 파싱 (2자리 또는 4자리 숫자)
        parsed_year = 0
        if year:
            m_yr = re.search(r'(\d{2,4})', str(year))
            if m_yr:
                y_val = int(m_yr.group(1))
                parsed_year = (y_val + 2000) if y_val < 100 else y_val

        # 정규화 검색용 문자열 (공백, 하이픈, 언더바 제거 및 소문자화)
        clean_lower = full_text.lower()
        s = clean_lower.replace(" ", "").replace("-", "").replace("_", "")

        best_brand = None
        best_model = None
        best_len = 0

        # 1. 종합 제조사/모델그룹 DB 정밀 추출 (1차: 차량명 car_name 기준, 2차: full_text)
        c_clean = str(car_name or '').lower().replace(" ", "").replace("-", "").replace("_", "")
        for brand, kw_list, model_group in SalesDataAnalyzer.ENCA_BRAND_MODELS:
            for kw in kw_list:
                clean_kw = kw.lower().replace(" ", "").replace("-", "").replace("_", "")
                if clean_kw in c_clean:
                    if len(clean_kw) > best_len:
                        best_len = len(clean_kw)
                        best_brand = brand
                        best_model = model_group

        # 차량명에서 모델그룹을 못 찾은 경우 전체 텍스트에서 보조 탐색 (단, 트림명 등 '마스터' 혼동 방지)
        if not best_model:
            for brand, kw_list, model_group in SalesDataAnalyzer.ENCA_BRAND_MODELS:
                for kw in kw_list:
                    clean_kw = kw.lower().replace(" ", "").replace("-", "").replace("_", "")
                    if clean_kw == '마스터' and '르노' not in s and '마스터밴' not in s:
                        continue
                    if clean_kw in s:
                        if len(clean_kw) > best_len:
                            best_len = len(clean_kw)
                            best_brand = brand
                            best_model = model_group

        # 2. 세부 세대/모델 정밀 감지 (키워드 매칭 + 연식 힌트 보정)
        matched_sub_model = None
        if best_model:
            clean_lower = full_text.lower()
            for pattern, mg, sub_name in SalesDataAnalyzer.ENCA_SUB_MODELS:
                if mg == best_model and re.search(pattern, clean_lower):
                    matched_sub_model = sub_name
                    break

            # 💡 연식 힌트를 통한 세부 세대 보정 (키워드가 모호한 경우)
            if best_model == "K5":
                if parsed_year in [2015, 2016, 2017, 2018] or "신형" in clean_lower or "mx" in clean_lower or "sx" in clean_lower:
                    matched_sub_model = "K5 2세대"
                elif parsed_year in [2018, 2019] and "더뉴" in clean_lower:
                    matched_sub_model = "더 뉴 K5 2세대"
                elif parsed_year >= 2024 or "더뉴k53세대" in clean_lower:
                    matched_sub_model = "더 뉴 K5 3세대"
                elif parsed_year in [2020, 2021, 2022, 2023] or "3세대" in clean_lower or "dl3" in clean_lower:
                    matched_sub_model = "K5 3세대"
                elif parsed_year in [2013, 2014, 2015] and "더뉴" in clean_lower:
                    matched_sub_model = "더 뉴 K5"
            elif best_model == "그랜저":
                if parsed_year >= 2023 or "gn7" in clean_lower:
                    matched_sub_model = "그랜저 (GN7)"
                elif parsed_year in [2020, 2021, 2022] or "더뉴그랜저" in clean_lower:
                    matched_sub_model = "더 뉴 그랜저 IG"
                elif parsed_year in [2016, 2017, 2018, 2019] or "ig" in clean_lower:
                    matched_sub_model = "그랜저 IG"
                elif parsed_year in [2011, 2012, 2013, 2014, 2015, 2016] or "hg" in clean_lower:
                    matched_sub_model = "그랜저 HG"
            elif best_model == "쏘렌토":
                if parsed_year >= 2024:
                    matched_sub_model = "더 뉴 쏘렌토 4세대"
                elif parsed_year in [2020, 2021, 2022, 2023] or "mq4" in clean_lower:
                    matched_sub_model = "쏘렌토 4세대"
                elif parsed_year in [2018, 2019, 2020] or "더뉴" in clean_lower:
                    matched_sub_model = "더 뉴 쏘렌토"
                elif parsed_year in [2014, 2015, 2016, 2017] or "올뉴" in clean_lower:
                    matched_sub_model = "올 뉴 쏘렌토"
                elif parsed_year in [2012, 2013, 2014] or "뉴쏘렌토r" in clean_lower or "뉴쏘렌토" in clean_lower:
                    matched_sub_model = "뉴 쏘렌토 R"
                elif parsed_year in [2009, 2010, 2011, 2012] or "쏘렌토r" in clean_lower:
                    matched_sub_model = "쏘렌토 R"
            elif best_model == "쏘나타":
                if parsed_year >= 2024 or "디엣지" in clean_lower:
                    matched_sub_model = "쏘나타 디 엣지(DN8)"
                elif parsed_year in [2019, 2020, 2021, 2022, 2023] or "dn8" in clean_lower:
                    matched_sub_model = "쏘나타 (DN8)"
                elif parsed_year in [2017, 2018, 2019] or "뉴라이즈" in clean_lower:
                    matched_sub_model = "쏘나타 뉴 라이즈"
                elif parsed_year in [2014, 2015, 2016, 2017] or "lf" in clean_lower:
                    matched_sub_model = "LF 쏘나타"
            elif best_model == "아반떼":
                if parsed_year >= 2024:
                    matched_sub_model = "더 뉴 아반떼 (CN7)"
                elif parsed_year in [2020, 2021, 2022, 2023] or "cn7" in clean_lower:
                    matched_sub_model = "아반떼 (CN7)"
                elif parsed_year in [2018, 2019, 2020] and "더뉴" in clean_lower:
                    matched_sub_model = "더 뉴 아반떼 AD"
                elif parsed_year in [2015, 2016, 2017, 2018] or "ad" in clean_lower:
                    matched_sub_model = "아반떼 AD"
                elif parsed_year in [2010, 2011, 2012, 2013, 2014, 2015] or "md" in clean_lower:
                    matched_sub_model = "아반떼 MD"
            elif best_model == "카니발":
                if parsed_year >= 2024:
                    matched_sub_model = "더 뉴 카니발 4세대"
                elif parsed_year in [2020, 2021, 2022, 2023] or "ka4" in clean_lower:
                    matched_sub_model = "카니발 4세대"
                elif parsed_year in [2018, 2019, 2020] and "더뉴" in clean_lower:
                    matched_sub_model = "더 뉴 카니발"
                elif parsed_year in [2014, 2015, 2016, 2017] or "올뉴" in clean_lower:
                    matched_sub_model = "올 뉴 카니발"
            elif best_model == "스포티지":
                if parsed_year >= 2021 or "5세대" in clean_lower or "nq5" in clean_lower:
                    matched_sub_model = "스포티지 5세대"
                elif parsed_year in [2018, 2019, 2020] and ("더볼드" in clean_lower or parsed_year >= 2019):
                    matched_sub_model = "스포티지 더 볼드"
                elif parsed_year in [2015, 2016, 2017, 2018] or "4세대" in clean_lower or "ql" in clean_lower:
                    matched_sub_model = "The SUV 스포티지"
                elif parsed_year in [2013, 2014, 2015] or "더뉴" in clean_lower:
                    matched_sub_model = "더 뉴 스포티지 R"
                elif parsed_year in [2010, 2011, 2012, 2013] or "스포티지r" in clean_lower:
                    matched_sub_model = "스포티지 R"

        # 3. 세부 등급(BadgeDetail: 프레스티지, 노블레스, 럭셔리, 시그니처 등) 감지
        badge_detail = None
        detail_keywords = [
            '프레스티지', '노블레스 스페셜', '노블레스', '시그니처', '캘리그래피', '인스퍼레이션',
            '익스클루시브', '프리미엄', '모던', '스타일 에디션', '스페셜 에디션', '디럭스', '럭셔리',
            '프리미에르', '샤이니', '프리미에', '마스터즈', '그래비티', 'VIP'
        ]
        for dk in detail_keywords:
            if dk.lower() in clean_lower or dk.replace(" ", "").lower() in s:
                badge_detail = dk
                break

        # 4. 엔카 PC 데스크톱 검색 Action 쿼리 조립 (정밀 스마트 밴드 적용)
        if best_brand and best_model:
            is_import = best_brand in [
                '벤츠', 'BMW', '아우디', '폭스바겐', '볼보', '포르쉐', '테슬라', 
                '포드', '링컨', '혼다', '토요타', '렉서스', '지프', '랜드로버', '미니', '푸조', '폴스타'
            ]
            car_type = "for" if is_import else "kor"
            
            f_brand = str(best_brand)
            f_mg = str(best_model)
            
            # 모델 및 등급 코어 트리
            if matched_sub_model and badge_detail:
                f_sub = str(matched_sub_model)
                core_tree = f"(C.CarType.Y._.(C.Manufacturer.{f_brand}._.(C.ModelGroup.{f_mg}._.(C.Model.{f_sub}._.BadgeDetail.{badge_detail}.))))"
            elif matched_sub_model:
                f_sub = str(matched_sub_model)
                core_tree = f"(C.CarType.Y._.(C.Manufacturer.{f_brand}._.(C.ModelGroup.{f_mg}._.Model.{f_sub}.)))"
            else:
                core_tree = f"(C.CarType.Y._.(C.Manufacturer.{f_brand}._.ModelGroup.{f_mg}.))"

            action = f"(And.Hidden.N._.{core_tree}"

            # 💡 연식 밴드 (기준 연식 ±1년)
            if parsed_year and parsed_year >= 2000:
                start_yr = parsed_year - 1
                end_yr = parsed_year + 1
                action += f"_.Year.range({start_yr}01..{end_yr}12)."

            # 💡 주행거리 밴드 (기준 주행거리 ±20,000km, 만단위 라운딩)
            # 단, 연식이 5년 이상 된 구형 차량에 4만km 이하의 기본값이 들어온 경우 과도한 1대 축소 방지
            try:
                mil_val = int(mileage)
                curr_y = 2026
                is_old_car = parsed_year and (curr_y - parsed_year >= 5)
                if mil_val >= 50000 or (not is_old_car and mil_val > 5000):
                    min_mil = max(0, ((mil_val - 20000) // 10000) * 10000)
                    max_mil = ((mil_val + 20000 + 9999) // 10000) * 10000
                    action += f"_.Mileage.range({min_mil}..{max_mil})."
            except Exception:
                pass

            action += ")"

            payload = {
                "action": action,
                "toggle": {},
                "layer": "",
                "sort": "ModifiedDate",
                "page": 1,
                "limit": 50
            }
            json_str = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
            return f"https://www.encar.com/dc/dc_carsearchlist.do?carType={car_type}&searchType=model#!{json_str}"

        # 5. 만약 DB 매칭이 안 된 희귀차종인 경우: 기본 엔카 국산차 검색 페이지로 안내
        return "https://www.encar.com/dc/dc_carsearchlist.do?carType=kor&searchType=model"

# 싱글톤 헬퍼 함수
def get_car_market_stats(car_name, sub_model="", year="", current_retail=0):
    return SalesDataAnalyzer.get_instance().get_market_stats(car_name, sub_model, year, current_retail)

def generate_encar_market_url(car_name, sub_model="", year="", mileage=0):
    return SalesDataAnalyzer.get_instance().generate_encar_url(car_name, sub_model, year, mileage)
