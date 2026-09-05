import streamlit as st
import pandas as pd
import requests
import urllib.parse
import json
import re
import os
import time
import random
import math
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
from heydealer_ai import extract_car_data_for_ai, get_gemini_estimate
from scraper import HeydealerScraper
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# ⚙️ 1. 설정 및 상태 관리
# ==========================================
st.set_page_config(page_title="J-PRO Valuation System", page_icon="🏅", layout="wide")

st.markdown('''
<style>
/* Midnight Vault Theme */
:root {
    --color-obsidian: #08080a;
    --color-carbon: #121317;
    --color-graphite: #1c1d22;
    --color-slate: #2e3038;
    --color-copper: #cc9166;
    --color-fog: #9194a1;
    --color-bone: #e2e3e9;
    --color-paper-white: #ffffff;
}

.stApp {
    background-color: var(--color-obsidian) !important;
    color: var(--color-bone) !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stSidebar"] {
    background-color: #0c0d11 !important;
    border-right: 1px solid var(--color-graphite) !important;
}

h1, h2, h3 {
    color: var(--color-paper-white) !important;
    font-family: 'Playfair Display', serif !important;
    font-weight: 500 !important;
}

h4, h5, h6 {
    color: var(--color-bone) !important;
    font-family: 'Inter', sans-serif !important;
}

/* Metric Cards (2/3 compact size) */
.metric-card {
    background-color: #121317 !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.4) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    margin-bottom: 10px !important;
    border: 1px solid #2e3038 !important;
    transition: all 0.2s ease;
}
.metric-card:hover {
    border-color: #cc9166 !important;
}
.metric-icon {
    font-size: 1.4em !important;
    background: #1c1d22 !important;
    padding: 6px 10px !important;
    border-radius: 8px !important;
    margin-right: 10px !important;
}
.metric-content h4 {
    margin: 0 !important;
    font-size: 0.75em !important;
    color: #9194a1 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}
.metric-content h2 {
    margin: 2px 0 0 0 !important;
    font-size: 1.2em !important;
    color: #ffffff !important;
    font-family: 'Playfair Display', serif !important;
}

/* Summary Box */
.summary-box {
    background: #121317 !important;
    border: 1px solid #1c1d22 !important;
    border-left: 4px solid #cc9166 !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    margin-top: 6px !important;
    margin-bottom: 20px !important;
    color: #e2e3e9 !important;
    font-size: 0.88em !important;
    line-height: 1.6 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 1px solid #1c1d22 !important;
    gap: 6px !important;
}
.stTabs [data-baseweb="tab"] {
    color: #9194a1 !important;
    background-color: #121317 !important;
    border: 1px solid #1c1d22 !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 8px 16px !important;
}
.stTabs [aria-selected="true"] {
    color: #cc9166 !important;
    border-color: #cc9166 #cc9166 transparent #cc9166 !important;
    background-color: #1a1b22 !important;
    font-weight: bold !important;
}
</style>
''', unsafe_allow_html=True)


DB_FILE = "jpro_db.csv"
LEDGER_FILE = "my_car_ledger.csv"
INVENTORY_FILE = "autoplus_inventory.csv" 
COOKIE_FILE = "encar_cookie.txt" 
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyFTXuPkC0R9y-UftHOFmJfgBwxycMwqOabhxKVT4bcsBK9gfsscQtGCTohzFiccq71/exec"

def load_cookie():
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_cookie(cookie_str):
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        f.write(cookie_str)

if 'inventory_data' not in st.session_state:
    if os.path.exists(INVENTORY_FILE):
        try: st.session_state.inventory_data = pd.read_csv(INVENTORY_FILE)
        except: st.session_state.inventory_data = pd.DataFrame()
    else: st.session_state.inventory_data = pd.DataFrame()

if 'scan_data' not in st.session_state: st.session_state.scan_data = pd.DataFrame()
if 'f_status' not in st.session_state: st.session_state.f_status = []
if 'f_brand' not in st.session_state: st.session_state.f_brand = "전체"
if 'f_name' not in st.session_state: st.session_state.f_name = "전체"
if 'f_sub' not in st.session_state: st.session_state.f_sub = "전체"
if 'my_ledger_data' not in st.session_state:
    if os.path.exists(LEDGER_FILE):
        try:
            st.session_state.my_ledger_data = pd.read_csv(LEDGER_FILE)
            st.session_state.my_ledger_data['차량번호'] = st.session_state.my_ledger_data['차량번호'].astype(str)
        except:
            st.session_state.my_ledger_data = pd.DataFrame(columns=['등록일', '차량번호', '제조사', '차량명', '세부모델', '연식', '주행거리', '매입가', '판매가', '특이사항'])
    else:
        st.session_state.my_ledger_data = pd.DataFrame(columns=['등록일', '차량번호', '제조사', '차량명', '세부모델', '연식', '주행거리', '매입가', '판매가', '특이사항'])

if 'option_catalog_cache' not in st.session_state:
    st.session_state.option_catalog_cache = {}

if 'purchase_route' not in st.session_state:
    st.session_state.purchase_route = "셀프(기본)"

# 🔥 입력값 초기화를 위한 리셋 키 (에러 해결의 핵심!)
if 'form_reset_key' not in st.session_state:
    st.session_state.form_reset_key = 0

if 'save_success' not in st.session_state: st.session_state.save_success = False
if 'saved_car_num' not in st.session_state: st.session_state.saved_car_num = ""

# ==========================================
# 2. 데이터 처리 클래스 (엔카, 헤이딜러 통합 데이터 표준화)
# ==========================================
def parse_heydealer_comps(json_data):
    import pandas as pd
    rows = []
    items = []
    if isinstance(json_data, dict) and 'results' in json_data:
        items = json_data['results']
    elif isinstance(json_data, list):
        items = json_data
        
    HEYDEALER_PART_MAP = {
        'bumper_front': '앞범퍼', 'bumper_rear': '뒤범퍼',
        'fender_front_driver': '앞휀더(운전석)', 'fender_front_passenger': '앞휀더(조수석)',
        'fender_rear_driver': '뒤휀더(운전석)', 'fender_rear_passenger': '뒤휀더(조수석)',
        'door_front_driver': '앞도어(운전석)', 'door_front_passenger': '앞도어(조수석)',
        'door_rear_driver': '뒤도어(운전석)', 'door_rear_passenger': '뒤도어(조수석)',
        'hood': '후드(보닛)', 'trunk_lid': '트렁크리드', 'roof': '루프',
        'radiator_support': '라디에이터 서포트', 'panel_front': '프론트패널', 'panel_rear': '리어패널',
        'front_panel': '프론트패널', 'rear_panel': '리어패널', 'trunk_floor': '트렁크플로어',
        'side_member': '사이드멤버', 'cross_member': '크로스멤버', 'inside_panel': '인사이드패널',
        'inside_panel_front_driver': '인사이드패널(앞/운전석)', 'inside_panel_front_passenger': '인사이드패널(앞/조수석)',
        'inside_panel_rear_driver': '인사이드패널(뒤/운전석)', 'inside_panel_rear_passenger': '인사이드패널(뒤/조수석)',
        'side_member_front_driver': '사이드멤버(앞/운전석)', 'side_member_front_passenger': '사이드멤버(앞/조수석)',
        'side_member_rear_driver': '사이드멤버(뒤/운전석)', 'side_member_rear_passenger': '사이드멤버(뒤/조수석)',
        'pillar_a': 'A필러', 'pillar_b': 'B필러', 'pillar_c': 'C필러',
        'pillar_a_driver': 'A필러(운전석)', 'pillar_a_passenger': 'A필러(조수석)',
        'pillar_b_driver': 'B필러(운전석)', 'pillar_b_passenger': 'B필러(조수석)',
        'pillar_c_driver': 'C필러(운전석)', 'pillar_c_passenger': 'C필러(조수석)',
        'quarter_panel_driver': '쿼터패널(운전석)', 'quarter_panel_passenger': '쿼터패널(조수석)',
        'wheel_house_front_driver': '휠하우스(앞/운전석)', 'wheel_house_front_passenger': '휠하우스(앞/조수석)',
        'wheel_house_rear_driver': '휠하우스(뒤/운전석)', 'wheel_house_rear_passenger': '휠하우스(뒤/조수석)',
    }
    HEYDEALER_REPAIR_MAP = {
        'exchange': '교환', 'replace': '교환', 'weld': '판금/용접', 'sheet_metal': '판금'
    }

    def format_hd_part(raw_p):
        if not raw_p: return '기타부위'
        p_str = str(raw_p).strip()
        if p_str in HEYDEALER_PART_MAP:
            return HEYDEALER_PART_MAP[p_str]
        
        # 언더스코어로 조합된 영문 부품명 스마트 변환
        tokens = p_str.split('_')
        pos_dict = {'front': '앞', 'rear': '뒤', 'driver': '운전석', 'passenger': '조수석', 'left': '좌', 'right': '우'}
        name_dict = {
            'bumper': '범퍼', 'fender': '휀더', 'door': '도어', 'panel': '패널',
            'member': '멤버', 'hood': '후드(보닛)', 'lid': '리드', 'trunk': '트렁크',
            'roof': '루프', 'inside': '인사이드', 'floor': '플로어', 'pillar': '필러',
            'quarter': '쿼터패널', 'radiator': '라디에이터', 'support': '서포트', 'wheel': '휠', 'house': '하우스'
        }
        res_tokens = []
        for t in tokens:
            t_low = t.lower()
            res_tokens.append(pos_dict.get(t_low, name_dict.get(t_low, t)))
        return ''.join(res_tokens) if all(k in list(pos_dict.values()) + list(name_dict.values()) for k in res_tokens) else ' '.join(res_tokens)

    for item in items:
        # 경매 내역 구조
        if "detail" in item and "auction" in item:
            d = item.get("detail", {})
            auc = item.get("auction", {}) or {}
            bid = auc.get("highest_bid") or {}
            price = bid.get("price")
            mileage = d.get("mileage")
            year = d.get("year", 0)
            
            repairs = d.get("accident_repairs", []) or []
            r_descs = []
            is_major = False
            for rep in repairs:
                p = rep.get('part') or rep.get('part_name') or ''
                t = rep.get('repair') or rep.get('type_name') or ''
                p_kr = format_hd_part(p)
                t_kr = HEYDEALER_REPAIR_MAP.get(t, t)
                if any(x in str(p).lower() for x in ['fender_rear', 'roof', 'pillar', 'panel', 'floor', 'member', 'quarter']):
                    is_major = True
                r_descs.append(f"{p_kr} ({t_kr})")
            
            repair_str = ", ".join(r_descs)
            cnt = len(repairs)
            ch = d.get('carhistory', {}) or {}
            oc = ch.get('owner_changed_count') if isinstance(ch, dict) else None

            # 헤이딜러 실제 태그 (예: ['완무 (보험0건)', '1인소유'], ['단순 (1)', '1인소유'], ['유사고', '대여'])
            tags = auc.get('tags', []) or []
            tag_texts = [t.get('short_text', '').strip() for t in tags if isinstance(t, dict) and t.get('short_text')]
            tag_texts = [t for t in tag_texts if t and t not in ['재경매', '연장']]

            if tag_texts:
                base_acc = " ".join(tag_texts)
                if any(k in base_acc for k in ['유사고', '사고']):
                    acc_icon = "🔴"
                elif any(k in base_acc for k in ['단순', '판금']):
                    acc_icon = "🟡"
                else:
                    acc_icon = "🟢"
            else:
                if cnt == 0:
                    base_acc = "무사고"
                    acc_icon = "🟢"
                elif is_major:
                    base_acc = f"사고 ({cnt})"
                    acc_icon = "🔴"
                else:
                    base_acc = f"단순 ({cnt})"
                    acc_icon = "🟡"
                if oc == 0:
                    base_acc += " 1인소유"
                
            car_spec = d.get("car_spec", {}) or {}
            spec_desc = car_spec.get("description", "")
            car_name = d.get("grade_part_name") or d.get("full_name") or "헤이딜러 매물"
            car_id = item.get("car_id") or d.get("id") or ""
            link = f"https://dealer.heydealer.com/cars/{car_id}" if car_id else ""
            import re
            options = []
            for line in spec_desc.split('\n'):
                m = re.search(r'^\d+\)\s*(.*?)(?:\s*\(|$)', line.strip())
                if m:
                    options.append(m.group(1).strip())
            
            p_val = price // 10000 if isinstance(price, (int, float)) and price >= 10000 else price
            try: y_num = int(re.search(r'\d{4}', str(year)).group(0)) if re.search(r'\d{4}', str(year)) else 0
            except: y_num = 0

            rows.append({
                "차량명": car_name,
                "연식": f"{y_num}년" if y_num else "-",
                "주행거리": f"{int(mileage):,} km" if mileage else "-",
                "낙찰가": f"{int(p_val):,} 만원" if p_val else "-",
                "사고유무": f"{acc_icon} {base_acc}",
                "사고상세": repair_str,
                "옵션": " / ".join(options[:4]) if options else "-",
                "링크": link,
                "판매가_num": p_val,
                "주행거리_num": mileage or 0,
                "연식_num": y_num,
                "옵션리스트": options,
            })
        # 일반 시세 구조
        else:
            price = item.get('price')
            mileage = item.get('mileage')
            year = item.get('year', 0)
            if price is None or mileage is None:
                continue
            is_acc = item.get('is_accident')
            if is_acc is not None:
                has_accident = is_acc
            else:
                has_accident = (item.get('accident', '') == '사고')
            opts = item.get('options', item.get('tags', []))
            options = [o.strip() for o in opts.split(',')] if isinstance(opts, str) else opts
            car_name = item.get('model_name') or item.get('full_name') or "헤이딜러 매물"
            car_id = item.get('car_id', '')
            link = f"https://dealer.heydealer.com/cars/{car_id}" if car_id else ""
            
            p_val = price // 10000 if isinstance(price, (int, float)) and price >= 10000 else price
            try: y_num = int(re.search(r'\d{4}', str(year)).group(0)) if re.search(r'\d{4}', str(year)) else 0
            except: y_num = 0

            rows.append({
                "차량명": car_name,
                "연식": f"{y_num}년" if y_num else "-",
                "주행거리": f"{int(mileage):,} km" if mileage else "-",
                "낙찰가": f"{int(p_val):,} 만원" if p_val else "-",
                "사고유무": "🔴 사고" if has_accident else "🟢 무사고",
                "사고상세": "",
                "옵션": " / ".join(options[:4]) if options else "-",
                "링크": link,
                "판매가_num": p_val,
                "주행거리_num": mileage or 0,
                "연식_num": y_num,
                "옵션리스트": options,
            })
    return pd.DataFrame(rows)

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

        if "재고" in ordered_df.columns:
            def format_inv(v):
                v_str = str(v).strip()
                if v_str.lower() in ['nan', 'none', '', '-']: return "-"
                try: return str(int(float(v_str)))
                except: return v_str
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

