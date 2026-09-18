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

from sales_analysis import get_car_market_stats, generate_encar_market_url, SalesDataAnalyzer
from services.encar_service import Scraper
from services.chaolma_service import ChaolmaService
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

        default_car_num = st.session_state.get(f"car_num_{reset_idx}", "")
        
        # 차량번호 입력과 견적조회 버튼을 한 줄로 나란히 배치 (줄바꿈 없이 슬림하게)
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
        
        default_mil_val = int(st.session_state.get(f"mil_{reset_idx}", st.session_state.get('user_target_mil', 0)))
        mil_k = f"mil_{reset_idx}"
        if default_mil_val > 0 and (mil_k not in st.session_state or st.session_state[mil_k] == 0):
            st.session_state[mil_k] = default_mil_val
        l_mil = st.sidebar.number_input("주행거리 (km)", min_value=0, value=default_mil_val, step=1000, key=mil_k)

        if not ChaolmaService.is_authenticated():
            st.sidebar.markdown("<div style='font-size: 0.72rem; color: #fbbf24; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 4px; padding: 4px 8px; margin: 4px 0 8px 0;'>⚠️ 견적조회 쿠키 미등록 (상단 🔑설정에서 입력 또는 확장프로그램 전송)</div>", unsafe_allow_html=True)

        if btn_fetch_chaolma:
            if not l_car_num:
                st.sidebar.warning("차량번호를 입력해주세요.")
            elif not ChaolmaService.is_authenticated():
                st.sidebar.error("❌ 견적조회 쿠키가 없습니다. 상단 [🔑 세션 쿠키 설정]에 붙여넣어주세요.")
            else:
                with st.sidebar.spinner(f"[{l_car_num}] 제원 및 옵션 조회 중..."):
                    res = ChaolmaService.fetch_car_info(l_car_num, mileage=l_mil)
                    if res.get("success"):
                        st.session_state.scan_source = "car_number"
                        st.session_state[f"chaolma_data_{l_car_num}"] = res
                        st.session_state["last_chaolma_data"] = res

                        # 헤이딜러 잔존 세션 데이터 클리어 (모드 간 오염 및 겹침 완벽 차단)
                        for k in ['hd_model_part_name', 'hd_grade_part_name', 'hd_full_name', 'auto_encar_url', 'hd_comp_df', 'hd_target_year', 'hd_target_options', 'encar_target_options']:
                            st.session_state.pop(k, None)

                        # 🔥 사이드바 및 빅데이터 필터 자동 주입
                        raw_maker = res.get("maker", "")
                        raw_model = res.get("model_name", "")
                        raw_grade = res.get("grade_name", "")
                        raw_trim = res.get("trim_name", "")
                        raw_year = str(res.get("model_year", "")).replace("년", "").strip()

                        if raw_maker:
                            st.session_state.f_brand = raw_maker

                        if raw_model:
                            # '신형 K5' -> 빅데이터/재고 DB 매칭을 위해 핵심 모델명 설정
                            st.session_state.f_name = raw_model

                        # 세부모델 지능형 합성 (엔진/배기량 2.0 + 트림 MX 프레스티지 정밀 결합)
                        combined_sub = raw_trim
                        disp_match = re.search(r'(\d\.\d)', str(raw_grade))
                        if disp_match and raw_trim:
                            disp_str = disp_match.group(1)
                            if disp_str not in raw_trim:
                                combined_sub = f"{disp_str} {raw_trim}"
                        elif not combined_sub and raw_grade:
                            combined_sub = raw_grade

                        st.session_state.f_sub = combined_sub

                        if raw_year:
                            # 2016 -> 16 (2자리 연식)
                            st.session_state.f_year = raw_year[-2:]
                            cur_yr_key = f"search_year_{st.session_state.form_reset_key}"
                            try:
                                st.session_state[cur_yr_key] = int(raw_year[-2:])
                            except:
                                pass

                        if l_mil > 0:
                            st.session_state.f_mil = l_mil
                            st.session_state.user_target_mil = l_mil

                        # 🚀 [자동 연동] 차량번호 조회 시 엔카 동급 매물 즉시 자동 스캔
                        target_encar_url = generate_encar_market_url(
                            raw_model, 
                            combined_sub or raw_trim or raw_grade, 
                            raw_year, 
                            l_mil
                        )
                        scan_cnt = 0
                        st.session_state.debug_encar_scan = {
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "car_num": l_car_num,
                            "target_url": target_encar_url,
                            "searched_model": raw_model,
                            "searched_sub": combined_sub,
                            "searched_year": raw_year,
                            "status": "진행안됨",
                            "count": 0,
                            "error": ""
                        }
                        if target_encar_url:
                            try:
                                with st.sidebar.spinner(f"[{raw_model}] 엔카 실시간 동급매물 자동 연동 중..."):
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
                                        # 스캔된 엔카 차량명으로 f_name 자동 일치 (미스매치 100% 차단)
                                        if '차량명' in new_scan_df.columns:
                                            st.session_state.f_name = new_scan_df['차량명'].iloc[0]
                                    else:
                                        st.session_state.debug_encar_scan["error"] = msg
                            except Exception as ex_scan:
                                st.session_state.debug_encar_scan["status"] = "예외 에러"
                                st.session_state.debug_encar_scan["error"] = str(ex_scan)
                                print(f"[견적조회 엔카 자동스캔 오류]: {ex_scan}")

                        msg_suffix = f" & 엔카 동급매물 {scan_cnt}대 연동 완료!" if scan_cnt > 0 else f" (엔카: {st.session_state.debug_encar_scan.get('status', '조회대기')})"
                        st.sidebar.success(f"✅ [{l_car_num}] {raw_model} {raw_trim} ({raw_year}년){msg_suffix}")
                        st.rerun()
                    else:
                        st.sidebar.error(f"❌ {res.get('message', '조회 실패')}")

        # 조회된 제원 데이터가 있으면 컴팩트하게 카드 렌더링
        cached_chaolma = st.session_state.get(f"chaolma_data_{l_car_num}") if l_car_num else None
        if cached_chaolma and cached_chaolma.get("success"):
            render_chaolma_card_ui(cached_chaolma)

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
                    '외판수리': l_ext_repair if 'l_ext_repair' in locals() else 0,
                    '외판수리비': ext_cost if 'ext_cost' in locals() else 0,
                    '헤딜수수료': purchase_fee if 'purchase_fee' in locals() else 0,
                    '특이사항': f"[{st.session_state.purchase_route}] " + l_memo,
                    '상태': '장부저장'
                }
                st.session_state.my_ledger_data = pd.concat([pd.DataFrame([new_record]), st.session_state.my_ledger_data], ignore_index=True)
                st.session_state.my_ledger_data.to_csv(LEDGER_FILE, index=False, encoding='utf-8-sig')

                try:
                    response = requests.post(WEBHOOK_URL, json=new_record, timeout=5)
                    response.raise_for_status()
                except Exception as e:
                    print(f"[구글 시트 웹훅 전송 실패]: {e}")

                st.session_state.save_success = True
                st.session_state.saved_car_num = l_car_num
                st.session_state.form_reset_key += 1

                st.rerun()


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
                bd_target_sub = last_c.get('trim_name', '') or last_c.get('grade_name', '')
            if not bd_target_car and st.session_state.get('f_name') != "전체" and st.session_state.get('f_name'):
                bd_target_car = st.session_state.f_name
                bd_target_sub = st.session_state.f_sub if st.session_state.get('f_sub') != "전체" else ""
        else:
            # 🖐️ 수동 필터 선택 모드
            if st.session_state.get('f_name') != "전체" and st.session_state.get('f_name'):
                bd_target_car = st.session_state.f_name
                bd_target_sub = st.session_state.f_sub if st.session_state.get('f_sub') != "전체" else ""
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

        # 2. 실시간 스캔 매물 또는 필터링 매물에서 추출
        if not target_carid:
            if 'scan_data' in st.session_state and not st.session_state.scan_data.empty:
                if '_carid' in st.session_state.scan_data.columns and st.session_state.scan_data['_carid'].iloc[0]:
                    target_carid = str(st.session_state.scan_data['_carid'].iloc[0])
                elif '링크' in st.session_state.scan_data.columns:
                    m = re.search(r'carid=(\d+)', str(st.session_state.scan_data['링크'].iloc[0]))
                    if m: target_carid = m.group(1)
            elif not filtered_df.empty and '링크' in filtered_df.columns:
                m = re.search(r'carid=(\d+)', str(filtered_df['링크'].iloc[0]))
                if m: target_carid = m.group(1)

        # 3. 최근 조회된 carid fallback
        if not target_carid and st.session_state.get('target_carid'):
            target_carid = str(st.session_state.target_carid)

        sold_out_res = Scraper.fetch_sold_out_cars(target_carid) if target_carid else {"has_data": False}

        total_sales_loaded = len(SalesDataAnalyzer.get_instance().df)
        if bd_target_car and bd_stats.get('has_data'):
            tier_badge = f" <span style='background:#1e293b; border:1px solid #3b82f6; color:#60a5fa; padding:2px 8px; border-radius:12px; font-size:0.8em; font-weight:600;'>{bd_stats.get('matched_tier', '')}</span>" if bd_stats.get('matched_tier') else ""
            st.caption(f"💡 순수 내수 소매 완판 데이터 **{bd_stats.get('pure_sales_count', total_sales_loaded):,}건** 중 **[{bd_stats.get('matched_name', bd_target_car)}]** 실적({bd_stats.get('total_count', 0)}대) 분석 결과입니다.{tier_badge} (경매·도매 출고 {bd_stats.get('auction_filtered_count', 1339):,}건 왜곡 방지 자동 제외 완료)", unsafe_allow_html=True)

            c_m1, c_m2, c_m3, c_m4 = st.columns(4)
            with c_m1:
                st.markdown(f"""
                <div class='metric-card' style='min-height: 88px; height: 88px; display: flex; align-items: center; box-sizing: border-box;'>
                    <div class='metric-icon'>⏱️</div>
                    <div class='metric-content' style='overflow: hidden;'>
                        <h4 style='white-space: nowrap; text-overflow: ellipsis; overflow: hidden;'>소매 평균 재고일수</h4>
                        <h2 style='color: {bd_stats.get("turnover_color", "#4ade80")}; white-space: nowrap;'>{bd_stats.get("avg_days", 0)}일 <span style='font-size: 0.6em;'>({bd_stats.get("turnover_grade", "-")})</span></h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_m2:
                st.markdown(f"""
                <div class='metric-card' style='min-height: 88px; height: 88px; display: flex; align-items: center; box-sizing: border-box;'>
                    <div class='metric-icon'>🏷️</div>
                    <div class='metric-content' style='overflow: hidden;'>
                        <h4 style='white-space: nowrap; text-overflow: ellipsis; overflow: hidden;'>과거 평균 판매가</h4>
                        <h2 style='color: #38bdf8; white-space: nowrap;'>{bd_stats.get("avg_sell_price", 0):,}만원</h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_m3:
                st.markdown(f"""
                <div class='metric-card' style='min-height: 88px; height: 88px; display: flex; align-items: center; box-sizing: border-box;'>
                    <div class='metric-icon'>🛣️</div>
                    <div class='metric-content' style='overflow: hidden;'>
                        <h4 style='white-space: nowrap; text-overflow: ellipsis; overflow: hidden;'>완판 평균 주행거리</h4>
                        <h2 style='color: #a78bfa; white-space: nowrap;'>{bd_stats.get("avg_mileage", 0):,}km</h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_m4:
                st.markdown(f"""
                <div class='metric-card' style='min-height: 88px; height: 88px; display: flex; align-items: center; box-sizing: border-box;'>
                    <div class='metric-icon'>💰</div>
                    <div class='metric-content' style='overflow: hidden;'>
                        <h4 style='white-space: nowrap; text-overflow: ellipsis; overflow: hidden;'>과거 평균 실현마진</h4>
                        <h2 style='color: #cc9166; white-space: nowrap;'>+{int(bd_stats.get("avg_profit", 0)):,}만원 <span style='font-size: 0.6em; color: #94a3b8;'>({bd_stats.get("profit_rate", 0)}%)</span></h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            sold_badge_html = ""
            sold_text_html = ""
            if sold_out_res.get("has_data"):
                sold_badge_html = f"<span style='font-size: 0.86em; background: rgba(255,255,255,0.06); padding: 3px 10px; border-radius: 12px; border: 1px solid #3b4252;'>엔카 완판: <b style='color: {sold_out_res.get('velocity_color', '#ef4444')};'>{sold_out_res.get('velocity_badge', '완판')}</b> <span style='color:#94a3b8;'>(최근30일 {sold_out_res.get('count_30d', 0)}대)</span></span>"
                sold_text_html = f"<div style='margin-top: 8px; font-size: 0.9em; color: #cbd5e1; border-top: 1px dashed #2e3038; padding-top: 6px;'>⚡ <b>엔카 실시간 소화 속도</b>: 최근 30일간 <b>{sold_out_res.get('count_30d', 0)}대</b> 완판 (일평균 <b>{sold_out_res.get('daily_rate', 0)}대</b> 출고 / 완판 평균 주행거리 <b>{sold_out_res.get('avg_mileage', 0):,}km</b> / 최근 완판: <b>{sold_out_res.get('latest_sold_date', '-')}</b>)</div>"

            briefing_box_html = (
                f"<div style='background-color: #121317; border: 1px solid #2e3038; border-radius: 8px; padding: 14px 18px; margin-top: 4px; margin-bottom: 12px;'>"
                f"<div style='display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;'>"
                f"<span style='color: #38bdf8; font-weight: bold; font-size: 1.05em;'>💡 AI 비딩 전략 브리핑</span>"
                f"<div style='display: flex; align-items: center; gap: 8px; flex-wrap: wrap;'>"
                f"<span style='font-size: 0.86em; background: rgba(255,255,255,0.06); padding: 3px 10px; border-radius: 12px; border: 1px solid #3b4252;'>"
                f"수요도: <b>{bd_stats.get('demand_badge', '보통')}</b> <span style='color:#94a3b8;'>({bd_stats.get('demand_level', '보통')})</span>"
                f"</span>"
                f"<span style='font-size: 0.86em; background: rgba(255,255,255,0.06); padding: 3px 10px; border-radius: 12px; border: 1px solid #3b4252;'>"
                f"자사 재고: <b style='color: {bd_stats.get('stock_color', '#38bdf8')};'>{bd_stats.get('current_stock_count', 0)}대</b> <span style='color:#94a3b8;'>({bd_stats.get('current_stock_desc', '미보유')})</span>"
                f"</span>"
                f"{sold_badge_html}"
                f"</div>"
                f"</div>"
                f"<div style='color: #e2e8f0; font-size: 0.95em; line-height: 1.55;'>"
                f"{bd_stats.get('turnover_desc', '')} 👉 <span style='color: #f59e0b; font-weight: bold;'>{bd_stats.get('rec_strategy', '')}</span>"
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
        # 실시간 엔카 스캔 데이터는 이미 정밀 스마트 밴드(±1년 등)가 적용되어 있으므로 1년 단위 추가 컷을 적용하지 않고 22대 온전히 표출
        is_live_encar = '상태' in chart_base.columns and (chart_base['상태'] == '실시간').any()
        if not is_live_encar and current_f_year and '연식' in chart_base.columns:
            year_subset = chart_base[chart_base['연식'].astype(str).str.contains(str(current_f_year).strip())]
            if not year_subset.empty:
                chart_base = year_subset

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
                    '사운드': 40, '크렐': 40, '보스': 40, 'JBL': 40, '렉시콘': 40
                }

                def score_key_options(opt_list_or_str):
                    text = " ".join(opt_list_or_str) if isinstance(opt_list_or_str, list) else str(opt_list_or_str)
                    matched_opts = []
                    score = 0
                    for k, w in KEY_OPT_WEIGHTS.items():
                        if k in text:
                            norm_k = '선루프' if '선루프' in k else ('HUD' if k in ('HUD', '헤드업') else ('어라운드뷰' if '라운드뷰' in k or '모니터링' in k else ('주행보조' if k in ('드라이브와이즈', '스마트센스', '반자율', 'ASCC') else k)))
                            if norm_k not in matched_opts:
                                matched_opts.append(norm_k)
                                score += w
                    return score, matched_opts

                # 차량 연식 확인 및 연식별 옵션 잔존가치 인정비율 산출
                target_year_val = None
                hd_year_val = st.session_state.get('hd_target_year')
                if hd_year_val:
                    try:
                        target_year_val = int(str(hd_year_val)[:4])
                    except Exception:
                        pass
                if not target_year_val and '연식' in chart_base.columns:
                    try:
                        extracted_years = chart_base['연식'].astype(str).str.extract(r'(\d{4})')[0].dropna().astype(int)
                        if not extracted_years.empty:
                            target_year_val = int(extracted_years.median())
                    except Exception:
                        pass
                if not target_year_val:
                    target_year_val = 2022
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
                            # 가격 정보가 없는 경우 점수 기반 가상 원가 추정
                            target_opt_new = int(target_score * 1.5)
                else:
                    # fallback: 리스트에서 선택한 차량의 옵션 참조
                    active_selected = str(st.session_state.get('selected_car_id', '')).strip()
                    matched_sel = chart_base[chart_base['_carid'].astype(str).str.strip() == active_selected] if (active_selected and '_carid' in chart_base.columns) else pd.DataFrame()
                    if not matched_sel.empty and pd.notna(matched_sel.iloc[0].get('추가옵션')):
                        sel_opt_str = str(matched_sel.iloc[0].get('추가옵션'))
                        target_opt_new = extract_option_val(sel_opt_str)
                        target_score, target_opt_names = score_key_options(sel_opt_str)

                # 옵션 가치 차액에 연식 감가율(opt_ratio) 적용
                if (target_opt_new > 0 or avg_opt_new > 0) and target_opt_new != avg_opt_new:
                    opt_adj = int(round((target_opt_new - avg_opt_new) * opt_ratio))
                elif target_score != avg_opt_score:
                    opt_adj = int(round((target_score - avg_opt_score) * opt_ratio))
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
            bubble_color = "#ef4444" if bubble_gap > 50 else ("#f59e0b" if bubble_gap > 0 else "#22c55e")
            bubble_desc = "시장 호가에 마진/거품 형성 중" if bubble_gap > 0 else "시장 호가가 매우 보수적으로 형성됨"
            safe_bid_limit = max(0, b_ind - 180)  # 기대마진 150만 + 부대비용 30만 기준

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
            • 평가 스펙: 주행 {user_target_mil:,}km / {target_acc_status if target_acc_status else '완전무사고'}
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

                # 산점도에서 선택된 차량이 있다면 표의 실제 체크박스(selection)에 즉시 동기화
                curr_selected_id = str(st.session_state.get('selected_car_id', '')).strip()
                target_sel_rows = []
                if curr_selected_id and '_carid' in display_df.columns:
                    matched_positions = [
                        i for i, cid in enumerate(display_df['_carid'])
                        if str(cid).strip() == curr_selected_id
                    ]
                    if matched_positions:
                        target_sel_rows = [matched_positions[0]]

                # 세션 상태 주입으로 표 기본 체크박스를 켬
                if target_sel_rows and st.session_state.get('last_selected_source') == 'scatter':
                    st.session_state["encar_car_table"] = {
                        "selection": {
                            "rows": target_sel_rows,
                            "columns": [],
                            "cells": []
                        }
                    }
                    st.session_state.prev_table_idx = target_sel_rows[0]

                try:
                    styled_df = display_df.style.set_properties(
                        subset=[c for c in ['주행거리', '판매가'] if c in display_df.columns],
                        **{'font-size': '1.05em', 'font-weight': 'bold'}
                    ).format(precision=0)

                    event = st.dataframe(
                        styled_df,
                        key="encar_car_table",
                        column_config={
                            "상태": st.column_config.TextColumn("상태"),
                            "성능일": st.column_config.TextColumn("성능일"),
                            "차량명": st.column_config.TextColumn("차량명"),
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
                            "성능일", "차량명", "세부모델", "연식", 
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
                selected_encar_row = None

                # 1. 표(DataFrame)에서 행을 새로 클릭한 경우 (이전 클릭 인덱스와 다를 때만 갱신)
                curr_table_idx = selected_rows[0] if selected_rows else None
                if curr_table_idx is not None and curr_table_idx != st.session_state.get('prev_table_idx'):
                    st.session_state.prev_table_idx = curr_table_idx
                    st.session_state.last_selected_source = 'table'
                    if curr_table_idx < len(display_df):
                        selected_encar_row = display_df.iloc[curr_table_idx]
                        st.session_state.selected_car_id = str(selected_encar_row.get('_carid', '')).strip()
                elif st.session_state.get('selected_car_id'):
                    # 세션에 저장된 car_id (산점도 또는 이전 선택) 우선 반영
                    target_id = str(st.session_state.get('selected_car_id', '')).strip()
                    matched = display_df[display_df['_carid'].astype(str).str.strip() == target_id]
                    if not matched.empty:
                        selected_encar_row = matched.iloc[0]
                elif curr_table_idx is not None and curr_table_idx < len(display_df):
                    selected_encar_row = display_df.iloc[curr_table_idx]

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
                            # 세션 캐싱 - 동일 carid는 api.encar.com을 재호출하지 않음 (봇 차단 방지)
                            cache_key = f"_damage_cache_{carid}"
                            if cache_key in st.session_state:
                                return st.session_state[cache_key]
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

                            st.session_state[cache_key] = damage_dict
                            return damage_dict
                        except Exception:
                            st.session_state[f"_damage_cache_{carid}"] = {}
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
        is_live_encar = '상태' in chart_base.columns and (chart_base['상태'] == '실시간').any()
        if not is_live_encar and current_f_year and '연식' in chart_base.columns:
            year_subset = chart_base[chart_base['연식'].astype(str).str.contains(str(current_f_year).strip())]
            if not year_subset.empty:
                chart_base = year_subset

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

                # 산점도에서 점 클릭 시 선택 차량 세션 갱신 (무한 리런 원천 차단)
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

                            curr_sel_id = str(st.session_state.get('selected_car_id', ''))
                            if clicked_carid and clicked_carid != curr_sel_id:
                                st.session_state.selected_car_id = clicked_carid
                                st.session_state.last_selected_source = 'scatter'
                                # 표의 이전 선택을 무효화하여 핑퐁 리런 루프 방지
                                st.session_state.prev_table_idx = -1
                                st.rerun()
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

                    is_export_car = bool(row.get('수출여부'))
                    export_badge = "<span style='background:#0284c7; color:#ffffff; padding:2px 8px; border-radius:6px; font-size:0.75em; font-weight:bold; margin-right:6px;'>🚢 수출딜러 낙찰</span>" if is_export_car else ""

                    card_html = (
                        f'<div style="background-color:#121317; padding:16px; border-radius:8px; border:1px solid #2e3038;">'
                        f'<div style="font-size:1.1em; font-weight:bold; color:#ffffff; margin-bottom:4px;">{row.get("차량명", "헤이딜러 매물")}</div>'
                        f'<div style="font-size:0.85em; color:#9194a1; margin-bottom:10px;">{row.get("연식", "-")} · {row.get("주행거리", "-")}</div>'
                        f'<div style="font-size:1.3em; font-weight:bold; color:#cc9166; margin-bottom:10px; display:flex; align-items:center;">{export_badge}{row.get("낙찰가", "-")}</div>'
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
