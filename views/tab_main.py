# views/tab_main.py
import os
import re
import json
import math
from datetime import datetime
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from sales_analysis import get_car_market_stats, generate_encar_market_url, SalesDataAnalyzer, is_target_option_matched, get_current_target_options
from services.encar_service import Scraper
from services.chaolma_service import ChaolmaService
from services.option_package_service import build_option_tooltip
from views.components.chaolma_card import render_chaolma_section, render_chaolma_card_ui

def render_main_tab(
    filtered_df=None,
    current_f_year="",
    current_f_mil=0,
    reset_idx=0,
    route_options=None,
    LEDGER_FILE="my_car_ledger.csv",
    WEBHOOK_URL="https://script.google.com/macros/s/AKfycbyFTXuPkC0R9y-UftHOFmJfgBwxycMwqOabhxKVT4bcsBK9gfsscQtGCTohzFiccq71/exec"
):
    if filtered_df is None:
        filtered_df = st.session_state.get('scan_data', pd.DataFrame()).copy()
    if route_options is None:
        route_options = ["헤이딜러", "엔카", "K-Car", "경매장", "지인/직거래", "기타"]

        # 사이드바 입력값 및 세션 상태 동기화 변수
        reset_idx = st.session_state.form_reset_key
        l_car_num = st.session_state.get(f"car_num_{reset_idx}", "").replace(" ", "").strip()
        l_mil = int(st.session_state.get(f"mil_{reset_idx}", st.session_state.get('user_target_mil', 0)))


        # ==========================================
        # 📊 [TOP] J-PRO 빅데이터 실적 분석 (회전율·마진·수요) - 최상단 배치
        # ==========================================
        hd_df = st.session_state.get('hd_comp_df', pd.DataFrame())

        # 대상 차량 및 세부모델 지능형 추출 (모드별 완벽 분리: URL 스캔 vs 차량번호 조회 vs 수동 필터)
        scan_src = st.session_state.get('scan_source', '')
        bd_target_car = ""
        bd_target_sub = ""

        if scan_src == "url":
            # 🌐 URL 스캔 모드: 헤이딜러 정보 1순위 (엔카 스캔 매물과 동기화)
            hd_model_sess = st.session_state.get('hd_model_part_name', '')
            hd_grade_sess = st.session_state.get('hd_grade_part_name', '')
            hd_full_sess = st.session_state.get('hd_full_name', '')
            if hd_model_sess:
                bd_target_car = hd_model_sess
                bd_target_sub = hd_grade_sess
            elif hd_full_sess:
                bd_target_car = hd_full_sess
                bd_target_sub = hd_grade_sess
            elif st.session_state.get('f_name') != "전체" and st.session_state.get('f_name'):
                bd_target_car = st.session_state.f_name
                bd_target_sub = st.session_state.f_sub if st.session_state.get('f_sub') != "전체" else ""
            elif 'scan_data' in st.session_state and not st.session_state.scan_data.empty and '차량명' in st.session_state.scan_data.columns:
                bd_target_car = str(st.session_state.scan_data['차량명'].iloc[0])
                bd_target_sub = str(st.session_state.scan_data['세부모델'].iloc[0]) if '세부모델' in st.session_state.scan_data.columns else ""
        elif scan_src == "car_number":
            # 🚗 차량번호 조회 모드: 차올마 정보 1순위
            last_c = st.session_state.get('last_chaolma_data', {})
            if last_c and last_c.get('success'):
                bd_target_car = last_c.get('model_name', '')
                c_sub_sess = st.session_state.get('f_sub', '')
                if c_sub_sess and c_sub_sess != "전체":
                    bd_target_sub = c_sub_sess
                else:
                    g = last_c.get('grade_name', '')
                    t = last_c.get('trim_name', '')
                    bd_target_sub = f"{g} {t}".strip() if (g and t and g not in t) else (t or g)
            if not bd_target_car and st.session_state.get('f_name') != "전체" and st.session_state.get('f_name'):
                bd_target_car = st.session_state.f_name
                bd_target_sub = st.session_state.f_sub if st.session_state.get('f_sub') != "전체" else ""
        else:
            # 🖐️ 수동 필터 선택 모드
            if st.session_state.get('f_name') != "전체" and st.session_state.get('f_name'):
                bd_target_car = st.session_state.f_name
                bd_target_sub = st.session_state.f_sub if st.session_state.get('f_sub') != "전체" else ""
            elif st.session_state.get('hd_model_part_name'):
                # 헤이딜러 세션에 저장된 차량명이 있으면 사용 (URL 스캔 후 탭 전환 시)
                bd_target_car = st.session_state.get('hd_model_part_name', '')
                bd_target_sub = st.session_state.get('hd_grade_part_name', '')
            elif not filtered_df.empty and '차량명' in filtered_df.columns:
                bd_target_car = str(filtered_df['차량명'].iloc[0])
                bd_target_sub = str(filtered_df['세부모델'].iloc[0]) if '세부모델' in filtered_df.columns else ""

        calc_year = current_f_year if current_f_year else str(st.session_state.get('f_year', '') or st.session_state.get('hd_target_year', ''))
        bd_stats = get_car_market_stats(bd_target_car, bd_target_sub, calc_year)

        # 🔍 엔카 팔린매물(soldoutCars) 데이터 연동
        target_carid = ""
        # 1. 헤이딜러 응답의 자동 엔카 URL에서 추출
        auto_url = st.session_state.get('auto_encar_url', '')
        if auto_url:
            m = re.search(r'carid=(\d+)', str(auto_url))
            if m: target_carid = m.group(1)

        # 2. 동급 필터링 매물(filtered_df) 1순위 추출 (GDe/LPe 등 세부등급 일치 매물)
        if not target_carid and not filtered_df.empty:
            if '_carid' in filtered_df.columns and filtered_df['_carid'].iloc[0]:
                target_carid = str(filtered_df['_carid'].iloc[0])
            elif '링크' in filtered_df.columns:
                m = re.search(r'carid=(\d+)', str(filtered_df['링크'].iloc[0]))
                if m: target_carid = m.group(1)

        # 3. 실시간 스캔 매물(scan_data)에서 타겟 세부모델과 유종 일치 매물 추출
        if not target_carid and 'scan_data' in st.session_state and not st.session_state.scan_data.empty:
            s_df = st.session_state.scan_data
            target_sub_clean = str(bd_target_sub).replace(' ', '').lower()
            matched_carid = None
            if target_sub_clean and '세부모델' in s_df.columns:
                # GDe, LPe, 디젤 등 유종 및 트림 일치 행 탐색
                for _, r in s_df.iterrows():
                    sm_clean = str(r['세부모델']).replace(' ', '').lower()
                    if ('gde' in target_sub_clean and 'gde' in sm_clean) or ('lpe' in target_sub_clean and 'lpe' in sm_clean):
                        cid = r.get('_carid')
                        if cid:
                            matched_carid = str(cid)
                            break
            if matched_carid:
                target_carid = matched_carid
            elif '_carid' in s_df.columns and s_df['_carid'].iloc[0]:
                target_carid = str(s_df['_carid'].iloc[0])
            elif '링크' in s_df.columns:
                m = re.search(r'carid=(\d+)', str(s_df['링크'].iloc[0]))
                if m: target_carid = m.group(1)

        # 3. 최근 조회된 carid fallback
        if not target_carid and st.session_state.get('target_carid'):
            target_carid = str(st.session_state.target_carid)

        sold_out_res = Scraper.fetch_sold_out_cars(target_carid) if target_carid else {"has_data": False}

        total_sales_loaded = len(SalesDataAnalyzer.get_instance().df)
        if bd_target_car and bd_stats.get('has_data'):
            tier_badge = f" <span style='background:rgba(204,145,102,0.12); border:1px solid #cc9166; color:#cc9166; padding:2px 8px; border-radius:12px; font-size:0.8em; font-weight:600;'>{bd_stats.get('matched_tier', '')}</span>" if bd_stats.get('matched_tier') else ""
            year_badge = f" <span style='background:rgba(239,68,68,0.15); border:1px solid #ef4444; color:#f87171; padding:2px 8px; border-radius:12px; font-size:0.8em; font-weight:700;'>⚠️ {bd_stats.get('year_diff_note')}</span>" if bd_stats.get('year_diff_note') else ""
            st.caption(f"💡 순수 내수 소매 완판 데이터 **{bd_stats.get('pure_sales_count', total_sales_loaded):,}건** 중 **[{bd_stats.get('matched_name', bd_target_car)}]** 실적({bd_stats.get('total_count', 0)}대) 분석 결과입니다.{tier_badge}{year_badge} (경매·도매 출고 {bd_stats.get('auction_filtered_count', 1339):,}건 왜곡 방지 자동 제외 완료)", unsafe_allow_html=True)

            c_m1, c_m2, c_m3, c_m4 = st.columns(4)
            with c_m1:
                st.markdown(f"""
                <div class='metric-card' style='min-height: 72px; height: 72px; display: flex; align-items: center; box-sizing: border-box;'>
                    <div class='metric-icon'>⏱️</div>
                    <div class='metric-content' style='overflow: hidden;'>
                        <h4 style='white-space: nowrap; text-overflow: ellipsis; overflow: hidden;'>소매 평균 재고일수</h4>
                        <h2 style='color: {bd_stats.get("turnover_color", "#4ade80")}; white-space: nowrap;'>{bd_stats.get("avg_days", 0)}일 <span style='font-size: 0.6em; color: #acafb9;'>({bd_stats.get("turnover_grade", "-")})</span></h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_m2:
                st.markdown(f"""
                <div class='metric-card' style='min-height: 72px; height: 72px; display: flex; align-items: center; box-sizing: border-box;'>
                    <div class='metric-icon'>🏷️</div>
                    <div class='metric-content' style='overflow: hidden;'>
                        <h4 style='white-space: nowrap; text-overflow: ellipsis; overflow: hidden;'>과거 평균 판매가</h4>
                        <h2 style='color: #e2e3e9; white-space: nowrap;'>{bd_stats.get("avg_sell_price", 0):,}만원</h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_m3:
                st.markdown(f"""
                <div class='metric-card' style='min-height: 72px; height: 72px; display: flex; align-items: center; box-sizing: border-box;'>
                    <div class='metric-icon'>🛣️</div>
                    <div class='metric-content' style='overflow: hidden;'>
                        <h4 style='white-space: nowrap; text-overflow: ellipsis; overflow: hidden;'>완판 평균 주행거리</h4>
                        <h2 style='color: #acafb9; white-space: nowrap;'>{bd_stats.get("avg_mileage", 0):,}km</h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_m4:
                st.markdown(f"""
                <div class='metric-card' style='min-height: 72px; height: 72px; display: flex; align-items: center; box-sizing: border-box;'>
                    <div class='metric-icon'>💰</div>
                    <div class='metric-content' style='overflow: hidden;'>
                        <h4 style='white-space: nowrap; text-overflow: ellipsis; overflow: hidden;'>과거 평균 실현마진</h4>
                        <h2 style='color: #cc9166; white-space: nowrap;'>+{int(bd_stats.get("avg_profit", 0)):,}만원 <span style='font-size: 0.6em; color: #acafb9;'>({bd_stats.get("profit_rate", 0)}%)</span></h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            sold_badge_html = ""
            sold_text_html = ""
            if sold_out_res.get("has_data"):
                sold_badge_html = f"<span style='font-size: 0.86em; background: rgba(255,255,255,0.06); padding: 3px 10px; border-radius: 12px; border: 1px solid #3b4252;'>엔카 완판: <b style='color: {sold_out_res.get('velocity_color', '#ef4444')};'>{sold_out_res.get('velocity_badge', '완판')}</b> <span style='color:#94a3b8;'>(최근30일 {sold_out_res.get('count_30d', 0)}대)</span></span>"
                sold_text_html = f"<div style='margin-top: 8px; font-size: 0.9em; color: #cbd5e1; border-top: 1px dashed #2e3038; padding-top: 6px;'>⚡ <b>엔카 실시간 소화 속도</b>: 최근 30일간 <b>{sold_out_res.get('count_30d', 0)}대</b> 완판 (일평균 <b>{sold_out_res.get('daily_rate', 0)}대</b> 출고 / 완판 평균 주행거리 <b>{sold_out_res.get('avg_mileage', 0):,}km</b> / 최근 완판: <b>{sold_out_res.get('latest_sold_date', '-')}</b>)</div>"

            briefing_box_html = (
                f"<div style='background-color: #121317; border: 1px solid #2e3038; border-radius: 10px; padding: 14px 18px; margin-top: 4px; margin-bottom: 12px;'>"
                f"<div style='display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;'>"
                f"<span style='color: #cc9166; font-weight: bold; font-size: 1.05em;'>💡 AI 비딩 전략 브리핑</span>"
                f"<div style='display: flex; align-items: center; gap: 8px; flex-wrap: wrap;'>"
                f"<span style='font-size: 0.86em; background: rgba(255,255,255,0.06); padding: 3px 10px; border-radius: 12px; border: 1px solid #2e3038;'>"
                f"수요도: <b>{bd_stats.get('demand_badge', '보통')}</b> <span style='color:#9194a1;'>({bd_stats.get('demand_level', '보통')})</span>"
                f"</span>"
                f"<span style='font-size: 0.86em; background: rgba(255,255,255,0.06); padding: 3px 10px; border-radius: 12px; border: 1px solid #2e3038;'>"
                f"자사 재고: <b style='color: {bd_stats.get('stock_color', '#cc9166')};'>{bd_stats.get('current_stock_count', 0)}대</b> <span style='color:#9194a1;'>({bd_stats.get('current_stock_desc', '미보유')})</span>"
                f"</span>"
                f"{sold_badge_html}"
                f"</div>"
                f"</div>"
                f"<div style='color: #e2e3e9; font-size: 0.95em; line-height: 1.55;'>"
                f"{bd_stats.get('turnover_desc', '')} 👉 <span style='color: #cc9166; font-weight: bold;'>{bd_stats.get('rec_strategy', '')}</span>"
                f"</div>"
                f"{sold_text_html}"
                f"</div>"
            )
            st.markdown(briefing_box_html, unsafe_allow_html=True)

            if sold_out_res.get("has_data") and sold_out_res.get("cars_sample"):
                with st.expander(f"📋 엔카 실시간 완판(팔린매물) 최근 실거래 리스트 (총 {sold_out_res.get('total_sold_count', 0):,}건 중 최근 10대)", expanded=False):
                    sample_df = pd.DataFrame(sold_out_res["cars_sample"])
                    if not sample_df.empty:
                        disp_df = pd.DataFrame()
                        disp_df['차량정보'] = sample_df['name'] if 'name' in sample_df.columns else ''
                        disp_df['연식'] = sample_df['year'] if 'year' in sample_df.columns else ''
                        
                        if 'km_num' in sample_df.columns:
                            disp_df['완판 주행거리'] = sample_df['km_num'].apply(lambda x: f"{int(x):,}km" if pd.notna(x) and str(x).isdigit() or isinstance(x, (int, float)) else str(x))
                        elif 'mileage' in sample_df.columns:
                            disp_df['완판 주행거리'] = sample_df['mileage'].apply(lambda x: str(x) if 'km' in str(x) else f"{x:,}km" if str(x).isdigit() else str(x))
                        else:
                            disp_df['완판 주행거리'] = '-'
                            
                        disp_df['판매일자'] = sample_df['sold_date'] if 'sold_date' in sample_df.columns else ''
                        st.dataframe(disp_df, use_container_width=True, hide_index=True)

            st.markdown("---")
        elif not bd_target_car:
            st.caption(f"💡 차량 조회 시 자사 순수 소매 완판 {total_sales_loaded:,}건 기반 회전율 및 보유 현황이 분석됩니다.")
            st.markdown("---")

        # ==========================================
        # 🚘 [1] 엔카 시세 요약본 (크기 2/3) + 요약 1번
        # ==========================================
        chart_base = filtered_df.copy()
        # 실시간 엔카 스캔 데이터(±1년 스마트밴드 포함: 20/21/22년 전 매물)를 온전히 표출

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
                <div class='metric-content'><h4>최저가</h4><h2 style='color: #acafb9;'>{encar_min_price:,} 만원 <span style='font-size: 0.6em'>⬇️</span></h2></div>
            </div>
            <div class='metric-card' style='flex: 1;'>
                <div class='metric-icon'>⬆️</div>
                <div class='metric-content'><h4>최고가</h4><h2 style='color: #e2e3e9;'>{encar_max_price:,} 만원 <span style='font-size: 0.6em'>⬆️</span></h2></div>
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

            # 타겟 연식 확인 (강조 및 중심 표시용)
            target_y_num = None
            q_year_str = str(current_f_year if 'current_f_year' in locals() and current_f_year else st.session_state.get('f_year', '') or st.session_state.get('hd_target_year', ''))
            m_ty = re.search(r'(\d{2,4})', q_year_str)
            if m_ty:
                ty_v = int(m_ty.group(1))
                target_y_num = ty_v % 100 if ty_v >= 1000 else ty_v

            # 연식별 평균 (정수 연도 단위 정규화 및 집계)
            if '연식' in chart_base.columns:
                def extract_reg_year(val):
                    m = re.search(r'(\d{2,4})', str(val))
                    if m:
                        v = int(m.group(1))
                        return v % 100 if v >= 1000 else v
                    return None

                norm_years = chart_base['연식'].apply(extract_reg_year)
                unique_years = sorted([int(y) for y in norm_years.dropna().unique()])
                
                # 연식이 5개 이상으로 너무 많을 때만 타겟 연식 중심 ±1~2년 필터링, 그 외에는 전 연식 표시
                if len(unique_years) > 4 and target_y_num:
                    display_years = [y for y in unique_years if abs(y - target_y_num) <= 1]
                    if not display_years:
                        display_years = unique_years[-3:]
                else:
                    display_years = unique_years

                y_parts = []
                for y in display_years:
                    sub_p = p_num[norm_years == y].dropna()
                    if not sub_p.empty:
                        avg_val = int(round(sub_p.mean()))
                        cnt = len(sub_p)
                        if target_y_num and y == target_y_num:
                            y_parts.append(f"<b style='color:#38bdf8;'>{y}년 {avg_val:,}만</b><span style='font-size:0.85em;color:#94a3b8;'>({cnt}대)</span>")
                        else:
                            y_parts.append(f"{y}년 {avg_val:,}만<span style='font-size:0.85em;color:#94a3b8;'>({cnt}대)</span>")
                if y_parts:
                    encar_year_stats = " / ".join(y_parts)

        # 🤖 AI 타겟 맞춤 소매가 자동 산출 (주행거리 추세선 기울기 + 옵션 차이 보정)
        ai_retail_price = 0
        ai_detail_desc = ""
        try:
            if not chart_base.empty:
                c_mil = pd.to_numeric(chart_base['주행거리'], errors='coerce').dropna()
                c_price = pd.to_numeric(chart_base['판매가'], errors='coerce').dropna()
                valid_idx = c_mil.index.intersection(c_price.index)

                # 1. 목표 주행거리: 세션 주입값(재고/헤이딜러) 또는 사이드바 l_mil 최우선
                explicit_mil = st.session_state.get('user_target_mil', 0)
                sidebar_mil = l_mil if ('l_mil' in locals() and l_mil > 0) else 0
                hd_mil_fallback = st.session_state.get('f_mil', 0)
                
                if explicit_mil > 0:
                    user_target_mil = explicit_mil
                elif sidebar_mil > 0:
                    user_target_mil = sidebar_mil
                elif hd_mil_fallback > 0:
                    user_target_mil = hd_mil_fallback
                else:
                    user_target_mil = int(c_mil.mean()) if not c_mil.empty else 0

                # 2. 기준 가격 (무사고 앵커 원칙)
                # 무사고 매물이 존재하면 무사고 매물의 평균 가격/주행거리를 기준점으로 삼고, 없으면 전체 평균 사용
                is_no_acc_series = chart_base['사고유무'].astype(str).str.contains('무사고') if '사고유무' in chart_base.columns else pd.Series(False, index=chart_base.index)
                no_acc_df = chart_base[is_no_acc_series] if is_no_acc_series.any() else chart_base

                no_acc_prices = pd.to_numeric(no_acc_df['판매가'], errors='coerce').dropna()
                no_acc_mils = pd.to_numeric(no_acc_df['주행거리'], errors='coerce').dropna()

                base_price = int(no_acc_prices.mean()) if not no_acc_prices.empty else (encar_avg_price if encar_avg_price > 0 else (int(c_price.mean()) if not c_price.empty else 0))
                base_mil = int(no_acc_mils.mean()) if not no_acc_mils.empty else (int(c_mil.loc[valid_idx].mean()) if len(valid_idx) > 0 else user_target_mil)

                # 3. 주행거리 감가 기울기 (무사고 매물 기준 회귀 분석 우선)
                slope = -0.005  # 기본값: 1만km당 약 50만원 감가
                reg_df = no_acc_df if len(no_acc_df) >= 3 else chart_base
                reg_mil = pd.to_numeric(reg_df['주행거리'], errors='coerce').dropna()
                reg_price = pd.to_numeric(reg_df['판매가'], errors='coerce').dropna()
                reg_idx = reg_mil.index.intersection(reg_price.index)

                if len(reg_idx) >= 2:
                    fit_z = np.polyfit(reg_mil.loc[reg_idx], reg_price.loc[reg_idx], 1)
                    if -0.02 <= fit_z[0] <= -0.001:
                        slope = fit_z[0]

                mil_diff = user_target_mil - base_mil
                mil_adj = int(round(mil_diff * slope))

                # 4. 대상 차량의 사고 상태 판별 및 사고 감가 계산
                # ★ 헤이딜러 긁어온 정보가 최우선 기준, 리스트 선택은 참고
                target_acc_status = ""
                hd_acc = st.session_state.get('hd_target_accident', '')

                if hd_acc:
                    # 헤이딜러 사고유무 최우선
                    target_acc_status = str(hd_acc)
                else:
                    # fallback: 리스트에서 선택한 차량 참조
                    active_selected = str(st.session_state.get('selected_car_id', '')).strip()
                    matched_sel = chart_base[chart_base['_carid'].astype(str).str.strip() == active_selected] if (active_selected and '_carid' in chart_base.columns) else pd.DataFrame()
                    if not matched_sel.empty and pd.notna(matched_sel.iloc[0].get('사고유무')):
                        target_acc_status = str(matched_sel.iloc[0].get('사고유무'))
                    else:
                        target_acc_status = "완전무사고"

                # 시장 무사고-유사고 실측 격차 (최소 50만 ~ 최대 180만 클리핑)
                market_gap = encar_acc_gap if encar_acc_gap > 0 else 80
                market_gap = max(40, min(market_gap, 180))

                acc_adj = 0
                acc_label = ""
                if "사고" in target_acc_status and "무사고" not in target_acc_status:
                    # 주요골격/유사고: 시장 무사고-유사고 격차 100% 감가
                    acc_adj = -int(round(market_gap))
                    acc_label = f"사고감가: {acc_adj:+}만"
                elif "단순" in target_acc_status or "교환" in target_acc_status or "판금" in target_acc_status:
                    # 단순교환/판금: 시장 격차의 40% 수준 경미 감가
                    acc_adj = -int(round(market_gap * 0.4))
                    acc_label = f"단순교환 감가: {acc_adj:+}만"
                else:
                    acc_adj = 0
                    acc_label = "완전무사고: 감가없음"

                # 5. 옵션 가치 차이 계산 (연식별 실 출고옵션가 감가율 80% / 50% / 35% / 20% 반영)
                def extract_option_val(opt_str):
                    if not opt_str or str(opt_str) in ("없음", "-", "없음(구버전점검)", "⚠️조회실패", "코드매칭실패"):
                        return 0
                    prices = re.findall(r'\((\d+)\s*만(?:원)?\)', str(opt_str))
                    return sum(int(p) for p in prices) if prices else 0

                KEY_OPT_WEIGHTS = {
                    '파노라마선루프': 90, '선루프': 70, 'HUD': 60, '헤드업': 60,
                    '어라운드뷰': 70, '서라운드뷰': 70, '모니터링': 60,
                    '드라이브와이즈': 80, '스마트센스': 80, '반자율': 70, 'ASCC': 70,
                    '통풍시트': 50, '전동트렁크': 40, '스마트테일게이트': 40,
                    '사운드': 40, '크렐': 40, '보스': 40, 'JBL': 40, '렉시콘': 40,
                    '컴포트': 70, '멀티미디어내비': 70, '내비게이션': 60, '내비': 60,
                    '익스테리어': 50, '스타일': 50, '플래티넘': 70, '빌트인캠': 40,
                    '시트패키지': 50, '파킹어시스트': 60
                }

                def score_key_options(opt_list_or_str):
                    text = " ".join(opt_list_or_str) if isinstance(opt_list_or_str, list) else str(opt_list_or_str)
                    matched_opts = []
                    score = 0
                    for k, w in KEY_OPT_WEIGHTS.items():
                        if k in text:
                            norm_k = '선루프' if '선루프' in k else ('HUD' if k in ('HUD', '헤드업') else ('어라운드뷰' if '라운드뷰' in k or '모니터링' in k else ('주행보조' if k in ('드라이브와이즈', '스마트센스', '반자율', 'ASCC') else ('내비' if '내비' in k or '멀티미디어' in k else k))))
                            if norm_k not in matched_opts:
                                matched_opts.append(norm_k)
                                score += w
                    return score, matched_opts

                # 차량 연식 확인 및 연식별 옵션 잔존가치 인정비율 산출
                target_year_val = None
                # 1순위: 파라미터 current_f_year ("21" or "2021")
                if current_f_year:
                    try:
                        m_y = re.search(r'(\d{2,4})', str(current_f_year))
                        if m_y:
                            v = int(m_y.group(1))
                            target_year_val = 2000 + v if v < 100 else v
                    except Exception:
                        pass

                # 2순위: 세션 상태 (헤이딜러 / 필터 연식)
                if not target_year_val:
                    hd_year_val = st.session_state.get('hd_target_year') or st.session_state.get('f_year')
                    if hd_year_val:
                        try:
                            m_y = re.search(r'(\d{2,4})', str(hd_year_val))
                            if m_y:
                                v = int(m_y.group(1))
                                target_year_val = 2000 + v if v < 100 else v
                        except Exception:
                            pass

                # 3순위: chart_base의 연식 칼럼에서 2자리 등록연도 최빈값 추출 (e.g. '21(21)' -> 2021)
                if not target_year_val and '연식' in chart_base.columns:
                    try:
                        extracted_years = chart_base['연식'].astype(str).str.extract(r'^\s*(\d{2})')[0].dropna().astype(int)
                        if not extracted_years.empty:
                            target_year_val = 2000 + int(extracted_years.mode().iloc[0] if not extracted_years.mode().empty else extracted_years.median())
                    except Exception:
                        pass
                if not target_year_val:
                    target_year_val = 2021
                curr_year = datetime.now().year
                car_age = max(0, curr_year - target_year_val)

                # 연식별 감가율: 0~1년차 80%, 2~3년차 50%, 4~5년차 35%, 6년차 이상 20%
                if car_age <= 1:
                    opt_ratio = 0.80
                    age_badge = f"{car_age}년차(신차급 80%)"
                elif car_age <= 3:
                    opt_ratio = 0.50
                    age_badge = f"{car_age}년차(보증내 50%)"
                elif car_age <= 5:
                    opt_ratio = 0.35
                    age_badge = f"{car_age}년차(일반 35%)"
                else:
                    opt_ratio = 0.20
                    age_badge = f"{car_age}년차(구형 20%)"

                # 무사고 매물군(no_acc_df)의 출고옵션 원가 평균 산출
                avg_opt_new = 0
                avg_opt_score = 0
                if '추가옵션' in no_acc_df.columns:
                    opt_vals = no_acc_df['추가옵션'].apply(extract_option_val)
                    avg_opt_new = int(opt_vals.mean()) if not opt_vals.empty else 0

                    scores = [score_key_options(str(x))[0] for x in no_acc_df['추가옵션'].dropna()]
                    avg_opt_score = int(np.mean(scores)) if scores else 0

                target_opt_names = []
                target_opt_new = 0
                target_score = avg_opt_score

                # 1순위: 차얼마2 실 출고 순정 옵션 원가 확인
                chaolma_key = f"chaolma_data_{l_car_num}" if 'l_car_num' in locals() and l_car_num else ""
                chaolma_info = st.session_state.get(chaolma_key) if chaolma_key else None
                if chaolma_info and chaolma_info.get("success") and chaolma_info.get("total_option_price", 0) > 0:
                    raw_c_opt = int(chaolma_info.get("total_option_price", 0))
                    # 차얼마 API의 옵션 원가는 원 단위(예: 2,600,000원)이므로 만원 단위(260)로 변환
                    target_opt_new = raw_c_opt // 10000 if raw_c_opt >= 10000 else raw_c_opt
                    target_opt_names = [o.get("name") for o in chaolma_info.get("options", []) if o.get("name")]
                else:
                    # 2순위: 헤이딜러 파싱 옵션가 확인
                    hd_parsed_opt_price = st.session_state.get('hd_target_opt_price', 0)
                    if hd_parsed_opt_price and hd_parsed_opt_price > 0:
                        raw_hd_opt = int(hd_parsed_opt_price)
                        target_opt_new = raw_hd_opt // 10000 if raw_hd_opt >= 10000 else raw_hd_opt

                # 헤이딜러 스펙 텍스트에서 옵션 가격 2차 정밀 파싱 (누락 방지)
                if target_opt_new == 0:
                    spec_desc_raw = st.session_state.get('hd_car_spec_desc', '')
                    if spec_desc_raw:
                        p_list = re.findall(r'\((\d+)\s*만(?:원)?\)', spec_desc_raw)
                        if p_list:
                            target_opt_new = sum(int(p) for p in p_list)

                # 헤이딜러/엔카 스캔 옵션 명칭 및 점수 산정
                hd_opts = st.session_state.get('hd_target_options', []) or []
                encar_opts = st.session_state.get('encar_target_options', []) or []
                all_target_opts = list(dict.fromkeys(hd_opts + encar_opts))

                if all_target_opts:
                    target_score, target_opt_names = score_key_options(all_target_opts)
                    if target_opt_new == 0:
                        # 엔카 등에서 옵션 가격이 문자열에 포함되어 있는 경우 추출
                        parsed_from_text = extract_option_val(" ".join(all_target_opts))
                        if parsed_from_text > 0:
                            target_opt_new = parsed_from_text
                        else:
                            # 가격 정보가 없는 경우 점수 및 옵션 갯수 기반 합리적 신차 원가 추정
                            target_opt_new = int(target_score * 1.5) if target_score > 0 else (len(all_target_opts) * 80)
                else:
                    # fallback: 리스트에서 선택한 차량의 옵션 참조
                    active_selected = str(st.session_state.get('selected_car_id', '')).strip()
                    matched_sel = chart_base[chart_base['_carid'].astype(str).str.strip() == active_selected] if (active_selected and '_carid' in chart_base.columns) else pd.DataFrame()
                    if not matched_sel.empty and pd.notna(matched_sel.iloc[0].get('추가옵션')):
                        sel_opt_str = str(matched_sel.iloc[0].get('추가옵션'))
                        target_opt_new = extract_option_val(sel_opt_str)
                        target_score, target_opt_names = score_key_options(sel_opt_str)

                # 옵션 가치 차액에 연식 감가율(opt_ratio) 적용
                if target_opt_new > 0:
                    if avg_opt_new > 0 and avg_opt_new != target_opt_new:
                        opt_adj = int(round((target_opt_new - avg_opt_new) * opt_ratio))
                    else:
                        opt_adj = int(round(target_opt_new * opt_ratio * 0.7))
                elif target_score != avg_opt_score and target_score > 0:
                    opt_adj = int(round((target_score - avg_opt_score) * opt_ratio))
                elif all_target_opts:
                    opt_adj = int(round(len(all_target_opts) * 70 * opt_ratio))
                else:
                    opt_adj = 0

                # 6. 최종 AI 추정 소매가 (무사고 앵커 기준 + 주행거리 + 사고 + 옵션)
                ai_retail_price = int(base_price + mil_adj + acc_adj + opt_adj)

                # 내역 설명 텍스트
                adj_parts = []
                if acc_adj != 0:
                    adj_parts.append(acc_label)
                elif "완전무사고" in target_acc_status:
                    adj_parts.append("완전무사고")

                if mil_adj != 0:
                    adj_parts.append(f"주행거리({user_target_mil:,}km): {mil_adj:+}만")
                if opt_adj != 0:
                    opt_label = f"옵션가치({age_badge} {opt_adj:+}만)"
                    adj_parts.append(opt_label)

                base_desc = f"무사고 평균 {base_price:,}만" if is_no_acc_series.any() else f"동급 평균 {base_price:,}만"
                ai_detail_desc = f" ({base_desc} 기준 " + ", ".join(adj_parts) + ")" if adj_parts else f" ({base_desc} 수준)"
        except Exception as e:
            ai_retail_price = encar_avg_price

        # 🎯 AI 빅데이터 정밀 밸류에이션 (기준가 & 적정 밴드 역산, 옵션가치 target_opt_adj 통합 반영)
        bench_val = Scraper.get_benchmarked_valuation(
            chart_base, 
            target_mil=user_target_mil, 
            target_accident=target_acc_status,
            target_year=target_year_val,
            target_opt_adj=opt_adj
        ) if not chart_base.empty else {"has_data": False}

        if bench_val.get("has_data"):
            b_ind = bench_val["calc_individual_price"]
            b_min = bench_val["calc_min_price"]
            b_max = bench_val["calc_max_price"]
            b_score = bench_val["calc_score"]
            bubble_gap = encar_avg_price - b_ind
            bubble_pct = round((bubble_gap / b_ind) * 100, 1) if b_ind > 0 else 0
            bubble_sign = "+" if bubble_gap > 0 else ""
            if abs(bubble_gap) <= 50:
                bubble_color = "#22c55e"
                bubble_desc = "시장 호가와 AI 적정 소매가가 안정적으로 일치함"
            elif bubble_gap > 50:
                bubble_color = "#f59e0b"
                bubble_desc = "시장 호가에 딜러 마진/거품 형성 중"
            else:
                bubble_color = "#38bdf8"
                bubble_desc = "시장 호가가 저렴하게 형성된 급매/경쟁 구간"
            safe_bid_limit = max(0, b_ind - 180)  # 기대마진 150만 + 부대비용 30만 기준

            # 옵션 가치 반영 내역 뱃지 생성
            opt_cnt = len(all_target_opts) if 'all_target_opts' in locals() and all_target_opts else 0
            if opt_adj > 0:
                opt_spec_html = f" / <b style='color: #38bdf8;'>추가옵션 {opt_cnt}개 (+{opt_adj:,}만 반영)</b>"
            elif opt_adj < 0:
                opt_spec_html = f" / <span style='color: #94a3b8;'>옵션 열세 ({opt_adj:,}만 반영)</span>"
            elif opt_cnt > 0:
                opt_spec_html = f" / 추가옵션 {opt_cnt}개 포함"
            else:
                opt_spec_html = " / 기본형 (추가옵션 없음)"

            ai_badge_html = f"<span style='background: #1e293b; color: #38bdf8; padding: 4px 12px; border-radius: 6px; font-weight: bold; font-size: 1.05em; border: 1px solid #0284c7;'>🎯 정밀 소매가: <span style='font-size: 1.2em; color: #ffffff;'>{b_ind:,}</span> 만원 <span style='font-size: 0.85em; color: #94a3b8;'>({b_min:,}~{b_max:,}만)</span></span>"

            summary_content = f"""<div class='summary-box'>
<div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2e3038; padding-bottom: 8px; margin-bottom: 10px;'>
    <b style='color: #cc9166; font-size: 1.1em;'>📋 실시간 소매 시세 & 빅데이터 밸류에이션</b>
    {ai_badge_html}
</div>
<div style='display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 10px;'>
    <div style='background: rgba(15, 23, 42, 0.65); padding: 12px 14px; border-radius: 6px; border-left: 3px solid #38bdf8;'>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
            <span style='color: #38bdf8; font-weight: bold; font-size: 0.95em;'>📊 AI 빅데이터 적정 시세</span>
            <span style='background: #0369a1; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold;'>가치지수 {b_score}점</span>
        </div>
        <div style='color: #f1f5f9; font-size: 0.9em; line-height: 1.6;'>
            • 적정 밴드: <b style='color: #38bdf8;'>{b_min:,} ~ {b_max:,}만 원</b> (기준: <b>{b_ind:,}만</b>)<br>
            • 평가 스펙: 주행 {user_target_mil:,}km / {target_acc_status if target_acc_status else '완전무사고'}{opt_spec_html}
        </div>
    </div>
    <div style='background: rgba(15, 23, 42, 0.65); padding: 12px 14px; border-radius: 6px; border-left: 3px solid #f59e0b;'>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
            <span style='color: #f59e0b; font-weight: bold; font-size: 0.95em;'>🏷️ 시장 판매 호가 현황 ({encar_total_count}대)</span>
            <span style='color: {bubble_color}; font-size: 0.8em; font-weight: bold;'>호가 괴리: {bubble_sign}{bubble_gap:,}만 ({bubble_sign}{bubble_pct}%)</span>
        </div>
        <div style='color: #f1f5f9; font-size: 0.9em; line-height: 1.6;'>
            • 시장 호가: 최저 <b>{encar_min_price:,}만</b> ~ 최고 <b>{encar_max_price:,}만</b> (평균 <b>{encar_avg_price:,}만</b>)<br>
            • {encar_year_stats if encar_year_stats else '연식별 데이터 집계 완료'}
        </div>
    </div>
</div>
<div style='color: #cbd5e1; font-size: 0.88em; line-height: 1.45; border-top: 1px dashed rgba(255,255,255,0.12); padding-top: 8px;'>
    💡 <b>AI 입찰 가이드:</b> 예상 소매가 <b>{b_ind:,}만 원</b>(적정상한 {b_max:,}만) 기준, 기대 마진(150만) 확보를 위해 <b>[안전 입찰 상한선: {safe_bid_limit:,}만 원 이하]</b> 매입을 권장합니다. ({bubble_desc})
</div>
</div>"""
        elif encar_total_count > 0:
            ai_badge_html = f"<span style='background: #1e293b; color: #38bdf8; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 1.05em; border: 1px solid #0284c7;'>🤖 AI 판단 소매가: <span style='font-size: 1.2em; color: #ffffff;'>{ai_retail_price:,}</span> 만원</span>" if ai_retail_price > 0 else ""
            summary_content = f"""<div class='summary-box'>
<div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2e3038; padding-bottom: 8px; margin-bottom: 8px;'>
    <b style='color: #cc9166; font-size: 1.1em;'>📋 실시간 소매 시세 & 빅데이터 밸류에이션</b>
    {ai_badge_html}
</div>
• <b>AI 소매가 산출 내역:</b> <b style='color: #38bdf8;'>{ai_retail_price:,}만원</b><span style='color: #94a3b8; font-size: 0.9em;'>{ai_detail_desc}</span><br>
• 동급 시장 평균: <b style='color: #fff;'>{encar_avg_price:,}만원</b> (무사고 <b>{encar_no_acc_avg:,}만원</b> / 유사고 <b>{encar_acc_avg:,}만원</b> - 사고감가 차이: {encar_acc_gap:,}만원)<br>
• {encar_year_stats if encar_year_stats else '연식별 데이터 집계 완료'}
</div>"""
        else:
            summary_content = """<div class='summary-box' style='border-left: 4px solid #f59e0b !important;'>
<div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2e3038; padding-bottom: 8px; margin-bottom: 8px;'>
    <b style='color: #cc9166; font-size: 1.1em;'>📋 실시간 소매 시세 & 빅데이터 밸류에이션</b>
    <span style='background: #33200a; color: #f59e0b; padding: 3px 10px; border-radius: 6px; font-weight: bold; font-size: 0.88em; border: 1px solid #78350f;'>⚠️ 동급 매물 없음 (0대)</span>
</div>
• <b>현재 조회된 엔카 조건의 실시간 동급 매물이 없습니다.</b><br>
• 엔카에서 해당 연식·세부모델의 등록 매물이 없거나 일시적으로 품절된 상태입니다. 좌측 [헤이딜러 동급 낙찰 데이터] 또는 [빅데이터 실적 분석]의 가이드를 참고하세요.
</div>"""

        st.markdown(summary_content, unsafe_allow_html=True)

        # ==========================================
        # 📊 [2] 엔카 시세 리스트 및 상세스펙
        # ==========================================
        if not filtered_df.empty:
            main_col1, main_col2 = st.columns([6.2, 3.8])

            with main_col1:
                st.markdown("#### 📊 엔카 시세 리스트")
                display_df = filtered_df.copy().reset_index(drop=True)

                def summarize_options(opt_str):
                    if not opt_str or opt_str in ("없음", "-", "없음(구버전점검)", "⚠️조회실패", "코드매칭실패"):
                        return opt_str
                    items = [o.strip() for o in str(opt_str).split(" / ") if o.strip()]
                    return f"{len(items)}개 옵션"

                display_df["추가옵션_요약"] = display_df["추가옵션"].apply(summarize_options)

                # 브라우저의 prefetch(사전 연결) 기능으로 인해 다량의 엔카 URL이 
                # 동시에 호출되어 봇으로 차단되는 현상을 방지하기 위해 
                # 표에서의 직접 링크 컬럼(차량명_링크)을 제거하고 일반 텍스트로 대체합니다.
                # 상세 보기 링크는 우측 상세 패널의 버튼을 통해 접근 가능합니다.

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

                # 1. 성능일 내림차순 ➔ 연식 내림차순 복합 정렬 (정렬을 먼저 수행해야 행 인덱스가 정확히 일치함)
                if not display_df.empty:
                    def _parse_sort_year(val):
                        # '연식(형식)' 표기에서 괄호 앞 순수 '연식' 추출 후 4자리 정규화
                        m = re.search(r'(\d+)', str(val))
                        if not m:
                            return 0
                        yr = int(m.group(1))
                        return yr + 2000 if yr < 100 else yr

                    display_df['_has_perf'] = display_df['성능일'].astype(str).apply(
                        lambda x: 1 if re.match(r'^\d{2}-\d{2}-\d{2}', str(x)) and str(x) not in ['미검사/사진', '⚠️미등록', '⚠️조회실패', '-'] else 0
                    )
                    display_df['_sort_perf'] = display_df['성능일'].astype(str).apply(
                        lambda x: x if re.match(r'^\d{2}-\d{2}-\d{2}', str(x)) and str(x) not in ['미검사/사진', '⚠️미등록', '⚠️조회실패', '-'] else '00-00-00'
                    )
                    display_df['_sort_year'] = display_df['연식'].apply(_parse_sort_year)

                    # 1순위: 성능점검 유무 (정상 점검 매물 우선, 미검사/사진 매물은 맨 뒤로 배치)
                    # 2순위: 연식 최신순 ➔ 3순위: 성능일 최신순
                    display_df = display_df.sort_values(
                        by=['_has_perf', '_sort_year', '_sort_perf'],
                        ascending=[False, False, False]
                    ).drop(columns=['_has_perf', '_sort_perf', '_sort_year']).reset_index(drop=True)

                # 산점도에서 선택된 차량이 있다면 표의 실제 체크박스(selection)에 1회 동기화
                curr_selected_id = str(st.session_state.get('selected_car_id', '')).strip()
                if curr_selected_id and '_carid' in display_df.columns and st.session_state.get('last_selected_source') == 'scatter':
                    matched_positions = [
                        i for i, cid in enumerate(display_df['_carid'])
                        if str(cid).strip() == curr_selected_id
                    ]
                    if matched_positions:
                        st.session_state["encar_car_table"] = {
                            "selection": {
                                "rows": [matched_positions[0]],
                                "columns": [],
                                "cells": []
                            }
                        }
                    st.session_state.last_selected_source = None

                # 2. 차량명에 파란색 엔카 링크 입히기 (차량명 텍스트 유지)
                def make_encar_link(r):
                    c_title = str(r.get('차량명', '엔카매물')).strip()
                    cand_l = str(r.get('링크', '')).strip()
                    if not cand_l.startswith('http'):
                        cid = str(r.get('_carid', '')).strip()
                        if cid and cid != 'None':
                            cand_l = f"http://www.encar.com/dc/dc_cardetailview.do?carid={cid}"
                    if cand_l.startswith('http'):
                        base_url = cand_l.split('#')[0]
                        return f"{base_url}#{c_title}"
                    return ""

                display_df['차량명_링크'] = display_df.apply(make_encar_link, axis=1)

                # 판매가를 "1,234만" 텍스트 포맷으로 변환 (st.dataframe canvas 렌더러는 font-size 미지원)
                if '판매가' in display_df.columns:
                    display_df['판매가_표시'] = display_df['판매가'].apply(
                        lambda x: f"💰 {int(x):,}만" if pd.notna(x) and x != 0 else "-"
                    )

                # 💡 [연식 하이라이트] 기준 연식 매물 선별 (아이콘/배경박스 없이 깔끔한 글자색만 변경)
                target_filter_year = ""
                if current_f_year:
                    m_yr = re.search(r'(\d{2,4})', str(current_f_year))
                    if m_yr:
                        y_val = int(m_yr.group(1))
                        target_filter_year = f"{y_val % 100:02d}"
                if not target_filter_year:
                    hd_y = st.session_state.get('hd_target_year')
                    if hd_y:
                        target_filter_year = f"{int(hd_y) % 100:02d}"

                def is_target_year_val(val):
                    if not target_filter_year:
                        return False
                    # 💡 괄호 안의 형식(모델연도)은 배제하고, 앞쪽의 순수 등록 연식 2자리만 정밀 대조
                    m = re.match(r'^\s*(\d{2})', str(val))
                    if m:
                        return m.group(1) == target_filter_year
                    return False

                try:
                    def _style_year_cell(val):
                        if is_target_year_val(val):
                            return "color: #38bdf8; font-weight: bold;"
                        return ""

                    styled_df = display_df.style.set_properties(
                        subset=[c for c in ['주행거리'] if c in display_df.columns],
                        **{'font-weight': 'bold'}
                    ).set_properties(
                        subset=[c for c in ['판매가_표시'] if c in display_df.columns],
                        **{'font-weight': 'bold', 'color': '#cc9166'}
                    )

                    styler_map = getattr(styled_df, 'map', getattr(styled_df, 'applymap', None))
                    if styler_map:
                        styled_df = styler_map(
                            _style_year_cell,
                            subset=[c for c in ['연식'] if c in display_df.columns]
                        )
                    styled_df = styled_df.format(precision=0)

                    event = st.dataframe(
                        styled_df,
                        key="encar_car_table",
                        column_config={
                            "성능일": st.column_config.TextColumn("성능일"),
                            "재고": st.column_config.TextColumn("재고일"),
                            "차량명_링크": st.column_config.LinkColumn("차량명", display_text=r"#(.*)"),
                            "연식": st.column_config.TextColumn("연식"),
                            "주행거리": st.column_config.NumberColumn("주행(km)", format="%d"),
                            "판매가_표시": st.column_config.TextColumn("💰가격"),
                            "사고유무_표시": st.column_config.TextColumn("사고유무"),
                            "외장컬러": st.column_config.TextColumn("색상"),
                            "추가옵션_요약": st.column_config.TextColumn("옵션"),
                        },
                        column_order=[
                            "성능일", "재고", "차량명_링크", "연식", 
                            "주행거리", "판매가_표시", "사고유무_표시", "외장컬러", "추가옵션_요약"
                        ],
                        use_container_width=True,
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
                selected_encar_row = None

                # 1. 표(DataFrame)에서 체크/선택된 경우 최우선 반영
                curr_table_idx = selected_rows[0] if selected_rows else None
                if curr_table_idx is not None and curr_table_idx < len(display_df):
                    selected_encar_row = display_df.iloc[curr_table_idx]
                    st.session_state.selected_car_id = str(selected_encar_row.get('_carid', '')).strip()
                elif st.session_state.get('selected_car_id'):
                    # 2. 산점도 등에서 선택된 car_id 반영
                    target_id = str(st.session_state.get('selected_car_id', '')).strip()
                    matched = display_df[display_df['_carid'].astype(str).str.strip() == target_id]
                    if not matched.empty:
                        selected_encar_row = matched.iloc[0]
                elif not display_df.empty:
                    # 3. 기본값: 첫 번째 차량
                    selected_encar_row = display_df.iloc[0]
                    st.session_state.selected_car_id = str(selected_encar_row.get('_carid', '')).strip()

                if selected_encar_row is not None:
                    row = selected_encar_row

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
                        (("라디에이터","서포트"),         55, 30,  110, 30, "R.S", "라디에이터 서포트"),
                        (("크로스","멤버"),               55, 65,  110, 30, "크로스", "크로스멤버"),
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

                    carid = row.get('_carid')
                    def get_full_vehicle_info(carid):
                        import requests
                        try:
                            if not carid: return {}
                            cache_key = f"_full_detail_cache_{carid}"
                            if cache_key in st.session_state:
                                return st.session_state[cache_key]
                            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": f"https://fem.encar.com/cars/detail/{carid}"}
                            v_url = f"https://api.encar.com/v1/readside/vehicle/{carid}?include=MANAGE,OPTIONS,SPEC"
                            v_resp = requests.get(v_url, headers=headers, timeout=5)
                            real_id = str(carid)
                            live_color = ""
                            live_opts = []
                            regist_dt = ""
                            if v_resp.status_code == 200:
                                vj = v_resp.json()
                                manage = vj.get("manage") or {}
                                spec = vj.get("spec") or {}
                                live_color = spec.get("colorName", "")
                                regist_dt = manage.get("registDateTime") or manage.get("firstAdvertisedDateTime") or ""
                                if manage.get("dummy") and manage.get("dummyVehicleId"):
                                    real_id = str(manage.get("dummyVehicleId"))
                                choice_codes = vj.get("options", {}).get("choice", []) or []
                                if choice_codes:
                                    o_url = f"https://api.encar.com/v1/readside/vehicles/car/{carid}/options/choice"
                                    o_resp = requests.get(o_url, headers=headers, timeout=5)
                                    if o_resp.status_code == 200:
                                        catalog = o_resp.json() or []
                                        for opt in catalog:
                                            if str(opt.get("optionCd", "")) in [str(c) for c in choice_codes]:
                                                o_name = Scraper.clean_option_name(opt.get("optionName", ""))
                                                p = opt.get("price", 0)
                                                if o_name and "외장컬러" not in o_name:
                                                    if p > 0: live_opts.append(f"{o_name}({p}만)")
                                                    else: live_opts.append(o_name)

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
                            live_perf_date = ""
                            live_inv_days = "-"
                            live_acc_status = ""
                            exch_cnt = 0
                            sheet_cnt = 0
                            acc_flag = None
                            rep_flag = None

                            i_url = f"https://api.encar.com/v1/readside/inspection/vehicle/{carid}"
                            i_resp = requests.get(i_url, headers=headers, timeout=5)
                            if i_resp.status_code == 404 and real_id != str(carid):
                                i_url = f"https://api.encar.com/v1/readside/inspection/vehicle/{real_id}"
                                i_resp = requests.get(i_url, headers=headers, timeout=5)

                            if i_resp.status_code == 200:
                                ij = i_resp.json()
                                master = ij.get("master") or {}
                                detail = master.get("detail") or {}
                                issue_date = detail.get("issueDate", "")
                                if issue_date and len(issue_date) >= 8:
                                    live_perf_date = f"{issue_date[2:4]}-{issue_date[4:6]}-{issue_date[6:8]}"
                                    live_inv_days = Scraper.calculate_inventory_days(live_perf_date)
                                
                                acc_flag = master.get("accdient")
                                rep_flag = master.get("simpleRepair")

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
                                        exch_cnt += 1
                                    elif any(c in codes for c in ["W", "C", "A", "U", "T"]):
                                        if damage_dict.get(norm_n) != "교환":
                                            damage_dict[norm_n] = "판금"
                                            sheet_cnt += 1

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
                                                exch_cnt += 1
                                            elif rc in ["SHEET_METAL", "WELD", "W", "C", "A", "U", "T"] or rt in ["판금", "용접", "도색", "수리"]:
                                                if damage_dict.get(norm_n) != "교환":
                                                    damage_dict[norm_n] = "판금"
                                                    sheet_cnt += 1

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
                                            exch_cnt += 1
                                        elif any(c in codes for c in ["W", "C", "A", "U", "T"]):
                                            if damage_dict.get(norm_n) != "교환":
                                                damage_dict[norm_n] = "판금"
                                                sheet_cnt += 1

                            if exch_cnt > 0 or sheet_cnt > 0:
                                if acc_flag: base_label = "사고"
                                elif exch_cnt > 0 and sheet_cnt == 0: base_label = "단순교환"
                                elif sheet_cnt > 0 and exch_cnt == 0: base_label = "단순판금"
                                else: base_label = "단순(교환/판금)"
                                live_acc_status = f"{base_label} [교환:{exch_cnt} / 판금:{sheet_cnt}]"
                            elif acc_flag is False and rep_flag is False:
                                live_acc_status = "완전무사고"
                            elif acc_flag:
                                live_acc_status = "사고"
                            elif rep_flag:
                                live_acc_status = "단순교환"
                            elif not live_acc_status:
                                live_acc_status = "미검사(사진)"

                            if not live_perf_date:
                                live_perf_date = "미검사/사진"
                                live_inv_days = "-"

                            res_obj = {
                                "damage": damage_dict,
                                "color": live_color,
                                "options": live_opts,
                                "perf_date": live_perf_date,
                                "inv_days": live_inv_days,
                                "accident_status": live_acc_status
                            }
                            st.session_state[cache_key] = res_obj
                            return res_obj
                        except Exception:
                            fallback_obj = {"damage": {}, "color": "", "options": [], "perf_date": "", "inv_days": "-", "accident_status": ""}
                            st.session_state[f"_full_detail_cache_{carid}"] = fallback_obj
                            return fallback_obj

                    full_info = {}
                    if carid:
                        full_info = get_full_vehicle_info(carid)

                    damage_data = full_info.get("damage", {})
                    diag_html = render_car_diagram(damage_data)

                    yr_val = f"{row['연식']}년식" if pd.notna(row.get('연식')) else ""
                    mil_num = int(row['주행거리']) if pd.notna(row.get('주행거리')) else 0
                    mil_val = f"{mil_num:,}km"

                    # 1. 성능점검일 및 재고일수 결정 (실시간 API 우선)
                    live_p_date = full_info.get("perf_date", "")
                    disp_perf_date = live_p_date if live_p_date else str(row.get('성능일', '-')).strip()
                    live_i_days = full_info.get("inv_days", "-")
                    disp_inv_days = live_i_days if live_i_days and live_i_days != "-" else str(row.get('재고', '-')).strip()
                    
                    # 2. 사고 상태 결정 (실시간 API 우선)
                    live_acc = full_info.get("accident_status", "")
                    disp_acc = live_acc if live_acc else str(row.get('사고유무', '-')).strip()

                    # 3. 색상 결정 (실시간 API 조회 결과 우선)
                    live_col = full_info.get("color", "")
                    raw_color = live_col if live_col and live_col not in ['-', '정보없음', '⚠️정보없음', '⚠️조회실패'] else str(row.get('외장컬러', '')).strip()
                    
                    # 4. 추가 옵션 목록 결정 (실시간 API 조회 결과 우선)
                    live_opt_list = full_info.get("options", [])
                    if live_opt_list:
                        opt_items = live_opt_list
                    else:
                        opt_items = [o.strip() for o in str(row.get('추가옵션', '')).split(" / ") if o.strip() and o.strip() not in ("없음", "-", "없음(구버전점검)", "⚠️조회실패", "코드매칭실패")]

                    current_car_name = str(row.get('차량명', '')).strip()
                    current_car_year = str(row.get('연식', '')).strip()

                    # 선택된 비교 차량의 옵션 목록 세션 저장 (사이드바 하이라이트 연동용)
                    st.session_state['selected_comp_car_opts'] = opt_items
                    target_opts = get_current_target_options() or []

                    matched_opts = []
                    unmatched_opts = []
                    for opt in opt_items:
                        if target_opts and is_target_option_matched(opt, target_opts, current_car_name, current_car_year):
                            matched_opts.append(opt)
                        else:
                            unmatched_opts.append(opt)

                    # 공통 옵션(파랑 ✓)을 앞에 배치하고, 비교차에만 있는 추가 옵션(오렌지 +)을 뒤에 배치
                    sorted_opt_items = [(opt, True) for opt in matched_opts] + [(opt, False) for opt in unmatched_opts]

                    opt_html = ""
                    if sorted_opt_items:
                        for opt, is_m in sorted_opt_items[:8]:
                            _, tooltip_text = build_option_tooltip(opt, target_opts, current_car_name, current_car_year)
                            c_tip = tooltip_text.replace('"', '&quot;').replace("'", '&#39;').replace('\n', '&#10;')
                            if is_m:
                                # 공통 옵션: 선명한 블루 강조 및 ✓ 체크
                                opt_html += f"<div title=\"{c_tip}\" style=\"background:rgba(14, 165, 233, 0.18); color:#38bdf8; padding:4px 9px; border-radius:6px; font-size:0.83em; font-weight:700; margin:2px 3px 2px 0; display:inline-block; border: 1px solid #0284c7; box-shadow:0 0 6px rgba(14,165,233,0.2); cursor:pointer;\">✓ {opt}</div>"
                            else:
                                # 비교차 전용 옵션: 앰버 오렌지 뱃지
                                opt_html += f"<div title=\"{c_tip}\" style=\"background:rgba(249, 115, 22, 0.18); color:#fb923c; padding:4px 9px; border-radius:6px; font-size:0.83em; font-weight:700; margin:2px 3px 2px 0; display:inline-block; border: 1px solid #ea580c; cursor:pointer;\">+ {opt}</div>"
                        if len(sorted_opt_items) > 8:
                            more_opts = [o for o, _ in sorted_opt_items[8:]]
                            more_tip = "추가 옵션:\n" + "\n".join([f"- {o}" for o in more_opts])
                            c_more_tip = more_tip.replace('"', '&quot;').replace("'", '&#39;').replace('\n', '&#10;')
                            opt_html += f"<div title=\"{c_more_tip}\" style=\"background:#1e222d; color:#94a3b8; padding:4px 8px; border-radius:6px; font-size:0.82em; font-weight:500; margin:2px 2px; display:inline-block; border: 1px solid #2e384d; cursor:pointer;\">+{len(sorted_opt_items)-8}</div>"
                    else:
                        opt_html = "<div style=\"color:#64748b; font-size:0.85em; margin-top:4px;\">추가옵션 없음 또는 기본 트림 사양</div>"

                    if not raw_color or raw_color in ['-', '정보없음', '⚠️정보없음', '⚠️조회실패']:
                        color_name = "색상미등록"
                        c_text_color = "#94a3b8"
                        c_bg_color = "rgba(148, 163, 184, 0.1)"
                        c_border_color = "rgba(148, 163, 184, 0.25)"
                        c_dot = "⚪"
                    else:
                        color_name = raw_color
                        c_lower = raw_color.lower()
                        if any(k in c_lower for k in ['검정', '블랙', 'black']):
                            c_text_color = "#f3f4f6"
                            c_bg_color = "#000000"
                            c_border_color = "#6b7280"
                            c_dot = "⚫"
                        elif any(k in c_lower for k in ['흰색', '화이트', 'white', '진주', '아이보리', '펄']):
                            c_text_color = "#ffffff"
                            c_bg_color = "rgba(255, 255, 255, 0.12)"
                            c_border_color = "#ffffff"
                            c_dot = "⚪"
                        elif any(k in c_lower for k in ['쥐색', '그레이', '다크그레이', '회색', '차콜', '메탈', '티타늄']):
                            c_text_color = "#94a3b8"
                            c_bg_color = "#1e2430"
                            c_border_color = "#475569"
                            c_dot = "🩶"
                        elif any(k in c_lower for k in ['은색', '실버', 'silver']):
                            c_text_color = "#e2e8f0"
                            c_bg_color = "rgba(203, 213, 225, 0.15)"
                            c_border_color = "#cbd5e1"
                            c_dot = "💿"
                        elif any(k in c_lower for k in ['빨강', '레드', 'red', '자주', '와인', '버건디', '주황', '오렌지']):
                            c_text_color = "#f87171"
                            c_bg_color = "rgba(239, 68, 68, 0.15)"
                            c_border_color = "#ef4444"
                            c_dot = "🔴"
                        elif any(k in c_lower for k in ['파랑', '블루', 'blue', '남색', '네이비', '청색', '하늘']):
                            c_text_color = "#60a5fa"
                            c_bg_color = "rgba(59, 130, 246, 0.15)"
                            c_border_color = "#3b82f6"
                            c_dot = "🔵"
                        elif any(k in c_lower for k in ['갈색', '브라운', 'brown', '베이지', '초코']):
                            c_text_color = "#d97706"
                            c_bg_color = "rgba(217, 119, 6, 0.15)"
                            c_border_color = "#b45309"
                            c_dot = "🟤"
                        elif any(k in c_lower for k in ['초록', '그린', 'green', '국방', '카키']):
                            c_text_color = "#4ade80"
                            c_bg_color = "rgba(34, 197, 94, 0.15)"
                            c_border_color = "#22c55e"
                            c_dot = "🟢"
                        elif any(k in c_lower for k in ['노랑', '옐로우', 'yellow', '골드', '금색']):
                            c_text_color = "#facc15"
                            c_bg_color = "rgba(234, 179, 8, 0.15)"
                            c_border_color = "#eab308"
                            c_dot = "🟡"
                        else:
                            c_text_color = "#cbd5e1"
                            c_bg_color = "rgba(148, 163, 184, 0.12)"
                            c_border_color = "rgba(148, 163, 184, 0.3)"
                            c_dot = "🎨"

                    color_badge_html = f"<span style='color: {c_text_color}; background: {c_bg_color}; border: 1px solid {c_border_color}; padding: 2px 8px; border-radius: 5px; font-weight: 700;'>{c_dot} {color_name}</span>"

                    # 📅 점검/재고 뱃지
                    perf_badge_html = ""
                    if disp_perf_date and disp_perf_date not in ['-', '미검사/사진', '⚠️미등록', '⚠️조회실패']:
                        days_str = f" ({disp_inv_days}일 전)" if disp_inv_days and disp_inv_days != '-' else ""
                        perf_badge_html = f"<span style='color: #38bdf8; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.25); padding: 2px 8px; border-radius: 5px;'>📅 점검 {disp_perf_date}{days_str}</span>"
                    else:
                        perf_badge_html = f"<span style='color: #94a3b8; background: rgba(148, 163, 184, 0.1); border: 1px solid rgba(148, 163, 184, 0.25); padding: 2px 8px; border-radius: 5px;'>📅 {disp_perf_date}</span>"

                    # 🛡️ 사고유무 뱃지
                    acc_badge_html = ""
                    if disp_acc and disp_acc not in ['-', '정보없음', '⚠️정보없음', '⚠️조회실패']:
                        if "완전" in disp_acc or "무사고" in disp_acc:
                            acc_badge_html = f"<span style='color: #4ade80; background: rgba(74, 222, 128, 0.12); border: 1px solid rgba(74, 222, 128, 0.3); padding: 2px 8px; border-radius: 5px;'>🛡️ {disp_acc}</span>"
                        elif "단순" in disp_acc or "판금" in disp_acc:
                            acc_badge_html = f"<span style='color: #facc15; background: rgba(250, 204, 21, 0.12); border: 1px solid rgba(250, 204, 21, 0.3); padding: 2px 8px; border-radius: 5px;'>⚠️ {disp_acc}</span>"
                        else:
                            acc_badge_html = f"<span style='color: #f87171; background: rgba(248, 113, 113, 0.12); border: 1px solid rgba(248, 113, 113, 0.3); padding: 2px 8px; border-radius: 5px;'>🚨 {disp_acc}</span>"

                    st.markdown(f"""
                    <div style='background:#121317; border: 1px solid #2e3038; border-radius: 8px; padding: 14px; margin-bottom: 10px;'>
                        <div style='font-size: 1.15em; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;'>{row['차량명']}</div>
                        <div style='font-size: 0.9em; font-weight: 500; color: #cbd5e1; margin-top: 2px;'>{row['세부모델']}</div>
                        <div style='font-size: 0.88em; font-weight: 700; margin-top: 6px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;'>
                            <span style='color: #cbd5e1; background: rgba(203, 213, 225, 0.1); border: 1px solid rgba(203, 213, 225, 0.25); padding: 2px 8px; border-radius: 5px;'>{yr_val}</span>
                            <span style='color: #a0ca92; background: rgba(160, 202, 146, 0.12); border: 1px solid rgba(160, 202, 146, 0.3); padding: 2px 8px; border-radius: 5px;'>{mil_val}</span>
                            {color_badge_html}
                            {perf_badge_html}
                            {acc_badge_html}
                        </div>
                        <div style='font-size: 1.35em; font-weight: 800; color: #cc9166; margin-top: 8px;'>{int(row['판매가']) if pd.notna(row['판매가']) else 0:,} 만원</div>
                        <div style='margin-top: 10px;'>{opt_html}</div>
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
        # 실시간 엔카 스캔 데이터(20/21/22년 전 매물)를 온전히 산점도에 반영

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

                car_ids = [str(r.get('_carid', '')) for _, r in chart_df.iterrows()]

                fig.add_trace(go.Scatter(
                    x=chart_df['주행거리_num'],
                    y=chart_df['판매가_num'],
                    mode='markers',
                    marker=dict(size=9, color=colors, opacity=0.85, line=dict(width=1, color='#1c1d22')),
                    text=hover_text,
                    customdata=car_ids,
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

                # 🎯 선택된 차량 산점도 강조 표시 (별 모양 및 외곽선)
                if 'selected_encar_row' in locals() and selected_encar_row is not None:
                    try:
                        sel_mil = pd.to_numeric(selected_encar_row.get('주행거리'), errors='coerce')
                        sel_price = pd.to_numeric(selected_encar_row.get('판매가'), errors='coerce')
                        if pd.notna(sel_mil) and pd.notna(sel_price):
                            sel_name = selected_encar_row.get('차량명', '선택 차량')
                            sel_acc = selected_encar_row.get('사고유무', '-')
                            fig.add_trace(go.Scatter(
                                x=[sel_mil],
                                y=[sel_price],
                                mode='markers+text',
                                marker=dict(
                                    symbol='star',
                                    size=22,
                                    color='#facc15',
                                    line=dict(color='#dc2626', width=2.5)
                                ),
                                text=[f"⭐ {sel_name}"],
                                textposition="top center",
                                textfont=dict(color='#ffffff', size=12, family='sans-serif'),
                                hoverinfo='skip',
                                name="선택 차량"
                            ))
                    except Exception as e:
                        pass

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

                chart_event = st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key="scatter_plot_chart",
                    on_select="rerun",
                    selection_mode="points"
                )

                # 산점도에서 점 클릭 시 선택 차량 세션 갱신 (산점도 자체 신규 클릭일 때만 반응)
                if chart_event and hasattr(chart_event, 'selection') and chart_event.selection:
                    points = getattr(chart_event.selection, 'points', [])
                    if points:
                        clicked_point = points[0]
                        # 메인 매물 점(curve_number 0)만 클릭으로 인정 (추세선/별표 무시)
                        if clicked_point.get('curve_number', 0) == 0:
                            clicked_carid = None
                            if 'customdata' in clicked_point:
                                cdata = clicked_point['customdata']
                                clicked_carid = str(cdata[0] if isinstance(cdata, list) else cdata)
                            elif 'point_index' in clicked_point:
                                pt_idx = clicked_point['point_index']
                                if pt_idx < len(car_ids):
                                    clicked_carid = str(car_ids[pt_idx])

                            scatter_sig = (clicked_point.get('curve_number'), clicked_point.get('point_index'), clicked_carid)
                            if clicked_carid and scatter_sig != st.session_state.get('last_scatter_click_sig'):
                                st.session_state.last_scatter_click_sig = scatter_sig
                                st.session_state.selected_car_id = clicked_carid
                                st.session_state.last_selected_source = 'scatter'
                                st.rerun()
                    else:
                        st.session_state.last_scatter_click_sig = None
            else:
                st.info("차트를 그릴 수 있는 유효 데이터가 없습니다.")
        else:
            st.info("현재 설정된 조건에 맞는 매물 데이터가 없습니다.")

        st.markdown("---")

        # ==========================================
        # 🤖 [4] 헤이딜러 낙찰데이터 요약본 (크기 2/3) + 요약 2번
        # ==========================================
        hd_raw_df = st.session_state.get('hd_comp_df', pd.DataFrame())

        # 대상 차량의 세부등급(트림) 추출
        target_grade = (st.session_state.get('hd_grade_part_name') or st.session_state.get('f_sub') or '').strip()
        if target_grade == "전체":
            target_grade = ""

        # 사용 가능한 등급 목록 및 건수 추출
        available_grades = []
        grade_counts = {}
        if not hd_raw_df.empty and '차량명' in hd_raw_df.columns:
            for g in hd_raw_df['차량명'].dropna().unique():
                g_str = str(g).strip()
                if g_str:
                    cnt = len(hd_raw_df[hd_raw_df['차량명'] == g])
                    available_grades.append(g_str)
                    grade_counts[g_str] = cnt

        # 타겟 등급과 일치하는 헤이딜러 등급 매칭
        best_match_grade = None
        if target_grade and available_grades:
            t_clean = target_grade.replace(" ", "").lower()
            # 1. 완전 일치 또는 상호 포함
            for g in available_grades:
                g_clean = g.replace(" ", "").lower()
                if g_clean == t_clean or g_clean in t_clean or t_clean in g_clean:
                    best_match_grade = g
                    break
            # 2. 핵심 트림 키워드 매칭
            if not best_match_grade:
                trim_keywords = ['인스퍼레이션', '프리미엄', '모던', '스마트', '노블레스', '시그니처', '프레스티지', '트렌디', '캘리그래피', '익스클루시브', '르블랑', '프리미에르', '어드밴스드', '어반', '스타일']
                for kw in trim_keywords:
                    if kw in t_clean:
                        for g in available_grades:
                            if kw in g.replace(" ", "").lower():
                                best_match_grade = g
                                break
                        if best_match_grade:
                            break

        # 필터 옵션 구성
        filter_options = []
        grade_opt_map = {}

        if best_match_grade:
            opt_target = f"🎯 조회 등급: {best_match_grade} ({grade_counts[best_match_grade]}대)"
            filter_options.append(opt_target)
            grade_opt_map[opt_target] = best_match_grade

        opt_all = f"🌐 전체 등급 보기 (총 {len(hd_raw_df)}대)"
        filter_options.append(opt_all)
        grade_opt_map[opt_all] = "ALL"

        for g in available_grades:
            if g != best_match_grade:
                opt_g = f"🏷️ {g} ({grade_counts[g]}대)"
                filter_options.append(opt_g)
                grade_opt_map[opt_g] = g

        # 헤더 및 등급 필터 선택기
        hd_title_col, hd_filter_col = st.columns([5.5, 4.5])
        with hd_title_col:
            st.markdown("### 🤖 헤이딜러 동급 낙찰 데이터 요약")
        with hd_filter_col:
            if len(available_grades) > 1:
                selected_opt = st.selectbox(
                    "헤이딜러 등급 필터",
                    filter_options,
                    index=0,
                    key="hd_grade_filter_selector",
                    label_visibility="collapsed",
                    help="원하는 세부 등급을 선택하시면 낙찰 시세 요약 및 리스트가 해당 등급만으로 정밀 필터링됩니다."
                )
                selected_grade_val = grade_opt_map.get(selected_opt, "ALL")
            else:
                selected_grade_val = "ALL"

        # 선택된 등급으로 hd_df 필터링
        if selected_grade_val != "ALL" and not hd_raw_df.empty:
            hd_df = hd_raw_df[hd_raw_df['차량명'] == selected_grade_val].copy()
        else:
            hd_df = hd_raw_df.copy()

        # 내수 시세 산출을 위해 수출 차량 분리 (내수 시세와 가격 기준이 전혀 다름)
        hd_domestic_df = hd_df[~hd_df['수출여부']] if ('수출여부' in hd_df.columns and not hd_df.empty) else hd_df
        calc_hd_df = hd_domestic_df if not hd_domestic_df.empty else hd_df

        hd_total_count = len(hd_df)
        hd_dom_count = len(hd_domestic_df)
        hd_export_count = hd_total_count - hd_dom_count

        hd_min_price = int(calc_hd_df['판매가_num'].min()) if not calc_hd_df.empty and '판매가_num' in calc_hd_df.columns else 0
        hd_max_price = int(calc_hd_df['판매가_num'].max()) if not calc_hd_df.empty and '판매가_num' in calc_hd_df.columns else 0
        hd_avg_price = int(calc_hd_df['판매가_num'].mean()) if not calc_hd_df.empty and '판매가_num' in calc_hd_df.columns else 0

        st.markdown(f"""
        <div style='display: flex; gap: 12px; margin-top: 8px; margin-bottom: 8px;'>
            <div class='metric-card' style='flex: 1;'>
                <div class='metric-icon'>🚙</div>
                <div class='metric-content'><h4>총 매물 수</h4><h2>{hd_total_count:,} 대 <span style='font-size: 0.55em; color: #94a3b8;'>({'내수 ' + str(hd_dom_count) + ' / 수출 ' + str(hd_export_count) if hd_export_count > 0 else '전체 내수'})</span></h2></div>
            </div>
            <div class='metric-card' style='flex: 1;'>
                <div class='metric-icon'>⬇️</div>
                <div class='metric-content'><h4>최저가(내수)</h4><h2 style='color: #4a90e2;'>{hd_min_price:,} 만원 <span style='font-size: 0.6em'>⬇️</span></h2></div>
            </div>
            <div class='metric-card' style='flex: 1;'>
                <div class='metric-icon'>⬆️</div>
                <div class='metric-content'><h4>최고가(내수)</h4><h2 style='color: #e25c5c;'>{hd_max_price:,} 만원 <span style='font-size: 0.6em'>⬆️</span></h2></div>
            </div>
            <div class='metric-card' style='flex: 1;'>
                <div class='metric-icon'>📊</div>
                <div class='metric-content'><h4>내수 평균가</h4><h2 style='color: #cc9166;'>{hd_avg_price:,} 만원</h2></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 요약 2번 계산 및 🤖 AI 판단 낙찰(매입)가 산출 (수출 차량 제외한 내수 기준)
        hd_no_acc_avg = hd_avg_price
        hd_acc_avg = hd_avg_price
        hd_year_stats = ""
        ai_wholesale_price = hd_avg_price
        hd_ai_detail_desc = ""

        if not calc_hd_df.empty and '판매가_num' in calc_hd_df.columns:
            p_num = pd.to_numeric(calc_hd_df['판매가_num'], errors='coerce')
            if '사고유무' in calc_hd_df.columns:
                is_no = calc_hd_df['사고유무'].astype(str).str.contains('완전무사고|무사고')
                if is_no.any(): hd_no_acc_avg = int(p_num[is_no].mean())
                if (~is_no).any(): hd_acc_avg = int(p_num[~is_no].mean())

            if '연식_num' in calc_hd_df.columns:
                years = sorted(calc_hd_df['연식_num'][calc_hd_df['연식_num'] > 0].dropna().unique())
                y_parts = []
                for y in years[-3:]:
                    sub_p = p_num[calc_hd_df['연식_num'] == y].dropna()
                    if not sub_p.empty:
                        y_parts.append(f"{y}년 평균 {int(sub_p.mean()):,}만원")
                if y_parts:
                    hd_year_stats = " / ".join(y_parts)

            # 🤖 AI 판단 낙찰(매입)가 계산
            try:
                hd_mil = pd.to_numeric(calc_hd_df['주행거리_num'], errors='coerce').dropna()
                hd_p = pd.to_numeric(calc_hd_df['판매가_num'], errors='coerce').dropna()
                valid_hd_idx = hd_mil.index.intersection(hd_p.index)

                user_hd_target_mil = l_mil if ('l_mil' in locals() and l_mil > 0) else (current_f_mil if ('current_f_mil' in locals() and current_f_mil > 0) else (int(hd_mil.mean()) if not hd_mil.empty else 0))

                hd_slope = -0.005  # 기본값: 1만km당 약 50만원 감가
                base_hd_mil = int(hd_mil.loc[valid_hd_idx].mean()) if len(valid_hd_idx) > 0 else user_hd_target_mil
                base_hd_price = hd_avg_price if hd_avg_price > 0 else (int(hd_p.mean()) if not hd_p.empty else 0)

                if len(valid_hd_idx) >= 2:
                    hd_fit_z = np.polyfit(hd_mil.loc[valid_hd_idx], hd_p.loc[valid_hd_idx], 1)
                    if -0.02 <= hd_fit_z[0] <= -0.001:
                        hd_slope = hd_fit_z[0]

                hd_mil_diff = user_hd_target_mil - base_hd_mil
                hd_mil_adj = int(round(hd_mil_diff * hd_slope))

                # 헤이딜러 타겟 차량 옵션 가치 보정 (연식 감가율 연동)
                hd_opt_adj = 0
                hd_target_opt_names = []
                try:
                    wholesale_opt_ratio = opt_ratio * 0.85  # 도매 낙찰 시장의 보수적 감안율
                    hd_parsed_opt_price = st.session_state.get('hd_target_opt_price', 0)
                    hd_opts = st.session_state.get('hd_target_options', []) or []
                    encar_opts = st.session_state.get('encar_target_options', []) or []
                    all_target_opts = list(dict.fromkeys(hd_opts + encar_opts))
                    if all_target_opts and '옵션리스트' in calc_hd_df.columns:
                        target_score, hd_target_opt_names = score_key_options(all_target_opts)
                        hd_scores = [score_key_options(opts)[0] for opts in calc_hd_df['옵션리스트'].dropna()]
                        avg_hd_opt_score = int(np.mean(hd_scores)) if hd_scores else 0
                        
                        if hd_parsed_opt_price and hd_parsed_opt_price > 0:
                            # 실 옵션 원가 파싱값 있는 경우
                            avg_hd_opt_new = int(avg_hd_opt_score * 1.5)
                            hd_opt_adj = int(round((hd_parsed_opt_price - avg_hd_opt_new) * wholesale_opt_ratio))
                        elif target_score != avg_hd_opt_score:
                            hd_opt_adj = int(round((target_score - avg_hd_opt_score) * wholesale_opt_ratio))
                except Exception:
                    hd_opt_adj = 0

                ai_wholesale_price = int(base_hd_price + hd_mil_adj + hd_opt_adj)

                hd_adj_parts = []
                if hd_mil_adj != 0:
                    hd_adj_parts.append(f"주행거리({user_hd_target_mil:,}km): {hd_mil_adj:+}만")
                if hd_opt_adj != 0:
                    opt_label = f"옵션가치({', '.join(hd_target_opt_names[:3])}): {hd_opt_adj:+}만" if hd_target_opt_names else f"옵션가치: {hd_opt_adj:+}만"
                    hd_adj_parts.append(opt_label)
                elif hd_target_opt_names:
                    hd_adj_parts.append(f"주요옵션({', '.join(hd_target_opt_names[:3])}): 동급 평균 수준")

                hd_ai_detail_desc = f" (내수 평균 {base_hd_price:,}만 대비 " + ", ".join(hd_adj_parts) + ")" if hd_adj_parts else " (내수 경매 평균 수준)"
            except Exception:
                ai_wholesale_price = hd_avg_price

        hd_ai_badge_html = f"<span style='background: #1e293b; color: #38bdf8; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 1.05em; border: 1px solid #0284c7;'>🤖 AI 판단 매입가: <span style='font-size: 1.2em; color: #ffffff;'>{ai_wholesale_price:,}</span> 만원</span>" if (ai_wholesale_price > 0 and hd_total_count > 0) else ""

        export_note = f" <span style='color: #38bdf8;'>(수출 {hd_export_count}대 제외됨)</span>" if hd_export_count > 0 else ""
        if hd_total_count > 0:
            hd_summary_content = f"""<div class='summary-box'>
    <div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2e3038; padding-bottom: 8px; margin-bottom: 8px;'>
    <b style='color: #cc9166; font-size: 1.1em;'>📋 (2) 예상 매입가 기준 (헤이딜러 내수 낙찰 데이터)</b>
    {hd_ai_badge_html}
    </div>
    • <b>AI 매입(낙찰)가 산출 내역:</b> <b style='color: #38bdf8;'>{ai_wholesale_price:,}만원</b><span style='color: #94a3b8; font-size: 0.9em;'>{hd_ai_detail_desc}{export_note}</span><br>
    • 동급 경매 평균(내수): <b style='color: #fff;'>{hd_avg_price:,}만원</b> (무사고 <b>{hd_no_acc_avg:,}만원</b> / 유사고 <b>{hd_acc_avg:,}만원</b>)<br>
    • {hd_year_stats if hd_year_stats else '연식별 데이터 집계 완료'}
    </div>"""
        else:
            hd_summary_content = """<div class='summary-box'>
    <b style='color: #cc9166; font-size: 1.1em;'>📋 (2) 예상 매입가 기준 (헤이딜러 낙찰 데이터)</b><br>
    • 헤이딜러 시세를 조회하면 동급 경매 평균 및 주행거리가 보정된 <b>AI 판단 매입(낙찰)가</b>가 여기에 계산되어 표시됩니다.
    </div>"""

        st.markdown(hd_summary_content, unsafe_allow_html=True)

        st.markdown("---")

        # ==========================================
        # 📋 [5] 헤이딜러 리스트 및 상세스펙
        # ==========================================
        if not hd_df.empty:
            hd_col1, hd_col2 = st.columns([6.2, 3.8])

            with hd_col1:
                filter_badge = f"<span style='background:#0f766e; color:#5eead4; padding:2px 8px; border-radius:4px; font-size:0.75em; font-weight:bold; margin-left:8px;'>🎯 {selected_grade_val} ({len(hd_df)}대)</span>" if selected_grade_val != "ALL" else f"<span style='background:#334155; color:#cbd5e1; padding:2px 8px; border-radius:4px; font-size:0.75em; font-weight:bold; margin-left:8px;'>🌐 전체 등급 ({len(hd_df)}대)</span>"
                st.markdown(f"#### 📋 헤이딜러 낙찰 이력 리스트 {filter_badge}", unsafe_allow_html=True)
                from services.heydealer_service import format_relative_date
                disp_hd_cols = [c for c in ['차량명', '연식', '주행거리', '낙찰가', '낙찰일', '사고유무', '옵션', '링크'] if c in hd_df.columns]
                hd_disp_df = hd_df[disp_hd_cols].copy()
                if '낙찰일' in hd_disp_df.columns:
                    def _resolve_relative_date(r):
                        for k in ['낙찰일', '낙찰일시', 'ended_at_display', 'end_at_display', 'ended_at', 'end_at', 'approved_at', 'selected_at', 'created_at', 'date']:
                            v = r.get(k)
                            if v:
                                formatted = format_relative_date(v)
                                if formatted != "-":
                                    return formatted
                        return "-"
                    hd_disp_df['낙찰일'] = hd_df.apply(_resolve_relative_date, axis=1)

                hd_event = st.dataframe(
                    hd_disp_df,
                    column_config={
                        "링크": st.column_config.LinkColumn("링크", display_text="보기"),
                        "낙찰일": st.column_config.TextColumn("낙찰시기", help="경매 종료 및 낙찰 시점 (예: 4일 전, 오늘)"),
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

                    is_export_car = bool(row.get('수출여부'))
                    export_badge = "<span style='background:#0284c7; color:#ffffff; padding:2px 8px; border-radius:6px; font-size:0.75em; font-weight:bold; margin-right:6px;'>🚢 수출딜러 낙찰</span>" if is_export_car else ""
                    date_badge = f"<span style='background:#1e293b; color:#38bdf8; border:1px solid #0284c7; padding:2px 8px; border-radius:6px; font-size:0.75em; font-weight:bold; margin-left:6px;'>⏱️ {row.get('낙찰일', '-')}</span>" if row.get('낙찰일') and row.get('낙찰일') != '-' else ""

                    card_html = (
                        f'<div style="background-color:#121317; padding:16px; border-radius:8px; border:1px solid #2e3038;">'
                        f'<div style="font-size:1.1em; font-weight:bold; color:#ffffff; margin-bottom:4px;">{row.get("차량명", "헤이딜러 매물")}</div>'
                        f'<div style="font-size:0.85em; color:#9194a1; margin-bottom:10px;">{row.get("연식", "-")} · {row.get("주행거리", "-")}</div>'
                        f'<div style="font-size:1.3em; font-weight:bold; color:#cc9166; margin-bottom:10px; display:flex; align-items:center;">{export_badge}{row.get("낙찰가", "-")}{date_badge}</div>'
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