# ==========================================
# ⚙️ 3. 초정밀 데이터 스크래퍼 엔진
# ==========================================
class Scraper:
    @staticmethod
    def calculate_inventory_days(date_str):
        try:
            full_date_str = f"20{date_str}" 
            delta = datetime.now() - datetime.strptime(full_date_str, "%Y-%m-%d")
            return str(delta.days)
        except: return "-"

    @staticmethod
    def _fetch_json(session, url, ref_id):
        headers = {"Referer": f"https://fem.encar.com/cars/detail/{ref_id}"}
        try:
            res = session.get(url, headers=headers, timeout=5)
            json_data = None
            if res.status_code == 200:
                try: json_data = res.json()
                except: pass
            return {"status": res.status_code, "json": json_data}
        except Exception:
            return {"status": "error", "json": None}

    @staticmethod
    def clean_option_name(name):
        return re.sub(r'\([^)]*\)|\[[^\]]*\]', '', str(name)).strip()

    @staticmethod
    def fetch_car_detail(session, c_id):
        perf_date = "⚠️미등록"
        inv_days = "-"
        accident_status = "⚠️정보없음"
        color = "⚠️정보없음"
        opt_str = "없음"
        is_rate_limited = False
        acc = None
        rep = None

        v_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/vehicle/{c_id}?include=MANAGE,OPTIONS,SPEC", c_id)
        if v_resp["status"] in [403, 429]: return {"성능일": "⚠️조회실패", "재고": "-", "사고유무": "⚠️조회실패", "외장컬러": "⚠️조회실패", "추가옵션": "⚠️조회실패", "is_rate_limited": True}
        
        real_id = str(c_id)
        applied_codes = []
        
        if v_resp["status"] == 200 and v_resp["json"]:
            manage = v_resp["json"].get("manage") or {}
            spec = v_resp["json"].get("spec") or {}
            color = spec.get("colorName", "⚠️정보없음")
            if manage.get("dummy"):
                real_id = str(manage.get("dummyVehicleId", c_id))
            applied_codes = v_resp["json"].get("options", {}).get("choice", [])

        i_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/inspection/vehicle/{real_id}", c_id)
        if i_resp["status"] in [403, 429]: return {"성능일": "⚠️조회실패", "재고": "-", "사고유무": "⚠️조회실패", "추가옵션": "⚠️조회실패", "is_rate_limited": True}
        
        if i_resp["status"] == 200 and i_resp["json"]:
            master = i_resp["json"].get("master") or {}
            detail = master.get("detail") or {}

            issue_date = detail.get("issueDate", "")
            if issue_date and len(issue_date) == 8:
                perf_date = f"{issue_date[2:4]}-{issue_date[4:6]}-{issue_date[6:8]}"
                inv_days = Scraper.calculate_inventory_days(perf_date)

            acc = master.get("accdient")
            rep = master.get("simpleRepair")

            if acc is False and rep is False:
                accident_status = "완전무사고"
            elif acc is None and rep is None:
                accident_status = "정보없음"
            else:
                flags = []
                if acc: flags.append("사고")
                if rep: flags.append("단순")
                accident_status = f"({'/'.join(flags)})"
        elif i_resp["status"] == 404:
            perf_date = "미검사/사진"
            accident_status = "기록부(사진)"

        exch_cnt = 0
        sheet_cnt = 0
        
        if i_resp["status"] == 200 and i_resp["json"]:
            ij = i_resp["json"]
            all_parts = (ij.get("outers", []) or []) + (ij.get("inners", []) or [])
            if not all_parts and "master" in ij:
                all_parts = (ij["master"].get("outers", []) or []) + (ij["master"].get("inners", []) or [])
            for part in all_parts:
                status_types = part.get("statusTypes", []) or []
                codes = [str(s.get("code", "")).upper() for s in status_types if isinstance(s, dict)]
                if "X" in codes:
                    exch_cnt += 1
                elif any(c in codes for c in ["W", "C", "A", "U", "T"]):
                    sheet_cnt += 1

        if exch_cnt == 0 and sheet_cnt == 0 and acc is not False and rep is not False:
            d_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/diagnosis/vehicle/{real_id}", c_id)
            if d_resp["status"] == 200 and d_resp["json"]:
                dj = d_resp["json"]
                if "items" in dj and isinstance(dj["items"], list):
                    for it in dj["items"]:
                        raw_n = it.get("name", "")
                        if raw_n in ["CHECKER_COMMENT", "OUTER_PANEL_COMMENT"]: continue
                        rc = str(it.get("resultCode", "") or "").upper()
                        rt = str(it.get("result", "") or "")
                        if rc in ["REPLACEMENT", "EXCHANGE", "X"] or "교환" in rt:
                            exch_cnt += 1
                        elif rc in ["SHEET_METAL", "WELD", "W", "C", "A", "U", "T"] or any(k in rt for k in ["판금", "용접", "도색", "수리"]):
                            sheet_cnt += 1

                outers = dj.get("outers", []) or []
                inners = dj.get("inners", []) or []
                all_parts = outers + inners
                for part in all_parts:
                    status_types = part.get("statusTypes", []) or []
                    codes = [str(s.get("code", "")).upper() for s in status_types if isinstance(s, dict)]
                    if "X" in codes:
                        exch_cnt += 1
                    elif any(c in codes for c in ["W", "C", "A", "U", "T"]):
                        sheet_cnt += 1
                    
        if exch_cnt > 0 or sheet_cnt > 0:
            if "기록부(사진)" not in accident_status:
                if acc:
                    base_label = "사고"
                elif exch_cnt > 0 and sheet_cnt == 0:
                    base_label = "단순교환"
                elif sheet_cnt > 0 and exch_cnt == 0:
                    base_label = "단순판금"
                else:
                    base_label = "단순(교환/판금)"
                accident_status = f"{base_label} [교환:{exch_cnt} / 판금:{sheet_cnt}]"
        else:
            if acc:
                accident_status = "사고"
            elif rep:
                accident_status = "단순교환"
            elif acc is False and rep is False:
                accident_status = "완전무사고"

        if applied_codes:
            if c_id not in st.session_state.option_catalog_cache:
                o_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/vehicles/car/{c_id}/options/choice", c_id)
                if o_resp["status"] == 200 and o_resp["json"]:
                    st.session_state.option_catalog_cache[c_id] = o_resp["json"]
                elif o_resp["status"] == 404:
                    opt_str = "없음(구버전점검)" 
                elif o_resp["status"] in [403, 429]:
                    opt_str = "⚠️조회실패"
                    is_rate_limited = True
                elif o_resp["status"] != 200:
                    opt_str = "코드매칭실패"

            if opt_str == "없음": 
                catalog = st.session_state.option_catalog_cache.get(c_id, [])
                if isinstance(catalog, list) and catalog:
                    applied_opts = []
                    for opt in catalog:
                        if isinstance(opt, dict) and str(opt.get("optionCd", "")) in applied_codes:
                            name = Scraper.clean_option_name(opt.get("optionName", ""))
                            price = opt.get("price", 0)
                            if name and "외장컬러" not in name:
                                if price > 0: applied_opts.append(f"{name}({price}만)")
                                else: applied_opts.append(name)
                    if applied_opts:
                        opt_str = " / ".join(applied_opts)

        return {
            "성능일": perf_date,
            "재고": inv_days,
            "사고유무": accident_status,
            "외장컬러": color,
            "추가옵션": opt_str,
            "is_rate_limited": is_rate_limited
        }

    @staticmethod
    def dedupe_after_scan(df):
        if df.empty: return df
        df_copy = df.copy()
        
        def calculate_score(row):
            score = 0
            if str(row.get('성능일', '')) not in ['⚠️미등록', '미검사/사진', '⚠️조회실패', '-']: score += 1
            if str(row.get('사고유무', '')) not in ['⚠️정보없음', '기록부(사진)', '⚠️조회실패', '-']: score += 1
            if str(row.get('추가옵션', '')) not in ['⚠️조회실패', '코드매칭실패', '없음(구버전점검)', '-']: score += 1
            return score

        df_copy['data_score'] = df_copy.apply(calculate_score, axis=1)
        deduped = df_copy.sort_values('data_score', ascending=False).drop_duplicates(
            subset=['차량명', '세부모델', '연식', '주행거리', '판매가'], keep='first'
        )
        deduped = deduped.drop(columns=['data_score']).reset_index(drop=True)
        return deduped

    @staticmethod
    def run(target_url, custom_cookie, progress_bar, status_text):
        try:
            status_text.text("1/3: 실시간 통신 준비...")
            progress_bar.progress(10)
            
            decoded_url = urllib.parse.unquote_plus(target_url.strip())
            condition = ""
            json_match = re.search(r'#!(\{.*\})', decoded_url)
            if json_match:
                try: condition = json.loads(json_match.group(1)).get("action", "")
                except: pass
                    
            if not condition:
                match = re.search(r'"action"\s*:\s*"([^"]+)"', decoded_url)
                if match: condition = match.group(1).encode('ascii', 'backslashreplace').decode('unicode_escape') if r'\u' in match.group(1) else match.group(1)
                elif 'q=' in decoded_url: 
                    try: condition = decoded_url.split('q=')[1].split('&')[0]
                    except: pass

            if not condition: return pd.DataFrame(), "❌ URL 검색 조건 누락"
                
            safe_condition = urllib.parse.quote(condition)
            api_url = f"https://api.encar.com/search/car/list/general?count=false&q={safe_condition}&sr=%7CModifiedDate%7C0%7C100"
            
            session = requests.Session()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Origin": "https://fem.encar.com",
            }
            if custom_cookie: headers["Cookie"] = custom_cookie
            session.headers.update(headers)

            cars_res = session.get(api_url).json()
            cars = cars_res.get("SearchResults", [])
            if not cars: return pd.DataFrame(), "❌ 매물 없음"

            car_data_list = []
            for car in cars:
                if car.get("Price", 0) <= 0: continue
                
                sell_type = str(car.get("SellType", ""))
                if "렌트" in sell_type or "리스" in sell_type: continue
                if car.get("LeaseType"): continue 
                
                badge_group = car.get('BadgeGroup', '')
                badge = car.get('Badge', '')
                badge_detail = car.get('BadgeDetail', '')
                
                parts = []
                if badge_group: parts.append(badge_group)
                if badge and badge not in parts: parts.append(badge)
                if badge_detail and badge_detail not in parts: parts.append(badge_detail)
                
                sub_model_full = " ".join(parts).strip()

                reg_year = str(car.get("Year", ""))
                form_year = str(car.get("FormYear", ""))
                if len(reg_year) >= 4:
                    year_str = f"{reg_year[2:4]}({form_year[2:] if len(form_year)==4 else form_year})"
                else:
                    year_str = f"{reg_year}({form_year})"

                car_data_list.append({
                    "상태": "실시간", "제조사": car.get('Manufacturer', '').strip(),
                    "차량명": car.get('Model', '').strip(), "세부모델": sub_model_full, 
                    "연식": year_str, "주행거리": car.get("Mileage", 0),
                    "판매가": car.get("Price", 0), "성능일": "-", "재고": "-",
                    "사고유무": "-", "외장컬러": "-", "추가옵션": "-",
                    "링크": f"http://www.encar.com/dc/dc_cardetailview.do?carid={car.get('Id', '')}",
                    "_carid": str(car.get('Id', ''))
                })
            
            total_cars = len(car_data_list)
            consecutive_failures = 0
            
            for idx, car in enumerate(car_data_list):
                status_text.text(f"2/3: 쾌속 정밀 스캔 중... ({idx+1}/{total_cars}대)")
                progress_bar.progress(10 + int(80 * (idx + 1) / total_cars))
                
                res = Scraper.fetch_car_detail(session, car["_carid"])
                
                car["성능일"] = res["성능일"]
                car["재고"] = res["재고"]
                car["사고유무"] = res["사고유무"]
                car["외장컬러"] = res.get("외장컬러", "-")
                car["추가옵션"] = res["추가옵션"]

                if res.get("is_rate_limited"):
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        status_text.text("⚠️ 엔카 방어막 감지! 15초간 보안 대기합니다...")
                        time.sleep(15.0)
                        consecutive_failures = 0
                else:
                    consecutive_failures = 0
                    
                time.sleep(random.uniform(0.01, 0.05))

            status_text.text("3/3: 스캔 완료. 스마트 데이터 취합 중...")
            raw_df = pd.DataFrame(car_data_list)
            deduped_df = Scraper.dedupe_after_scan(raw_df)

            progress_bar.progress(100)
            status_text.text("✅ 스캔 및 최적화 완전 성공!")
            return DataProcessor.standardize(deduped_df), "success"
        except Exception as e:
            return pd.DataFrame(), f"❌ 에러: {str(e)}"

    @staticmethod
    def rescan(failed_indices, custom_cookie, progress_bar, status_text):
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://fem.encar.com",
        }
        if custom_cookie: headers["Cookie"] = custom_cookie
        session.headers.update(headers)
        
        consecutive_failures = 0
        total_cars = len(failed_indices)
        
        for i, idx in enumerate(failed_indices):
            status_text.text(f"♻️ 실패 매물 원터치 재스캔... ({i+1}/{total_cars}대)")
            progress_bar.progress(int(100 * (i + 1) / total_cars))
            
            time.sleep(random.uniform(0.05, 0.1)) 
            
            c_id = st.session_state.scan_data.loc[idx, '_carid']
            res = Scraper.fetch_car_detail(session, c_id)
            
            st.session_state.scan_data.loc[idx, '성능일'] = res["성능일"]
            st.session_state.scan_data.loc[idx, '재고'] = res["재고"]
            st.session_state.scan_data.loc[idx, '사고유무'] = res["사고유무"]
            st.session_state.scan_data.loc[idx, '추가옵션'] = res["추가옵션"]
            
            if res.get("is_rate_limited"):
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    status_text.text("⚠️ 보안 대기 중 (15초)...")
                    time.sleep(15.0)
                    consecutive_failures = 0
            else:
                consecutive_failures = 0
                
        status_text.text("✅ 재스캔 완료!")

