import os
import re
import json
import time
import random
import math
import importlib
from datetime import datetime
import numpy as np
import pandas as pd
import requests
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from dotenv import load_dotenv

# python app.py 직접 실행 시 브라우저 및 Streamlit 웹 서버 자동 실행
if not st.runtime.exists():
    import sys
    from streamlit.web import cli as stcli
    print("[J-PRO] Starting Streamlit server for app.py...")
    sys.argv = ["streamlit", "run", __file__]
    sys.exit(stcli.main())

from heydealer_ai import extract_car_data_for_ai, get_gemini_estimate
from scraper import HeydealerScraper
import sales_analysis
from sales_analysis import get_car_market_stats, generate_encar_market_url, SalesDataAnalyzer

# ==========================================
# 📦 Services & Views Modular Imports
from services.cookie_server import get_current_hd_cookie, get_current_autoplus_cookie, start_cookie_server
from services.heydealer_service import parse_heydealer_comps, parse_heydealer_options
from services.data_processor import DataProcessor
from services.encar_service import Scraper
from services.settlement_service import get_auto_fee_rate, recalc_settlement_df
from services.chaolma_service import ChaolmaService
from views.components.chaolma_card import render_chaolma_card_ui

import views.tab_main
importlib.reload(views.tab_main)
from views.tab_main import render_main_tab
from views.tab_settlement import render_settlement_tab
from views.tab_ledger import (
    render_ledger_tab,
    render_completed_tab,
    render_sales_tab,
    render_inventory_tab
)

load_dotenv()

# 🍪 Chrome Extension 쿠키 수신 서버 시작 (포트 8502)
start_cookie_server(port=8502)
st.set_page_config(page_title="J-PRO Valuation System", page_icon="🏅", layout="wide")

st.markdown('''
<style>
/* ═══════════════════════════════════════════
   Factory — Terminal War Room Theme
   Based on 공장.md design tokens
   ═══════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap');

:root {
    /* ── Surfaces (Factory) ── */
    --color-obsidian-canvas: #101010;
    --color-carbon-lift: #1c1917;
    --color-surface-card: #181716;
    --color-ash-stroke: #33302f;
    --color-graphite-mid: #4d4947;
    
    /* ── Typography Grays (Factory) ── */
    --color-warm-granite: #8a8380;
    --color-pale-stone: #b8b3b0;
    --color-bone: #eeeeee;
    --color-chalk: #fafafa;
    
    /* ── Functional Accents (Factory) ── */
    --color-signal-orange: #ee6018;
    --color-metric-green: #a0ca92;
    --color-metric-blue: #60a5fa;

    /* ── Fonts ── */
    --font-geist: 'Geist', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --font-geist-mono: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* ── Global Canvas ── */
.stApp {
    background-color: var(--color-obsidian-canvas) !important;
    color: var(--color-bone) !important;
    font-family: var(--font-geist) !important;
    letter-spacing: -0.015em !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #141312 !important;
    border-right: 1px solid var(--color-ash-stroke) !important;
}

/* ── Headings (Factory Style: Clean, Tight Tracking, Sans-only) ── */
h1, h2, h3 {
    color: var(--color-chalk) !important;
    font-family: var(--font-geist) !important;
    font-weight: 600 !important;
    letter-spacing: -0.03em !important;
}
h4, h5, h6 {
    color: var(--color-pale-stone) !important;
    font-family: var(--font-geist) !important;
    font-weight: 500 !important;
    letter-spacing: -0.02em !important;
}

/* ═══ Metric Cards (Factory Compact High-Contrast) ═══ */
.metric-card {
    background-color: var(--color-surface-card) !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    box-shadow: none !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: flex-start !important;
    margin-bottom: 4px !important;
    border: 1px solid var(--color-ash-stroke) !important;
    transition: border-color 0.15s ease, background-color 0.15s ease;
    box-sizing: border-box !important;
    width: 100% !important;
}
.metric-card:hover {
    border-color: var(--color-warm-granite) !important;
    background-color: #211e1c !important;
}
.metric-icon {
    font-size: 1.25em !important;
    background: #252220 !important;
    border: 1px solid var(--color-ash-stroke) !important;
    width: 36px !important;
    height: 36px !important;
    border-radius: 8px !important;
    margin-right: 10px !important;
    flex-shrink: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
.metric-content {
    flex: 1 !important;
    min-width: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
}
/* KPI 라벨: 또렷하게 읽히는 0.82em, 선명한 Bone 화이트 */
.metric-content h4 {
    margin: 0 !important;
    padding: 0 !important;
    font-size: 0.82em !important;
    font-weight: 500 !important;
    color: var(--color-pale-stone) !important;
    font-family: var(--font-geist) !important;
    letter-spacing: -0.01em !important;
    white-space: nowrap !important;
    text-overflow: ellipsis !important;
    overflow: hidden !important;
    line-height: 1.2 !important;
}
/* KPI 핵심 숫자: Factory Bold + 선명한 대문자/수치 */
.metric-content h2 {
    margin: 2px 0 0 0 !important;
    padding: 0 !important;
    font-size: 1.25em !important;
    font-weight: 700 !important;
    color: var(--color-chalk) !important;
    font-family: var(--font-geist) !important;
    letter-spacing: -0.02em !important;
    white-space: nowrap !important;
    line-height: 1.2 !important;
}

/* ═══ Summary Box (Factory War Room Callout - 글자 시원하게 확대) ═══ */
.summary-box {
    background: #161413 !important;
    border: 1px solid var(--color-ash-stroke) !important;
    border-left: 3px solid var(--color-signal-orange) !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    margin-top: 3px !important;
    margin-bottom: 8px !important;
    color: var(--color-bone) !important;
    font-size: 0.95em !important;
    line-height: 1.55 !important;
}

/* ═══ Tabs (Factory Flush Tabs) ═══ */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 1px solid var(--color-ash-stroke) !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    color: var(--color-pale-stone) !important;
    background-color: var(--color-carbon-lift) !important;
    border: 1px solid var(--color-ash-stroke) !important;
    border-radius: 4px 4px 0 0 !important;
    padding: 6px 14px !important;
    font-size: 0.86em !important;
}
.stTabs [aria-selected="true"] {
    color: var(--color-chalk) !important;
    border-color: var(--color-signal-orange) var(--color-ash-stroke) transparent var(--color-ash-stroke) !important;
    border-top: 2px solid var(--color-signal-orange) !important;
    background-color: #24201e !important;
    font-weight: 600 !important;
}

/* ═══ Global & Top Toolbar Expanders ═══ */
[data-testid="stExpander"] {
    border: 1px solid var(--color-ash-stroke) !important;
    border-radius: 6px !important;
    background: #161413 !important;
    box-shadow: none !important;
    margin-bottom: 4px !important;
}
[data-testid="stExpander"] details {
    border: none !important;
}
[data-testid="stExpander"] summary {
    padding: 6px 12px !important;
    min-height: 38px !important;
    height: 38px !important;
    display: flex !important;
    align-items: center !important;
    cursor: pointer !important;
    border-radius: 6px !important;
    background: #181716 !important;
    transition: background-color 0.15s ease;
}
[data-testid="stExpander"] summary:hover {
    background: #221f1d !important;
}
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary div {
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    color: var(--color-bone) !important;
    margin: 0 !important;
    line-height: 1 !important;
}
[data-testid="stExpander"] summary svg {
    width: 13px !important;
    height: 13px !important;
    fill: var(--color-warm-granite) !important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    padding: 10px 14px !important;
    background: #121110 !important;
    border-top: 1px solid var(--color-ash-stroke) !important;
}

/* ═══ Top Selectbox (화면 이동) 칼맞춤 ═══ */
div[data-testid="stSelectbox"] > div > div {
    min-height: 38px !important;
    height: 38px !important;
    border-radius: 6px !important;
    border: 1px solid var(--color-ash-stroke) !important;
    background-color: #181716 !important;
    color: var(--color-chalk) !important;
    display: flex !important;
    align-items: center !important;
}

/* ═══ Dataframe ═══ */
[data-testid="stDataFrame"] {
    cursor: pointer !important;
}
[data-testid="stDataFrame"] canvas {
    cursor: pointer !important;
}

/* ═══ 헤이딜러 URL/ID 입력창 (Factory Signal Orange Accent) ═══ */
div[data-testid="stTextInput"]:has(input[placeholder*="헤이딜러 URL"]) input,
input[placeholder*="헤이딜러 URL"] {
    background-color: var(--color-carbon-lift) !important;
    border: 1px solid var(--color-signal-orange) !important;
    border-radius: 6px !important;
    color: var(--color-chalk) !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    box-shadow: 0 0 8px rgba(238, 96, 24, 0.15) !important;
    padding: 6px 10px !important;
}
input[placeholder*="헤이딜러 URL"]:focus {
    border-color: #ff7528 !important;
    box-shadow: 0 0 12px rgba(238, 96, 24, 0.3) !important;
}

/* ═══ Encar Direct Link Button ═══ */
.encar-direct-btn {
    display: block !important;
    width: 100% !important;
    text-align: center !important;
    background: #201e1d !important;
    color: #60a5fa !important;
    font-size: 0.9em !important;
    font-weight: 600 !important;
    padding: 8px 0 !important;
    border-radius: 6px !important;
    border: 1px solid #3b3734 !important;
    text-decoration: none !important;
    transition: all 0.15s ease !important;
    box-sizing: border-box !important;
}
.encar-direct-btn:hover {
    background: #2d2926 !important;
    color: #93c5fd !important;
    border-color: #60a5fa !important;
}
/* ═══ Green Bid Card & Click Bridge ═══ */
#green_bid_card {
    cursor: pointer !important;
    user-select: none !important;
}
#green_bid_card * {
    cursor: pointer !important;
}
#green_bid_card:hover {
    background-color: rgba(74, 222, 128, 0.18) !important;
    border-color: rgba(74, 222, 128, 0.6) !important;
    box-shadow: 0 0 12px rgba(74, 222, 128, 0.2) !important;
}
#green_bid_card:active {
    transform: scale(0.97) !important;
    background-color: rgba(74, 222, 128, 0.28) !important;
    border-color: #22c55e !important;
}
iframe[height="0"] {
    display: none !important;
    height: 0 !important;
    width: 0 !important;
    border: none !important;
}
</style>
''', unsafe_allow_html=True)


