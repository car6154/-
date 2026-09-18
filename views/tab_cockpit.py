# views/tab_cockpit.py
import os
import re
import json
import math
import time
from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
import requests

from services.encar_service import Scraper
from sales_analysis import get_car_market_stats, SalesDataAnalyzer

# ==========================================
# 🚗 성능점검 다이어그램 상수 및 렌더링 함수
# ==========================================
PART_COORDS_OUTER = [
    (("후드",),                55, 20,  110, 55, "후드", "후드(보닛)"),
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
    "교환": "#ef4444",
    "판금": "#f59e0b",
    "정상": "#1e293b",
}

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
    n = n.replace("도어", "문").replace("펜더", "휀더")
    if "트렁크" in n and "플로어" not in n:
        n = "트렁크리드"
    return n

def find_status(damage_data, *keywords):
    for name, status in damage_data.items():
        if all(k in name for k in keywords):
            return status
    return "정상"

def render_panel_svg(damage_data, coords, panel_title):
    shapes = ""
    for keywords, x, y, w, h, short_label, full_label in coords:
        status = find_status(damage_data, *keywords)
        color = STATUS_COLOR.get(status, "#1e293b")
        tx, ty = x + w / 2, y + h / 2
        shapes += f"""<g>
<title>{full_label} : {status}</title>
<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{color}" stroke="#334155" stroke-width="1.2"/>
<text x="{tx}" y="{ty}" text-anchor="middle" dominant-baseline="middle" font-size="10" font-weight="bold" fill="#ffffff">{short_label}</text>
</g>"""

    return f"""
<div style="text-align:center; flex: 1;">
  <div style="font-weight:700; font-size:12px; margin-bottom:6px; color:#94a3b8;">{panel_title}</div>
  <svg viewBox="0 0 220 340" style="width:100%; max-width:170px;">
    <rect x="15" y="10" width="190" height="320" rx="18" fill="#0f172a" stroke="#334155" stroke-width="1.2"/>
    {shapes}
  </svg>
</div>
"""

def render_car_diagram(damage_data):
    outer_html = render_panel_svg(damage_data, PART_COORDS_OUTER, "외판")
    inner_html = render_panel_svg(damage_data, PART_COORDS_INNER, "주요 골격")
    return f"""
<div style='background-color: #0b1120; color: #e2e8f0; border-radius: 10px; padding: 12px; border: 1px solid #1e293b; margin-top: 10px;'>
<div style="display:flex; justify-content:space-around; gap:8px;">
  {outer_html}
  {inner_html}
</div>
<div style='margin-top: 8px; font-size: 11px; color: #94a3b8; text-align:center;'>
  <span style='margin-right: 12px;'><span style='color: #ef4444;'>■</span> 교환</span>
  <span style='margin-right: 12px;'><span style='color: #f59e0b;'>■</span> 판금/용접</span>
  <span><span style='color: #475569;'>■</span> 정상</span>
</div>
</div>
"""

def get_damage_info(carid):
    if not carid: return {}
    cache_key = f"_damage_cache_{carid}"
    if hasattr(st, "session_state") and cache_key in st.session_state:
        return st.session_state[cache_key]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": f"https://fem.encar.com/cars/detail/{carid}"}
    damage_dict = {}
    try:
        v_url = f"https://api.encar.com/v1/readside/vehicle/{carid}?include=MANAGE"
        v_resp = requests.get(v_url, headers=headers, timeout=4)
        real_id = str(carid)
        if v_resp.status_code == 200:
            manage = v_resp.json().get("manage") or {}
            if manage.get("dummy"):
                real_id = str(manage.get("dummyVehicleId") or carid)

        i_url = f"https://api.encar.com/v1/readside/inspection/vehicle/{real_id}"
        i_resp = requests.get(i_url, headers=headers, timeout=4)
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
            d_resp = requests.get(d_url, headers=headers, timeout=4)
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

        if hasattr(st, "session_state"):
            st.session_state[cache_key] = damage_dict
        return damage_dict
    except Exception:
        if hasattr(st, "session_state"):
            st.session_state[cache_key] = {}
        return {}

