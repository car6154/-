import os
import re
import json
import time
import random
import math
from datetime import datetime
import numpy as np
import pandas as pd
import requests
import urllib.parse
import streamlit as st
import plotly.graph_objects as go
from dotenv import load_dotenv

from heydealer_ai import extract_car_data_for_ai, get_gemini_estimate
from scraper import HeydealerScraper
from sales_analysis import get_car_market_stats, generate_encar_market_url, SalesDataAnalyzer

# ==========================================
# 📦 Services & Views Modular Imports
from services.cookie_server import get_current_hd_cookie, get_current_autoplus_cookie
from services.heydealer_service import parse_heydealer_comps
from services.data_processor import DataProcessor
from services.encar_service import Scraper
from services.settlement_service import get_auto_fee_rate, recalc_settlement_df

from views.tab_main import render_main_tab
from views.tab_settlement import render_settlement_tab
from views.tab_ledger import (
    render_ledger_tab,
    render_completed_tab,
    render_sales_tab,
    render_inventory_tab
)

load_dotenv()
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
    padding: 12px 14px !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.4) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    margin-bottom: 10px !important;
    border: 1px solid #2e3038 !important;
    transition: all 0.2s ease;
    box-sizing: border-box !important;
}
.metric-card:hover {
    border-color: #cc9166 !important;
}
.metric-icon {
    font-size: 1.35em !important;
    background: #1c1d22 !important;
    padding: 6px 10px !important;
    border-radius: 8px !important;
    margin-right: 12px !important;
    flex-shrink: 0 !important;
}
.metric-content {
    flex: 1 !important;
    min-width: 0 !important;
}
.metric-content h4 {
    margin: 0 !important;
    font-size: 0.78em !important;
    color: #9194a1 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    white-space: nowrap !important;
    text-overflow: ellipsis !important;
    overflow: hidden !important;
}
.metric-content h2 {
    margin: 2px 0 0 0 !important;
    font-size: 1.22em !important;
    color: #ffffff !important;
    font-family: 'Playfair Display', serif !important;
    white-space: nowrap !important;
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

/* Sidebar Ultra-Compact Mini Expanders (초슬림 크기 대폭 축소) */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    border: 1px solid #1e293b !important;
    border-radius: 5px !important;
    margin-bottom: 3px !important;
    background: #0f172a !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] details {
    border: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    padding: 2px 8px !important;
    min-height: 24px !important;
    height: 24px !important;
    display: flex !important;
    align-items: center !important;
    cursor: pointer !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
    background: #1e293b !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary span,
[data-testid="stSidebar"] [data-testid="stExpander"] summary div {
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    color: #94a3b8 !important;
    margin: 0 !important;
    line-height: 1 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
    width: 10px !important;
    height: 10px !important;
    fill: #64748b !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    padding: 6px 8px !important;
    background: #090d16 !important;
    border-top: 1px solid #1e293b !important;
}

/* Dataframe Row One-Click Selection & Subtle Selection Column Styling */
[data-testid="stDataFrame"] {
    cursor: pointer !important;
}
[data-testid="stDataFrame"] canvas {
    cursor: pointer !important;
}

/* 🎯 헤이딜러 URL/ID 입력창 시인성 극대화 (글로우 및 뚜렷한 포커스) */
div[data-testid="stTextInput"]:has(input[placeholder*="헤이딜러 URL"]) input,
input[placeholder*="헤이딜러 URL"] {
    background-color: #0f172a !important;
    border: 2px solid #38bdf8 !important;
    border-radius: 6px !important;
    color: #ffffff !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.25) !important;
    padding: 8px 12px !important;
}
input[placeholder*="헤이딜러 URL"]:focus {
    border-color: #0284c7 !important;
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.45) !important;
}
</style>
''', unsafe_allow_html=True)


DB_FILE = "jpro_db.csv"
LEDGER_FILE = "my_car_ledger.csv"
SETTLEMENT_FILE = "my_inventory_settlement.csv"
INVENTORY_FILE = "autoplus_inventory.csv" 
COOKIE_FILE = "encar_cookie.txt" 
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyFTXuPkC0R9y-UftHOFmJfgBwxycMwqOabhxKVT4bcsBK9gfsscQtGCTohzFiccq71/exec"



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
if 'f_year' not in st.session_state: st.session_state.f_year = ""
if 'f_mil' not in st.session_state: st.session_state.f_mil = 0
if 'my_ledger_data' not in st.session_state:
    LEDGER_COLS = ['등록일', '차량번호', '제조사', '차량명', '세부모델', '연식', '주행거리', '외판수리', '매입가', '판매가', '외판수리비', '헤딜수수료', '특이사항', '상태']
    if os.path.exists(LEDGER_FILE):
        try:
            st.session_state.my_ledger_data = pd.read_csv(LEDGER_FILE)
            st.session_state.my_ledger_data['차량번호'] = st.session_state.my_ledger_data['차량번호'].astype(str)
            for c in LEDGER_COLS:
                if c not in st.session_state.my_ledger_data.columns:
                    st.session_state.my_ledger_data[c] = 0 if c in ['외판수리', '외판수리비', '헤딜수수료'] else ""
        except:
            st.session_state.my_ledger_data = pd.DataFrame(columns=LEDGER_COLS)
    else:
        st.session_state.my_ledger_data = pd.DataFrame(columns=LEDGER_COLS)
else:
    if '외판수리' not in st.session_state.my_ledger_data.columns:
        st.session_state.my_ledger_data['외판수리'] = 0

# 내 실전 재고 및 정산 관리 데이터 (만원 단위 관리)
SETTLEMENT_COLS = [
    '순차', '매입일', '상태', '차량번호', '차종', '판매가', '재고일', '매입가', 
    '외판수리', '상품화', '헤딜수수료', '기본제경비', '공헌이익', '실수익', 
    '수수료율', '판매수수료', '수수료율_수동'
]
if 'my_settlement_data' not in st.session_state:
    if os.path.exists(SETTLEMENT_FILE):
        try:
            st.session_state.my_settlement_data = pd.read_csv(SETTLEMENT_FILE)
            st.session_state.my_settlement_data['차량번호'] = st.session_state.my_settlement_data['차량번호'].astype(str)
            for c in SETTLEMENT_COLS:
                if c not in st.session_state.my_settlement_data.columns:
                    st.session_state.my_settlement_data[c] = 0 if c in ['순차', '판매가', '재고일', '매입가', '외판수리', '상품화', '헤딜수수료', '기본제경비', '공헌이익', '실수익', '판매수수료'] else ""
        except:
            st.session_state.my_settlement_data = pd.DataFrame(columns=SETTLEMENT_COLS)
    else:
        st.session_state.my_settlement_data = pd.DataFrame(columns=SETTLEMENT_COLS)

if 'option_catalog_cache' not in st.session_state:
    st.session_state.option_catalog_cache = {}

if 'purchase_route' not in st.session_state:
    st.session_state.purchase_route = "셀프(기본)"

# 🔥 입력값 초기화를 위한 리셋 키 (에러 해결의 핵심!)
if 'form_reset_key' not in st.session_state:
    st.session_state.form_reset_key = 0

if 'save_success' not in st.session_state: st.session_state.save_success = False
# 🔥 재고관리/장부에서 역추적 자동 스캔 요청이 들어온 경우 앱 시작 시 최우선으로 즉시 실행
auto_url = st.session_state.pop('auto_scan_url', None)
if auto_url:
    p_bar, s_text = st.progress(0), st.empty()
    s_text.text("⚡ 재고 차량 동급 매물 실시간 자동 스캔 중...")
    new_scan_df, msg = Scraper.run(auto_url, "", p_bar, s_text)
    if msg == "success":
        # 기존 스캔 데이터 완전 교체
        st.session_state.scan_data = new_scan_df.drop_duplicates(subset=['_carid'], keep='last').reset_index(drop=True)
        if not new_scan_df.empty:
            st.session_state.f_brand = new_scan_df['제조사'].iloc[0] if '제조사' in new_scan_df.columns else "전체"
            st.session_state.f_name = new_scan_df['차량명'].iloc[0] if '차량명' in new_scan_df.columns else "전체"
            
            target_sub = str(st.session_state.get('target_sub_model', '')).strip()
            subs = new_scan_df['세부모델'].dropna().unique().tolist()
            matched_s = None
            if target_sub:
                t_clean = target_sub.replace(" ", "").lower()
                for s in subs:
                    s_clean = str(s).replace(" ", "").lower()
                    if t_clean in s_clean or s_clean in t_clean:
                        matched_s = s
                        break
            if matched_s:
                st.session_state.f_sub = matched_s
            elif target_sub:
                st.session_state.f_sub = target_sub
            else:
                st.session_state.f_sub = "전체"
            st.session_state.f_status = []
        p_bar.empty()
        s_text.empty()
        st.rerun()
    else:
        st.error(f"동급 매물 자동 스캔 실패: {msg}")

st.sidebar.markdown("""
<div style='margin-bottom: -15px;'>
    <span style='font-size: 30px; font-weight: 800; color: #1E3A8A; letter-spacing: -1px;'>J-PRO</span>
</div>
<div style='margin-bottom: 12px;'>
    <span style='font-size: 11px; font-weight: 500; color: #64748B; letter-spacing: 1.5px; text-transform: uppercase;'>Auto Valuation Intelligence</span>
</div>
""", unsafe_allow_html=True)

# 🔼 [사이드바 최상단] 접어두는 보조 설정 메뉴 (초슬림 크기)
live_cookie = get_current_hd_cookie()
if 'cookie_version' not in st.session_state:
    st.session_state.cookie_version = 0

if st.session_state.get('_last_loaded_hd_cookie') != live_cookie:
    st.session_state._last_loaded_hd_cookie = live_cookie
    st.session_state.cookie_version += 1
    st.session_state[f"hd_cookie_box_{st.session_state.cookie_version}"] = live_cookie

heydealer_cookie_input = live_cookie
live_ap_cookie = get_current_autoplus_cookie()

with st.sidebar.expander("🔑 세션 쿠키 설정", expanded=False):
    cookie_status = st.session_state.get('hd_cookie_status', 'valid' if (live_cookie and len(live_cookie.strip()) > 20) else 'empty')
    if not live_cookie or not live_cookie.strip() or cookie_status == 'empty':
        badge_html = "<span style='color:#f87171; font-weight:600;'>🔴 헤이딜러 미등록</span>"
    elif cookie_status == 'expired':
        badge_html = "<span style='color:#f87171; font-weight:600;'>🔴 헤이딜러 만료됨</span>"
    else:
        badge_html = "<span style='color:#4ade80; font-weight:600;'>🟢 헤이딜러 정상</span>"

    ap_has_cookie = bool(live_ap_cookie and len(live_ap_cookie.strip()) > 10)
    ap_badge_html = "<span style='color:#4ade80; font-weight:600;'>🟢 견적조회 정상</span>" if ap_has_cookie else "<span style='color:#f87171; font-weight:600;'>🔴 견적조회 미등록</span>"

    c_sk1, c_sk2 = st.columns([3, 1.2])
    with c_sk1:
        st.markdown(f"<div style='font-size:0.73rem; margin-top:2px;'>{badge_html}<br>{ap_badge_html}</div>", unsafe_allow_html=True)
    with c_sk2:
        if st.button("🔄", help="쿠키 최신 동기화", key="sync_cookie_btn", use_container_width=True):
            live_cookie = get_current_hd_cookie()
            live_ap_cookie = get_current_autoplus_cookie()
            st.session_state._last_loaded_hd_cookie = live_cookie
            st.session_state.cookie_version += 1
            st.session_state[f"hd_cookie_box_{st.session_state.cookie_version}"] = live_cookie
            st.session_state.hd_cookie_status = 'valid' if (live_cookie and len(live_cookie.strip()) > 20) else 'empty'
            st.rerun()

    typed_cookie = st.text_input(
        "헤이딜러 쿠키",
        value=live_cookie,
        key=f"hd_cookie_box_{st.session_state.cookie_version}",
        type="password"
    )
    if typed_cookie:
        heydealer_cookie_input = typed_cookie

    typed_ap_cookie = st.text_input(
        "견적조회 쿠키",
        value=live_ap_cookie,
        key="ap_cookie_manual_box",
        type="password"
    )
    if typed_ap_cookie and typed_ap_cookie != live_ap_cookie:
        from services.cookie_server import save_autoplus_cookie
        save_autoplus_cookie(typed_ap_cookie)
        os.environ['AUTOPLUS_COOKIE'] = typed_ap_cookie
        st.rerun()

with st.sidebar.expander("🗃️ 부가 데이터 및 엔카 스캔", expanded=False):
    st.caption("📁 자사 재고 엑셀 연동")
    uploaded_files = st.file_uploader("자사 재고 엑셀 업로드", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True, label_visibility="collapsed", key="top_inventory_uploader")
    if st.button("📁 엑셀 병합 및 DB 저장", use_container_width=True, key="top_merge_db_btn"):
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
                try:
                    from sales_analysis import SalesDataAnalyzer
                    SalesDataAnalyzer.get_instance().load_data()
                except Exception as ex_reload:
                    print(f"SalesDataAnalyzer reload error: {ex_reload}")
                st.rerun()

    if st.button("🗑️ 저장된 엑셀 DB 지우기", use_container_width=True, key="top_clear_db_btn"):
        st.session_state.inventory_data = pd.DataFrame()
        if os.path.exists(INVENTORY_FILE): os.remove(INVENTORY_FILE)
        try:
            from sales_analysis import SalesDataAnalyzer
            SalesDataAnalyzer.get_instance().load_data()
        except:
            pass
        st.rerun()

    st.markdown("---")
    st.caption("🚗 엔카 정밀 스캔")
    scan_url = st.text_input("엔카 정밀 스캔 URL 입력:", key=f"scan_url_{st.session_state.form_reset_key}", label_visibility="collapsed", placeholder="엔카 URL 붙여넣기")
    if st.button("🚀 실시간 엔카 스캔", use_container_width=True, key="top_scan_btn"):
        if scan_url:
            p_bar, s_text = st.progress(0), st.empty()
            new_scan_df, msg = Scraper.run(scan_url, "", p_bar, s_text)
            if msg == "success":
                st.session_state.scan_source = "url"
                st.session_state.scan_data = pd.concat([st.session_state.scan_data, new_scan_df], ignore_index=True)
                st.session_state.scan_data = st.session_state.scan_data.drop_duplicates(subset=['_carid'], keep='last').reset_index(drop=True)
                if not new_scan_df.empty:
                    st.session_state.f_brand = "전체"
                    st.session_state.f_name = "전체"
                    st.session_state.f_sub = "전체"
                    st.session_state.f_status = [] 
                st.rerun()
            else: s_text.error(msg)
            
    if st.button("스캔 초기화", use_container_width=True, key="top_reset_scan_btn"): 
        st.session_state.scan_source = "inventory"
        st.session_state.scan_data = pd.DataFrame()
        st.session_state.f_brand = "전체"
        st.session_state.f_name = "전체"
        st.session_state.f_sub = "전체"
        st.session_state.f_year = ""
        st.session_state.f_mil = 0
        st.rerun()

    if not st.session_state.scan_data.empty:
        failed_mask = st.session_state.scan_data['성능일'].astype(str).str.contains("조회실패") | \
                      st.session_state.scan_data['사고유무'].astype(str).str.contains("조회실패") | \
                      st.session_state.scan_data['추가옵션'].astype(str).str.contains("조회실패")
        failed_count = failed_mask.sum()
        if failed_count > 0:
            st.warning(f"⚠️ 조회실패 차량: {failed_count}대")
            if st.button("♻️ 실패 차량만 재스캔", use_container_width=True, key="top_rescan_failed_btn"):
                p_bar, s_text = st.progress(0), st.empty()
                failed_indices = st.session_state.scan_data[failed_mask].index
                Scraper.rescan(failed_indices, "", p_bar, s_text)
                st.rerun()

st.sidebar.markdown("<hr style='margin: 10px 0 8px 0; border: none; border-top: 1px solid #1e293b;'>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div style='display: flex; align-items: center; gap: 6px; margin-bottom: 6px;'>
    <span style='font-size: 1.05rem; font-weight: 700; color: #38bdf8;'>🤖 헤이딜러 AI 매입 견적</span>
</div>
<div style='font-size: 0.8rem; color: #94a3b8; margin-bottom: 4px;'>🔗 <b>헤이딜러 차량 URL 또는 ID</b> (붙여넣기)</div>
""", unsafe_allow_html=True)

heydealer_url_input = st.sidebar.text_input(
    "헤이딜러 차량 URL/ID", 
    placeholder="👉 여기에 헤이딜러 URL 또는 ID를 붙여넣으세요!", 
    key=f"hd_url_box_{st.session_state.form_reset_key}",
    label_visibility="collapsed"
)

# KCar 검색 URL 사전 생성 (헤이딜러 조회 차량 또는 설정된 필터 반영)
kcar_search_text = ""
f_name = st.session_state.get('f_name', '전체')
f_sub = st.session_state.get('f_sub', '전체')
hd_model = st.session_state.get('hd_model_part_name', '')
hd_grade = st.session_state.get('hd_grade_part_name', '')
hd_full = st.session_state.get('hd_full_name', '')

base_name = ""
if hd_model:
    base_name = hd_model
elif f_name != "전체":
    base_name = str(f_name)
elif hd_full:
    base_name = hd_full

if base_name:
    clean_name = re.sub(r'\(.*?\)', '', base_name).strip()
    clean_name = clean_name.replace('더 뉴 QM6', '뉴 QM6').replace('더뉴QM6', '뉴 QM6').replace('더뉴 QM6', '뉴 QM6')
    
    m_core = re.search(r'^(뉴\s*[^0-9]+|더\s*뉴\s*[^0-9]+|올\s*뉴\s*[^0-9]+|[가-힣A-Za-z0-9\s]+?)(?=\s+\d+\.\d+|\s+가솔린|\s+디젤|\s+하이브리드|\s+LPG|\s+EV|$)', clean_name)
    model_str = m_core.group(1).strip() if (m_core and m_core.group(1).strip()) else (clean_name.split()[0] if clean_name.split() else clean_name)
    
    sub_raw = hd_grade if hd_grade else (f_sub if f_sub != "전체" else "")
    trim_words = []
    if sub_raw:
        s_clean = str(sub_raw).replace(" ", "")
        if "LE" in s_clean and "시그니처" in s_clean:
            trim_words.append("LE 시그니처")
        elif "RE" in s_clean and "시그니처" in s_clean:
            trim_words.append("RE 시그니처")
        elif "프리미에르" in s_clean:
            trim_words.append("프리미에르")
        else:
            for t in ["캘리그래피", "인스퍼레이션", "프레스티지", "노블레스", "시그니처", "익스클루시브", "모던", "프리미엄", "노블레스"]:
                if t in s_clean:
                    trim_words.append(t)
                    break
    
    if trim_words:
        kcar_search_text = f"{model_str} {' '.join(trim_words)}".strip()
    else:
        kcar_search_text = model_str

if kcar_search_text:
    cond = {"wr_txt_idx": kcar_search_text}
    cond_str = json.dumps(cond, separators=(',', ':'))
    kcar_url = f"https://www.kcar.com/bc/search?searchCond={urllib.parse.quote(cond_str)}"
else:
    kcar_url = "https://www.kcar.com/bc/search"

# 🚀 URL 바로 밑에 [AI 견적 산출]과 [KCAR] 버튼 직관적 배치!
col_ai_btn, col_kcar_btn = st.sidebar.columns([2.3, 1])
is_ai_running = st.session_state.get('ai_status') == "진행중"
with col_ai_btn:
    run_heydealer = st.button("🤖 AI 견적 산출", key="heydealer_btn", disabled=is_ai_running, use_container_width=True)
with col_kcar_btn:
    st.link_button("KCAR", kcar_url, use_container_width=True)

if run_heydealer:
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
            HeydealerScraper.start_keepalive_worker(st.session_state.heydealer_session)

            with st.sidebar.spinner("헤이딜러 서버에서 차량 정보를 가져오는 중입니다..."):
                result = HeydealerScraper.fetch_car_detail(
                    heydealer_url_input,
                    session=st.session_state.heydealer_session
                )
                heydealer_json_str = result['detail']
                if not heydealer_json_str.strip() or not heydealer_json_str.strip().startswith('{'):
                    raise Exception(f'잘못된 응답입니다(로그인 만료 또는 차단 의심). 응답: {heydealer_json_str[:100]}')
                
                st.session_state.scan_source = "url"
                st.session_state.pop('last_chaolma_data', None)

                hd_detail_tmp = json.loads(heydealer_json_str).get('detail', {})
                car_spec_tmp = hd_detail_tmp.get('car_spec') or {}
                spec_desc_tmp = car_spec_tmp.get('description', '')
                import re
                hd_target_options = []
                hd_opt_prices = re.findall(r'\((\d+)\s*만(?:원)?\)', spec_desc_tmp)
                hd_target_opt_price_sum = sum(int(p) for p in hd_opt_prices) if hd_opt_prices else 0

                for line in spec_desc_tmp.split('\n'):
                    m = re.search(r'^\d+\)\s*(.*?)(?:\s*\(|$)', line.strip())
                    if m:
                        hd_target_options.append(m.group(1).strip())
                
                advanced_options_tmp = hd_detail_tmp.get('advanced_options') or []
                encar_target_options = [
                    opt.get('name', '') for opt in advanced_options_tmp 
                    if isinstance(opt, dict) and opt.get('choice') == 'loaded'
                ]
                st.session_state.hd_target_options = hd_target_options
                st.session_state.encar_target_options = encar_target_options
                st.session_state.hd_target_opt_price = hd_target_opt_price_sum
                st.session_state.hd_car_spec_desc = spec_desc_tmp
                if hd_detail_tmp.get('year'):
                    st.session_state.hd_target_year = int(hd_detail_tmp.get('year'))
                
                # 헤이딜러 사고유무 정보 저장 (AI 시세 산정 기준)
                hd_acc_summary = hd_detail_tmp.get('accident_repairs_summary_display', '') or hd_detail_tmp.get('accident_display', '')
                if hd_acc_summary:
                    st.session_state.hd_target_accident = hd_acc_summary
                
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
                                st.session_state.scan_source = "url"
                                st.session_state.scan_data = new_scan_df
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
                    m = re.search(r'\d{2,3}[가-힣]\s*\d{4}', hd_plate)
                    hd_plate = m.group(0).replace(" ", "") if m else ""

                st.session_state.form_reset_key = st.session_state.get('form_reset_key', 0) + 1
                reset_key = st.session_state.form_reset_key
                
                # 헤이딜러 차종/제조사/모델/세부모델을 사이드바 필터에 직접 주입
                hd_brand = hd_detail.get('brand_name', '')
                hd_model = hd_detail.get('model_part_name', '')
                hd_grade = hd_detail.get('grade_part_name', '')
                hd_full = hd_detail.get('full_name', '')
                
                if hd_brand:
                    st.session_state.f_brand = hd_brand

                # 차량명: 스캔된 엔카 매물이 있으면 엔카 매물의 차량명과 정확히 일치시켜 필터 누락 차단
                if 'scan_data' in st.session_state and not st.session_state.scan_data.empty and '차량명' in st.session_state.scan_data.columns:
                    st.session_state.f_name = str(st.session_state.scan_data['차량명'].iloc[0])
                elif hd_model:
                    st.session_state.f_name = hd_model
                elif hd_full:
                    st.session_state.f_name = hd_full

                if hd_grade:
                    st.session_state.f_sub = hd_grade

                # 헤이딜러 기준 연식(뒤 2자리 또는 전체) 및 주행거리를 사이드바 필터에 자동 설정
                if hd_year:
                    hd_year_str = str(hd_year).strip()
                    f_year_val = hd_year_str[-2:] if len(hd_year_str) == 4 and hd_year_str.isdigit() else hd_year_str
                    st.session_state.f_year = f_year_val
                    cur_yr_key = f"search_year_{reset_key}"
                    try:
                        st.session_state[cur_yr_key] = int(f_year_val)
                    except:
                        pass
                if hd_mil:
                    st.session_state.f_mil = int(hd_mil)
                    st.session_state[f"mil_{reset_key}"] = int(hd_mil)
                if hd_plate:
                    st.session_state[f"car_num_{reset_key}"] = str(hd_plate)
                
                # KCar 및 검색용 모델 정보 저장
                st.session_state.hd_model_part_name = hd_detail.get('model_part_name', '')
                st.session_state.hd_grade_part_name = hd_detail.get('grade_part_name', '')
                st.session_state.hd_full_name = hd_detail.get('full_name', '')
                    
                st.session_state.debug_autofill = f"추출 결과: 브랜드={hd_brand}, 차량명={st.session_state.f_name}, 연식={hd_year}, 주행거리={hd_mil}, 번호={hd_plate}"
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
                        
                        # 수출 차량은 내수 시세 계산에서 제외
                        hd_valid_comps = hd_comp_df[~hd_comp_df['수출여부']] if ('수출여부' in hd_comp_df.columns and not hd_comp_df.empty) else hd_comp_df
                        if hd_valid_comps.empty:
                            hd_valid_comps = hd_comp_df

                        if not hd_valid_comps.empty:
                            if target_year:
                                hd_same_year = hd_valid_comps[hd_valid_comps['연식_num'] == int(target_year)]
                                hd_prev = hd_valid_comps[hd_valid_comps['연식_num'] == int(target_year) - 1]
                                hd_next = hd_valid_comps[hd_valid_comps['연식_num'] == int(target_year) + 1]
                            else:
                                hd_same_year = hd_valid_comps
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
            
            st.session_state.hd_cookie_status = 'valid'
            st.session_state.ai_estimate_result = data_header
            st.session_state.ai_status = "표시됨"
            st.rerun()
            
        except Exception as e:
            err_msg = str(e)
            if any(k in err_msg for k in ['로그인 만료', '차단 의심', '401', '403']):
                st.session_state.hd_cookie_status = 'expired'
                st.sidebar.error("❌ 헤이딜러 로그인 세션이 만료되었습니다. 크롬 확장프로그램에서 [프로그램으로 자동 전송]을 눌러주세요.")
            else:
                st.sidebar.error(f"작업 실패: {err_msg}")

filtered_df = st.session_state.scan_data.copy()
filtered_df = DataProcessor.standardize(filtered_df)

is_url_mode = (st.session_state.get('scan_source') == "url")
current_f_year = ""

# 🔍 사이드바 상세 검색 필터 (스캔 데이터, 자사 재고, 빅데이터 및 견적조회 차량 상시 연동)
if not filtered_df.empty:
    st.sidebar.markdown(f"**총 스캔 대수: {len(st.session_state.scan_data)} 대**")
st.sidebar.markdown("### 🔍 상세 검색 필터")

# 1. 브랜드/제조사 목록 구성
f_brand_opts = ["전체"]
if not filtered_df.empty and '제조사' in filtered_df.columns:
    f_brand_opts += list(filtered_df['제조사'].dropna().unique())
if 'inventory_data' in st.session_state and not st.session_state.inventory_data.empty and '제조사' in st.session_state.inventory_data.columns:
    f_brand_opts += list(st.session_state.inventory_data['제조사'].dropna().unique())
major_brands = ["현대", "기아", "제네시스", "쉐보레", "르노코리아", "KG모빌리티(쌍용)", "벤츠", "BMW", "아우디", "폭스바겐", "볼보", "포르쉐", "미니"]
for b in major_brands:
    if b not in f_brand_opts: f_brand_opts.append(b)
if st.session_state.f_brand and st.session_state.f_brand not in f_brand_opts:
    f_brand_opts.append(st.session_state.f_brand)

if st.session_state.f_brand not in f_brand_opts: st.session_state.f_brand = "전체"
st.session_state.f_brand = st.sidebar.selectbox("제조사/브랜드", f_brand_opts, index=f_brand_opts.index(st.session_state.f_brand))
if not is_url_mode and not filtered_df.empty and st.session_state.f_brand != "전체" and '제조사' in filtered_df.columns: 
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

# 2. 차량명 목록 구성 (스캔 + 자사재고 + 실적DB + 견적조회 차량)
raw_names = set()
if not filtered_df.empty and '차량명' in filtered_df.columns:
    raw_names.update(filtered_df['차량명'].dropna().unique())
if 'inventory_data' in st.session_state and not st.session_state.inventory_data.empty and '차량명' in st.session_state.inventory_data.columns:
    raw_names.update(st.session_state.inventory_data['차량명'].dropna().unique())
try:
    from sales_analysis import SalesDataAnalyzer
    s_analyzer = SalesDataAnalyzer.get_instance()
    s_df = s_analyzer.raw_df if hasattr(s_analyzer, 'raw_df') else s_analyzer.df
    if s_df is not None and not s_df.empty and '차량명' in s_df.columns:
        raw_names.update(s_df['차량명'].dropna().unique())
except Exception:
    pass

if st.session_state.f_name and st.session_state.f_name != "전체":
    raw_names.add(st.session_state.f_name)

sorted_names = sorted(list(raw_names), key=get_smart_sort_key)
f_name_opts = ["전체"] + sorted_names

# 만약 f_name 부분일치 매칭 지원
cur_name = str(st.session_state.get('f_name', '전체')).strip()
if cur_name not in f_name_opts and cur_name != "전체":
    matched_name = None
    for n in f_name_opts:
        if n != "전체" and (cur_name.lower() in n.lower() or n.lower() in cur_name.lower()):
            matched_name = n
            break
    if matched_name:
        st.session_state.f_name = matched_name

if st.session_state.f_name not in f_name_opts: st.session_state.f_name = "전체"
st.session_state.f_name = st.sidebar.selectbox("차량명", f_name_opts, index=f_name_opts.index(st.session_state.f_name))

if not is_url_mode and not filtered_df.empty and st.session_state.f_name != "전체" and '차량명' in filtered_df.columns: 
    name_clean_f = str(st.session_state.f_name).replace(" ", "").lower()
    # 1. 완전/부분 문자열 포함 매칭
    mask = filtered_df['차량명'].astype(str).str.replace(" ", "").str.lower().str.contains(name_clean_f, na=False, regex=False)
    
    # 2. 미스매치 방지: 핵심 어근(Root) 기반 지능형 매칭 (예: '신형k5' <-> 'k5 2세대')
    if not mask.any():
        core_keywords = ['그랜저', '싼타페', '아반떼', '쏘나타', '투싼', '팰리세이드', '스타리아', '스타렉스',
                         'k3', 'k5', 'k7', 'k8', 'k9', '쏘렌토', '스포티지', '카니발', '모닝', '레이',
                         'g70', 'g80', 'g90', 'gv70', 'gv80', 'gv60', '제네시스',
                         '스파크', '말리부', '트레일블레이저', 'sm3', 'sm5', 'sm6', 'qm3', 'qm6', 'xm3',
                         '티볼리', '코란도', '렉스턴', '토레스']
        for kw in core_keywords:
            if kw in name_clean_f:
                mask = filtered_df['차량명'].astype(str).str.replace(" ", "").str.lower().str.contains(kw, na=False, regex=False)
                if mask.any():
                    break
    
    if mask.any():
        filtered_df = filtered_df[mask]

# 3. 세부모델 목록 구성
raw_subs = set()
if not filtered_df.empty and '세부모델' in filtered_df.columns:
    raw_subs.update(filtered_df['세부모델'].dropna().unique())
if 'inventory_data' in st.session_state and not st.session_state.inventory_data.empty and '세부모델' in st.session_state.inventory_data.columns:
    inv_df_filtered = st.session_state.inventory_data
    if st.session_state.f_name != "전체":
        name_clean_f = str(st.session_state.f_name).replace(" ", "").lower()
        full_names = inv_df_filtered['차량명'].astype(str) + " " + inv_df_filtered['세부모델'].astype(str)
        full_names_clean = full_names.str.replace(" ", "").str.lower()
        inv_df_filtered = inv_df_filtered[full_names_clean.str.contains(name_clean_f, na=False, regex=False)]
    raw_subs.update(inv_df_filtered['세부모델'].dropna().unique())

try:
    if s_df is not None and not s_df.empty and '세부모델' in s_df.columns:
        if st.session_state.f_name != "전체":
            name_clean_f = str(st.session_state.f_name).replace(" ", "").lower()
            m_rows = s_df[s_df['차량명'].astype(str).str.replace(" ", "").str.lower().str.contains(name_clean_f, na=False, regex=False)]
            raw_subs.update(m_rows['세부모델'].dropna().unique())
except Exception:
    pass

if st.session_state.f_sub and st.session_state.f_sub != "전체":
    raw_subs.add(st.session_state.f_sub)

f_sub_opts = ["전체"] + sorted(list(raw_subs))

cur_sub = str(st.session_state.get('f_sub', '전체')).strip()
if cur_sub not in f_sub_opts and cur_sub != "전체":
    matched_opt = None
    for opt in f_sub_opts:
        if opt != "전체" and (cur_sub.lower() in opt.lower() or opt.lower() in cur_sub.lower()):
            matched_opt = opt
            break
    if matched_opt:
        st.session_state.f_sub = matched_opt
    else:
        f_sub_opts.append(cur_sub)

if st.session_state.f_sub not in f_sub_opts: st.session_state.f_sub = "전체"
st.session_state.f_sub = st.sidebar.selectbox("세부모델", f_sub_opts, index=f_sub_opts.index(st.session_state.f_sub))

if not is_url_mode and not filtered_df.empty and st.session_state.f_sub != "전체" and '세부모델' in filtered_df.columns: 
    sub_raw = str(st.session_state.f_sub).strip()
    sub_clean = sub_raw.lower().replace(" ", "")
    sub_parts = [p for p in sub_raw.split() if len(p) >= 2]
    encar_sub_clean = filtered_df['세부모델'].astype(str).str.replace(" ", "").str.lower()
    
    # 1. 모든 키워드 토큰 포함 매칭
    all_matched = pd.Series(True, index=filtered_df.index)
    for part in sub_parts:
        part_clean = part.replace(" ", "").lower()
        all_matched = all_matched & encar_sub_clean.str.contains(part_clean, na=False, regex=False)
    
    cand_df = filtered_df[all_matched] if all_matched.any() else filtered_df
    
    # 2. 구동방식(2WD vs 4WD) 정밀 격리: 검색어에 4WD/4륜/AWD가 없으면 4WD 매물 자동 배제
    is_target_4wd = any(x in sub_clean for x in ['4wd', '4륜', 'awd'])
    if not is_target_4wd:
        non_4wd = ~cand_df['세부모델'].astype(str).str.contains(r'4wd|4륜|awd', case=False, regex=True, na=False)
        if non_4wd.any():
            cand_df = cand_df[non_4wd]
    else:
        is_4wd = cand_df['세부모델'].astype(str).str.contains(r'4wd|4륜|awd', case=False, regex=True, na=False)
        if is_4wd.any():
            cand_df = cand_df[is_4wd]
            
    # 3. 서브트림 키워드 엄격 일치 ('스페셜', '플러스', '에디션' 등)
    for sub_kw in ['스페셜', '플러스', '에디션', '마스터']:
        if sub_kw not in sub_clean:
            # 선택된 등급에 '스페셜'이 없는데 '스페셜' 매물이 섞여 있다면 제외
            has_kw = cand_df['세부모델'].astype(str).str.contains(sub_kw, na=False)
            if (~has_kw).any():
                cand_df = cand_df[~has_kw]
        else:
            has_kw = cand_df['세부모델'].astype(str).str.contains(sub_kw, na=False)
            if has_kw.any():
                cand_df = cand_df[has_kw]
                
    if not cand_df.empty:
        filtered_df = cand_df

# 4. 연식 필터 (2자리 연식, 0=전체)
default_f_year = st.session_state.get('f_year', '')
try:
    init_year_val = (int(str(default_f_year).strip()) % 100) if str(default_f_year).strip().isdigit() else 0
except Exception:
    init_year_val = 0

cur_yr_key = f"search_year_{st.session_state.form_reset_key}"
if init_year_val > 0 and (cur_yr_key not in st.session_state or st.session_state[cur_yr_key] == 0):
    st.session_state[cur_yr_key] = init_year_val

f_year_num = st.sidebar.number_input(
    "📈 시세분석용 연식 (0=전체, 예: 24)",
    min_value=0,
    max_value=99,
    value=st.session_state.get(cur_yr_key, init_year_val),
    step=1,
    key=cur_yr_key
)
current_f_year = f"{f_year_num:02d}" if f_year_num > 0 else ""

if not filtered_df.empty and "주행거리" in filtered_df.columns:
    filtered_df["주행거리"] = pd.to_numeric(filtered_df["주행거리"], errors='coerce').fillna(0)

if not filtered_df.empty and "재고" in filtered_df.columns:
    filtered_df['_sort_inv'] = pd.to_numeric(filtered_df['재고'], errors='coerce').fillna(99999)
    filtered_df = filtered_df.sort_values(by='_sort_inv', ascending=True).drop(columns=['_sort_inv']).reset_index(drop=True)

# 🛠️ [DEBUG] 엔카 연동 상태 실시간 디버그 모니터
with st.sidebar.expander("🛠️ 엔카 연동 디버그 정보", expanded=True):
    total_scanned = len(st.session_state.scan_data) if ('scan_data' in st.session_state and not st.session_state.scan_data.empty) else 0
    final_filtered = len(filtered_df) if ('filtered_df' in locals() and not filtered_df.empty) else 0
    
    st.markdown(f"**📡 수집 상태**: {'🟢 ' + str(total_scanned) + '대 수집됨' if total_scanned > 0 else '⚪ 수집 매물 없음'}")
    st.markdown(f"**🎯 필터 표출**: **{final_filtered}대** / 전체 {total_scanned}대")
    
    dbg_info = st.session_state.get('debug_encar_scan', {})
    if dbg_info:
        st.markdown(f"- **시간**: {dbg_info.get('time', '-')}")
        st.markdown(f"- **대상차량**: {dbg_info.get('car_num', '-')} ({dbg_info.get('searched_model', '-')})")
        st.markdown(f"- **API 상태**: `{dbg_info.get('status', '-')}`")
        if dbg_info.get('error'):
            st.error(f"오류: {dbg_info.get('error')}")
        st.caption(f"호출 URL: {dbg_info.get('target_url', '-')[:60]}...")
    else:
        st.caption("차량번호 조회 또는 [🚀 엔카 동급매물 스캔] 클릭 시 디버그 로그가 기록됩니다.")

    if total_scanned > 0 and final_filtered == 0:
        st.warning("⚠️ 스캔 매물은 있으나 필터 조건(차량명/세부모델)과 일치하지 않아 0대로 필터링되었습니다. 차량명/세부모델을 '전체'로 변경해보세요.")

st.sidebar.markdown("---")





# 상단 헤더 & 은닉형 메뉴 드롭다운 (남들 눈에 띄지 않도록 단일 셀렉트박스로 축소)
header_col1, header_col2 = st.columns([7.5, 2.5])
with header_col1:
    st.markdown("<h3 style='margin: 0; padding: 4px 0 12px 0; color: #ffffff;'>🏅 J-PRO 스마트 밸류에이션 시스템</h3>", unsafe_allow_html=True)
with header_col2:
    nav_options = [
        "📊 시세 분석 및 스캔", 
        "📋 매입 장부 관리", 
        "💰 재고 및 정산 관리", 
        "🎉 판매완료 정산 내역", 
        "📈 자사 판매 실적", 
        "📦 자사 보유 재고"
    ]
    cur_nav = st.session_state.get('nav_selection', '📊 시세 분석 및 스캔')
    if cur_nav not in nav_options: cur_nav = "📊 시세 분석 및 스캔"
    nav_idx = nav_options.index(cur_nav)
    nav_selection = st.selectbox(
        "화면 이동",
        nav_options,
        index=nav_idx,
        label_visibility="collapsed"
    )
    st.session_state['nav_selection'] = nav_selection

if nav_selection == "📊 시세 분석 및 스캔":
    render_main_tab(
        filtered_df=filtered_df,
        current_f_year=current_f_year,
        current_f_mil=st.session_state.get('f_mil', 0),
        reset_idx=st.session_state.form_reset_key,
        LEDGER_FILE=LEDGER_FILE,
        WEBHOOK_URL=WEBHOOK_URL
    )
elif nav_selection == "📋 매입 장부 관리":
    render_ledger_tab(
        LEDGER_FILE=LEDGER_FILE,
        SETTLEMENT_FILE=SETTLEMENT_FILE
    )
elif nav_selection == "💰 재고 및 정산 관리":
    render_settlement_tab(
        SETTLEMENT_FILE=SETTLEMENT_FILE
    )
elif nav_selection == "🎉 판매완료 정산 내역":
    render_completed_tab(
        SETTLEMENT_FILE=SETTLEMENT_FILE
    )
elif nav_selection == "📈 자사 판매 실적":
    render_sales_tab(
        current_f_year=current_f_year
    )
elif nav_selection == "📦 자사 보유 재고":
    render_inventory_tab(
        current_f_year=current_f_year
    )

if 'debug_success_msg' in st.session_state:
    st.success(st.session_state.debug_success_msg)
if 'debug_autofill' in st.session_state:
    st.warning(st.session_state.debug_autofill)
if 'debug_hd_market' in st.session_state:
    st.warning(st.session_state.debug_hd_market)