DB_FILE = "jpro_db.csv"
LEDGER_FILE = "my_car_ledger.csv"
SETTLEMENT_FILE = "my_inventory_settlement.csv"
INVENTORY_FILE = "autoplus_inventory.csv" 
COOKIE_FILE = "encar_cookie.txt" 
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyFTXuPkC0R9y-UftHOFmJfgBwxycMwqOabhxKVT4bcsBK9gfsscQtGCTohzFiccq71/exec"



if 'inventory_data' not in st.session_state or st.session_state.inventory_data.empty:
    if os.path.exists(INVENTORY_FILE):
        for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
            try:
                st.session_state.inventory_data = pd.read_csv(INVENTORY_FILE, encoding=enc)
                break
            except Exception:
                continue
        if 'inventory_data' not in st.session_state:
            st.session_state.inventory_data = pd.DataFrame()
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
        p_bar.empty()
        s_text.empty()
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
live_cookie = (get_current_hd_cookie() or "").strip()
if 'cookie_version' not in st.session_state:
    st.session_state.cookie_version = 0

if st.session_state.get('_last_loaded_hd_cookie') != live_cookie:
    st.session_state._last_loaded_hd_cookie = live_cookie
    st.session_state.cookie_version += 1
    st.session_state[f"hd_cookie_box_{st.session_state.cookie_version}"] = live_cookie

live_ap_cookie = (get_current_autoplus_cookie() or "").strip()
if 'ap_cookie_version' not in st.session_state:
    st.session_state.ap_cookie_version = 0

if st.session_state.get('_last_loaded_ap_cookie') != live_ap_cookie:
    st.session_state._last_loaded_ap_cookie = live_ap_cookie
    st.session_state.ap_cookie_version += 1
    st.session_state[f"ap_cookie_box_{st.session_state.ap_cookie_version}"] = live_ap_cookie

# 🔼 사이드바 상단은 즉시 핵심 업무(헤이딜러 견적 & 차량조회)로 시작
heydealer_cookie_input = live_cookie