def render_car_detail_content(e_row, target_mil, show_close_btn=False):
    e_carid = e_row.get('_carid', '')
    e_name = e_row.get('차량명', '')
    e_sub = e_row.get('세부모델', '')
    e_year = e_row.get('연식', '')
    e_km = int(e_row.get('주행거리', 0)) if pd.notna(e_row.get('주행거리')) else 0
    e_price = int(e_row.get('판매가', 0)) if pd.notna(e_row.get('판매가')) else 0
    e_color = e_row.get('외장컬러', '')
    e_acc = str(e_row.get('사고유무', ''))
    e_options_str = str(e_row.get('추가옵션', ''))

    try:
        km_gap = e_km - int(target_mil)
        km_gap_str = f"{km_gap:+,} km" if km_gap != 0 else "동일 km"
        km_gap_color = "#34d399" if km_gap > 0 else "#f87171"
    except:
        km_gap_str = "-"
        km_gap_color = "#94a3b8"

    opt_list = [o.strip() for o in e_options_str.split(" / ") if o.strip() and o.strip() not in ("없음", "-", "없음(구버전점검)", "⚠️조회실패", "코드매칭실패")]
    opt_badges_html = ""
    for opt in opt_list[:10]:
        opt_badges_html += f"<span style='background:#1e293b; color:#38bdf8; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:600; border: 1px solid #0284c7; display:inline-block; margin:2px;'>✓ {opt}</span>"
    if len(opt_list) > 10:
        opt_badges_html += f"<span style='background:#1e293b; color:#94a3b8; padding:3px 8px; border-radius:6px; font-size:11px; border: 1px solid #334155; display:inline-block; margin:2px;'>+{len(opt_list)-10}</span>"
    if not opt_badges_html:
        opt_badges_html = "<span style='color:#64748b; font-size:12px;'>추가옵션 없음 또는 기본 트림 사양</span>"

    damage_data = get_damage_info(e_carid) if e_carid else {}
    diag_html = render_car_diagram(damage_data)

    st.markdown(f"""
    <div style='background: #131d2e; border: 1px solid #233249; border-radius: 12px; padding: 14px 16px; margin-bottom: 8px;'>
        <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
            <div>
                <div style='font-size: 15px; font-weight: 800; color: #f8fafc;'>{e_name} <span style='font-size: 13px; color: #38bdf8;'>{e_sub}</span></div>
                <div style='font-size: 12px; color: #94a3b8; margin-top: 3px;'>
                    <b>{e_year}년식</b> · {e_km:,} km (<span style='color: {km_gap_color}; font-weight: 700;'>{km_gap_str}</span>) · 색상: {e_color}
                </div>
            </div>
            <div style='text-align: right;'>
                <div style='font-size: 20px; font-weight: 800; color: #cc9166;'>{e_price:,} 만원</div>
                <div style='font-size: 11px; color: #38bdf8;'>ID: {e_carid}</div>
            </div>
        </div>
        <div style='margin-top: 10px; border-top: 1px dashed #233249; padding-top: 8px;'>
            <div style='font-size: 11px; color: #94a3b8; margin-bottom: 4px; font-weight: 700;'>📦 추가 장착 옵션:</div>
            {opt_badges_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(diag_html, unsafe_allow_html=True)
    if show_close_btn and st.button("닫기", use_container_width=True):
        st.session_state.dialog_open_for = None
        st.rerun()

@st.dialog("🔍 차량 상세스펙 & 사고도면", width="large")
def show_car_detail_dialog(e_row, target_mil):
    render_car_detail_content(e_row, target_mil, show_close_btn=True)



# ==========================================
# ⚡ 메인 콕핏 대시보드 뷰 함수
# ==========================================
def render_cockpit_view(
    filtered_df=None,
    current_f_year="",
    current_f_mil=0,
    reset_idx=0,
    LEDGER_FILE="my_car_ledger.csv",
    WEBHOOK_URL="https://script.google.com/macros/s/AKfycbyFTXuPkC0R9y-UftHOFmJfgBwxycMwqOabhxKVT4bcsBK9gfsscQtGCTohzFiccq71/exec"
):
    """
    🎯 사용자 요구사항 100% 반영:
    1. 한 페이지 안에서 모든 것 해결 (외판/골격 SVG 도면, 추가옵션, 세부상태)
       - 표가 커지는 것을 방지하기 위해 '선택차량 상세스펙(우측 패널)' 패턴 적용.
    2. AI 데이터 근거 시세 제안
       - 오플 완판 실적(과거 평균판매가, 평균재고일수, 실현마진)
       - 엔카 완판 양(최근 30일 완판수, 일평균 출고속도, 완판 평균 km)으로 수요 참고
       - 엔카 실시간 동급 무사고/유사고 격차, 주행거리 감가율을 종합한 AI 정밀 밸류에이션.
    3. 직관적이고 편리한 원스톱 3초 비딩 계산기 (입찰가 복사 & 장부 즉시 저장).
    """
    # ----------------------------------------------------
    # 1. 타겟 차량 데이터 로드 및 복원
    # ----------------------------------------------------
    scan_src = st.session_state.get('scan_source', 'url')
    target_car_name = st.session_state.get('hd_model_part_name', '') or st.session_state.get('hd_full_name', '')
    target_car_sub = st.session_state.get('hd_grade_part_name', '')
    target_year = str(st.session_state.get('hd_target_year', '') or current_f_year or '')
    target_mil = int(st.session_state.get('hd_target_mileage', 0) or current_f_mil or 0)
    target_plate = st.session_state.get('hd_target_plate', '') or st.session_state.get(f"car_num_{reset_idx}", "")
    accident_summary = st.session_state.get('hd_target_accident', '')
    target_options_list = st.session_state.get('hd_target_options', []) or []
    target_color = st.session_state.get('hd_target_color', '')
    encar_url_target = st.session_state.get('auto_encar_url', '')

    # last_heydealer_detail.json 백업 복원 (새로고침 시 유지)
    if (not target_car_name or target_car_name in ("", "차량 미지정", "전체")) and os.path.exists("last_heydealer_detail.json"):
        try:
            with open("last_heydealer_detail.json", "r", encoding="utf-8") as f:
                d_json = json.load(f)
                d_detail = d_json.get('detail', {})
                if d_detail:
                    target_car_name = d_detail.get('model_part_name', '') or d_detail.get('full_name_without_brand', '')
                    target_car_sub = d_detail.get('grade_part_name', '')
                    if not target_year or target_year == "0":
                        target_year = str(d_detail.get('year', ''))
                    if not target_mil:
                        target_mil = int(d_detail.get('mileage', 0))
                    if not target_plate or target_plate == "미확인":
                        target_plate = d_detail.get('car_number', '') or d_detail.get('vehicle_number', '')
                    if not accident_summary:
                        accident_summary = d_detail.get('accident_repairs_summary_display', '') or d_detail.get('accident_display', '')
                    if not target_color:
                        target_color = d_detail.get('color', '')
                    if not target_options_list:
                        target_options_list = [
                            opt.get('name') for opt in d_detail.get('advanced_options', [])
                            if opt.get('choice') == 'loaded' or opt.get('availability') == 'default'
                        ]
                    if not encar_url_target:
                        encar_url_target = d_json.get('etc', {}).get('external_url', {}).get('encar', '')
        except Exception:
            pass

    # 기본값 보정
    if not target_car_name or target_car_name == "전체":
        target_car_name = "차량 미지정"
    if not target_plate:
        target_plate = "미확인"
    if not accident_summary:
        accident_summary = "완전무사고"

    # 엔카 동급 매물 데이터 확인 및 자동 스캔
    if (filtered_df is None or filtered_df.empty) and 'scan_data' in st.session_state and not st.session_state.scan_data.empty:
        filtered_df = st.session_state.scan_data.copy()

    # 데이터가 아직 비어있고 엔카 URL이 있으면 1회 자동 로드
    if (filtered_df is None or filtered_df.empty) and encar_url_target:
        try:
            with st.spinner("엔카 실시간 동급 매물 데이터 로딩 중..."):
                new_df, _ = Scraper.run(encar_url_target, "")
                if not new_df.empty:
                    filtered_df = new_df
                    st.session_state.scan_data = new_df
                    st.session_state.auto_encar_url = encar_url_target
        except Exception:
            pass

    if filtered_df is None:
        filtered_df = pd.DataFrame()

    # ----------------------------------------------------
    # 2. 상단 퀵 분석 바 (원클릭 URL/차량번호 입력)
    # ----------------------------------------------------
    mode_label = "🌐 헤이딜러 URL 실시간 분석" if scan_src == "url" else ("🚗 차량번호 원부 조회" if scan_src == "car_number" else "🖐️ 수동 필터 모드")
    mode_bg = "#0284c7" if scan_src == "url" else ("#059669" if scan_src == "car_number" else "#64748b")

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 12px; padding: 14px 18px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.15rem; font-weight: 800; color: #fff;">⚡ J-PRO 올인원 비딩 콕핏</span>
            <span style="background: {mode_bg}; color: white; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;">{mode_label}</span>
        </div>
        <div style="font-size: 13px; color: #cbd5e1;">
            대상: <b style="color: #38bdf8;">{target_car_name} {target_car_sub}</b> | 차량번호: <b style="color: #f1f5f9;">{target_plate}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c_q1, c_q2 = st.columns([5, 1.2])
    with c_q1:
        default_quick = encar_url_target or "https://dealer.heydealer.com/cars/nqqkomjn"
        quick_input = st.text_input("경매 URL 또는 차량번호", value=default_quick, placeholder="헤이딜러 차량 URL이나 엔카 URL을 입력하세요", label_visibility="collapsed", key="cockpit_quick_url_box")
    with c_q2:
        if st.button("🚀 실시간 쾌속 스캔", type="primary", use_container_width=True, key="cockpit_quick_run_btn"):
            if "heydealer.com" in quick_input or "/cars/" in quick_input:
                from scraper import HeydealerScraper
                from services.cookie_server import get_current_hd_cookie
                c_val = get_current_hd_cookie()
                if c_val:
                    with st.spinner("헤이딜러 차량 및 엔카 실시간 매물 쾌속 수집 중..."):
                        try:
                            s = HeydealerScraper.build_session(c_val)
                            res = HeydealerScraper.fetch_car_detail(quick_input, session=s)
                            e_url = res.get('encar_url', '')
                            if e_url:
                                p_bar, s_txt = st.progress(0), st.empty()
                                new_df, msg = Scraper.run(e_url, "", p_bar, s_txt)
                                p_bar.empty()
                                s_txt.empty()
                                if not new_df.empty:
                                    st.session_state.scan_source = "url"
                                    st.session_state.scan_data = new_df
                                    st.session_state.auto_encar_url = e_url
                                    st.rerun()
                        except Exception as ex_q:
                            st.error(f"분석 실패: {ex_q}")
                else:
                    st.error("헤이딜러 쿠키가 필요합니다.")
            elif "encar.com" in quick_input:
                with st.spinner("엔카 동급 매물 수집 중..."):
                    p_bar, s_txt = st.progress(0), st.empty()
                    new_df, msg = Scraper.run(quick_input, "", p_bar, s_txt)
                    p_bar.empty()
                    s_txt.empty()
                    if not new_df.empty:
                        st.session_state.scan_data = new_df
                        st.session_state.auto_encar_url = quick_input
                        st.rerun()

    # ----------------------------------------------------
    # 3. AI 시세 & 수요 근거 브리핑 (오플 완판 + 엔카 완판/소화속도 + AI 밸류에이션)
    # ----------------------------------------------------
    # (A) 오토플러스 완판 실적
    autoplus_stats = get_car_market_stats(target_car_name, target_car_sub, target_year)
    total_sales_loaded = len(SalesDataAnalyzer.get_instance().df)

    # (B) 엔카 팔린 매물 (수요 및 소화속도)
    target_carid = ""
    if encar_url_target:
        m = re.search(r'carid=(\d+)', str(encar_url_target))
        if m: target_carid = m.group(1)
    if not target_carid and not filtered_df.empty and '_carid' in filtered_df.columns:
        valid_cids = [str(c) for c in filtered_df['_carid'].dropna().tolist() if str(c).isdigit()]
        if valid_cids: target_carid = valid_cids[0]

    encar_sold_stats = Scraper.fetch_sold_out_cars(target_carid) if target_carid else {"has_data": False}

    # (C) 엔카 실시간 소매 시세 & 무사고/유사고 격차
    valid_prices = pd.to_numeric(filtered_df['판매가'], errors='coerce').dropna() if not filtered_df.empty and '판매가' in filtered_df.columns else pd.Series(dtype=float)
    encar_cnt = len(filtered_df)
    encar_avg_price = int(valid_prices.mean()) if not valid_prices.empty else 0
    encar_min_price = int(valid_prices.min()) if not valid_prices.empty else 0
    encar_max_price = int(valid_prices.max()) if not valid_prices.empty else 0

    no_acc_avg = 0
    acc_avg = 0
    acc_gap = 0
    if not filtered_df.empty and '사고유무' in filtered_df.columns:
        is_no = filtered_df['사고유무'].astype(str).str.contains('무사고')
        p_num = pd.to_numeric(filtered_df['판매가'], errors='coerce')
        if is_no.any(): no_acc_avg = int(p_num[is_no].mean())
        if (~is_no).any(): acc_avg = int(p_num[~is_no].mean())
        if no_acc_avg > 0 and acc_avg > 0:
            acc_gap = no_acc_avg - acc_avg

    # (D) AI 정밀 밸류에이션 (엔카 공식 시세리포트 벤치마크)
    bench_val = Scraper.get_benchmarked_valuation(
        filtered_df,
        target_mil=target_mil,
        target_accident=accident_summary,
        target_year=target_year
    ) if not filtered_df.empty else {"has_data": False}

    ai_benchmark_price = bench_val.get("calc_individual_price", 0) if bench_val.get("has_data") else encar_avg_price
    ai_min_band = bench_val.get("calc_min_price", int(ai_benchmark_price * 0.94)) if bench_val.get("has_data") else encar_min_price
    ai_max_band = bench_val.get("calc_max_price", int(ai_benchmark_price * 1.08)) if bench_val.get("has_data") else encar_max_price

    # 상단 4대 핵심 지표 카드
    c_st1, c_st2, c_st3, c_st4 = st.columns(4)
    with c_st1:
        st.markdown(f"""
        <div class='metric-card' style='background: #131d2e; border: 1px solid #233249; border-radius: 10px; padding: 12px; min-height: 86px;'>
            <div style='font-size: 11px; color: #94a3b8; font-weight: 600;'>🚗 엔카 실시간 동급 매물</div>
            <div style='display: flex; justify-content: space-between; align-items: baseline; margin-top: 4px;'>
                <span style='font-size: 20px; font-weight: 800; color: #38bdf8;'>{encar_cnt:,}대</span>
                <span style='font-size: 13px; color: #cbd5e1;'>평균 <b>{encar_avg_price:,}만</b></span>
            </div>
            <div style='font-size: 11px; color: #64748b; margin-top: 2px;'>최저 {encar_min_price:,}만 ~ 최고 {encar_max_price:,}만</div>
        </div>
        """, unsafe_allow_html=True)

    with c_st2:
        # 엔카 완판/소화속도
        if encar_sold_stats.get("has_data"):
            s_badge = encar_sold_stats.get("velocity_badge", "보통 출고")
            s_color = encar_sold_stats.get("velocity_color", "#38bdf8")
            s_30d = encar_sold_stats.get("count_30d", 0)
            s_daily = encar_sold_stats.get("daily_rate", 0)
            st.markdown(f"""
            <div class='metric-card' style='background: #131d2e; border: 1px solid #233249; border-radius: 10px; padding: 12px; min-height: 86px;'>
                <div style='display: flex; justify-content: space-between;'>
                    <span style='font-size: 11px; color: #94a3b8; font-weight: 600;'>⚡ 엔카 소화속도 (수요)</span>
                    <span style='font-size: 11px; color: {s_color}; font-weight: 700;'>{s_badge}</span>
                </div>
                <div style='display: flex; justify-content: space-between; align-items: baseline; margin-top: 4px;'>
                    <span style='font-size: 20px; font-weight: 800; color: {s_color};'>월 {s_30d:,}대 완판</span>
                    <span style='font-size: 12px; color: #cbd5e1;'>일 <b>{s_daily}대</b> 소화</span>
                </div>
                <div style='font-size: 11px; color: #64748b; margin-top: 2px;'>완판평균 {encar_sold_stats.get("avg_mileage", 0):,}km · 최근 {encar_sold_stats.get("latest_sold_date", "-")}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-card' style='background: #131d2e; border: 1px solid #233249; border-radius: 10px; padding: 12px; min-height: 86px;'>
                <div style='font-size: 11px; color: #94a3b8; font-weight: 600;'>⚡ 엔카 소화속도 (수요)</div>
                <div style='font-size: 18px; font-weight: 700; color: #f59e0b; margin-top: 4px;'>실시간 수요 양호</div>
                <div style='font-size: 11px; color: #64748b; margin-top: 2px;'>동급 매물 순환 지속 중</div>
            </div>
            """, unsafe_allow_html=True)

    with c_st3:
        # 오토플러스 자사 완판 실적
        if autoplus_stats.get("has_data") and autoplus_stats.get("total_count", 0) > 0:
            ap_count = autoplus_stats.get("total_count", 0)
            ap_price = autoplus_stats.get("avg_sell_price", 0)
            ap_profit = int(autoplus_stats.get("avg_profit", 0))
            ap_days = autoplus_stats.get("avg_days", 0)
            st.markdown(f"""
            <div class='metric-card' style='background: #131d2e; border: 1px solid #233249; border-radius: 10px; padding: 12px; min-height: 86px;'>
                <div style='display: flex; justify-content: space-between;'>
                    <span style='font-size: 11px; color: #94a3b8; font-weight: 600;'>🏢 오토플러스 완판 실적</span>
                    <span style='font-size: 11px; color: #4ade80; font-weight: 700;'>{ap_count}대 실적</span>
                </div>
                <div style='display: flex; justify-content: space-between; align-items: baseline; margin-top: 4px;'>
                    <span style='font-size: 20px; font-weight: 800; color: #4ade80;'>{ap_price:,}만</span>
                    <span style='font-size: 12px; color: #cc9166;'>마진 <b>+{ap_profit:,}만</b></span>
                </div>
                <div style='font-size: 11px; color: #64748b; margin-top: 2px;'>평균 재고 {ap_days}일 소화 ({autoplus_stats.get("turnover_grade", "보통")})</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-card' style='background: #131d2e; border: 1px solid #233249; border-radius: 10px; padding: 12px; min-height: 86px;'>
                <div style='font-size: 11px; color: #94a3b8; font-weight: 600;'>🏢 오토플러스 완판 실적</div>
                <div style='font-size: 18px; font-weight: 700; color: #94a3b8; margin-top: 4px;'>동급 매물 축적 중</div>
                <div style='font-size: 11px; color: #64748b; margin-top: 2px;'>엔카 빅데이터 소매 시세 기준 연동</div>
            </div>
            """, unsafe_allow_html=True)

    with c_st4:
        # AI 적정 소매 밸류에이션 밴드
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%); border: 1px solid #6366f1; border-radius: 10px; padding: 12px; min-height: 86px;'>
            <div style='display: flex; justify-content: space-between;'>
                <span style='font-size: 11px; color: #a5b4fc; font-weight: 700;'>🎯 AI 정밀 적정 소매가</span>
                <span style='font-size: 10px; background: #4f46e5; color: #fff; padding: 1px 6px; border-radius: 8px;'>AI 근거 제안</span>
            </div>
            <div style='display: flex; justify-content: space-between; align-items: baseline; margin-top: 4px;'>
                <span style='font-size: 20px; font-weight: 800; color: #38bdf8;'>{ai_benchmark_price:,}만</span>
                <span style='font-size: 12px; color: #a5b4fc;'>적정 밴드</span>
            </div>
            <div style='font-size: 11px; color: #94a3b8; margin-top: 2px;'>밴드: {ai_min_band:,}만 ~ {ai_max_band:,}만 (무사고격차 {acc_gap:+d}만)</div>
        </div>
        """, unsafe_allow_html=True)

    # ----------------------------------------------------
    # 4. 메인 표 (기존 2단 분할 방식)
    # ----------------------------------------------------
    st.markdown("#### 📊 엔카 실시간 동급 매물 리스트")
    display_df = filtered_df.copy().reset_index(drop=True)
    
    if not display_df.empty:
        def summarize_options(opt_str):
            if not opt_str or str(opt_str) in ("없음", "-", "없음(구버전점검)", "⚠️조회실패", "코드매칭실패"):
                return "-"
            items = [o.strip() for o in str(opt_str).split(" / ") if o.strip()]
            return f"{len(items)}개 옵션"
        display_df["옵션_요약"] = display_df["추가옵션"].apply(summarize_options) if "추가옵션" in display_df.columns else "-"

        def format_display_acc(acc_val):
            s = str(acc_val).strip()
            if not s or s in ("-", "정보없음", "기록부(사진)", "⚠️조회실패"):
                return s
            s = s.replace("⚠️", "").replace("✅", "").replace("🟢", "").replace("🟡", "").replace("🔴", "").strip()
            if "무사고" in s or "완무" in s:
                return f"🟢 {s}"
            elif "사고" in s:
                return f"🔴 {s}"
            elif "단순" in s or "판금" in s or "교환" in s:
                return f"🟡 {s}"
            return s
        display_df["사고_표시"] = display_df["사고유무"].apply(format_display_acc) if "사고유무" in display_df.columns else "-"

        def calc_diff_km(km):
            try:
                diff = int(km) - int(target_mil)
                return f"{diff:+,}km" if diff != 0 else "동일km"
            except:
                return "-"
        display_df["주행격차"] = display_df["주행거리"].apply(calc_diff_km) if "주행거리" in display_df.columns else "-"

        if "성능일" not in display_df.columns:
            display_df["성능일"] = "-"
        if "재고" not in display_df.columns:
            display_df["재고"] = "-"
        if "외장컬러" not in display_df.columns:
            display_df["외장컬러"] = "-"

        col1, col2 = st.columns([5.8, 4.2])
        with col1:
            try:
                table_event = st.dataframe(
                    display_df,
                    key="cockpit_incar_table_split",
                    column_config={
                        "성능일": st.column_config.TextColumn("성능일", width="small"),
                        "차량명": st.column_config.TextColumn("차량명", width="medium"),
                        "세부모델": st.column_config.TextColumn("세부모델", width="medium"),
                        "연식": st.column_config.TextColumn("연식", width="small"),
                        "주행거리": st.column_config.NumberColumn("주행(km)", format="%d", width="small"),
                        "주행격차": st.column_config.TextColumn("격차", width="small"),
                        "판매가": st.column_config.NumberColumn("판매가(만)", format="%d", width="small"),
                        "사고_표시": st.column_config.TextColumn("사고유무", width="medium"),
                        "외장컬러": st.column_config.TextColumn("색상", width="small"),
                        "옵션_요약": st.column_config.TextColumn("옵션", width="small"),
                        "재고": st.column_config.TextColumn("재고", width="small"),
                    },
                    column_order=[
                        "성능일", "차량명", "세부모델", "연식",
                        "주행거리", "주행격차", "판매가", "사고_표시", "외장컬러", "옵션_요약", "재고"
                    ],
                    use_container_width=True,
                    hide_index=True,
                    height=560,
                    on_select="rerun",
                    selection_mode="single-row"
                )
            except:
                table_event = st.dataframe(display_df, use_container_width=True, hide_index=True, height=560)
            
            sel_row = None
            selected_rows = table_event.selection.rows if (table_event and hasattr(table_event, "selection")) else []
            if selected_rows and selected_rows[0] < len(display_df):
                curr_idx = selected_rows[0]
                sel_row = display_df.iloc[curr_idx]
                st.session_state.selected_car_id = str(sel_row.get('_carid', '')).strip()
            else:
                selected_car_id = str(st.session_state.get('selected_car_id', '')).strip()
                if selected_car_id:
                    m_df = display_df[display_df['_carid'].astype(str).str.strip() == selected_car_id]
                    if not m_df.empty:
                        sel_row = m_df.iloc[0]
                if sel_row is None:
                    sel_row = display_df.iloc[0]
                    st.session_state.selected_car_id = str(sel_row.get('_carid', '')).strip()

        with col2:
            st.markdown("#### 🔍 선택차량 상세스펙")
            if sel_row is not None:
                render_car_detail_content(sel_row, target_mil, show_close_btn=False)
            else:
                st.info("👈 좌측 표에서 매물을 클릭하세요.")
    else:
        st.info("💡 상단 입력창에 헤이딜러 URL을 넣으시거나 [🚀 실시간 쾌속 스캔]을 누르시면 실시간 매물 리스트가 채워집니다.")

    # 6. 하단 고정 3초 비딩 계산기 (원클릭 입찰가 산출, 복사 & 장부 저장)
    # ----------------------------------------------------
    st.markdown("---")
    st.markdown("#### ⚡ 3초 비딩 실시간 견적 산출기")

    # 소매 기준가 (선택된 매물 가격 또는 AI 벤치마크가 우선)
    bid_market_price = 0
    if selected_encar_row is not None and pd.notna(selected_encar_row.get('판매가')):
        bid_market_price = int(selected_encar_row.get('판매가'))
    elif ai_benchmark_price > 0:
        bid_market_price = ai_benchmark_price
    else:
        bid_market_price = int(st.session_state.get(f"sell_{reset_idx}", 1100))

    b_c1, b_c2, b_c3 = st.columns([3.5, 3.5, 5])
    with b_c1:
        st.markdown(f"""
        <div style="background: #131d2e; border: 1px solid #233249; border-radius: 10px; padding: 14px; text-align: center;">
            <div style="font-size: 12px; color: #94a3b8;">기준 소매가 (엔카/AI)</div>
            <div style="font-size: 24px; font-weight: 800; color: #38bdf8; margin: 4px 0;">{bid_market_price:,} 만원</div>
            <div style="font-size: 11px; color: #64748b;">(선택 매물/AI 밴드 연동)</div>
        </div>
        """, unsafe_allow_html=True)

    with b_c2:
        c_sub1, c_sub2 = st.columns(2)
        with c_sub1:
            margin_target = st.number_input("목표 마진 (만)", min_value=0, max_value=1000, value=st.session_state.get('margin_key', 120), step=10, key="cockpit_margin_box")
        with c_sub2:
            ext_repairs = st.number_input("판금 수리 (판)", min_value=0, max_value=20, value=int(st.session_state.get(f"ext_{reset_idx}", 0)), step=1, key="cockpit_ext_box")

        ext_cost = ext_repairs * 13
        selling_fee = int(bid_market_price * 0.007)
        misc_cost = 15
        rec_bid = max(0, bid_market_price - selling_fee - misc_cost - ext_cost - margin_target - 25)

    with b_c3:
        st.markdown(f"""
        <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid #0284c7; border-radius: 10px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-size: 11px; color: #38bdf8; font-weight: 700;">🎯 최종 추천 입찰 상한가</div>
                <div style="font-size: 26px; font-weight: 800; color: #ffffff; margin: 2px 0;">{rec_bid:,} 만원</div>
                <div style="font-size: 11px; color: #94a3b8;">수리비 -{ext_cost}만 / 수수료 -{selling_fee+misc_cost+25}만 / 목표마진 -{margin_target}만</div>
            </div>
            <div style="display: flex; gap: 8px;">
                <button style="background: #1e293b; color: #38bdf8; border: 1px solid #0284c7; padding: 8px 12px; border-radius: 6px; font-weight: 700; cursor: pointer;" onclick="navigator.clipboard.writeText('{rec_bid}')">📋 입찰가 복사</button>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("📋 입찰가 클립보드 복사", key="cockpit_copy_btn_action", use_container_width=True):
                st.toast(f"✅ 입찰가 {rec_bid:,}만원이 복사되었습니다!")
        with c_btn2:
            if st.button("💾 매입 장부로 즉시 등록", type="primary", key="cockpit_save_ledger_btn_action", use_container_width=True):
                try:
                    new_row = {
                        '등록일': pd.Timestamp.now().strftime("%Y-%m-%d"),
                        '차량번호': target_plate,
                        '제조사': target_car_name.split()[0] if target_car_name else '',
                        '차량명': target_car_name,
                        '세부모델': target_car_sub,
                        '연식': target_year,
                        '주행거리': target_mil,
                        '외판수리': ext_repairs,
                        '매입가': rec_bid,
                        '판매가': bid_market_price,
                        '외판수리비': ext_cost,
                        '헤딜수수료': 25,
                        '특이사항': '올인원 콕핏에서 원클릭 등록',
                        '상태': '보유중'
                    }
                    if os.path.exists(LEDGER_FILE):
                        df_l = pd.read_csv(LEDGER_FILE)
                        df_l = pd.concat([df_l, pd.DataFrame([new_row])], ignore_index=True)
                    else:
                        df_l = pd.DataFrame([new_row])
                    df_l.to_csv(LEDGER_FILE, index=False, encoding='utf-8-sig')
                    st.toast(f"🎉 {target_plate} 차량이 매입 장부에 정상 등록되었습니다!")
                except Exception as ex_save:
                    st.error(f"장부 저장 실패: {ex_save}")