# ==========================================
# ⚙️ 4. 사이드바 UI 및 메인 리스트 출력
# ==========================================
# ⚙️ 4. 사이드바 UI 및 메인 리스트 출력
# ==========================================
st.sidebar.markdown("""
<div style='margin-bottom: -15px;'>
    <span style='font-size: 32px; font-weight: 800; color: #1E3A8A; letter-spacing: -1px;'>J-PRO</span>
</div>
<div style='margin-bottom: 25px;'>
    <span style='font-size: 12px; font-weight: 500; color: #64748B; letter-spacing: 2px; text-transform: uppercase;'>Auto Valuation Intelligence</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 헤이딜러 AI 매입 견적")




heydealer_url_input = st.sidebar.text_input("헤이딜러 차량 URL/ID", placeholder="URL 또는 ID 입력")
default_cookie = os.getenv("HEYDEALER_COOKIE", "")
heydealer_cookie_input = st.sidebar.text_input("세션 쿠키 (Cookie 헤더 전체)", value=default_cookie, type="password", help="브라우저 개발자 도구(F12) -> Network 탭에서 가져온 Cookie 문자열 전체를 붙여넣으세요. (.env에 HEYDEALER_COOKIE 로 저장하면 자동 입력됩니다.)")

is_ai_running = st.session_state.get('ai_status') == "진행중"
if st.sidebar.button("차량 정보 수집 및 AI 견적 산출", key="heydealer_btn", disabled=is_ai_running):
    if not heydealer_url_input.strip():
        st.sidebar.warning("헤이딜러 차량 URL이나 ID를 입력해주세요.")
    elif not heydealer_cookie_input.strip():
        st.sidebar.warning("헤이딜러 세션 쿠키를 입력해주세요.")
    else:
        try:
            # 쿠키가 바뀌면 세션을 새로 만들고, 바뀌지 않으면 기존 세션을 재사용 (자동 쿠키 갱신)
            if ('heydealer_session' not in st.session_state or
                    st.session_state.get('heydealer_last_cookie') != heydealer_cookie_input):
                st.session_state.heydealer_session = HeydealerScraper.build_session(heydealer_cookie_input)
                st.session_state.heydealer_last_cookie = heydealer_cookie_input

            with st.sidebar.spinner("헤이딜러 서버에서 차량 정보를 가져오는 중입니다..."):
                result = HeydealerScraper.fetch_car_detail(
                    heydealer_url_input,
                    session=st.session_state.heydealer_session
                )
                heydealer_json_str = result['detail']
                if not heydealer_json_str.strip() or not heydealer_json_str.strip().startswith('{'):
                    raise Exception(f'잘못된 응답입니다(로그인 만료 또는 차단 의심). 응답: {heydealer_json_str[:100]}')
                
                hd_detail_tmp = json.loads(heydealer_json_str).get('detail', {})
                car_spec_tmp = hd_detail_tmp.get('car_spec') or {}
                spec_desc_tmp = car_spec_tmp.get('description', '')
                import re
                hd_target_options = []
                for line in spec_desc_tmp.split('\n'):
                    m = re.search(r'^\d+\)\s*(.*?)(?:\s*\(|$)', line.strip())
                    if m:
                        hd_target_options.append(m.group(1).strip())
                
                advanced_options_tmp = hd_detail_tmp.get('advanced_options') or []
                encar_target_options = [
                    opt.get('name', '') for opt in advanced_options_tmp 
                    if isinstance(opt, dict) and opt.get('choice') == 'loaded'
                ]
                
                auction_repairs_json = result.get('auction_repairs') or ""
                market_prices_json = result.get('market_prices') or ""
                encar_url = result.get('encar_url') or ""
                
                # 헤이딜러 응답에 포함된 엔카 시세 URL이 있으면 자동 스캔 실행
                if encar_url:
                    st.session_state.auto_encar_url = encar_url
                    try:
                        with st.sidebar.spinner("엔카 실시간 시세를 자동 스캔 중입니다..."):
                            p_bar, s_text = st.sidebar.progress(0), st.sidebar.empty()
                            new_scan_df, msg = Scraper.run(encar_url, "", p_bar, s_text)
                            p_bar.empty()
                            s_text.empty()
                            if msg == "success" and not new_scan_df.empty:
                                st.session_state.scan_data = new_scan_df
                                st.session_state.f_brand = new_scan_df['제조사'].iloc[0] if '제조사' in new_scan_df.columns else "전체"
                                st.session_state.f_name = new_scan_df['차량명'].iloc[0] if '차량명' in new_scan_df.columns else "전체"
                                st.session_state.f_sub = new_scan_df['세부모델'].iloc[0] if '세부모델' in new_scan_df.columns else "전체"
                                st.session_state.f_status = []
                    except Exception as e:
                        print(f"엔카 자동 스캔 예외: {e}")
                
            st.session_state.debug_success_msg = f"차량 정보 수집 성공! {'✅ 낙찰이력 데이터도 자동 수집됨' if auction_repairs_json else '⚠️ 낙찰이력 없음 (없거나 미지원)'}"

            # 헤이딜러 정보로 사이드바 폼 값 자동 채우기
            try:
                import json
                hd_data = json.loads(heydealer_json_str)
                hd_detail = hd_data.get('detail', {})
                reg_date = hd_detail.get('initial_registration_date') or hd_detail.get('first_registration_date') or hd_detail.get('registration_date') or ''
                import re
                m_year = re.search(r'(\d{4})', str(reg_date))
                hd_year = m_year.group(1) if m_year else hd_detail.get('year', '')
                hd_mil = hd_detail.get('mileage', '')
                hd_plate = hd_detail.get('vehicle_no') or hd_detail.get('number') or hd_detail.get('car_number') or hd_detail.get('plate_number') or hd_detail.get('plate') or hd_detail.get('full_name') or ''
                
                # 차량번호가 full_name에 포함되어 있을 수 있음 (예: "캐스퍼 일렉트릭 123가4567")
                if hd_plate == hd_detail.get('full_name'):
                    # 번호판 패턴 추출 시도
                    import re
                    m = re.search(r'\d{2,3}[가-힣]\s*\d{4}', hd_plate)
                    hd_plate = m.group(0).replace(" ", "") if m else ""

                st.session_state.form_reset_key = st.session_state.get('form_reset_key', 0) + 1
                reset_key = st.session_state.form_reset_key
                
                if hd_mil:
                    st.session_state[f"mil_{reset_key}"] = int(hd_mil)
                if hd_plate:
                    st.session_state[f"car_num_{reset_key}"] = str(hd_plate)
                    
                st.session_state.debug_autofill = f"추출 결과: 연식={hd_year}, 주행거리={hd_mil}, 번호={hd_plate}"
            except Exception as e:
                st.session_state.debug_autofill = f"사이드바 자동 채우기 에러: {str(e)}"

            
            # 실시간 엔카 데이터 통계 사전 계산
            market_data_str = ""
            if 'filtered_df' in globals() and not filtered_df.empty:
                import pandas as pd
                df_temp = filtered_df.copy()
                df_temp['판매가'] = pd.to_numeric(df_temp['판매가'], errors='coerce')
                df_temp = df_temp.dropna(subset=['판매가'])
                
                if not df_temp.empty:
                    avg_price = int(df_temp['판매가'].mean())
                    
                    # 사고 유무별 평균
                    is_no_acc = df_temp['사고유무'].astype(str).str.contains('무사고')
                    no_acc_avg = int(df_temp[is_no_acc]['판매가'].mean()) if is_no_acc.any() else avg_price
                    acc_avg = int(df_temp[~is_no_acc]['판매가'].mean()) if (~is_no_acc).any() else avg_price
                    acc_gap = no_acc_avg - acc_avg
                    
                    # 타겟 차량 옵션 유무별 평균
                    if encar_target_options:
                        has_target_opt = df_temp['추가옵션'].apply(lambda x: any(opt in str(x) for opt in encar_target_options))
                        target_opt_avg = int(df_temp[has_target_opt]['판매가'].mean()) if has_target_opt.any() else avg_price
                        no_target_opt_avg = int(df_temp[~has_target_opt]['판매가'].mean()) if (~has_target_opt).any() else avg_price
                    else:
                        target_opt_avg = avg_price
                        no_target_opt_avg = avg_price
                    opt_gap = target_opt_avg - no_target_opt_avg
                    
                    market_data_str = f"엔카 동급 매물 평균가: {avg_price}만원\n무사고 평균가: {no_acc_avg}만원 / 유사고 평균가: {acc_avg}만원 (사고감가 차이: {acc_gap}만원)\n유사 옵션 포함 평균가: {target_opt_avg}만원 / 미포함 평균가: {no_target_opt_avg}만원 (옵션 차이: {opt_gap}만원)\n"

            # 헤이딜러 동급 낙찰시세 통계 추가
            hd_market_avg = 0
            hd_no_acc_avg = 0
            hd_acc_avg = 0
            hd_target_opt_avg = 0
            hd_no_target_opt_avg = 0
            prev_year_avg = 0
            next_year_avg = 0
            
            if market_prices_json:
                try:
                    mp_data = json.loads(market_prices_json)
                    if isinstance(mp_data, list):
                        results = mp_data
                    else:
                        results = mp_data.get('results', [])
                        
                    if results:
                        hd_comp_df = parse_heydealer_comps(results)
                        st.session_state.hd_comp_df = hd_comp_df
                        
                        hd_detail = json.loads(heydealer_json_str).get('detail', {})
                        reg_date_hd = hd_detail.get('initial_registration_date') or hd_detail.get('first_registration_date') or hd_detail.get('registration_date') or ''
                        import re
                        m_year_hd = re.search(r'(\d{4})', str(reg_date_hd))
                        target_year = int(m_year_hd.group(1)) if m_year_hd else hd_detail.get('year', 0)
                        
                        target_mileage = hd_detail.get('mileage', 0)
                        target_plate = hd_detail.get('vehicle_number', '') or hd_detail.get('plate_number', '')
                        
                        # 세션 상태에 저장하여 사이드바에 표시
                        st.session_state.hd_target_year = target_year
                        st.session_state.hd_target_mileage = target_mileage
                        st.session_state.hd_target_plate = target_plate
                        
                        if not hd_comp_df.empty:
                            if target_year:
                                hd_same_year = hd_comp_df[hd_comp_df['연식_num'] == int(target_year)]
                                hd_prev = hd_comp_df[hd_comp_df['연식_num'] == int(target_year) - 1]
                                hd_next = hd_comp_df[hd_comp_df['연식_num'] == int(target_year) + 1]
                            else:
                                hd_same_year = hd_comp_df
                                hd_prev = pd.DataFrame()
                                hd_next = pd.DataFrame()
                                
                            # 기준 데이터: 동일 연식 우선, 없으면 전체 낙찰 데이터 활용
                            if not hd_same_year.empty:
                                base_df = hd_same_year
                            elif not hd_comp_df.empty:
                                base_df = hd_comp_df
                            else:
                                base_df = pd.DataFrame()

                            if not base_df.empty:
                                # 1. Polyfit 추세선 기준가 계산
                                if len(base_df) >= 2:
                                    z = np.polyfit(base_df['주행거리_num'], base_df['판매가_num'], 1)
                                    hd_market_avg = int(np.polyval(z, int(target_mileage) if target_mileage else 50000))
                                else:
                                    hd_market_avg = int(base_df['판매가_num'].mean())
                                    
                                # 2. 사고/무사고 차이
                                is_no_acc = base_df['사고유무'].astype(str).str.contains('완전무사고')
                                hd_no_acc_avg = int(base_df[is_no_acc]['판매가_num'].mean()) if is_no_acc.any() else hd_market_avg
                                hd_acc_avg = int(base_df[~is_no_acc]['판매가_num'].mean()) if (~is_no_acc).any() else hd_market_avg
                                
                                # 3. 타겟 차량 추가옵션 포함 여부 차이
                                if hd_target_options:
                                    has_target_opt = base_df['옵션리스트'].apply(lambda opts: any(opt in hd_target_options for opt in opts))
                                    hd_target_opt_avg = int(base_df[has_target_opt]['판매가_num'].mean()) if has_target_opt.any() else hd_market_avg
                                    hd_no_target_opt_avg = int(base_df[~has_target_opt]['판매가_num'].mean()) if (~has_target_opt).any() else hd_market_avg
                                else:
                                    hd_target_opt_avg = hd_market_avg
                                    hd_no_target_opt_avg = hd_market_avg
                            else:
                                hd_market_avg = 0
                                hd_no_acc_avg = 0
                                hd_acc_avg = 0
                                hd_target_opt_avg = 0
                                hd_no_target_opt_avg = 0
                            
                            # 4. 전후 연식
                            prev_year_avg = int(hd_prev['판매가_num'].mean()) if not hd_prev.empty else 0
                            next_year_avg = int(hd_next['판매가_num'].mean()) if not hd_next.empty else 0
                            total_count = mp_data.get('count', '?') if isinstance(mp_data, dict) else '?'
                            st.session_state.debug_hd_market = f"매입시세 계산 성공! 기준가: {hd_market_avg}만원 (최근 1페이지 기준: {len(base_df)}대 반영 / 전체 {total_count}대)"
                except Exception as e:
                    st.session_state.debug_hd_market = f"매입시세 파싱 에러: {str(e)}"
            else:
                st.session_state.debug_hd_market = "매입시세 JSON 데이터가 없습니다 (빈 문자열 또는 None)"

            # heydealer_ai.py에서 가져온 함수 실행 (AI가 소매가 직접 추정)
            encar_avg_price = 0
            encar_no_acc_avg = 0
            encar_acc_avg = 0
            encar_target_opt_avg = 0
            encar_no_target_opt_avg = 0
            ai_result = extract_car_data_for_ai(
                heydealer_json_str, 
                retail_avg=avg_price if 'avg_price' in locals() else 0,
                retail_no_acc_avg=no_acc_avg if 'no_acc_avg' in locals() else 0,
                retail_acc_avg=acc_avg if 'acc_avg' in locals() else 0,
                retail_opt_avg=target_opt_avg if 'target_opt_avg' in locals() else 0,
                retail_no_opt_avg=no_target_opt_avg if 'no_target_opt_avg' in locals() else 0,
                wholesale_avg=hd_market_avg,
                wholesale_no_acc_avg=hd_no_acc_avg,
                wholesale_acc_avg=hd_acc_avg,
                wholesale_opt_avg=hd_target_opt_avg,
                wholesale_no_opt_avg=hd_no_target_opt_avg,
                prev_year_avg=prev_year_avg if 'prev_year_avg' in locals() else 0,
                next_year_avg=next_year_avg if 'next_year_avg' in locals() else 0,
                auction_repairs_json=auction_repairs_json
            )
            ai_prompt = ai_result.get("ai_prompt", "")
            data_header = ai_result.get("data_header", "")
            
            st.session_state.ai_estimate_result = data_header
            st.session_state.ai_status = "표시됨"
            st.rerun()
            
        except Exception as e:
            st.sidebar.error(f"작업 실패: {str(e)}")
st.sidebar.markdown("### 🗃️ 데이터 스캔 관리")

with st.sidebar.expander("📁 자사 재고 엑셀 관리", expanded=False):
    uploaded_files = st.file_uploader("자사 재고 엑셀 업로드", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True, label_visibility="collapsed")
    if st.button("📁 엑셀 병합 및 DB 저장", use_container_width=True):
        if uploaded_files:
            new_dfs = []
            for uf in uploaded_files:
                try: new_dfs.append(pd.read_excel(uf) if uf.name.endswith(('xls', 'xlsx')) else pd.read_csv(uf))
                except: pass
            if new_dfs:
                merged_df = pd.concat(new_dfs, ignore_index=True)
                if not st.session_state.inventory_data.empty:
                    st.session_state.inventory_data = pd.concat([st.session_state.inventory_data, merged_df])
                else:
                    st.session_state.inventory_data = merged_df
                
                if '차량번호' in st.session_state.inventory_data.columns:
                    st.session_state.inventory_data = st.session_state.inventory_data.drop_duplicates(subset=['차량번호'], keep='last')
                st.session_state.inventory_data.to_csv(INVENTORY_FILE, index=False, encoding='utf-8-sig')
                st.rerun()

    if st.button("🗑️ 저장된 엑셀 DB 지우기", use_container_width=True):
        st.session_state.inventory_data = pd.DataFrame()
        if os.path.exists(INVENTORY_FILE): os.remove(INVENTORY_FILE)
        st.rerun()

scan_url = st.sidebar.text_input("엔카 정밀 스캔 URL 입력:", key=f"scan_url_{st.session_state.form_reset_key}", label_visibility="collapsed", placeholder="엔카 URL 붙여넣기")
    
if st.sidebar.button("🚀 실시간 엔카 스캔", use_container_width=True):
    if scan_url:
        p_bar, s_text = st.progress(0), st.empty()
        new_scan_df, msg = Scraper.run(scan_url, "", p_bar, s_text)
        if msg == "success":
            st.session_state.scan_data = pd.concat([st.session_state.scan_data, new_scan_df], ignore_index=True)
            st.session_state.scan_data = st.session_state.scan_data.drop_duplicates(subset=['_carid'], keep='last').reset_index(drop=True)
            
            if not new_scan_df.empty:
                st.session_state.f_brand = new_scan_df['제조사'].iloc[0] if '제조사' in new_scan_df.columns else "전체"
                st.session_state.f_name = new_scan_df['차량명'].iloc[0]
                st.session_state.f_sub = new_scan_df['세부모델'].iloc[0]
                st.session_state.f_status = [] 
            st.rerun()
        else: s_text.error(msg)
        
btn_col1, btn_col2 = st.sidebar.columns(2)
with btn_col1:
    if st.button("스캔 초기화", use_container_width=True): 
        st.session_state.scan_data = pd.DataFrame()
        st.session_state.f_brand = "전체"
        st.session_state.f_name = "전체"
        st.session_state.f_sub = "전체"
        st.rerun()
with btn_col2:
    kcar_search_text = ""
    f_name = st.session_state.get('f_name', '전체')
    f_sub = st.session_state.get('f_sub', '전체')
    
    if f_name != "전체":
        import re
        
        # 괄호 제거 후 띄어쓰기 모두 없앰 (Kcar는 띄어쓰기 없는게 검색 더 잘됨)
        kcar_name_clean = re.sub(r'\(.*?\)', '', str(f_name)).replace(" ", "").strip()
        kcar_parts = [kcar_name_clean]
        
        if f_sub != "전체":
            # 세부모델의 괄호 제거
            kcar_sub_clean = re.sub(r'\(.*?\)', '', str(f_sub)).strip()
            # KCar는 영문과 숫자 사이 띄어쓰기를 인식하는 경우가 많음 (예: VX 2WD)
            kcar_sub_clean = re.sub(r'([A-Za-z])(\d)', r'\1 \2', kcar_sub_clean).strip()
            if kcar_sub_clean:
                kcar_parts.append(kcar_sub_clean)
                
        kcar_search_text = " ".join(kcar_parts)
        
    if kcar_search_text:
        import urllib.parse, json
        # KCar의 현재 검색 파라미터 규격에 맞춤
        cond = {"wr_txt_idx": kcar_search_text}
        cond_str = json.dumps(cond, separators=(',', ':'))
        kcar_url = f"https://www.kcar.com/bc/search?searchCond={urllib.parse.quote(cond_str)}"
    else:
        kcar_url = "https://www.kcar.com/bc/search"
    st.link_button("🔎 KCAR", kcar_url, use_container_width=True)

if not st.session_state.scan_data.empty:
    failed_mask = st.session_state.scan_data['성능일'].astype(str).str.contains("조회실패") | \
                  st.session_state.scan_data['사고유무'].astype(str).str.contains("조회실패") | \
                  st.session_state.scan_data['추가옵션'].astype(str).str.contains("조회실패")
    failed_count = failed_mask.sum()
    
    if failed_count > 0:
        st.markdown("---")
        st.warning(f"⚠️ 조회실패 차량: {failed_count}대")
        if st.sidebar.button("♻️ 실패 차량만 재스캔", use_container_width=True):
            p_bar, s_text = st.progress(0), st.empty()
            failed_indices = st.session_state.scan_data[failed_mask].index
            Scraper.rescan(failed_indices, "", p_bar, s_text)
            st.rerun()

st.sidebar.markdown(f"**총 스캔 대수: {len(st.session_state.scan_data)} 대**")

st.sidebar.markdown("### 🔍 상세 검색 필터")
filtered_df = st.session_state.scan_data.copy()
filtered_df = DataProcessor.standardize(filtered_df)

current_f_year = ""
current_f_mil = 0

if not filtered_df.empty:
        f_brand_opts = ["전체"] + list(filtered_df['제조사'].dropna().unique())
        if st.session_state.f_brand not in f_brand_opts: st.session_state.f_brand = "전체"
        st.session_state.f_brand = st.sidebar.selectbox("제조사/브랜드", f_brand_opts, index=f_brand_opts.index(st.session_state.f_brand))
        if st.session_state.f_brand != "전체": 
            filtered_df = filtered_df[filtered_df['제조사'] == st.session_state.f_brand]

        def get_smart_sort_key(name):
            name_str = str(name)
            core_models = ['그랜저', '싼타페', '아반떼', '쏘나타', '투싼', '팰리세이드', '스타리아', '스타렉스',
                           'K3', 'K5', 'K7', 'K8', 'K9', '쏘렌토', '스포티지', '카니발', '모닝', '레이',
                           '제네시스', 'G70', 'G80', 'G90', 'GV70', 'GV80', 'GV60',
                           '스파크', '말리부', '트레일블레이저', 'SM3', 'SM5', 'SM6', 'QM3', 'QM6', 'XM3',
                           '티볼리', '코란도', '렉스턴', '토레스', 'E클래스', 'S클래스', 'C클래스', '5시리즈', '3시리즈', '7시리즈']
            for core in core_models:
                if core in name_str: return f"{core}_{name_str}"
            return name_str

        raw_names = set(filtered_df['차량명'].dropna().unique())
        if 'inventory_data' in st.session_state and not st.session_state.inventory_data.empty:
            raw_names.update(st.session_state.inventory_data['차량명'].dropna().unique())
        
        sorted_names = sorted(list(raw_names), key=get_smart_sort_key)
        f_name_opts = ["전체"] + sorted_names
        
        if st.session_state.f_name not in f_name_opts: st.session_state.f_name = "전체"
        st.session_state.f_name = st.sidebar.selectbox("차량명", f_name_opts, index=f_name_opts.index(st.session_state.f_name))
        
        if st.session_state.f_name != "전체": 
            # 엔카 데이터도 띄어쓰기 무시 필터 적용
            name_clean_f = str(st.session_state.f_name).replace(" ", "").lower()
            filtered_df = filtered_df[filtered_df['차량명'].astype(str).str.replace(" ", "").str.lower().str.contains(name_clean_f, na=False, regex=False)]
        
        raw_subs = set(filtered_df['세부모델'].dropna().unique())
        if 'inventory_data' in st.session_state and not st.session_state.inventory_data.empty:
            if '세부모델' in st.session_state.inventory_data.columns:
                inv_df_filtered = st.session_state.inventory_data
                if st.session_state.f_name != "전체":
                    name_clean_f = str(st.session_state.f_name).replace(" ", "").lower()
                    full_names = inv_df_filtered['차량명'].astype(str) + " " + inv_df_filtered['세부모델'].astype(str)
                    full_names_clean = full_names.str.replace(" ", "").str.lower()
                    inv_df_filtered = inv_df_filtered[full_names_clean.str.contains(name_clean_f, na=False, regex=False)]
                raw_subs.update(inv_df_filtered['세부모델'].dropna().unique())
        
        f_sub_opts = ["전체"] + sorted(list(raw_subs))
        if st.session_state.f_sub not in f_sub_opts: st.session_state.f_sub = "전체"
        st.session_state.f_sub = st.sidebar.selectbox("세부모델", f_sub_opts, index=f_sub_opts.index(st.session_state.f_sub))
        
        if st.session_state.f_sub != "전체": 
            # 엔카 데이터도 띄어쓰기 무시 + 단어별 필터 적용
            sub_parts = str(st.session_state.f_sub).split()
            encar_sub_clean = filtered_df['세부모델'].astype(str).str.replace(" ", "").str.lower()
            for part in sub_parts:
                part_clean = part.replace(" ", "").lower()
                filtered_df = filtered_df[encar_sub_clean.str.contains(part_clean, na=False, regex=False)]
                encar_sub_clean = encar_sub_clean[filtered_df.index]
        
        current_f_year = st.sidebar.text_input("연식 검색 (예: 24)", key=f"search_year_{st.session_state.form_reset_key}")
        if current_f_year: filtered_df = filtered_df[filtered_df['연식'].astype(str).str.contains(current_f_year)]
        
        if "주행거리" in filtered_df.columns:
            filtered_df["주행거리"] = pd.to_numeric(filtered_df["주행거리"], errors='coerce').fillna(0)
            max_mil = int(filtered_df["주행거리"].max()) if not filtered_df.empty else 0
            if max_mil > 0:
                current_f_mil = st.sidebar.slider("📈 시세분석용 주행거리 이하 (km)", 0, max_mil, max_mil, step=1000)

        if "재고" in filtered_df.columns:
            filtered_df['_sort_inv'] = pd.to_numeric(filtered_df['재고'], errors='coerce').fillna(99999)
            filtered_df = filtered_df.sort_values(by='_sort_inv', ascending=True).drop(columns=['_sort_inv']).reset_index(drop=True)

st.sidebar.markdown("---")


tab_main, tab_sales, tab_inventory, tab_ledger = st.tabs(["📊 시세 조회 및 스캔", "📋 판매 리스트", "📋 재고 리스트", "📋 내 실전 장부 리스트"])

with tab_main:
    # ==========================================
    # 📝 실시간 장부 자동 계산기 (리얼타임 반응형)
    # ==========================================
    ai_summary_placeholder = st.sidebar.empty()


    st.sidebar.markdown("### 📝 장부 관리")

    if st.session_state.save_success:
        st.sidebar.success(f"✅ {st.session_state.saved_car_num} 장부 및 구글시트 저장 완료!")
        st.session_state.save_success = False

    # 🔥 폼 입력칸들에 동적 키(form_reset_key)를 부여하여, 저장 시 에러 없이 통째로 교체되게 만듦
    reset_idx = st.session_state.form_reset_key

    l_car_num = st.sidebar.text_input("차량번호 (필수)", key=f"car_num_{reset_idx}")
    l_mil = st.sidebar.number_input("주행거리 (km)", min_value=0, step=1000, key=f"mil_{reset_idx}")

    st.sidebar.markdown("---")

    l_sell_price = st.sidebar.number_input("판매가 (예상, 만원)", min_value=0, step=10, key=f"sell_{reset_idx}")
    l_ext_repair = st.sidebar.number_input("외판 수리 갯수", min_value=0, step=1, format="%d", key=f"ext_{reset_idx}")

    route_options = ["셀프(기본)", "제로", "개인"]
    def update_route():
        if "_route_selector" in st.session_state:
            st.session_state.purchase_route = st.session_state._route_selector

    l_route = st.sidebar.radio("매입 경로", route_options, index=route_options.index(st.session_state.purchase_route), key="_route_selector", on_change=update_route)

    l_manual_fee = 0
    if l_route == "개인":
        l_manual_fee = st.sidebar.number_input("매입 수수료 (직접입력, 만원)", min_value=0, step=1, key=f"man_{reset_idx}")

    l_margin = st.sidebar.number_input("목표 마진 (만원)", min_value=0, step=10, value=120, key="margin_key")

    name_val = st.session_state.f_name if st.session_state.f_name != "전체" else ""
    is_light_car = any(x in name_val for x in ["모닝", "레이", "스파크", "마티즈", "캐스퍼", "티코"])

    selling_fee = l_sell_price * 0.007
    misc_cost = 15
    ext_cost = l_ext_repair * 13

    first_target = l_sell_price - selling_fee - misc_cost - ext_cost - l_margin
    purchase_fee = 0

    if l_route == "셀프(기본)":
        if first_target <= 100: purchase_fee = 7.5
        elif first_target <= 500: purchase_fee = 18.5
        elif first_target <= 1000: purchase_fee = 19.0 if is_light_car else 24.5
        elif first_target <= 3000: purchase_fee = 25.0
        else: purchase_fee = 36.0
    elif l_route == "제로":
        if first_target <= 100: purchase_fee = 14.0
        elif first_target <= 500: purchase_fee = 30.0
        elif first_target <= 1000: purchase_fee = 30.5 if is_light_car else 36.5
        elif first_target <= 1500: purchase_fee = 36.5
        elif first_target <= 3000: purchase_fee = 39.5
        elif first_target <= 4000: purchase_fee = 47.5
        else: purchase_fee = 50.5
    elif l_route == "개인":
        purchase_fee = l_manual_fee

    final_target_raw = first_target - purchase_fee
    final_target = int(math.floor(final_target_raw))

    st.sidebar.markdown("---")
    if l_sell_price > 0:
        html_content = f"""
        <div style="background-color: #d1e7dd; border: 1px solid #badbcc; padding: 15px; border-radius: 8px; color: #0f5132; margin-bottom: 15px;">
            <div style="font-size: 1.1em; font-weight: bold; margin-bottom: 5px;">✅ 권장 입찰가(매입가)</div>
            <div style="font-size: 2.3em; font-weight: 900; text-align: right; margin-bottom: 15px; color: #0a3622;">
                {final_target:,} <span style="font-size: 0.6em; font-weight: normal;">만원</span>
            </div>
            <div style="font-size: 0.9em; text-align: right; color: #146c43;">
                (수수료: {purchase_fee:g}만 / 수리비: {ext_cost:g}만)
            </div>
        </div>
        """
        st.sidebar.markdown(html_content, unsafe_allow_html=True)
    else:
        st.sidebar.info("💡 판매가를 입력하시면 매입가가 자동 계산됩니다.")

    l_memo = st.sidebar.text_area("특이사항 / 메모", height=80, key=f"memo_{reset_idx}")

    if st.sidebar.button("💾 내 장부 및 구글시트에 저장", use_container_width=True):
        if not l_car_num:
            st.sidebar.error("⚠️ 차량번호 필수")
        else:
            brand_val = st.session_state.f_brand if st.session_state.f_brand != "전체" else ""
            sub_val = st.session_state.f_sub if st.session_state.f_sub != "전체" else ""
            year_val = current_f_year if current_f_year else ""

            new_record = {
                '등록일': datetime.now().strftime("%y-%m-%d"), 
                '차량번호': l_car_num, 
                '제조사': brand_val,
                '차량명': name_val,
                '세부모델': sub_val,
                '연식': year_val,
                '주행거리': f"{l_mil:,} km" if l_mil > 0 else "", 
                '매입가': final_target if l_sell_price > 0 else "", 
                '판매가': l_sell_price if l_sell_price > 0 else "", 
                '특이사항': f"[{st.session_state.purchase_route}] " + l_memo
            }
            st.session_state.my_ledger_data = pd.concat([st.session_state.my_ledger_data, pd.DataFrame([new_record])], ignore_index=True)
            st.session_state.my_ledger_data.to_csv(LEDGER_FILE, index=False, encoding='utf-8-sig')
        
            try:
                response = requests.post(WEBHOOK_URL, json=new_record, timeout=5)
                response.raise_for_status()
            except Exception as e:
                print(f"🔥 구글 시트 웹훅 전송 실패: {e}")

            st.session_state.save_success = True
            st.session_state.saved_car_num = l_car_num
            st.session_state.form_reset_key += 1
        
            st.rerun()


        # ==========================================
    # 🚘 [1] 엔카 시세 요약본 (크기 2/3) + 요약 1번
    # ==========================================
    chart_base = filtered_df.copy()
    if current_f_mil > 0 and '주행거리' in chart_base.columns:
        chart_base = chart_base[chart_base['주행거리'] <= current_f_mil]

    if not chart_base.empty and '판매가' in chart_base.columns:
        valid_prices = pd.to_numeric(chart_base['판매가'], errors='coerce').dropna()
    else:
        valid_prices = pd.Series(dtype=float)
        
    encar_total_count = len(chart_base)
    encar_min_price = int(valid_prices.min()) if not valid_prices.empty else 0
    encar_max_price = int(valid_prices.max()) if not valid_prices.empty else 0
    encar_avg_price = int(valid_prices.mean()) if not valid_prices.empty else 0

    st.markdown("### 🚘 엔카 실시간 소매 시세 요약")
    st.markdown(f"""
    <div style='display: flex; gap: 12px; margin-top: 8px; margin-bottom: 8px;'>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>🚙</div>
            <div class='metric-content'><h4>총 매물 수</h4><h2>{encar_total_count:,} 대</h2></div>
        </div>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>⬇️</div>
            <div class='metric-content'><h4>최저가</h4><h2 style='color: #4a90e2;'>{encar_min_price:,} 만원 <span style='font-size: 0.6em'>⬇️</span></h2></div>
        </div>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>⬆️</div>
            <div class='metric-content'><h4>최고가</h4><h2 style='color: #e25c5c;'>{encar_max_price:,} 만원 <span style='font-size: 0.6em'>⬆️</span></h2></div>
        </div>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>📊</div>
            <div class='metric-content'><h4>평균가</h4><h2 style='color: #cc9166;'>{encar_avg_price:,} 만원</h2></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 요약 1번 계산 및 렌더링
    encar_no_acc_avg = 0
    encar_acc_avg = 0
    encar_acc_gap = 0
    encar_year_stats = ""
    if not chart_base.empty and '사고유무' in chart_base.columns:
        is_no = chart_base['사고유무'].astype(str).str.contains('무사고')
        p_num = pd.to_numeric(chart_base['판매가'], errors='coerce')
        if is_no.any(): encar_no_acc_avg = int(p_num[is_no].mean())
        if (~is_no).any(): encar_acc_avg = int(p_num[~is_no].mean())
        
        if encar_no_acc_avg > 0 and encar_acc_avg > 0:
            encar_acc_gap = encar_no_acc_avg - encar_acc_avg
            
        # 연식별 평균
        if '연식' in chart_base.columns:
            years = sorted(chart_base['연식'].dropna().unique())
            y_parts = []
            for y in years[-3:]:
                sub_p = p_num[chart_base['연식'] == y].dropna()
                if not sub_p.empty:
                    y_parts.append(f"{y}년 평균 {int(sub_p.mean()):,}만원")
            if y_parts:
                encar_year_stats = " / ".join(y_parts)

    st.markdown(f"""
    <div class='summary-box'>
        <b style='color: #cc9166; font-size: 1.05em;'>📋 (1) 예상 소매가 기준 (엔카 판매 데이터)</b><br>
        • 동급 평균: <b style='color: #fff;'>{encar_avg_price:,}만원</b> (무사고 <b>{encar_no_acc_avg:,}만원</b> / 유사고 <b>{encar_acc_avg:,}만원</b> - 사고감가 차이: {encar_acc_gap:,}만원)<br>
        • {encar_year_stats if encar_year_stats else '연식별 데이터 집계 완료'}
    </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # 📊 [2] 엔카 시세 리스트 및 상세스펙
    # ==========================================
    if not filtered_df.empty:
        main_col1, main_col2 = st.columns([6.2, 3.8])

        with main_col1:
            st.markdown("#### 📊 엔카 시세 리스트")
            display_df = filtered_df.copy()

            def summarize_options(opt_str):
                if not opt_str or opt_str in ("없음", "-", "없음(구버전점검)", "⚠️조회실패", "코드매칭실패"):
                    return opt_str
                items = [o.strip() for o in str(opt_str).split(" / ") if o.strip()]
                return f"{len(items)}개 옵션"

            display_df["추가옵션_요약"] = display_df["추가옵션"].apply(summarize_options)
    
            def make_link_name(row):
                if pd.notna(row.get('링크')) and str(row.get('링크')).startswith('http'):
                    name = row.get('차량명', '상세보기')
                    return f"{str(row['링크'])}#_name={name}"
                return ""
            display_df["차량명_링크"] = display_df.apply(make_link_name, axis=1)

            def format_display_acc(acc_val):
                s = str(acc_val).strip()
                if not s or s in ("-", "정보없음", "기록부(사진)", "⚠️조회실패"):
                    return s
                
                # 1. 기존 중복 아이콘 제거
                s = s.replace("⚠️", "").replace("✅", "").replace("🟢", "").replace("🟡", "").replace("🔴", "").strip()
                
                # 2. 세션에 남아있는 기존 오표기 일괄 자동 치환
                s = s.replace("(사고/판금)", "사고").replace("(사고/단순)", "사고")
                s = s.replace("(판금)", "단순교환").replace("(단순)", "단순교환")
                s = s.replace("사고/판금", "사고").replace("사고/단순", "사고")
                
                # 3. [판금:0], [교환:0] 정리
                s = re.sub(r'\s*/\s*판금:0', '', s)
                s = re.sub(r'교환:0\s*/\s*', '', s)
                s = re.sub(r'\[교환:0\]', '', s)
                s = re.sub(r'\[판금:0\]', '', s)
                s = re.sub(r'\[\s*\]', '', s)

                if '교환:' in s and '판금:' not in s:
                    s = re.sub(r'단순\s*\([^)]*\)|단순판금', '단순교환', s)
                elif '판금:' in s and '교환:' not in s:
                    s = re.sub(r'단순\s*\([^)]*\)|단순교환', '단순판금', s)
                elif '교환:' in s and '판금:' in s:
                    s = re.sub(r'단순\s*\([^)]*\)|단순교환|단순판금', '단순(교환/판금)', s)

                s = s.strip()
                
                # 4. 단일 정품 아이콘 부여
                if "무사고" in s or "완무" in s:
                    return f"🟢 {s}"
                elif "사고" in s:
                    return f"🔴 {s}"
                elif "단순" in s or "판금" in s or "교환" in s:
                    return f"🟡 {s}"
                return s
            display_df["사고유무_표시"] = display_df["사고유무"].apply(format_display_acc)

            try:
                styled_df = display_df.style.set_properties(
                    subset=[c for c in ['주행거리', '판매가'] if c in display_df.columns],
                    **{'font-size': '1.05em', 'font-weight': 'bold'}
                ).format(precision=0)

                event = st.dataframe(
                    styled_df,
                    column_config={
                        "상태": st.column_config.TextColumn("상태"),
                        "성능일": st.column_config.TextColumn("성능일"),
                        "차량명_링크": st.column_config.LinkColumn("차량명", display_text=r"#_name=(.*)"),
                        "세부모델": st.column_config.TextColumn("세부모델"),
                        "연식": st.column_config.TextColumn("연식"),
                        "주행거리": st.column_config.NumberColumn("주행(km)", format="%d"),
                        "판매가": st.column_config.NumberColumn("가격(만)", format="%d"),
                        "사고유무_표시": st.column_config.TextColumn("사고유무"),
                        "외장컬러": st.column_config.TextColumn("색상"),
                        "추가옵션_요약": st.column_config.TextColumn("옵션"),
                        "재고": st.column_config.TextColumn("재고"),
                    },
                    column_order=[
                        "성능일", "차량명_링크", "세부모델", "연식", 
                        "주행거리", "판매가", "사고유무_표시", "외장컬러", "추가옵션_요약", "재고"
                    ],
                    use_container_width=False,
                    hide_index=True,
                    height=520,
                    on_select="rerun",
                    selection_mode="single-row"
                )
            except Exception as e:
                st.dataframe(display_df, use_container_width=True, hide_index=True, height=520)

        with main_col2:
            st.markdown("#### 🔍 상세 스펙 & 성능점검")
            selected_rows = event.selection.rows if hasattr(event, "selection") else []
            
            if selected_rows:
                selected_idx = selected_rows[0]
                row = display_df.iloc[selected_idx]

                PART_COORDS_OUTER = [
                    (("후드",),                55, 20,  110, 55, "후드", "후드"),
                    (("앞","휀더","좌"),    15, 25,  35, 65, "F휀", "프론트 휀더(좌)"),
                    (("앞","휀더","우"),   170, 25,  35, 65, "F휀", "프론트 휀더(우)"),
                    (("앞","문","좌"),    10, 100, 40, 60, "F도", "프론트 도어(좌)"),
                    (("앞","문","우"),   170, 100, 40, 60, "F도", "프론트 도어(우)"),
                    (("뒤","문","좌"),      10, 165, 40, 60, "R도", "리어 도어(좌)"),
                    (("뒤","문","우"),     170, 165, 40, 60, "R도", "리어 도어(우)"),
                    (("쿼터","좌"),             10, 230, 40, 60, "쿼터", "쿼터 패널(리어펜더)(좌)"),
                    (("쿼터","우"),            170, 230, 40, 60, "쿼터", "쿼터 패널(리어펜더)(우)"),
                    (("루프",),                 55, 80,  110, 145, "루프", "루프"),
                    (("트렁크","리드"),         55, 230, 110, 60, "TR", "트렁크리드"),
                ]

                PART_COORDS_INNER = [
                    (("앞","사이드","멤버","좌"), 10, 30,  40, 55, "F멤", "프론트 사이드멤버(좌)"),
                    (("앞","사이드","멤버","우"),170, 30,  40, 55, "F멤", "프론트 사이드멤버(우)"),
                    (("크로스","멤버"),               55, 30,  110, 30, "크로스", "크로스멤버"),
                    (("라디에이터","서포트"),         55, 65,  110, 30, "R.S", "라디에이터 서포트"),
                    (("인사이드","패널","좌"),        10, 100, 40, 120, "I패", "인사이드 패널(좌)"),
                    (("인사이드","패널","우"),       170, 100, 40, 120, "I패", "인사이드 패널(우)"),
                    (("뒤","사이드","멤버","좌"),   10, 230, 40, 60, "R멤", "리어 사이드멤버(좌)"),
                    (("뒤","사이드","멤버","우"),  170, 230, 40, 60, "R멤", "리어 사이드멤버(우)"),
                    (("트렁크","플로어"),             55, 230, 110, 60, "T플", "트렁크 플로어"),
                    (("뒤","패널"),                 55, 290, 110, 20, "R패", "리어 패널"),
                ]

                STATUS_COLOR = {
                    "교환": "#ff4d4d",
                    "판금": "#ffdd57",
                    "정상": "#2e3038",
                }

                def find_status(damage_data, *keywords):
                    for name, status in damage_data.items():
                        if all(k in name for k in keywords):
                            return status
                    return "정상"

                def render_panel_svg(damage_data, coords, panel_title):
                    shapes = ""
                    for keywords, x, y, w, h, short_label, full_label in coords:
                        status = find_status(damage_data, *keywords)
                        color = STATUS_COLOR.get(status, "#2e3038")
                        tx, ty = x + w / 2, y + h / 2
                        shapes += f"""<g>
    <title>{full_label} : {status}</title>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{color}" stroke="#464853" stroke-width="1.2"/>
    <text x="{tx}" y="{ty}" text-anchor="middle" dominant-baseline="middle" font-size="10" fill="#ffffff">{short_label}</text>
    </g>"""

                    return f"""
    <div style="text-align:center;">
      <div style="font-weight:bold; margin-bottom:6px; color:#acafb9;">{panel_title}</div>
      <svg viewBox="0 0 220 340" style="width:100%; max-width:210px;">
        <rect x="15" y="10" width="190" height="320" rx="20" fill="#121317" stroke="#2e3038" stroke-width="1"/>
        {shapes}
      </svg>
    </div>
    """

                def render_car_diagram(damage_data):
                    outer_html = render_panel_svg(damage_data, PART_COORDS_OUTER, "외판")
                    inner_html = render_panel_svg(damage_data, PART_COORDS_INNER, "주요골격")
                    return f"""
    <div style='background-color: #121317; color: #e2e3e9; border-radius: 10px; padding: 15px; border: 1px solid #2e3038;'>
    <div style="display:flex; justify-content:space-around; gap:8px;">
      {outer_html}
      {inner_html}
    </div>
    <div style='margin-top: 10px; font-size: 0.85em; color: #acafb9; text-align:center;'>
    <span style='margin-right: 10px;'><span style='color: #ff4d4d;'>■</span> 교환</span>
    <span style='margin-right: 10px;'><span style='color: #ffdd57;'>■</span> 판금/손상</span>
    <span><span style='color: #2e3038; border: 1px solid #464853; padding: 0 4px;'>■</span> 정상</span>
    </div>
    </div>
    """

                opt_items = [o.strip() for o in str(row['추가옵션']).split(" / ") if o.strip() and o.strip() not in ("없음", "-", "없음(구버전점검)", "⚠️조회실패", "코드매칭실패")]
                opt_html = ""
                for opt in opt_items[:8]:
                    opt_html += f"<div style='background:#1e222d; color:#93c5fd; padding:5px 10px; border-radius:8px; font-size:0.86em; font-weight:500; margin:3px 2px; display:inline-block; border: 1px solid #2e384d;'>✓ {opt}</div>"
                if len(opt_items) > 8:
                    opt_html += f"<div style='background:#1e222d; color:#94a3b8; padding:5px 10px; border-radius:8px; font-size:0.86em; font-weight:500; margin:3px 2px; display:inline-block; border: 1px solid #2e384d;'>+{len(opt_items)-8}</div>"

                carid = row.get('_carid')
                def get_damage_info(carid):
                    import requests
                    try:
                        if not carid: return {}
                        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": f"https://fem.encar.com/cars/detail/{carid}"}
                        v_url = f"https://api.encar.com/v1/readside/vehicle/{carid}?include=MANAGE"
                        v_resp = requests.get(v_url, headers=headers, timeout=5)
                        real_id = str(carid)
                        if v_resp.status_code == 200:
                            manage = v_resp.json().get("manage") or {}
                            if manage.get("dummy"):
                                real_id = str(manage.get("dummyVehicleId") or carid)

                        ENCAR_NAME_MAP = {
                            "FRONT_DOOR_LEFT": "앞문(좌)", "FRONT_DOOR_RIGHT": "앞문(우)",
                            "BACK_DOOR_LEFT": "뒷문(좌)", "BACK_DOOR_RIGHT": "뒷문(우)",
                            "REAR_DOOR_LEFT": "뒷문(좌)", "REAR_DOOR_RIGHT": "뒷문(우)",
                            "FRONT_FENDER_LEFT": "앞휀더(좌)", "FRONT_FENDER_RIGHT": "앞휀더(우)",
                            "BACK_FENDER_LEFT": "뒤휀더/쿼터(좌)", "BACK_FENDER_RIGHT": "뒤휀더/쿼터(우)",
                            "REAR_FENDER_LEFT": "뒤휀더/쿼터(좌)", "REAR_FENDER_RIGHT": "뒤휀더/쿼터(우)",
                            "QUARTER_LEFT": "쿼터패널(좌)", "QUARTER_RIGHT": "쿼터패널(우)",
                            "HOOD": "후드(보닛)", "BONNET": "후드(보닛)", "TRUNK_LID": "트렁크리드", "TRUNK": "트렁크리드",
                            "ROOF": "루프", "RADIATOR_SUPPORT": "라디에이터 서포트", "FRONT_PANEL": "프론트패널", "REAR_PANEL": "리어패널",
                            "CROSS_MEMBER": "크로스멤버", "INSIDE_PANEL_LEFT": "인사이드패널(좌)", "INSIDE_PANEL_RIGHT": "인사이드패널(우)",
                            "SIDE_MEMBER_LEFT": "사이드멤버(좌)", "SIDE_MEMBER_RIGHT": "사이드멤버(우)",
                            "WHEEL_HOUSE_LEFT": "휠하우스(좌)", "WHEEL_HOUSE_RIGHT": "휠하우스(우)",
                            "DASH_PANEL": "대쉬패널", "FLOOR_PANEL": "플로어패널", "TRUNK_FLOOR": "트렁크플로어"
                        }

                        def normalize_part_name(name):
                            n = str(name).strip().replace(" ", "")
                            n = n.replace("프론트", "앞").replace("리어", "뒤")
                            n = n.replace("보닛", "후드(보닛)").replace("후드", "후드(보닛)").replace("후드(보닛)(보닛)", "후드(보닛)")
                            n = n.replace("도어", "문")
                            n = n.replace("펜더", "휀더")
                            if "트렁크" in n and "플로어" not in n:
                                n = "트렁크리드"
                            return n

                        damage_dict = {}

                        i_url = f"https://api.encar.com/v1/readside/inspection/vehicle/{real_id}"
                        i_resp = requests.get(i_url, headers=headers, timeout=5)
                        if i_resp.status_code == 200:
                            ij = i_resp.json()
                            all_parts = (ij.get("outers", []) or []) + (ij.get("inners", []) or [])
                            if not all_parts and "master" in ij:
                                all_parts = (ij["master"].get("outers", []) or []) + (ij["master"].get("inners", []) or [])
                            for part in all_parts:
                                part_type = part.get("type", {}) or {}
                                name = part_type.get("title", "")
                                status_types = part.get("statusTypes", []) or []
                                codes = [str(s.get("code", "")).upper() for s in status_types if isinstance(s, dict)]
                                if not name: continue
                                norm_n = normalize_part_name(name)
                                if "X" in codes:
                                    damage_dict[norm_n] = "교환"
                                elif any(c in codes for c in ["W", "C", "A", "U", "T"]):
                                    if damage_dict.get(norm_n) != "교환":
                                        damage_dict[norm_n] = "판금"

                        has_damage = any(v in ["교환", "판금"] for v in damage_dict.values())
                        if not has_damage:
                            d_url = f"https://api.encar.com/v1/readside/diagnosis/vehicle/{real_id}"
                            d_resp = requests.get(d_url, headers=headers, timeout=5)
                            if d_resp.status_code == 200:
                                dj = d_resp.json()
                                if "items" in dj and isinstance(dj["items"], list):
                                    for it in dj["items"]:
                                        raw_n = it.get("name", "")
                                        if raw_n in ["CHECKER_COMMENT", "OUTER_PANEL_COMMENT"]: continue
                                        rc = str(it.get("resultCode", "") or "").upper()
                                        rt = it.get("result", "") or ""
                                        mapped_n = ENCAR_NAME_MAP.get(raw_n, raw_n)
                                        norm_n = normalize_part_name(mapped_n)
                                        if rc in ["REPLACEMENT", "EXCHANGE", "X"] or rt == "교환":
                                            damage_dict[norm_n] = "교환"
                                        elif rc in ["SHEET_METAL", "WELD", "W", "C", "A", "U", "T"] or rt in ["판금", "용접", "도색", "수리"]:
                                            if damage_dict.get(norm_n) != "교환":
                                                damage_dict[norm_n] = "판금"

                                d_parts = (dj.get("outers", []) or []) + (dj.get("inners", []) or [])
                                for part in d_parts:
                                    part_type = part.get("type", {}) or {}
                                    name = part_type.get("title", "")
                                    status_types = part.get("statusTypes", []) or []
                                    codes = [str(s.get("code", "")).upper() for s in status_types if isinstance(s, dict)]
                                    if not name: continue
                                    norm_n = normalize_part_name(name)
                                    if "X" in codes:
                                        damage_dict[norm_n] = "교환"
                                    elif any(c in codes for c in ["W", "C", "A", "U", "T"]):
                                        if damage_dict.get(norm_n) != "교환":
                                            damage_dict[norm_n] = "판금"

                        return damage_dict
                    except Exception:
                        return {}

                damage_data = {}
                if carid:
                    damage_data = get_damage_info(carid)

                diag_html = render_car_diagram(damage_data)
                
                st.markdown(f"""
                <div style='background:#121317; border: 1px solid #2e3038; border-radius: 8px; padding: 12px; margin-bottom: 10px;'>
                    <div style='font-size: 1.1em; font-weight: bold; color: #ffffff;'>{row['차량명']}</div>
                    <div style='font-size: 0.85em; color: #9194a1;'>{row['세부모델']} · {row['연식']}년식 · {int(row['주행거리']) if pd.notna(row['주행거리']) else 0:,}km</div>
                    <div style='font-size: 1.25em; font-weight: bold; color: #cc9166; margin-top: 4px;'>{int(row['판매가']) if pd.notna(row['판매가']) else 0:,} 만원</div>
                    <div style='margin-top: 8px;'>{opt_html}</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(diag_html, unsafe_allow_html=True)
            else:
                st.info("👈 좌측 표에서 차량을 클릭하시면 상세 정보와 성능기록부 사고 부위가 여기에 표시됩니다.")
    else:
        st.info("👈 좌측 사이드바에서 엔카 URL을 스캔하거나 헤이딜러 수집을 실행하여 데이터를 불러와 주세요.")

    st.markdown("---")

    # ==========================================
    # 📈 [3] 가격-주행거리 산점도
    # ==========================================
    st.markdown("### 📈 가격-주행거리 산점도")

    chart_base = filtered_df.copy()
    if current_f_mil > 0 and '주행거리' in chart_base.columns:
        chart_base = chart_base[chart_base['주행거리'] <= current_f_mil]

    valid_prices = pd.to_numeric(chart_base['판매가'], errors='coerce').dropna() if not chart_base.empty and '판매가' in chart_base.columns else pd.Series(dtype=float)

    if not valid_prices.empty:
        chart_base['주행거리_num'] = pd.to_numeric(chart_base['주행거리'], errors='coerce')
        chart_base['판매가_num'] = pd.to_numeric(chart_base['판매가'], errors='coerce')
        chart_df = chart_base.dropna(subset=['주행거리_num', '판매가_num'])

        if not chart_df.empty:
            fig = go.Figure()

            def get_color(acc):
                acc_str = str(acc)
                if "완전무사고" in acc_str or "무사고" in acc_str: return '#2CA02C' 
                elif "사고" in acc_str: return '#D62728' 
                elif "판금" in acc_str or "교환" in acc_str: return '#FF7F0E' 
                else: return '#7F7F7F'

            colors = chart_df['사고유무'].apply(get_color).tolist()

            hover_text = [
                f"출처: {r.get('상태', '실시간')}<br>{r.get('연식', '')}년식 · {r.get('차량명', '')}<br>{r.get('사고유무', '')}"
                for _, r in chart_df.iterrows()
            ]

            fig.add_trace(go.Scatter(
                x=chart_df['주행거리_num'],
                y=chart_df['판매가_num'],
                mode='markers',
                marker=dict(size=9, color=colors, opacity=0.85, line=dict(width=1, color='#1c1d22')),
                text=hover_text,
                hovertemplate="주행거리: %{x:,.0f}km<br>판매가: %{y:,.0f}만원<br>%{text}<extra></extra>",
                name="엔카 매물"
            ))

            if len(chart_df) >= 2:
                try:
                    z = np.polyfit(chart_df['주행거리_num'], chart_df['판매가_num'], 1)
                    x_trend = np.linspace(chart_df['주행거리_num'].min(), chart_df['주행거리_num'].max(), 50)
                    y_trend = np.polyval(z, x_trend)
                    fig.add_trace(go.Scatter(
                        x=x_trend, y=y_trend,
                        mode='lines',
                        line=dict(color='#cc9166', dash='dash', width=2),
                        name='추세선',
                        hoverinfo='skip'
                    ))
                except: pass

            fig.update_layout(
                paper_bgcolor='#08080a',
                plot_bgcolor='#121317',
                font=dict(color='#acafb9'),
                xaxis=dict(title='주행거리 (km)', gridcolor='#1c1d22', zerolinecolor='#2e3038'),
                yaxis=dict(title='판매가 (만원)', gridcolor='#1c1d22', zerolinecolor='#2e3038'),
                height=420,
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                hovermode='closest',
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("차트를 그릴 수 있는 유효 데이터가 없습니다.")
    else:
        st.info("현재 설정된 조건에 맞는 매물 데이터가 없습니다.")

    st.markdown("---")

    # ==========================================
    # 🤖 [4] 헤이딜러 낙찰데이터 요약본 (크기 2/3) + 요약 2번
    # ==========================================
    st.markdown("### 🤖 헤이딜러 동급 낙찰 데이터 요약")
    
    hd_df = st.session_state.get('hd_comp_df', pd.DataFrame())
    if os.path.exists('scratch_market_price.json') and (hd_df.empty or '사고상세' not in hd_df.columns or not hd_df['사고상세'].astype(str).str.strip().any() or hd_df['사고유무'].astype(str).str.contains('사고/단순').any()):
        try:
            with open('scratch_market_price.json', 'r', encoding='utf-8') as f:
                raw_sc = json.load(f)
                hd_df = parse_heydealer_comps(raw_sc)
                st.session_state.hd_comp_df = hd_df
        except Exception: pass

    hd_total_count = len(hd_df)
    hd_min_price = int(hd_df['판매가_num'].min()) if not hd_df.empty and '판매가_num' in hd_df.columns else 0
    hd_max_price = int(hd_df['판매가_num'].max()) if not hd_df.empty and '판매가_num' in hd_df.columns else 0
    hd_avg_price = int(hd_df['판매가_num'].mean()) if not hd_df.empty and '판매가_num' in hd_df.columns else 0

    st.markdown(f"""
    <div style='display: flex; gap: 12px; margin-top: 8px; margin-bottom: 8px;'>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>🚙</div>
            <div class='metric-content'><h4>총 매물 수</h4><h2>{hd_total_count:,} 대</h2></div>
        </div>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>⬇️</div>
            <div class='metric-content'><h4>최저가</h4><h2 style='color: #4a90e2;'>{hd_min_price:,} 만원 <span style='font-size: 0.6em'>⬇️</span></h2></div>
        </div>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>⬆️</div>
            <div class='metric-content'><h4>최고가</h4><h2 style='color: #e25c5c;'>{hd_max_price:,} 만원 <span style='font-size: 0.6em'>⬆️</span></h2></div>
        </div>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>📊</div>
            <div class='metric-content'><h4>평균가</h4><h2 style='color: #cc9166;'>{hd_avg_price:,} 만원</h2></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 요약 2번 계산
    hd_no_acc_avg = hd_avg_price
    hd_acc_avg = hd_avg_price
    hd_year_stats = ""
    if not hd_df.empty and '판매가_num' in hd_df.columns:
        p_num = pd.to_numeric(hd_df['판매가_num'], errors='coerce')
        if '사고유무' in hd_df.columns:
            is_no = hd_df['사고유무'].astype(str).str.contains('완전무사고|무사고')
            if is_no.any(): hd_no_acc_avg = int(p_num[is_no].mean())
            if (~is_no).any(): hd_acc_avg = int(p_num[~is_no].mean())

        if '연식_num' in hd_df.columns:
            years = sorted(hd_df['연식_num'][hd_df['연식_num'] > 0].dropna().unique())
            y_parts = []
            for y in years[-3:]:
                sub_p = p_num[hd_df['연식_num'] == y].dropna()
                if not sub_p.empty:
                    y_parts.append(f"{y}년 평균 {int(sub_p.mean()):,}만원")
            if y_parts:
                hd_year_stats = " / ".join(y_parts)

    st.markdown(f"""
    <div class='summary-box'>
        <b style='color: #cc9166; font-size: 1.05em;'>📋 (2) 예상 매입가 기준 (헤이딜러 낙찰 데이터)</b><br>
        • 동급 평균: <b style='color: #fff;'>{hd_avg_price:,}만원</b> (무사고 <b>{hd_no_acc_avg:,}만원</b> / 유사고 <b>{hd_acc_avg:,}만원</b>)<br>
        • {hd_year_stats if hd_year_stats else '연식별 데이터 집계 완료'}
    </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # 📋 [5] 헤이딜러 리스트 및 상세스펙
    # ==========================================
    if not hd_df.empty:
        hd_col1, hd_col2 = st.columns([6.2, 3.8])
        
        with hd_col1:
            st.markdown("#### 📋 헤이딜러 동급 낙찰 이력 리스트")
            disp_hd_cols = [c for c in ['차량명', '연식', '주행거리', '낙찰가', '사고유무', '옵션', '링크'] if c in hd_df.columns]
            hd_disp_df = hd_df[disp_hd_cols].copy()

            hd_event = st.dataframe(
                hd_disp_df,
                column_config={
                    "링크": st.column_config.LinkColumn("링크", display_text="보기"),
                },
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                height=480
            )

        with hd_col2:
            st.markdown("#### 🔍 상세 스펙 & 옵션 (헤이딜러)")
            hd_selected_rows = hd_event.selection.rows if hasattr(hd_event, "selection") else []
            if hd_selected_rows:
                sel_idx = hd_selected_rows[0]
                row = hd_df.iloc[sel_idx]
                
                base_acc = str(row.get('사고유무', ''))
                if '무사고' in base_acc:
                    hd_acc_style = "background:#14532d; color:#86efac; border:1px solid #16a34a;"
                elif '단순' in base_acc:
                    hd_acc_style = "background:#713f12; color:#fde047; border:1px solid #ca8a04;"
                elif '사고' in base_acc:
                    hd_acc_style = "background:#7f1d1d; color:#fca5a5; border:1px solid #dc2626;"
                else:
                    hd_acc_style = "background:#27272a; color:#d4d4d8; border:1px solid #52525b;"
                
                acc_html = f"<div style='margin-bottom: 6px;'><span style='color: #9194a1; margin-right:8px; font-size:0.85em;'>사고유무:</span> <span style='{hd_acc_style} padding:2px 10px; border-radius:12px; font-weight: bold; font-size:0.85em; display:inline-block;'>{base_acc}</span></div>"
                
                acc_detail = row.get("사고상세", "")
                if acc_detail and str(acc_detail) != "nan" and str(acc_detail).strip():
                    issue_items = []
                    for item in [p.strip() for p in str(acc_detail).split(",") if p.strip()]:
                        bg_color = "#dc2626" if "교환" in item else "#d97706"
                        issue_items.append(f"<span style='background:{bg_color}; color:#ffffff; padding:4px 10px; border-radius:6px; font-size:0.88em; margin-right:6px; margin-bottom:6px; display:inline-block; font-weight:700; letter-spacing:-0.3px;'>{item}</span>")
                    acc_html += f"<div style='margin-top: 10px; padding-top: 10px; border-top: 1px dashed #3f3f46;'><div style='color: #a1a1aa; font-size: 0.85em; margin-bottom: 6px; font-weight:700;'>🛠️ 교환 및 수리 부위</div><div style='display:flex; flex-wrap:wrap;'>{' '.join(issue_items)}</div></div>"
                else:
                    acc_html += f"<div style='margin-top: 10px; padding-top: 10px; border-top: 1px dashed #3f3f46;'><div style='color: #4ade80; font-size: 0.88em; font-weight:700;'>✨ 특이사항 없음 (교환/수리 부위 없음)</div></div>"
                

                option_style = "background-color:#1e222d; border:1px solid #2e384d; padding:4px 10px; border-radius:8px; font-size:0.86em; font-weight:500; color:#93c5fd; display:inline-flex; align-items:center;"
                raw_opts = row.get('옵션리스트', []) if isinstance(row.get('옵션리스트'), list) else []
                if not raw_opts and row.get('옵션') and row.get('옵션') != '-':
                    raw_opts = [o.strip() for o in str(row['옵션']).split('/') if o.strip()]
                clean_opts = [o for o in raw_opts if o and 'div' not in str(o).lower() and not str(o).startswith('<')]
                options_badges = "".join([f'<span style="{option_style}">{opt}</span> ' for opt in clean_opts])
                if not options_badges:
                    options_badges = '<span style="color:#9194a1; font-size:0.85em;">등록된 옵션 없음</span>'
                
                link_val = row.get('링크', '')
                link_html = f"<div style='margin-top: 12px;'><a href='{link_val}' target='_blank' style='color:#cc9166; font-size:0.85em; text-decoration:none; font-weight:bold;'>🔗 헤이딜러 매물 바로가기 ↗</a></div>" if link_val and str(link_val).startswith('http') else ""
                
                card_html = (
                    f'<div style="background-color:#121317; padding:16px; border-radius:8px; border:1px solid #2e3038;">'
                    f'<div style="font-size:1.1em; font-weight:bold; color:#ffffff; margin-bottom:4px;">{row.get("차량명", "헤이딜러 매물")}</div>'
                    f'<div style="font-size:0.85em; color:#9194a1; margin-bottom:10px;">{row.get("연식", "-")} · {row.get("주행거리", "-")}</div>'
                    f'<div style="font-size:1.3em; font-weight:bold; color:#cc9166; margin-bottom:10px;">{row.get("낙찰가", "-")}</div>'
                    f'<hr style="border:0; border-top:1px solid #2e3038; margin:10px 0;">'
                    f'<div style="margin-bottom:12px;">{acc_html}</div>'
                    f'<div><span style="color:#9194a1; font-size:0.85em; font-weight:bold;">주요 옵션</span><div style="margin-top:6px; display:flex; flex-wrap:wrap; gap:4px;">{options_badges}</div></div>'
                    f'{link_html}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
            else:
                st.info("👈 좌측 헤이딜러 리스트에서 체크(선택)하시면 상세 스펙과 수리 부위가 여기에 표시됩니다.")
    else:
        st.info("👈 좌측 사이드바 상단의 [차량 정보 수집 및 AI 견적 산출]을 실행하시면 헤이딜러 낙찰 데이터 리스트가 표시됩니다.")

    st.markdown("---")

with tab_ledger:
    st.markdown("### 📋 내 실전 장부 리스트")
    if not st.session_state.my_ledger_data.empty:
        st.dataframe(
            st.session_state.my_ledger_data,
            use_container_width=True, 
            height=400, 
            hide_index=True
        )
    else:
        st.info("아직 저장된 장부 내역이 없습니다. 좌측 장부 입력폼을 통해 타점을 기록해 보세요!")

with tab_sales:
    st.markdown("### 📋 자사 판매 리스트")
    inv_df = pd.DataFrame()
    if 'inventory_data' in st.session_state and not st.session_state.inventory_data.empty:
        inv_df = st.session_state.inventory_data.copy()
        
    if not inv_df.empty:
        col_map = {}
        for col in inv_df.columns:
            clean_col = str(col).replace(" ", "").lower()
            if "차종" in clean_col or "차량명" in clean_col: col_map[col] = "차량명"
            elif "세부모델" in clean_col: col_map[col] = "세부모델"
            elif "최초등록일" in clean_col: col_map[col] = "연식"
            elif "경과일수" in clean_col: col_map[col] = "재고"
            elif "할인적용가" in clean_col: col_map[col] = "판매가_할인"
            elif "지점판매가" in clean_col: col_map[col] = "판매가_지점"
            elif "eurl" in clean_col: col_map[col] = "링크"
        inv_df = inv_df.rename(columns=col_map)
        
        # 2. 필수 컬럼 확보
        for req_col in ["최종수정일", "차량명", "링크", "세부모델", "연식", "주행거리", "재고", "판매가", "매입가", "색상", "홈페이지상태"]:
            if req_col not in inv_df.columns:
                inv_df[req_col] = ""
                
        # 3. 값 정리
        if '판매가_할인' in inv_df.columns and '판매가_지점' in inv_df.columns:
            inv_df['판매가'] = pd.to_numeric(inv_df['판매가_할인'], errors='coerce').fillna(0)
            inv_df.loc[inv_df['판매가'] <= 0, '판매가'] = pd.to_numeric(inv_df['판매가_지점'], errors='coerce').fillna(0)
        else:
            inv_df['판매가'] = pd.to_numeric(inv_df['판매가'], errors='coerce').fillna(0)
            
        inv_df['판매가'] = inv_df['판매가'].apply(lambda x: int(x/10000) if pd.notna(x) and x >= 10000 else x)
        inv_df['매입가'] = pd.to_numeric(inv_df['매입가'], errors='coerce').fillna(0)
        inv_df['매입가'] = inv_df['매입가'].apply(lambda x: int(x/10000) if pd.notna(x) and x >= 10000 else x)
        

        def extract_encar_link(row):
            link = str(row.get('링크', '')).strip()
            # http로 시작하는 정상 링크만 살리고, javascript 등은 링크 제거(None 반환)
            if link.startswith('http'):
                return link
            return None
            
        inv_df['엔카 링크'] = inv_df.apply(extract_encar_link, axis=1)

        # 4. 출력용 데이터프레임 구성
        disp_cols = ["최종수정일", "차량명", "세부모델", "연식", "주행거리", "재고", "판매가", "매입가", "색상", "엔카 링크"]
        out_df = inv_df[disp_cols + ["홈페이지상태"]].copy()
        
        # 사이드바 필터 적용 (차량명/세부모델 분리가 다른 경우를 대비해 병합 검색)
        full_names = out_df['차량명'].astype(str) + " " + out_df['세부모델'].astype(str)
        full_names_clean = full_names.str.replace(" ", "").str.lower()

        f_name_val = st.session_state.get('f_name', '전체')
        f_sub_val = st.session_state.get('f_sub', '전체')
        
        if f_name_val != "전체":
            name_clean = str(f_name_val).replace(" ", "").lower()
            out_df = out_df[full_names_clean.str.contains(name_clean, na=False, regex=False)]
            full_names_clean = full_names_clean[out_df.index]
            
        if f_sub_val != "전체":
            # 세부모델은 '가솔린 1.6' vs '1.6 가솔린' 처럼 순서가 다를 수 있으므로 쪼개서 모두 포함되는지 확인
            sub_parts = str(f_sub_val).split()
            for part in sub_parts:
                part_clean = part.replace(" ", "").lower()
                out_df = out_df[full_names_clean.str.contains(part_clean, na=False, regex=False)]
                full_names_clean = full_names_clean[out_df.index]
                
        if current_f_year:
            out_df = out_df[out_df['연식'].astype(str).str.contains(current_f_year, na=False)]
        
        # 컬럼 컨피그
        ccfg = {
            "차량명": st.column_config.TextColumn("차량명"),
            "판매가": st.column_config.NumberColumn("판매가(만)", format="%d"),
            "매입가": st.column_config.NumberColumn("매입가(만)", format="%d"),
            "엔카 링크": st.column_config.LinkColumn("엔카 링크", display_text="🔗 보러가기"),
        }
                
        status_col = out_df['홈페이지상태'].astype(str).str.strip()
        sales_df = out_df[status_col != '판매중'][disp_cols] # 판매완료, 계약중
        stock_df = out_df[status_col == '판매중'][disp_cols] # 판매중
        
        st.dataframe(sales_df, use_container_width=True, hide_index=True, height=600, column_config=ccfg)
    else:
        st.info("👈 좌측에서 자사 재고 엑셀 파일을 업로드해 주세요.")

with tab_inventory:
    st.markdown("### 📋 자사 재고 리스트")
    if not inv_df.empty:
        st.dataframe(stock_df, use_container_width=True, hide_index=True, height=600, column_config=ccfg)
    else:
        st.info("👈 좌측에서 자사 재고 엑셀 파일을 업로드해 주세요.")



if 'debug_success_msg' in st.session_state:
    st.success(st.session_state.debug_success_msg)
    # 한 번 표시 후 삭제하여 계속 떠있지 않게 함 (단, 다시 조회하면 다시 생성됨)
    # st.session_state.pop('debug_success_msg', None) - rerun 때문에 바로 지우면 안 될 수 있으니 유지하거나 폼 변경 시 지우는 게 좋지만, 일단 유지합니다.

if 'debug_autofill' in st.session_state:
    st.warning(st.session_state.debug_autofill)
if 'debug_hd_market' in st.session_state:
    st.warning(st.session_state.debug_hd_market)

# 강제 리로드 완료