heydealer_url_input = st.sidebar.text_input(
    "헤이딜러 차량 URL/ID", 
    placeholder="헤이딜러 URL 또는 ID 입력", 
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
    run_heydealer = st.button("AI 견적 산출", key="heydealer_btn", disabled=is_ai_running, use_container_width=True)
with col_kcar_btn:
    st.link_button("KCAR", kcar_url, use_container_width=True)

if run_heydealer:
    # 💡 실행 직전 .env의 최신 쿠키를 강제 리로드하여 세션에 실시간 반영
    latest_live_cookie = get_current_hd_cookie()
    if latest_live_cookie and len(latest_live_cookie.strip()) > 20:
        heydealer_cookie_input = latest_live_cookie

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
                st.session_state.pop('target_carid', None)
                st.session_state.pop('selected_car_id', None)
                st.session_state.scan_data = pd.DataFrame()
                st.session_state.hd_comp_df = pd.DataFrame()
                st.session_state.auto_encar_url = ""
                st.session_state.f_status = []

                hd_detail_tmp = json.loads(heydealer_json_str).get('detail', {})
                car_spec_tmp = hd_detail_tmp.get('car_spec') or {}
                spec_desc_tmp = car_spec_tmp.get('description', '')
                import re
                hd_opt_prices = re.findall(r'\((\d+)\s*만(?:원)?\)', spec_desc_tmp)
                hd_target_opt_price_sum = sum(int(p) for p in hd_opt_prices) if hd_opt_prices else 0

                # 💡 순수 '신차 추가옵션'만 정확히 선별 파싱 (* 등급 기본옵션 섹션 제외)
                hd_target_options = parse_heydealer_options(spec_desc_tmp)
                
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
                
                # 헤이딜러 응답에 포함된 엔카 시세 URL이 있으면 자동 스캔 실행 및 마스터 매핑 자체 학습
                if encar_url:
                    try:
                        from services.master_mapping import MasterMappingService
                        MasterMappingService.learn_from_heydealer(hd_detail_tmp, encar_url)
                    except Exception as e_map:
                        print(f"[MasterMapping] 자동 학습 실패: {e_map}")

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
                            else:
                                st.session_state.scan_source = "url"
                                st.session_state.scan_data = pd.DataFrame()
                                st.session_state.f_status = []
                    except Exception as e:
                        print(f"엔카 자동 스캔 예외: {e}")
                        st.session_state.scan_data = pd.DataFrame()
                else:
                    st.session_state.scan_data = pd.DataFrame()
                    st.session_state.auto_encar_url = ""
                
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
                else:
                    st.session_state.f_name = "전체"

                if hd_grade:
                    st.session_state.f_sub = hd_grade
                elif 'scan_data' in st.session_state and not st.session_state.scan_data.empty and '세부모델' in st.session_state.scan_data.columns:
                    st.session_state.f_sub = str(st.session_state.scan_data['세부모델'].iloc[0])
                else:
                    st.session_state.f_sub = "전체"

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

                        # 타겟 등급과 일치하는 낙찰 매물 우선 필터링
                        target_trim_hd = hd_detail.get('grade_part_name', '')
                        if target_trim_hd and not hd_valid_comps.empty and '차량명' in hd_valid_comps.columns:
                            t_clean = str(target_trim_hd).replace(" ", "").lower()
                            matched_grade_mask = hd_valid_comps['차량명'].apply(lambda x: t_clean in str(x).replace(" ", "").lower() or str(x).replace(" ", "").lower() in t_clean)
                            if matched_grade_mask.any():
                                hd_valid_comps = hd_valid_comps[matched_grade_mask]

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

# ═══════════════════════════════════════════
# 📋 사이드바 (차량번호 ➔ 제조사 ➔ 차량명 ➔ 세부모델 ➔ 연식 ➔ 주행거리 ➔ 옵션 ➔ 판매/장부)
# ═══════════════════════════════════════════
reset_idx = st.session_state.form_reset_key

# 0. 저장 성공 배너 (슬림하게 표시)
if st.session_state.save_success:
    st.sidebar.success(f"✅ {st.session_state.saved_car_num} 저장 완료!")
    st.session_state.save_success = False

# 1. 차량번호 (필수) + 조회 버튼
default_car_num = st.session_state.get(f"car_num_{reset_idx}", "")
st.sidebar.markdown("<div style='font-size: 0.82rem; font-weight: 600; margin-bottom: 2px; color: #e2e3e9;'>차량번호 (필수)</div>", unsafe_allow_html=True)
col_cnum, col_cbtn = st.sidebar.columns([3.0, 1.2])
with col_cnum:
    l_car_num = st.text_input(
        "차량번호 (필수)",
        value=default_car_num,
        key=f"car_num_{reset_idx}",
        label_visibility="collapsed",
        placeholder="예: 12수1496"
    ).replace(" ", "").strip()
with col_cbtn:
    btn_fetch_chaolma = st.button("조회", key=f"btn_chaolma_{reset_idx}", use_container_width=True, help="신차 출고가 & 순정옵션 견적조회")

if not ChaolmaService.is_authenticated():
    st.sidebar.markdown("<div style='font-size: 0.72rem; color: #fbbf24; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 4px; padding: 2px 6px; margin: 1px 0 4px 0;'>⚠️ 견적조회 쿠키 미등록</div>", unsafe_allow_html=True)

if btn_fetch_chaolma:
    if not l_car_num:
        st.sidebar.warning("차량번호를 입력해주세요.")
    elif not ChaolmaService.is_authenticated():
        st.sidebar.error("❌ 견적조회 쿠키가 없습니다. 상단 [🔑 세션 쿠키 설정]에 붙여넣어주세요.")
    else:
        cur_mil_val = int(st.session_state.get(f"mil_{reset_idx}", st.session_state.get('user_target_mil', 0)))
        with st.sidebar.spinner(f"[{l_car_num}] 제원 및 옵션 조회 중..."):
            res = ChaolmaService.fetch_car_info(l_car_num, mileage=cur_mil_val)
            if res.get("success"):
                st.session_state.scan_source = "car_number"
                st.session_state[f"chaolma_data_{l_car_num}"] = res
                st.session_state["last_chaolma_data"] = res

                # 헤이딜러 잔존 세션 데이터 클리어
                for k in ['hd_model_part_name', 'hd_grade_part_name', 'hd_full_name', 'auto_encar_url', 'hd_comp_df', 'hd_target_year', 'hd_target_options', 'encar_target_options']:
                    st.session_state.pop(k, None)

                # 사이드바 및 빅데이터 필터 자동 주입
                raw_maker = res.get("maker", "")
                raw_model = res.get("model_name", "")
                raw_grade = res.get("grade_name", "")
                raw_trim = res.get("trim_name", "")
                
                # 💡 [연식/형식 엄격 구분]
                # reg_year: 최초등록일 기준 연식 (예: 2022년 11월 등록 -> 2022 / '22년식')
                # model_year: 모델 형식연도 (예: 2023년형 -> '23년형')
                reg_year = str(res.get("reg_year", "")).replace("년", "").strip()
                model_year = str(res.get("model_year", "")).replace("년", "").strip()
                target_year = reg_year if reg_year else model_year
                year_display = res.get("year_display", f"{target_year[-2:]}년식" if target_year else "")

                if raw_maker:
                    st.session_state.f_brand = raw_maker
                if raw_model:
                    st.session_state.f_name = raw_model

                # 💡 유종/배기량(raw_grade: 예 '2.0 GDe')과 세부트림(raw_trim: 예 'RE 시그니처')을 지능적으로 온전히 결합
                if raw_grade and raw_trim:
                    if raw_grade in raw_trim:
                        combined_sub = raw_trim
                    else:
                        g_parts = [p for p in raw_grade.split() if p not in raw_trim]
                        combined_sub = f"{' '.join(g_parts)} {raw_trim}".strip() if g_parts else f"{raw_grade} {raw_trim}".strip()
                elif raw_trim:
                    combined_sub = raw_trim
                else:
                    combined_sub = raw_grade

                st.session_state.f_sub = combined_sub

                # 필터 연식(f_year)에는 시장 표준인 '최초등록연도(reg_year)' 주입 (22년식)
                if target_year:
                    st.session_state.f_year = target_year[-2:]
                    cur_yr_key = f"search_year_{st.session_state.form_reset_key}"
                    try:
                        st.session_state[cur_yr_key] = int(target_year[-2:])
                    except:
                        pass

                if cur_mil_val > 0:
                    st.session_state.f_mil = cur_mil_val
                    st.session_state.user_target_mil = cur_mil_val

                # 🚀 [자동 연동] 차량번호 조회 시 엔카 동급 매물 즉시 자동 스캔
                st.session_state.scan_data = pd.DataFrame()
                st.session_state.pop('target_carid', None)
                st.session_state.pop('selected_car_id', None)

                target_encar_url = generate_encar_market_url(
                    raw_model, 
                    combined_sub or raw_trim or raw_grade, 
                    target_year, 
                    cur_mil_val
                )
                scan_cnt = 0
                st.session_state.debug_encar_scan = {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "car_num": l_car_num,
                    "target_url": target_encar_url,
                    "searched_model": raw_model,
                    "searched_sub": combined_sub,
                    "searched_year": target_year,
                    "status": "진행안됨",
                    "count": 0,
                    "error": ""
                }
                if target_encar_url:
                    try:
                        with st.sidebar.spinner(f"[{raw_model}] 엔카 동급매물 자동 연동 중..."):
                            p_bar, s_text = st.sidebar.progress(0), st.sidebar.empty()
                            new_scan_df, msg = Scraper.run(target_encar_url, "", p_bar, s_text)
                            p_bar.empty()
                            s_text.empty()
                            st.session_state.debug_encar_scan["status"] = msg
                            if msg == "success" and not new_scan_df.empty:
                                st.session_state.scan_data = new_scan_df
                                scan_cnt = len(new_scan_df)
                                st.session_state.debug_encar_scan["count"] = scan_cnt
                                st.session_state.debug_encar_scan["encar_model"] = new_scan_df['차량명'].iloc[0] if '차량명' in new_scan_df.columns else "-"
                                if '차량명' in new_scan_df.columns:
                                    st.session_state.f_name = new_scan_df['차량명'].iloc[0]
                                if '제조사' in new_scan_df.columns and new_scan_df['제조사'].iloc[0]:
                                    st.session_state.f_brand = new_scan_df['제조사'].iloc[0]
                            else:
                                st.session_state.scan_data = pd.DataFrame()
                                st.session_state.debug_encar_scan["count"] = 0
                                st.session_state.debug_encar_scan["error"] = msg
                    except Exception as ex_scan:
                        st.session_state.scan_data = pd.DataFrame()
                        st.session_state.debug_encar_scan["count"] = 0
                        st.session_state.debug_encar_scan["status"] = "예외 에러"
                        st.session_state.debug_encar_scan["error"] = str(ex_scan)
                else:
                    st.session_state.scan_data = pd.DataFrame()

                msg_suffix = f" & 엔카 {scan_cnt}대 연동 완료!" if scan_cnt > 0 else ""
                disp_yr = f" ({year_display})" if year_display else ""
                st.sidebar.success(f"✅ [{l_car_num}] {raw_model} {raw_trim}{disp_yr}{msg_suffix}")
                st.rerun()
            else:
                st.sidebar.error(f"❌ {res.get('message', '조회 실패')}")

# 2. 제조사/브랜드
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
    def is_brand_matched(target_b, row_b):
        t = re.sub(r'[\(\)_\-\s]', '', str(target_b)).lower()
        r = re.sub(r'[\(\)_\-\s]', '', str(row_b)).lower()
        if t == r or t in r or r in t:
            return True
        brand_groups = [
            {'르노코리아', '르노삼성', '르노', 'renault'},
            {'kg모빌리티', '쌍용', 'kgm', 'ssangyong'},
            {'쉐보레', 'gm대우', '대우', 'chevrolet'},
            {'현대', '현대자동차', 'hyundai'},
            {'기아', '기아자동차', 'kia'},
            {'벤츠', 'mercedes', 'mercedesbenz'},
            {'bmw'},
            {'아우디', 'audi'},
            {'폭스바겐', 'volkswagen'}
        ]
        for g in brand_groups:
            if any(k in t for k in g) and any(k in r for k in g):
                return True
        return False

    b_mask = filtered_df['제조사'].apply(lambda x: is_brand_matched(st.session_state.f_brand, x))
    if b_mask.any():
        filtered_df = filtered_df[b_mask]

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

# 3. 차량명 목록 구성 및 선택
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
    mask = filtered_df['차량명'].astype(str).str.replace(" ", "").str.lower().str.contains(name_clean_f, na=False, regex=False)
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

# 4. 세부모델 목록 구성 및 선택
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
    
    # 💡 엔카 데이터는 '살룬' 등이 세부모델이 아닌 차량명(Model)에 위치하므로 [차량명 + 세부모델] 통합 풀텍스트로 검색
    encar_full_clean = (filtered_df['차량명'].astype(str) + " " + filtered_df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
    
    all_matched = pd.Series(True, index=filtered_df.index)
    for part in sub_parts:
        part_clean = part.replace(" ", "").lower()
        all_matched = all_matched & encar_full_clean.str.contains(part_clean, na=False, regex=False)
    
    cand_df = filtered_df[all_matched] if all_matched.any() else filtered_df.copy()
    
    # 1. 🚗 [파생 바디/타입(살룬, 왜건, 하이리무진, 밴, 칸, 크로스오버 등) 범용 상호 배제]
    BODY_TYPE_KEYWORDS = [
        '살룬', '왜건', '해치백', '하이리무진', '리무진', '밴', '카고', 
        '쿠페', '컨버터블', '카브리올레', '로드스터', '그란쿠페', 
        '칸', '크로스오버', '아웃도어'
    ]
    target_all_text = (str(st.session_state.get('f_name', '')) + " " + sub_raw).lower()
    cand_full_clean = (cand_df['차량명'].astype(str) + " " + cand_df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
    
    for b_kw in BODY_TYPE_KEYWORDS:
        if b_kw in target_all_text:
            # 타겟에 파생타입이 있으면 해당 키워드가 있는 매물만 엄격 필터링
            has_b = cand_full_clean.str.contains(b_kw, na=False)
            if has_b.any():
                cand_df = cand_df[has_b]
                cand_full_clean = (cand_df['차량명'].astype(str) + " " + cand_df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
        else:
            # 타겟에 파생타입이 없는데 엔카 매물 풀에 파생매물이 섞여있다면 파생매물 자동 탈락
            has_b = cand_full_clean.str.contains(b_kw, na=False)
            if has_b.any() and (~has_b).any():
                cand_df = cand_df[~has_b]
                cand_full_clean = (cand_df['차량명'].astype(str) + " " + cand_df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
                
    # 2. ⛽ [유종(디젤 vs 가솔린 vs LPG) 엄격 상호 배제]
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
            
    # 3. 🔍 [배기량(Displacement: 1.7 vs 2.0 등) 엄격 일치]
    disp_m = re.search(r'(\d\.\d)', sub_raw)
    if disp_m:
        disp_val = disp_m.group(1)
        cand_full_clean = (cand_df['차량명'].astype(str) + " " + cand_df['세부모델'].astype(str)).str.replace(" ", "").str.lower()
        disp_mask = cand_full_clean.str.contains(disp_val, na=False)
        if disp_mask.any():
            cand_df = cand_df[disp_mask]
    
    # 4. ⚙️ [구동방식 (2WD vs 4WD/AWD)]
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
            
    # 5. ✨ [스페셜/플러스/에디션/마스터 등 서브 키워드]
    for sub_kw in ['스페셜', '플러스', '에디션', '마스터']:
        if sub_kw not in sub_clean:
            has_kw = cand_df['세부모델'].astype(str).str.contains(sub_kw, na=False)
            if (~has_kw).any():
                cand_df = cand_df[~has_kw]
        else:
            has_kw = cand_df['세부모델'].astype(str).str.contains(sub_kw, na=False)
            if has_kw.any():
                cand_df = cand_df[has_kw]
                
    if not cand_df.empty:
        filtered_df = cand_df

# 5. 연식 (시세분석용 연식, 0=전체)
default_f_year = st.session_state.get('f_year', '')
try:
    init_year_val = (int(str(default_f_year).strip()) % 100) if str(default_f_year).strip().isdigit() else 0
except Exception:
    init_year_val = 0

cur_yr_key = f"search_year_{st.session_state.form_reset_key}"
if init_year_val > 0 and (cur_yr_key not in st.session_state or st.session_state[cur_yr_key] == 0):
    st.session_state[cur_yr_key] = init_year_val

f_year_num = st.sidebar.number_input(
    "연식 (시세분석용, 0=전체)",
    min_value=0,
    max_value=99,
    value=st.session_state.get(cur_yr_key, init_year_val),
    step=1,
    key=cur_yr_key
)
current_f_year = f"{f_year_num:02d}" if f_year_num > 0 else ""

if not filtered_df.empty:
    if "주행거리" in filtered_df.columns:
        filtered_df["주행거리"] = pd.to_numeric(filtered_df["주행거리"], errors='coerce').fillna(0)
    
    def _parse_app_year(val):
        m = re.search(r'(\d+)', str(val))
        return int(m.group(1)) if m else 0

    if "성능일" in filtered_df.columns and "연식" in filtered_df.columns:
        filtered_df['_has_perf'] = filtered_df['성능일'].astype(str).apply(
            lambda x: 1 if re.match(r'^\d{2}-\d{2}-\d{2}', str(x)) and str(x) not in ['미검사/사진', '⚠️미등록', '⚠️조회실패', '-'] else 0
        )
        filtered_df['_sort_perf'] = filtered_df['성능일'].astype(str).apply(
            lambda x: x if re.match(r'^\d{2}-\d{2}-\d{2}', str(x)) and str(x) not in ['미검사/사진', '⚠️미등록', '⚠️조회실패', '-'] else '00-00-00'
        )
        filtered_df['_sort_year'] = filtered_df['연식'].apply(_parse_app_year)
        filtered_df = filtered_df.sort_values(
            by=['_has_perf', '_sort_year', '_sort_perf'],
            ascending=[False, False, False]
        ).drop(columns=['_has_perf', '_sort_perf', '_sort_year']).reset_index(drop=True)

# 6. 주행거리 (km)
default_mil_val = int(st.session_state.get(f"mil_{reset_idx}", st.session_state.get('user_target_mil', 0)))
mil_k = f"mil_{reset_idx}"
if default_mil_val > 0 and (mil_k not in st.session_state or st.session_state[mil_k] == 0):
    st.session_state[mil_k] = default_mil_val
l_mil = st.sidebar.number_input("주행거리 (km)", min_value=0, value=default_mil_val, step=1000, key=mil_k)
if l_mil > 0:
    st.session_state.user_target_mil = l_mil
    st.session_state.f_mil = l_mil

# 7. 옵션 (출고정보 카드 - 사이드바 전용 컴팩트 렌더링)
cached_chaolma = st.session_state.get(f"chaolma_data_{l_car_num}") if l_car_num else None
if not cached_chaolma:
    cached_chaolma = st.session_state.get("last_chaolma_data")

hd_opts = st.session_state.get('hd_target_options', [])
encar_opts = st.session_state.get('encar_target_options', [])
hd_spec_desc = st.session_state.get('hd_car_spec_desc', '')

# 🔍 현재 선택된 비교 매물의 옵션 목록 실시간 추출 (지연 없는 사이드바 하이라이트 동기화)
cur_comp_opts = []
if 'filtered_df' in locals() and not filtered_df.empty:
    table_state = st.session_state.get('encar_car_table', {})
    sel_rows = table_state.get('selection', {}).get('rows', []) if isinstance(table_state, dict) else []
    
    target_row = None
    if sel_rows and sel_rows[0] < len(filtered_df):
        target_row = filtered_df.iloc[sel_rows[0]]
    elif st.session_state.get('selected_car_id'):
        target_id = str(st.session_state.get('selected_car_id')).strip()
        matched = filtered_df[filtered_df['_carid'].astype(str).str.strip() == target_id] if '_carid' in filtered_df.columns else pd.DataFrame()
        if not matched.empty:
            target_row = matched.iloc[0]
            
    if target_row is None and not filtered_df.empty:
        target_row = filtered_df.iloc[0]
        
    if target_row is not None:
        carid = target_row.get('_carid')
        cache_key = f"_full_detail_cache_{carid}"
        full_info = st.session_state.get(cache_key, {})
        live_opt_list = full_info.get("options", [])
        if live_opt_list:
            cur_comp_opts = live_opt_list
        else:
            raw_opts = str(target_row.get('추가옵션', '')).split(" / ")
            cur_comp_opts = [o.strip() for o in raw_opts if o.strip() and o.strip() not in ("없음", "-", "없음(구버전점검)", "⚠️조회실패", "코드매칭실패")]

if not cur_comp_opts:
    cur_comp_opts = st.session_state.get('selected_comp_car_opts', [])

from sales_analysis import is_target_option_matched
c_name_for_match = st.session_state.get('hd_model_part_name', '') or st.session_state.get('f_name', '')
c_year_for_match = str(st.session_state.get('f_year', '') or '')
has_comp_selected = bool(cur_comp_opts)

if cached_chaolma and cached_chaolma.get("success"):
    raw_new_p = cached_chaolma.get("new_car_price", 0)
    raw_base_p = cached_chaolma.get("base_car_price", 0)
    raw_opt_p = cached_chaolma.get("total_option_price", 0)
    raw_deprec_p = cached_chaolma.get("total_depreciated_opt_price", 0)
    
    new_p = raw_new_p // 10000 if raw_new_p >= 10000 else raw_new_p
    base_p = raw_base_p // 10000 if raw_base_p >= 10000 else raw_base_p
    opt_p = raw_opt_p // 10000 if raw_opt_p >= 10000 else raw_opt_p
    deprec_p = raw_deprec_p // 10000 if raw_deprec_p >= 10000 else raw_deprec_p
    opts_list = cached_chaolma.get("options", [])
    
    badges = []
    target_win_count = 0
    for o in opts_list:
        o_name = o.get("name", "")
        o_pr = o.get("price", 0)
        pr_str = f" ({o_pr // 10000}만)" if o_pr >= 10000 else (f" ({o_pr}만)" if o_pr > 0 else "")
        if has_comp_selected:
            is_matched_in_comp = any(is_target_option_matched(c_opt, [o_name], c_name_for_match, c_year_for_match) for c_opt in cur_comp_opts)
            if not is_matched_in_comp:
                target_win_count += 1
                badges.append(f'<span style="display:inline-block; background:rgba(34, 197, 94, 0.22); border:1.5px solid #22c55e; color:#4ade80; border-radius:5px; padding:3px 7px; font-size:0.75rem; font-weight:700; margin:2px 2px; box-shadow:0 0 6px rgba(34, 197, 94, 0.25);">+ {o_name}{pr_str}</span>')
            else:
                badges.append(f'<span style="display:inline-block; background:rgba(56, 189, 248, 0.12); border:1px solid rgba(56, 189, 248, 0.25); color:#94a3b8; border-radius:4px; padding:2px 6px; font-size:0.72rem; margin:2px 2px;">✓ {o_name}{pr_str}</span>')
        else:
            badges.append(f'<span style="display:inline-block; background:rgba(56,189,248,0.15); border:1px solid rgba(56,189,248,0.3); color:#7dd3fc; border-radius:4px; padding:2px 6px; font-size:0.72rem; margin:2px 2px;">{o_name}{pr_str}</span>')
    
    badge_html = "".join(badges)
    header_extra = f"<span style=\"font-size:0.68rem; color:#4ade80; font-weight:700; background:rgba(34,197,94,0.15); border:1px solid #22c55e; padding:1px 6px; border-radius:4px;\">🟢 우세 {target_win_count}개</span>" if (has_comp_selected and target_win_count > 0) else ""

    st.sidebar.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 8px; padding: 10px 12px; margin-top: 4px; margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 4px; margin-bottom: 6px;">
            <span style="font-size: 0.82rem; font-weight: 700; color: #38bdf8;">🏷️ 출고정보 & 순정옵션</span>
            <div style="display:flex; align-items:center; gap:6px;">
                {header_extra}
                <span style="font-size: 0.74rem; font-weight: 600; color: #f8fafc;">출고가 {new_p:,}만원</span>
            </div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-bottom: 6px;">
            <span>기본: {base_p:,}만</span>
            <span>옵션: <b style="color: #38bdf8;">{opt_p:,}만</b> (잔존 <b style="color: #34d399;">{deprec_p:,}만</b>)</span>
        </div>
        <div style="margin-top: 4px; line-height: 1.4;">
            {badge_html if badge_html else '<span style="font-size:0.72rem; color:#64748b;">장착 옵션 없음 (기본 사양)</span>'}
        </div>
    </div>
    """, unsafe_allow_html=True)
elif hd_opts:
    badges = []
    target_win_count = 0

    for opt in hd_opts:
        if has_comp_selected:
            # 비교 차량의 옵션 목록과 대조
            is_matched_in_comp = any(is_target_option_matched(c_opt, [opt], c_name_for_match, c_year_for_match) for c_opt in cur_comp_opts)
            if not is_matched_in_comp:
                # 🟢 비교차에 없는 옵션: 내 차 우세! (에메랄드 그린 강조)
                target_win_count += 1
                badges.append(f'<span style="display:inline-block; background:rgba(34, 197, 94, 0.22); border:1.5px solid #22c55e; color:#4ade80; border-radius:5px; padding:3px 7px; font-size:0.75rem; font-weight:700; margin:2px 2px; box-shadow:0 0 6px rgba(34, 197, 94, 0.25);">+ {opt}</span>')
            else:
                # ⚪ 비교차에도 있는 공통 옵션
                badges.append(f'<span style="display:inline-block; background:rgba(56, 189, 248, 0.12); border:1px solid rgba(56, 189, 248, 0.25); color:#94a3b8; border-radius:4px; padding:2px 6px; font-size:0.72rem; margin:2px 2px;">✓ {opt}</span>')
        else:
            # 비교차가 아직 선택되지 않은 기본 상태
            badges.append(f'<span style="display:inline-block; background:rgba(56, 189, 248, 0.15); border:1px solid rgba(56, 189, 248, 0.3); color:#7dd3fc; border-radius:4px; padding:2px 6px; font-size:0.72rem; margin:2px 2px;">{opt}</span>')

    badge_html = "".join(badges)
    header_extra = f"<span style=\"font-size:0.68rem; color:#4ade80; font-weight:700; background:rgba(34,197,94,0.15); border:1px solid #22c55e; padding:1px 6px; border-radius:4px;\">🟢 우세 {target_win_count}개</span>" if (has_comp_selected and target_win_count > 0) else ""

    st.sidebar.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 8px; padding: 10px 12px; margin-top: 4px; margin-bottom: 8px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 4px;">
            <span style="font-size: 0.82rem; font-weight: 700; color: #38bdf8;">🏷️ 신차 추가 옵션 ({len(hd_opts)}개)</span>
            {header_extra}
        </div>
        <div style="margin-top: 4px; line-height: 1.4;">
            {badge_html}
        </div>
    </div>
    """, unsafe_allow_html=True)
elif hd_spec_desc:
    # 헤이딜러 출고정보는 있으나 추가 옵션이 없는 경우
    st.sidebar.markdown("""
    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 8px; padding: 10px 12px; margin-top: 4px; margin-bottom: 8px;">
        <div style="font-size: 0.82rem; font-weight: 700; color: #38bdf8; margin-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 4px;">
            🏷️ 신차 추가 옵션
        </div>
        <div style="margin-top: 4px; font-size: 0.74rem; color: #94a3b8;">
            추가 옵션 없음 (기본 출고 사양)
        </div>
    </div>
    """, unsafe_allow_html=True)
elif encar_opts:
    badges = []
    target_win_count = 0

    for opt in encar_opts:
        if has_comp_selected:
            is_matched_in_comp = any(is_target_option_matched(c_opt, [opt], c_name_for_match, c_year_for_match) for c_opt in cur_comp_opts)
            if not is_matched_in_comp:
                target_win_count += 1
                badges.append(f'<span style="display:inline-block; background:rgba(34, 197, 94, 0.22); border:1.5px solid #22c55e; color:#4ade80; border-radius:5px; padding:3px 7px; font-size:0.75rem; font-weight:700; margin:2px 2px; box-shadow:0 0 6px rgba(34, 197, 94, 0.25);">+ {opt}</span>')
            else:
                badges.append(f'<span style="display:inline-block; background:rgba(56, 189, 248, 0.12); border:1px solid rgba(56, 189, 248, 0.25); color:#94a3b8; border-radius:4px; padding:2px 6px; font-size:0.72rem; margin:2px 2px;">✓ {opt}</span>')
        else:
            badges.append(f'<span style="display:inline-block; background:rgba(56, 189, 248, 0.15); border:1px solid rgba(56, 189, 248, 0.3); color:#7dd3fc; border-radius:4px; padding:2px 6px; font-size:0.72rem; margin:2px 2px;">{opt}</span>')

    badge_html = "".join(badges)
    header_extra = f"<span style=\"font-size:0.68rem; color:#4ade80; font-weight:700; background:rgba(34,197,94,0.15); border:1px solid #22c55e; padding:1px 6px; border-radius:4px;\">🟢 우세 {target_win_count}개</span>" if (has_comp_selected and target_win_count > 0) else ""

    st.sidebar.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 8px; padding: 10px 12px; margin-top: 4px; margin-bottom: 8px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 4px;">
            <span style="font-size: 0.82rem; font-weight: 700; color: #38bdf8;">🏷️ 주요 장착 편의장치 ({len(encar_opts)}개)</span>
            {header_extra}
        </div>
        <div style="margin-top: 4px; line-height: 1.4;">
            {badge_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

l_sell_price = st.sidebar.number_input("판매가 (예상, 만원)", min_value=0, step=10, key=f"sell_{reset_idx}")
l_ext_repair = st.sidebar.number_input("외판 수리 갯수", min_value=0, step=1, format="%d", key=f"ext_{reset_idx}")

route_options = ["셀프(기본)", "제로", "개인"]
cur_route = st.session_state.get("purchase_route", "셀프(기본)")
if cur_route not in route_options:
    cur_route = "셀프(기본)"

def update_route():
    if "_route_selector" in st.session_state:
        st.session_state.purchase_route = st.session_state._route_selector

l_route = st.sidebar.selectbox(
    "매입 경로", 
    route_options, 
    index=route_options.index(cur_route), 
    key="_route_selector", 
    on_change=update_route
)
st.session_state.purchase_route = l_route

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
final_target = max(0, int(math.floor(final_target_raw)))

# 💡 [양방향 연동] 권장 입찰가 직접 수정 및 실시간 마진 연동
last_calc_key = f"_last_calc_target_{reset_idx}"
user_bid_key = f"user_final_bid_{reset_idx}"

# 판매가나 마진 등이 변경되어 기본 계산값이 바뀌면 사용자 수정값도 새 계산값으로 동기화
if st.session_state.get(last_calc_key) != final_target:
    st.session_state[last_calc_key] = final_target
    st.session_state[user_bid_key] = final_target

if l_sell_price > 0:
    # 🎨 최종 입찰가 입력창 및 복사 버튼 줄바꿈 방지 & 컴팩트 CSS
    st.sidebar.markdown("""
    <style>
    /* 입력창 내부 숫자 크고 선명하게 */
    div[data-testid="stSidebar"] input[aria-label="최종 입찰가"] {
        font-size: 1.3rem !important;
        font-weight: 800 !important;
        color: #4ade80 !important;
    }
    /* 복사 버튼 글자 줄바꿈 절대 방지 및 깔끔한 높이 맞춤 */
    div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button {
        white-space: nowrap !important;
        padding: 4px 6px !important;
        font-size: 0.85rem !important;
        color: #cbd5e1 !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button p {
        white-space: nowrap !important;
        word-break: keep-all !important;
    }
    /* 녹색 매입가 창 클릭 인터랙션 */
    #green_bid_card:hover {
        border-color: #4ade80 !important;
        background-color: rgba(74, 222, 128, 0.18) !important;
        box-shadow: 0 0 10px rgba(74, 222, 128, 0.3) !important;
    }
    #green_bid_card:active {
        transform: scale(0.975);
    }
    [data-testid="stSidebar"] iframe[height="0"] {
        display: none !important;
        position: absolute !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 🎯 가로 1행: [입찰가 수정 입력창] + [📋 복사 버튼] (줄바꿈 없도록 너비 2.3 : 1.1 분할)
    c_input, c_btn = st.sidebar.columns([2.3, 1.1])
    cur_bid_default = st.session_state.get(user_bid_key, final_target)
    
    with c_input:
        user_bid = st.number_input(
            "최종 입찰가",
            min_value=0,
            step=1,
            value=cur_bid_default,
            key=f"bid_input_{reset_idx}_{final_target}",
            label_visibility="collapsed",
            help="권장가에서 직접 금액 수정 시 실시간 반영됩니다."
        )
        st.session_state[user_bid_key] = user_bid

    # 💡 수정된 입찰가(user_bid) 기준 실시간 수수료 & 실제 마진 재계산
    actual_purchase_fee = purchase_fee
    if l_route == "셀프(기본)":
        if user_bid <= 100: actual_purchase_fee = 7.5
        elif user_bid <= 500: actual_purchase_fee = 18.5
        elif user_bid <= 1000: actual_purchase_fee = 19.0 if is_light_car else 24.5
        elif user_bid <= 3000: actual_purchase_fee = 25.0
        else: actual_purchase_fee = 36.0
    elif l_route == "제로":
        if user_bid <= 100: actual_purchase_fee = 14.0
        elif user_bid <= 500: actual_purchase_fee = 30.0
        elif user_bid <= 1000: actual_purchase_fee = 30.5 if is_light_car else 36.5
        elif user_bid <= 1500: actual_purchase_fee = 36.5
        elif user_bid <= 3000: actual_purchase_fee = 39.5
        elif user_bid <= 4000: actual_purchase_fee = 47.5
        else: actual_purchase_fee = 50.5
    elif l_route == "개인":
        actual_purchase_fee = l_manual_fee

    actual_margin = l_sell_price - selling_fee - misc_cost - ext_cost - actual_purchase_fee - user_bid
    diff_bid = final_target - user_bid

    with c_btn:
        if st.button("📋 복사", key=f"btn_copy_target_{user_bid}", help=f"클립보드에 {user_bid} 복사", use_container_width=True):
            try:
                import subprocess
                subprocess.run('clip', input=str(user_bid), text=True, check=True)
                st.toast(f"📋 입찰가 {user_bid:,}만원 ({user_bid}) 복사 완료!")
            except Exception as e:
                st.toast(f"⚠️ 복사 오류: {e}")

    # 🏷️ 라벨 (기본은 '권장 매입가', 수정한 경우만 '최종 매입가')
    if user_bid != final_target:
        label_html = f"<span style='font-size: 0.8rem; font-weight: 700; color: #cbd5e1;'>최종 매입가 <small style='color: #64748b; font-weight: normal;'>(권장 {final_target:,}만)</small></span>"
    else:
        label_html = "<span style='font-size: 0.85rem; font-weight: 700; color: #94a3b8;'>권장 매입가</span>"

    # 💰 실시간 마진 간결한 한줄 표기 (아이콘 및 괄호 문구 제거로 줄바꿈 원천 차단)
    margin_html = f"""<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 2px; padding-top: 2px; border-top: 1px dashed rgba(74, 222, 128, 0.2); white-space: nowrap; line-height: 1.2;">
        <span style="font-size: 0.76rem; color: #94a3b8; font-weight: 600;">예상마진</span>
        <span style="font-size: 0.88rem; font-weight: 800; color: #38bdf8;">{actual_margin:,.0f}만원</span>
    </div>"""

    # 가로 2행: 권장매입가 및 실시간 마진 노출 (녹색 창 클릭 시 장부 즉시 저장)
    html_content = f"""
    <div id="green_bid_card" 
         title="클릭 시 내 장부에 즉시 저장됩니다"
         style="background-color: rgba(74, 222, 128, 0.1); border: 1px solid rgba(74, 222, 128, 0.35); padding: 7px 12px; border-radius: 8px; margin-top: -4px; margin-bottom: 6px; cursor: pointer; transition: all 0.15s ease;">
        <div style="display: flex; justify-content: space-between; align-items: baseline; white-space: nowrap;">
            <div>{label_html}</div>
            <div style="font-size: 1.55rem; font-weight: 900; text-align: right; color: #4ade80; letter-spacing: -0.02em; white-space: nowrap;">
                {user_bid:,} <span style="font-size: 0.55em; font-weight: 700;">만원</span>
            </div>
        </div>
        {margin_html}
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.7rem; color: #64748b; margin-top: 3px; white-space: nowrap;">
            <div>수수료: {actual_purchase_fee:g}만 · 수리: {ext_cost:g}만 · 잡비: {misc_cost}만</div>
            <div style="color: #4ade80; font-weight: 700; font-size: 0.68rem; letter-spacing: -0.02em;">💾 누르면 저장</div>
        </div>
    </div>
    """
    st.sidebar.markdown(html_content, unsafe_allow_html=True)
else:
    user_bid = 0
    actual_purchase_fee = 0
    actual_margin = 0
    st.sidebar.caption("💡 판매가 입력 시 권장 매입가가 계산됩니다.")

l_memo = st.sidebar.text_area("특이사항 / 메모", height=65, key=f"memo_{reset_idx}")

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
            '매입가': user_bid if l_sell_price > 0 else "", 
            '판매가': l_sell_price if l_sell_price > 0 else "", 
            '외판수리': l_ext_repair if 'l_ext_repair' in locals() else 0,
            '외판수리비': ext_cost if 'ext_cost' in locals() else 0,
            '헤딜수수료': actual_purchase_fee if 'actual_purchase_fee' in locals() else 0,
            '특이사항': f"[{st.session_state.purchase_route} / 마진: {actual_margin:,.0f}만] " + l_memo,
            '상태': '장부저장'
        }
        st.session_state.my_ledger_data = pd.concat([pd.DataFrame([new_record]), st.session_state.my_ledger_data], ignore_index=True)
        st.session_state.my_ledger_data.to_csv(LEDGER_FILE, index=False, encoding='utf-8-sig')

        # 마스터 매핑 서비스에 차량번호별 확정 엔카 URL 영구 저장 (0오차 동급 시세 복원용)
        cur_target_url = st.session_state.get('auto_encar_url') or st.session_state.get('auto_scan_url') or ""
        if cur_target_url and l_car_num:
            try:
                from services.master_mapping import MasterMappingService
                MasterMappingService.save_car_link(l_car_num, cur_target_url)
            except Exception as e_link:
                print(f"[MasterMapping] 차량 링크 저장 실패: {e_link}")

        try:
            response = requests.post(WEBHOOK_URL, json=new_record, timeout=5)
            response.raise_for_status()
        except Exception as e:
            print(f"[구글 시트 웹훅 전송 실패]: {e}")

        st.session_state.save_success = True
        st.session_state.saved_car_num = l_car_num
        st.session_state.form_reset_key += 1

        st.rerun()

# 🔗 권장매입가 초록창 클릭 -> 장부 저장 버튼 자동 격발 브릿지
components.html("""
<script>
(function() {
    try {
        const parentDoc = window.parent.document;
        if (parentDoc.__greenBidCardListenerSet) return;
        parentDoc.__greenBidCardListenerSet = true;

        parentDoc.addEventListener('click', function(e) {
            const card = e.target.closest('#green_bid_card');
            if (!card) return;

            // 시각적 피드백
            card.style.transform = 'scale(0.95)';
            card.style.borderColor = '#22c55e';
            card.style.backgroundColor = 'rgba(74, 222, 128, 0.3)';
            setTimeout(() => {
                if (card) {
                    card.style.transform = '';
                    card.style.borderColor = '';
                    card.style.backgroundColor = '';
                }
            }, 200);

            // 사이드바의 저장 버튼 찾기
            const sidebar = parentDoc.querySelector('[data-testid="stSidebar"]');
            if (!sidebar) return;
            const buttons = Array.from(sidebar.querySelectorAll('button'));
            const saveBtn = buttons.find(b => {
                const txt = b.innerText || b.textContent || '';
                return txt.includes('장부 및 구글시트에 저장') || txt.includes('내 장부');
            });

            if (saveBtn) {
                // React 합성 이벤트 격발을 위한 마우스 시퀀스
                const events = ['mousedown', 'mouseup', 'click'];
                events.forEach(eventType => {
                    saveBtn.dispatchEvent(new MouseEvent(eventType, {
                        bubbles: true,
                        cancelable: true,
                        view: window.parent,
                        buttons: 1
                    }));
                });
                saveBtn.focus();
                saveBtn.click();
            } else {
                console.warn('[green_bid_card] 저장 버튼을 찾지 못했습니다.');
            }
        }, true);
    } catch (err) {
        console.error('[green_bid_card bridge error]', err);
    }
})();
</script>
""", height=0)






# ═══════════════════════════════════════════
# 🛠️ 상단 가로 유틸리티 바 (쿠키 설정, 부가데이터, 뷰 네비게이션)
# ═══════════════════════════════════════════
live_ap_cookie = get_current_autoplus_cookie()
cookie_status = st.session_state.get('hd_cookie_status', 'valid' if (live_cookie and len(live_cookie.strip()) > 20) else 'empty')
hd_ok = bool(live_cookie and len(live_cookie.strip()) > 20 and cookie_status != 'expired')
ap_ok = ChaolmaService.is_authenticated()

hd_badge_text = "🟢 헤이딜러" if hd_ok else "🔴 헤이딜러"
ap_badge_text = "🟢 견적조회" if ap_ok else "🔴 견적조회"

h_col1, h_col2, h_col3 = st.columns([3.6, 3.8, 2.6])

with h_col1:
    with st.expander(f"🔑 세션 쿠키 ({hd_badge_text} | {ap_badge_text})", expanded=False):
        c_sk1, c_sk2 = st.columns([3, 1.2])
        with c_sk1:
            st.markdown(f"<div style='font-size:0.75rem; margin-top:2px;'><b>헤이딜러</b>: {'<span style=\"color:#4ade80;\">정상</span>' if hd_ok else '<span style=\"color:#f87171;\">미등록/만료</span>'}&nbsp;&nbsp;|&nbsp;&nbsp;<b>견적조회</b>: {'<span style=\"color:#4ade80;\">정상</span>' if ap_ok else '<span style=\"color:#f87171;\">미등록/만료</span>'}</div>", unsafe_allow_html=True)
        with c_sk2:
            if st.button("🔄 동기화", key="top_sync_cookie_btn", use_container_width=True):
                live_cookie = get_current_hd_cookie()
                live_ap_cookie = get_current_autoplus_cookie()
                st.session_state._last_loaded_hd_cookie = live_cookie
                st.session_state.cookie_version += 1
                st.session_state[f"hd_cookie_box_{st.session_state.cookie_version}"] = live_cookie
                st.session_state.hd_cookie_status = 'valid' if (live_cookie and len(live_cookie.strip()) > 20) else 'empty'

                st.session_state._last_loaded_ap_cookie = live_ap_cookie
                st.session_state.ap_cookie_version += 1
                st.session_state[f"ap_cookie_box_{st.session_state.ap_cookie_version}"] = live_ap_cookie
                st.rerun()

        typed_cookie = st.text_input(
            "헤이딜러 쿠키",
            value=live_cookie,
            key=f"hd_cookie_box_{st.session_state.cookie_version}",
            type="password"
        )
        if typed_cookie:
            heydealer_cookie_input = typed_cookie
            if typed_cookie.strip() != (live_cookie or "").strip():
                from services.cookie_server import set_env_variable
                set_env_variable("HEYDEALER_COOKIE", typed_cookie.strip())
                st.session_state._last_loaded_hd_cookie = typed_cookie.strip()
                st.rerun()

        typed_ap_cookie = st.text_input(
            "견적조회(차얼마2) 쿠키",
            value=live_ap_cookie,
            key=f"ap_cookie_box_{st.session_state.ap_cookie_version}",
            type="password"
        )
        if typed_ap_cookie and typed_ap_cookie.strip() != (live_ap_cookie or "").strip():
            from services.cookie_server import save_autoplus_cookie
            save_autoplus_cookie(typed_ap_cookie.strip())
            st.session_state._last_loaded_ap_cookie = typed_ap_cookie.strip()
            try:
                from services.chaolma_service import ChaolmaService
                ChaolmaService.clear_cache()
            except Exception:
                pass
            st.rerun()

with h_col2:
    with st.expander("🗃️ 부가 데이터 및 엔카 스캔", expanded=False):
        st.caption("📁 자사 재고 엑셀 업로드")
        uploaded_files = st.file_uploader("자사 재고 엑셀 업로드", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True, label_visibility="collapsed", key="top_inventory_uploader")
        c_ex1, c_ex2 = st.columns(2)
        with c_ex1:
            if st.button("📁 엑셀 병합/DB저장", use_container_width=True, key="top_merge_db_btn"):
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
        with c_ex2:
            if st.button("🗑️ 저장 엑셀 DB 삭제", use_container_width=True, key="top_clear_db_btn"):
                st.session_state.inventory_data = pd.DataFrame()
                if os.path.exists(INVENTORY_FILE): os.remove(INVENTORY_FILE)
                try:
                    from sales_analysis import SalesDataAnalyzer
                    SalesDataAnalyzer.get_instance().load_data()
                except:
                    pass
                st.rerun()

        st.markdown("<hr style='margin:6px 0; border:none; border-top:1px dashed #33302f;'>", unsafe_allow_html=True)
        st.caption("🚗 엔카 정밀 스캔")
        c_sc1, c_sc2, c_sc3 = st.columns([2.5, 1, 1])
        with c_sc1:
            scan_url = st.text_input("엔카 정밀 스캔 URL:", key=f"scan_url_{st.session_state.form_reset_key}", label_visibility="collapsed", placeholder="엔카 URL 붙여넣기")
        with c_sc2:
            if st.button("🚀 스캔", use_container_width=True, key="top_scan_btn"):
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
        with c_sc3:
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
                st.warning(f"⚠️ 조회실패: {failed_count}대")
                if st.button("♻️ 실패 재스캔", use_container_width=True, key="top_rescan_failed_btn"):
                    p_bar, s_text = st.progress(0), st.empty()
                    failed_indices = st.session_state.scan_data[failed_mask].index
                    Scraper.rescan(failed_indices, "", p_bar, s_text)
                    st.rerun()

with h_col3:
    nav_options = [
        "📊 시세 분석 및 스캔", 
        "📋 매입 장부 관리", 
        "💰 재고 및 정산 관리", 
        "🎉 판매완료 정산 내역", 
        "📈 자사 판매 실적", 
        "📦 자사 보유 재고"
    ]
    if st.session_state.get('nav_target') in nav_options:
        st.session_state['nav_selection'] = st.session_state.pop('nav_target')

    if 'nav_selection' not in st.session_state or st.session_state['nav_selection'] not in nav_options:
        st.session_state['nav_selection'] = "📊 시세 분석 및 스캔"

    # 1. 위젯 키 사전 초기화 및 외부 변경 시 상태 동기화 (KeyError 원천 차단)
    if 'nav_selection_box' not in st.session_state or st.session_state['nav_selection_box'] != st.session_state['nav_selection']:
        st.session_state['nav_selection_box'] = st.session_state['nav_selection']
        
    nav_idx = nav_options.index(st.session_state['nav_selection'])
    
    # 2. get() 메서드로 안전하게 참조
    def _on_nav_change():
        new_val = st.session_state.get('nav_selection_box')
        if new_val:
            st.session_state['nav_selection'] = new_val
        
    nav_selection = st.selectbox(
        "화면 이동",
        nav_options,
        index=nav_idx,
        key="nav_selection_box",
        on_change=_on_nav_change,
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
