# views/tab_ledger.py
import os
import re
from datetime import datetime
import pandas as pd
import streamlit as st
from services.settlement_service import get_auto_fee_rate, recalc_settlement_df
from services.encar_service import Scraper
from sales_analysis import SalesDataAnalyzer

def render_ledger_tab(LEDGER_FILE='my_car_ledger.csv', SETTLEMENT_FILE='my_inventory_settlement.csv'):
    st.markdown("### 📋 내 실전 장부 리스트")
    st.caption("💡 낙찰/매입된 차량의 [📦 매입 확정]을 누르면 `💰 실전 재고 및 정산 관리` 탭으로 이동하여 실제 판매 및 내 실수익을 정산합니다.")

    if not st.session_state.my_ledger_data.empty:
        disp_ledger_df = st.session_state.my_ledger_data.copy()
        if '등록일' in disp_ledger_df.columns:
            disp_ledger_df = disp_ledger_df.sort_values(by='등록일', ascending=False, kind='mergesort')

        # 상단에 매입 확정 처리 폼
        c_num_list = [str(x) for x in disp_ledger_df['차량번호'].dropna().unique() if str(x).strip()]
        if c_num_list:
            # 선택된 차량번호 결정
            current_sel_car = st.session_state.get('selected_ledger_car', c_num_list[0])
            if current_sel_car not in c_num_list:
                current_sel_car = c_num_list[0]
                st.session_state['selected_ledger_car'] = current_sel_car
            default_box_idx = c_num_list.index(current_sel_car)

            buy_col1, buy_col2, buy_col3, buy_col4 = st.columns([2.5, 2, 2, 2.5])
            with buy_col1:
                sel_buy_car = st.selectbox(
                    "📦 차량번호 선택:", 
                    c_num_list, 
                    index=default_box_idx,
                    key=f"sel_buy_car_{current_sel_car}"
                )
                if sel_buy_car != current_sel_car:
                    st.session_state['selected_ledger_car'] = sel_buy_car
                    st.rerun()

            with buy_col2:
                # 선택한 차량의 기본 정보 조회
                matched_rows = disp_ledger_df[disp_ledger_df['차량번호'] == current_sel_car]
                default_buy_price = 0
                if not matched_rows.empty:
                    p_val = matched_rows.iloc[0].get('매입가', 0)
                    try: default_buy_price = int(float(p_val)) if p_val and str(p_val).strip() else 0
                    except: default_buy_price = 0
                actual_buy_price = st.number_input("실제 낙찰/매입가 (만원):", min_value=0, value=default_buy_price, step=10, key=f"act_buy_price_{current_sel_car}")
            with buy_col3:
                st.write("")
                st.write("")
                if st.button("🚀 매입 확정", use_container_width=True, type="primary"):
                    if not matched_rows.empty:
                        t_row = matched_rows.iloc[0]
                        # 이미 등록되어 있는지 확인
                        already_exists = False
                        if not st.session_state.my_settlement_data.empty:
                            already_exists = sel_buy_car in st.session_state.my_settlement_data['차량번호'].astype(str).values

                        if already_exists:
                            st.warning(f"⚠️ {sel_buy_car} 차량은 이미 [재고 및 정산 관리]에 등록되어 있습니다.")
                        else:
                            today_str = datetime.now().strftime("%m. %d")
                            seq_num = len(st.session_state.my_settlement_data) + 1

                            c_brand = str(t_row.get('제조사', '')).strip()
                            c_name = str(t_row.get('차량명', '')).strip()
                            c_sub = str(t_row.get('세부모델', '')).strip()
                            c_full_name = f"{c_brand} {c_name} {c_sub}".strip() if (c_brand or c_name or c_sub) else sel_buy_car

                            p_sell_val = t_row.get('판매가', 0)
                            try: p_sell_num = int(float(p_sell_val)) if p_sell_val and str(p_sell_val).strip() else 0
                            except: p_sell_num = 0

                            ext_count = t_row.get('외판수리', 0)
                            try: ext_count_num = int(float(ext_count)) if ext_count else 0
                            except: ext_count_num = 0

                            ext_c = t_row.get('외판수리비', 0)
                            try: ext_c_num = int(float(ext_c)) if ext_c else (ext_count_num * 13)
                            except: ext_c_num = (ext_count_num * 13)

                            h_fee = t_row.get('헤딜수수료', 0)
                            try: h_fee_num = int(float(h_fee)) if h_fee else 0
                            except: h_fee_num = 0

                            new_settle_item = {
                                '순차': seq_num,
                                '매입일': today_str,
                                '상태': '보유/상품화중',
                                '차량번호': sel_buy_car,
                                '차종': c_full_name,
                                '판매가': p_sell_num,
                                '재고일': 0,
                                '매입가': actual_buy_price,
                                '외판수리': ext_count_num,
                                '상품화': ext_c_num,
                                '헤딜수수료': h_fee_num,
                                '기본제경비': 15,
                                '공헌이익': 0,
                                '실수익': 0,
                                '수수료율': 0.10,
                                '판매수수료': int(round(p_sell_num * 0.007)) if p_sell_num > 0 else 0,
                                '수수료율_수동': 0.0
                            }
                            st.session_state.my_settlement_data = pd.concat([pd.DataFrame([new_settle_item]), st.session_state.my_settlement_data], ignore_index=True)
                            st.session_state.my_settlement_data.to_csv(SETTLEMENT_FILE, index=False, encoding='utf-8-sig')

                            st.session_state.my_ledger_data.loc[st.session_state.my_ledger_data['차량번호'] == sel_buy_car, '상태'] = '매입완료'
                            st.session_state.my_ledger_data.to_csv(LEDGER_FILE, index=False, encoding='utf-8-sig')

                            st.success(f"🎉 {sel_buy_car} 차량이 [실전 재고 및 정산 관리] 탭으로 이동되었습니다!")
                            st.rerun()

            with buy_col4:
                st.write("")
                st.write("")
                if st.button("🔍 동급 시세 분석", use_container_width=True, help="메인 시세 분석 화면으로 이동하여 이 차량의 동급 매물을 자동 스캔합니다."):
                    if not matched_rows.empty:
                        t_row = matched_rows.iloc[0]
                        c_brand = str(t_row.get('제조사', '')).strip()
                        c_name = str(t_row.get('차량명', '')).strip()
                        c_sub = str(t_row.get('세부모델', '')).strip()
                        full_c_text = f"{c_brand} {c_name} {c_sub}".strip()
                        
                        target_url = SalesDataAnalyzer.generate_encar_url(c_name, c_sub)
                        if target_url:
                            # 1. 폼 리셋 키 버전업 ➔ 기존 사이드바의 헤이딜러 URL 및 연식/키로수 위젯 캐시 완전 리셋!
                            st.session_state.form_reset_key = st.session_state.get('form_reset_key', 0) + 1
                            new_k = st.session_state.form_reset_key

                            # 2. 이전 헤이딜러 세션 찌꺼기 완벽 클리어
                            stale_keys = [
                                'hd_target_url', 'hd_url_input', 'hd_detail_data', 'hd_target_options', 
                                'encar_target_options', 'hd_model_part_name', 'hd_grade_part_name', 
                                'hd_full_name', 'auto_encar_url', 'hd_comp_df', 'hd_car_spec_desc', 'hd_target_opt_price'
                            ]
                            for stale_k in stale_keys:
                                if stale_k in st.session_state:
                                    st.session_state[stale_k] = [] if 'options' in stale_k else ""

                            # 연식, 키로수 주입
                            yr_str = str(t_row.get('연식', ''))
                            m_yr = re.search(r'(\d{2,4})', yr_str)
                            if m_yr:
                                parsed_y = int(m_yr.group(1))
                                if parsed_y < 100: parsed_y += 2000
                                two_digit_yr = parsed_y % 100
                                st.session_state[f"search_year_{new_k}"] = two_digit_yr
                                st.session_state[f"search_year_num_{new_k}"] = two_digit_yr
                                st.session_state['f_year'] = f"{two_digit_yr:02d}"
                                st.session_state['hd_target_year'] = parsed_y
                            
                            mil_str = str(t_row.get('주행거리', ''))
                            m_mil = re.sub(r'[^\d]', '', mil_str)
                            if m_mil:
                                parsed_m = int(m_mil)
                                st.session_state[f"mil_{new_k}"] = parsed_m
                                st.session_state['f_mil'] = parsed_m
                                st.session_state['user_target_mil'] = parsed_m
                                st.session_state['hd_target_mil'] = parsed_m
                            
                            st.session_state[f"car_num_{new_k}"] = sel_buy_car
                            st.session_state[f"hd_url_box_{new_k}"] = ""
                            st.session_state['target_car_name'] = full_c_text
                            st.session_state['target_sub_model'] = c_sub
                            st.session_state['f_sub'] = c_sub if c_sub else "전체"
                            st.session_state['auto_scan_url'] = target_url
                            st.session_state['nav_target'] = "📊 시세 분석 및 스캔"
                            st.session_state['nav_selection'] = "📊 시세 분석 및 스캔"
                            st.session_state['nav_selection_box'] = "📊 시세 분석 및 스캔"
                            st.rerun()
                        else:
                            st.error("동급 매물 검색 조건을 생성하지 못했습니다.")

        # 표시용 컬럼 정리 및 외판수리 기본값 보정
        if '외판수리' not in disp_ledger_df.columns:
            disp_ledger_df['외판수리'] = 0
        disp_ledger_df['외판수리'] = pd.to_numeric(disp_ledger_df['외판수리'], errors='coerce').fillna(0).astype(int)

        ledger_display_order = [
            '등록일', '차량번호', '제조사', '차량명', '세부모델', '연식', '주행거리', 
            '외판수리', '매입가', '판매가', '외판수리비', '헤딜수수료', '특이사항', '상태'
        ]
        # 실존하는 컬럼만 필터링
        final_ledger_cols = [col for col in ledger_display_order if col in disp_ledger_df.columns]
        # 나머지 혹시 모를 추가 컬럼 뒤에 붙이기
        final_ledger_cols += [col for col in disp_ledger_df.columns if col not in final_ledger_cols]

        # 원클릭 반응형 장부 테이블 (체크박스 없이 줄 전체 어디든 클릭 시 즉시 선택)
        st.markdown("""
        <style>
        .ledger-table-container {
            width: 100%;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #232733;
            background: #0f1117;
            margin-top: 10px;
        }
        .ledger-header-row {
            display: flex;
            background: #181b24;
            padding: 10px 14px;
            border-bottom: 2px solid #282c3c;
            color: #8b92a5;
            font-size: 0.82rem;
            font-weight: 700;
        }
        .ledger-data-row {
            display: flex;
            align-items: center;
            padding: 9px 14px;
            border-bottom: 1px solid #1a1d27;
            font-size: 0.88rem;
            transition: all 0.15s ease-in-out;
            cursor: pointer;
        }
        .ledger-data-row:hover {
            background-color: #1e2230 !important;
        }
        .ledger-data-row.active {
            background-color: #24293d !important;
            border-left: 4px solid #3b82f6 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # 헤더 라인
        h_cols = st.columns([1.1, 1.3, 1.1, 2.0, 1.8, 0.8, 1.4, 0.8, 1.2, 1.2, 1.0, 1.2])
        headers = ["등록일", "차량번호", "제조사", "차량명", "세부모델", "연식", "주행거리", "외판", "매입가", "판매가", "상태", "선택"]
        with st.container():
            st.markdown(f"""
            <div style="display:flex; background:#181b24; padding:8px 12px; border-radius:6px; border:1px solid #2a2e3f; margin-bottom:6px; font-size:0.83rem; font-weight:700; color:#94a3b8;">
                <div style="flex:1.0;">📅 등록일</div>
                <div style="flex:1.3;">🚘 차량번호</div>
                <div style="flex:1.0;">🏭 제조사</div>
                <div style="flex:2.0;">🚗 차량명</div>
                <div style="flex:1.8;">🏷️ 세부모델</div>
                <div style="flex:0.7; text-align:center;">연식</div>
                <div style="flex:1.3; text-align:right;">주행거리</div>
                <div style="flex:0.8; text-align:center;">외판</div>
                <div style="flex:1.2; text-align:right;">매입가</div>
                <div style="flex:1.2; text-align:right;">판매가</div>
                <div style="flex:1.0; text-align:center;">상태</div>
                <div style="flex:1.0; text-align:center;">선택</div>
            </div>
            """, unsafe_allow_html=True)

            # 각 행 렌더링 (최대 30개 표시)
            for idx, r in disp_ledger_df.head(30).iterrows():
                c_num = str(r.get('차량번호', '')).strip()
                is_selected = (c_num == current_sel_car)
                
                bg_color = "#1d233a" if is_selected else ("#12151e" if idx % 2 == 0 else "#0d0f15")
                border_style = "2px solid #3b82f6" if is_selected else "1px solid #1c202d"
                badge_color = "#3b82f6" if is_selected else "#64748b"

                row_col_info, row_col_btn = st.columns([11, 1.2])
                with row_col_info:
                    reg_date = str(r.get('등록일', ''))
                    brand = str(r.get('제조사', ''))
                    c_name = str(r.get('차량명', ''))
                    c_sub = str(r.get('세부모델', ''))
                    c_yr = str(r.get('연식', ''))
                    c_mil = str(r.get('주행거리', ''))
                    ext_cnt = f"{int(r.get('외판수리', 0))}판" if r.get('외판수리') else "0판"
                    
                    b_price = f"{int(float(r.get('매입가', 0))):,}만" if r.get('매입가') and str(r.get('매입가')).strip() != '0' else "-"
                    s_price = f"{int(float(r.get('판매가', 0))):,}만" if r.get('판매가') and str(r.get('판매가')).strip() != '0' else "-"
                    status_val = str(r.get('상태', '보유중'))
                    status_badge = f"<span style='background:#065f46; color:#34d399; padding:2px 6px; border-radius:4px; font-size:0.75rem;'>{status_val}</span>" if '완료' in status_val else f"<span style='background:#1e293b; color:#94a3b8; padding:2px 6px; border-radius:4px; font-size:0.75rem;'>{status_val}</span>"

                    st.markdown(f"""
                    <div style="display:flex; align-items:center; background:{bg_color}; padding:8px 12px; border-radius:6px; border:{border_style}; margin-bottom:4px; font-size:0.86rem; color:#e2e8f0;">
                        <div style="flex:1.0; color:#94a3b8; font-size:0.8rem;">{reg_date}</div>
                        <div style="flex:1.3; font-weight:800; color:{'#60a5fa' if is_selected else '#ffffff'};">{c_num}</div>
                        <div style="flex:1.0; color:#cbd5e1;">{brand}</div>
                        <div style="flex:2.0; font-weight:700;">{c_name}</div>
                        <div style="flex:1.8; color:#94a3b8; font-size:0.82rem;">{c_sub}</div>
                        <div style="flex:0.7; text-align:center; color:#94a3b8;">{c_yr}</div>
                        <div style="flex:1.3; text-align:right; font-weight:600;">{c_mil}</div>
                        <div style="flex:0.8; text-align:center; color:#f59e0b;">{ext_cnt}</div>
                        <div style="flex:1.2; text-align:right; font-weight:700; color:#34d399;">{b_price}</div>
                        <div style="flex:1.2; text-align:right; font-weight:700; color:#60a5fa;">{s_price}</div>
                        <div style="flex:1.0; text-align:center;">{status_badge}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with row_col_btn:
                    btn_label = "✅ 선택됨" if is_selected else "👉 선택"
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(btn_label, key=f"sel_btn_{c_num}_{idx}", type=btn_type, use_container_width=True):
                        if current_sel_car != c_num:
                            st.session_state['selected_ledger_car'] = c_num
                            st.rerun()
    else:
        st.info("아직 저장된 장부 내역이 없습니다. 좌측 장부 입력폼을 통해 타점을 기록해 보세요!")



def render_completed_tab(SETTLEMENT_FILE='my_inventory_settlement.csv'):
    st.markdown("### 🎉 판매완료 정산 내역")
    st.caption("📋 판매가 완료된 차량들의 최종 확정 매출, 공헌이익, 그리고 내 실수익을 확인·관리합니다.")

    completed_mask = (st.session_state.my_settlement_data['상태'] == '판매완료') if not st.session_state.my_settlement_data.empty else pd.Series(dtype=bool)
    completed_df = st.session_state.my_settlement_data[completed_mask].copy() if not st.session_state.my_settlement_data.empty else pd.DataFrame()

    total_sold_count = len(completed_df)
    total_sales_revenue = int(completed_df['판매가'].sum()) if not completed_df.empty else 0
    total_net_profit = int(completed_df['공헌이익'].sum()) if not completed_df.empty else 0
    total_my_take = int(completed_df['실수익'].sum()) if not completed_df.empty else 0

    # 상단 최종 성과 대시보드 카드
    st.markdown(f"""
    <div style='display: flex; gap: 12px; margin-top: 8px; margin-bottom: 16px;'>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>🏆</div>
            <div class='metric-content'>
                <h4>총 판매완료 대수</h4>
                <h2 style='color:#4ade80;'>{total_sold_count:,} 대</h2>
            </div>
        </div>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>📈</div>
            <div class='metric-content'>
                <h4>누적 총 매출(판매가)</h4>
                <h2>{total_sales_revenue:,} 만원</h2>
            </div>
        </div>
        <div class='metric-card' style='flex: 1;'>
            <div class='metric-icon'>📊</div>
            <div class='metric-content'>
                <h4>누적 총 공헌이익</h4>
                <h2 style='color: {"#38bdf8" if total_net_profit >= 0 else "#f87171"};'>{total_net_profit:,} 만원</h2>
            </div>
        </div>
        <div class='metric-card' style='flex: 1.2; border: 1.5px solid #cc9166 !important;'>
            <div class='metric-icon' style='background: #2a1f18 !important;'>💰</div>
            <div class='metric-content'>
                <h4 style='color:#cc9166;'>내 정산 실수익 총합 (내 수익)</h4>
                <h2 style='color: {"#4ade80" if total_my_take >= 0 else "#f87171"}; font-weight:900;'>{total_my_take:,} 만원</h2>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not completed_df.empty:
        st.markdown("#### 📜 판매완료 최종 확정 정산표 (단위: 만원)")
        st.caption("💡 각 차량별 최종 판매 결과입니다. 필요 시 셀을 더블클릭하여 최종 숫자를 보정하실 수 있습니다.")

        comp_view_cols = [
            '순차', '매입일', '차량번호', '차종', '판매가', '재고일', '매입가', 
            '외판수리', '상품화', '헤딜수수료', '기본제경비', '공헌이익', '실수익', 
            '수수료율', '판매수수료'
        ]

        comp_settle_cfg = {
            "순차": st.column_config.NumberColumn("순차", width=45, format="%d"),
            "매입일": st.column_config.TextColumn("매입일", width=65),
            "차량번호": st.column_config.TextColumn("차량번호", width=95),
            "차종": st.column_config.TextColumn("차종", width=160),
            "판매가": st.column_config.NumberColumn("판매가", width=70, format="%d"),
            "재고일": st.column_config.NumberColumn("재고일", width=55, format="%d일"),
            "매입가": st.column_config.NumberColumn("매입가", width=70, format="%d"),
            "외판수리": st.column_config.NumberColumn("외판수", width=55, format="%d"),
            "상품화": st.column_config.NumberColumn("상품화", width=65, format="%d"),
            "헤딜수수료": st.column_config.NumberColumn("수수료", width=65, format="%d"),
            "기본제경비": st.column_config.NumberColumn("제경비", width=65, format="%d"),
            "공헌이익": st.column_config.NumberColumn("공헌이익", width=70, format="%d"),
            "실수익": st.column_config.NumberColumn("실수익", width=70, format="%d"),
            "수수료율": st.column_config.NumberColumn("수수료율", width=65, format="%.2f"),
            "판매수수료": st.column_config.NumberColumn("판매수수료", width=70, format="%d"),
        }

        edited_comp_df = st.data_editor(
            completed_df[comp_view_cols],
            use_container_width=False,
            height=380,
            hide_index=True,
            column_config=comp_settle_cfg,
            key="completed_settlement_data_editor"
        )

        # 수정사항 동기화
        current_comp_view = completed_df[comp_view_cols]
        comp_changed = False
        for c in comp_view_cols:
            if not (edited_comp_df[c].fillna(0).astype(str) == current_comp_view[c].fillna(0).astype(str)).all():
                comp_changed = True
                break

        if comp_changed:
            for idx in edited_comp_df.index:
                car_num = str(edited_comp_df.at[idx, '차량번호'])
                for c in comp_view_cols:
                    st.session_state.my_settlement_data.loc[st.session_state.my_settlement_data['차량번호'].astype(str) == car_num, c] = edited_comp_df.at[idx, c]
            st.session_state.my_settlement_data = recalc_settlement_df(st.session_state.my_settlement_data, auto_fee_rate)
            st.session_state.my_settlement_data.to_csv(SETTLEMENT_FILE, index=False, encoding='utf-8-sig')
            st.rerun()

        # 잘못 판매완료 처리했을 때를 대비한 복구 기능
        st.markdown("---")
        c_rec1, c_rec2, c_rec3 = st.columns([3, 2, 5])
        with c_rec1:
            restore_target_car = st.selectbox("↩️ 다시 보유재고로 복구할 차량:", ["선택..."] + list(completed_df['차량번호'].unique()), key="restore_car_box")
        with c_rec2:
            st.write("")
            st.write("")
            if st.button("보유재고로 복구", use_container_width=True, key="btn_restore_car"):
                if restore_target_car != "선택...":
                    st.session_state.my_settlement_data.loc[st.session_state.my_settlement_data['차량번호'].astype(str) == restore_target_car, '상태'] = '보유재고'
                    st.session_state.my_settlement_data.to_csv(SETTLEMENT_FILE, index=False, encoding='utf-8-sig')
                    st.success(f"↩️ {restore_target_car} 차량이 다시 [보유 재고 관리] 탭으로 복구되었습니다!")
                    st.rerun()
    else:
        st.info("아직 판매완료된 차량이 없습니다. [💰 실전 재고 및 정산 관리] 탭에서 판매된 차량의 [판매완료]를 체크하시면 여기에 정산 내역이 기록됩니다.")




def _prepare_inventory_dfs(current_f_year="", apply_filter=True):
    inv_df = pd.DataFrame()
    if 'inventory_data' in st.session_state and not st.session_state.inventory_data.empty:
        inv_df = st.session_state.inventory_data.copy()
    elif os.path.exists("autoplus_inventory.csv"):
        for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
            try:
                inv_df = pd.read_csv("autoplus_inventory.csv", encoding=enc)
                st.session_state.inventory_data = inv_df.copy()
                break
            except Exception:
                continue
        
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
        
        for req_col in ["최종수정일", "차량명", "링크", "세부모델", "연식", "주행거리", "재고", "판매가", "매입가", "색상", "홈페이지상태"]:
            if req_col not in inv_df.columns:
                inv_df[req_col] = ""
                
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
            if link.startswith('http'):
                return link
            return None
            
        inv_df['엔카 링크'] = inv_df.apply(extract_encar_link, axis=1)

        disp_cols = ["차량번호", "최종수정일", "차량명", "세부모델", "연식", "주행거리", "재고", "판매가", "매입가", "색상", "엔카 링크"]
        out_df = inv_df[disp_cols + ["홈페이지상태"]].copy()
        
        filter_applied_info = ""
        if apply_filter:
            full_names = out_df['차량명'].astype(str) + " " + out_df['세부모델'].astype(str)
            full_names_clean = full_names.str.replace(" ", "").str.lower()

            f_name_val = st.session_state.get('f_name', '전체')
            f_sub_val = st.session_state.get('f_sub', '전체')
            
            # 1단계: 차량명(f_name) 매칭
            if f_name_val != "전체":
                name_clean = str(f_name_val).replace(" ", "").lower()
                matched_mask = full_names_clean.str.contains(name_clean, na=False, regex=False)
                if matched_mask.any():
                    out_df = out_df[matched_mask]
                    full_names_clean = full_names_clean[out_df.index]
                    filter_applied_info = f"차종: {f_name_val}"
                
            # 2단계: 세부등급 매칭 (단, 결과가 0건이 되면 세부등급 필터는 스킵하고 차종 수준 유지)
            if f_sub_val != "전체" and not out_df.empty:
                sub_parts = [p for p in str(f_sub_val).split() if len(p) > 1]
                temp_df = out_df.copy()
                temp_names = full_names_clean.copy()
                for part in sub_parts:
                    part_clean = part.replace(" ", "").lower()
                    mask = temp_names.str.contains(part_clean, na=False, regex=False)
                    if mask.any():
                        temp_df = temp_df[mask]
                        temp_names = temp_names[temp_df.index]
                if not temp_df.empty:
                    out_df = temp_df
                    filter_applied_info += f" / 세부등급: {f_sub_val}"
                    
            # 3단계: 연식 매칭 (결과가 0건이 되면 완화)
            if current_f_year and not out_df.empty:
                year_clean = str(current_f_year).strip()
                # 2자리 연식이면 (예: '19') -> '2019' 또는 '19'
                if len(year_clean) == 2:
                    yr_regex = f"(20{year_clean}|19{year_clean}|^{year_clean})"
                else:
                    yr_regex = year_clean
                mask_yr = out_df['연식'].astype(str).str.contains(yr_regex, na=False, regex=True)
                if mask_yr.any():
                    out_df = out_df[mask_yr]
                    filter_applied_info += f" / 연식: {current_f_year}"
        
        ccfg = {
            "차량번호": st.column_config.TextColumn("차량번호"),
            "차량명": st.column_config.TextColumn("차량명"),
            "판매가": st.column_config.NumberColumn("판매가(만)", format="%d"),
            "매입가": st.column_config.NumberColumn("매입가(만)", format="%d"),
            "엔카 링크": st.column_config.LinkColumn("엔카 매물 링크", display_text="🔗 엔카 보기"),
        }
                
        status_col = out_df['홈페이지상태'].astype(str).str.strip()
        sales_df = out_df[status_col != '판매중'][disp_cols]
        stock_df = out_df[status_col == '판매중'][disp_cols]
        return sales_df, stock_df, ccfg, filter_applied_info
    return None, None, None, ""

def _trigger_market_scan_from_inventory(selected_row):
    """자사 재고/판매 차량 정보를 메인 화면 시세 분석으로 주입하고 이동하는 함수"""
    c_no = str(selected_row.get('차량번호', '')).strip()
    c_name = str(selected_row.get('차량명', '')).strip()
    c_sub = str(selected_row.get('세부모델', '')).strip()
    full_c_text = f"{c_name} {c_sub}".strip() if (c_name or c_sub) else c_no
    
    encar_link = str(selected_row.get('엔카 링크', '')).strip()
    if not encar_link.startswith('http') and '링크' in selected_row:
        cand_l = str(selected_row.get('링크', '')).strip()
        if cand_l.startswith('http'): encar_link = cand_l

    target_search_url = ""
    target_car_name = c_name
    target_sub_model = c_sub
    target_mil = 0
    target_year = 0
    target_acc = "완전무사고"

    # 주행거리
    raw_mil = str(selected_row.get('주행거리', 0)).replace(',', '').strip()
    try:
        m_val = int(float(raw_mil))
        if m_val > 0: target_mil = m_val
    except Exception:
        pass

    # 연식
    yr_str = str(selected_row.get('연식', ''))
    m_yr = re.search(r'(\d{2,4})', yr_str)
    if m_yr:
        y_num = int(m_yr.group(1))
        target_year = (2000 + y_num) if y_num < 100 else y_num

    # 1순위: 엔카 링크 역추적
    if encar_link and encar_link.startswith('http'):
        res = Scraper.build_search_from_car_url(encar_link)
        if res.get("success"):
            target_search_url = res.get("search_url", "")
            if res.get("car_name"): target_car_name = res["car_name"]
            if res.get("grade"): target_sub_model = res["grade"]
            if res.get("mileage", 0) > 0: target_mil = res["mileage"]
            if res.get("year", 0) > 0: target_year = res["year"]
            target_acc = res.get("accident", target_acc)

    # 2순위: 엔카 URL이 없거나 실패 시 차종명 기반 생성
    if not target_search_url and target_car_name:
        target_search_url = SalesDataAnalyzer.generate_encar_url(target_car_name, target_sub_model)

    if target_search_url:
        # 1. 폼 리셋 키 버전업
        st.session_state.form_reset_key = st.session_state.get('form_reset_key', 0) + 1
        new_k = st.session_state.form_reset_key

        # 2. 세션 찌꺼기 클리어
        stale_keys = [
            'hd_target_url', 'hd_url_input', 'hd_detail_data', 'hd_target_options', 
            'encar_target_options', 'hd_model_part_name', 'hd_grade_part_name', 
            'hd_full_name', 'auto_encar_url', 'hd_comp_df', 'hd_car_spec_desc', 'hd_target_opt_price',
            'hd_target_mil', 'hd_target_year', 'f_mil'
        ]
        for stale_k in stale_keys:
            if stale_k in st.session_state:
                st.session_state[stale_k] = [] if 'options' in stale_k else ("" if 'part' in stale_k or 'desc' in stale_k or 'url' in stale_k or 'name' in stale_k else 0)

        # 3. 사이드바 및 스캐너 위젯 주입
        two_digit_yr = (target_year % 100) if target_year > 0 else 0
        st.session_state[f"search_year_{new_k}"] = two_digit_yr
        st.session_state[f"search_year_num_{new_k}"] = two_digit_yr
        st.session_state['f_year'] = f"{two_digit_yr:02d}" if two_digit_yr > 0 else ""
        st.session_state['hd_target_year'] = target_year

        if target_mil > 0:
            st.session_state[f"mil_{new_k}"] = target_mil
            st.session_state['f_mil'] = target_mil
            st.session_state['user_target_mil'] = target_mil
            st.session_state['hd_target_mil'] = target_mil
        else:
            st.session_state['user_target_mil'] = 0

        st.session_state[f"car_num_{new_k}"] = c_no
        st.session_state[f"hd_url_box_{new_k}"] = ""

        if target_sub_model:
            st.session_state['target_sub_model'] = target_sub_model
            st.session_state['f_sub'] = target_sub_model
        else:
            st.session_state['target_sub_model'] = ""
            st.session_state['f_sub'] = "전체"

        st.session_state['hd_target_accident'] = target_acc if target_acc else "완전무사고"
        if target_car_name:
            st.session_state['target_car_name'] = target_car_name

        st.session_state['auto_scan_url'] = target_search_url
        st.session_state['nav_target'] = "📊 시세 분석 및 스캔"
        st.session_state['nav_selection'] = "📊 시세 분석 및 스캔"
        st.session_state['nav_selection_box'] = "📊 시세 분석 및 스캔"
        st.rerun()
    else:
        st.error("동급 매물 검색 조건을 생성하지 못했습니다.")

def render_sales_tab(current_f_year=""):
    st.markdown("### 📋 자사 판매 실적 (판매완료)")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        use_filter = st.checkbox("🔍 현재 검색 차량 조건 필터 적용", value=False, key="filter_sales_check")
        
    sales_df, stock_df, ccfg, filter_info = _prepare_inventory_dfs(current_f_year, apply_filter=use_filter)
    if sales_df is not None and not sales_df.empty:
        # 상단 차량번호 직접 입력 & 시세 분석 연동 바
        with st.container():
            st.markdown("""
            <div style="background:#161922; border:1px solid #232738; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
                <span style="font-size:0.92rem; font-weight:700; color:#60a5fa;">🔍 차량번호로 판매완료 차량 시세 분석</span>
                <span style="font-size:0.8rem; color:#94a3b8; margin-left:8px;">차량번호를 직접 입력(예: 123가4567 또는 뒷4자리)하거나 목록에서 선택하면 메인 화면으로 이동하여 즉시 동급 시세를 스캔합니다.</span>
            </div>
            """, unsafe_allow_html=True)
            
            b_c1, b_c2, b_c3 = st.columns([2.2, 3.8, 1.8])
            with b_c1:
                input_c_no = st.text_input("🚘 차량번호 직접 입력:", placeholder="예: 123가4567 또는 4567", key="input_sales_car_no").strip()
            
            # 차량번호 입력이 있으면 해당 매물 자동 필터링된 옵션 제시, 없으면 전체 상위 옵션
            c_options = []
            if input_c_no:
                matched_cand = sales_df[sales_df['차량번호'].astype(str).str.contains(input_c_no, na=False, regex=False)]
            else:
                matched_cand = sales_df

            c_options = [
                f"{row.get('차량번호', '')} | {row.get('차량명', '')} {row.get('세부모델', '')} ({str(row.get('연식', ''))[:4]}년 / {int(float(str(row.get('주행거리', 0)).replace(',', '') or 0)):,}km)"
                for _, row in matched_cand.iterrows()
                if str(row.get('차량번호', '')).strip()
            ]
            
            with b_c2:
                sel_label = f"일치하는 차량 ({len(c_options)}건):" if input_c_no else "또는 목록에서 선택:"
                if c_options:
                    sel_item = st.selectbox(sel_label, c_options, key="sel_sales_car_scan")
                else:
                    st.selectbox(sel_label, ["일치하는 차량번호가 없습니다"], disabled=True, key="sel_sales_car_scan_empty")
                    sel_item = None

            with b_c3:
                st.write("")
                st.write("")
                if st.button("🚀 동급 시세 분석", type="primary", use_container_width=True, key="btn_run_sales_scan"):
                    target_row = None
                    if sel_item and "|" in sel_item:
                        sel_c_no = sel_item.split("|")[0].strip()
                        matched = sales_df[sales_df['차량번호'] == sel_c_no]
                        if not matched.empty: target_row = matched.iloc[0]
                    elif input_c_no:
                        exact_m = sales_df[sales_df['차량번호'].astype(str).str.strip() == input_c_no]
                        if not exact_m.empty: target_row = exact_m.iloc[0]
                        else:
                            part_m = sales_df[sales_df['차량번호'].astype(str).str.contains(input_c_no, na=False, regex=False)]
                            if not part_m.empty: target_row = part_m.iloc[0]

                    if target_row is not None:
                        _trigger_market_scan_from_inventory(target_row)
                    else:
                        st.error("입력한 차량번호에 해당하는 차량을 찾을 수 없습니다.")

        if use_filter and filter_info:
            st.caption(f"ℹ️ 적용된 조건: **{filter_info}** (총 {len(sales_df):,}건)")
        else:
            st.caption(f"ℹ️ 자사 전체 판매완료 데이터: **총 {len(sales_df):,}건**")
            
        st.dataframe(sales_df, use_container_width=True, hide_index=True, height=600, column_config=ccfg)
    elif sales_df is not None:
        st.warning("⚠️ 현재 조건에 일치하는 판매 실적 데이터가 없습니다. 상단의 '현재 검색 차량 조건 필터 적용' 체크를 해제하면 전체 판매 실적을 확인할 수 있습니다.")
    else:
        st.info("👈 자사 재고 엑셀/CSV 파일(`autoplus_inventory.csv`)이 없거나 데이터가 비어 있습니다.")

def render_inventory_tab(current_f_year=""):
    st.markdown("### 📦 자사 보유 재고 (판매중)")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        use_filter = st.checkbox("🔍 현재 검색 차량 조건 필터 적용", value=False, key="filter_inv_check")
        
    sales_df, stock_df, ccfg, filter_info = _prepare_inventory_dfs(current_f_year, apply_filter=use_filter)
    if stock_df is not None and not stock_df.empty:
        # 상단 차량번호 직접 입력 & 시세 분석 연동 바
        with st.container():
            st.markdown("""
            <div style="background:#161922; border:1px solid #232738; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
                <span style="font-size:0.92rem; font-weight:700; color:#34d399;">🚘 차량번호로 보유 재고 시세 분석</span>
                <span style="font-size:0.8rem; color:#94a3b8; margin-left:8px;">차량번호를 직접 입력(예: 123가4567 또는 뒷4자리)하면 즉시 해당 매칭 차량을 찾아 메인 화면 동급 시세 분석으로 전달합니다.</span>
            </div>
            """, unsafe_allow_html=True)
            
            b_c1, b_c2, b_c3 = st.columns([2.2, 3.8, 1.8])
            with b_c1:
                input_c_no = st.text_input("🚘 차량번호 직접 입력:", placeholder="예: 123가4567 또는 4567", key="input_inv_car_no").strip()
            
            if input_c_no:
                matched_cand = stock_df[stock_df['차량번호'].astype(str).str.contains(input_c_no, na=False, regex=False)]
            else:
                matched_cand = stock_df

            c_options = [
                f"{row.get('차량번호', '')} | {row.get('차량명', '')} {row.get('세부모델', '')} ({str(row.get('연식', ''))[:4]}년 / {int(float(str(row.get('주행거리', 0)).replace(',', '') or 0)):,}km)"
                for _, row in matched_cand.iterrows()
                if str(row.get('차량번호', '')).strip()
            ]
            
            with b_c2:
                sel_label = f"일치하는 재고 ({len(c_options)}건):" if input_c_no else "또는 목록에서 선택:"
                if c_options:
                    sel_item = st.selectbox(sel_label, c_options, key="sel_inv_car_scan")
                else:
                    st.selectbox(sel_label, ["일치하는 차량번호가 없습니다"], disabled=True, key="sel_inv_car_scan_empty")
                    sel_item = None

            with b_c3:
                st.write("")
                st.write("")
                if st.button("🚀 동급 시세 분석", type="primary", use_container_width=True, key="btn_run_inv_scan"):
                    target_row = None
                    if sel_item and "|" in sel_item:
                        sel_c_no = sel_item.split("|")[0].strip()
                        matched = stock_df[stock_df['차량번호'] == sel_c_no]
                        if not matched.empty: target_row = matched.iloc[0]
                    elif input_c_no:
                        exact_m = stock_df[stock_df['차량번호'].astype(str).str.strip() == input_c_no]
                        if not exact_m.empty: target_row = exact_m.iloc[0]
                        else:
                            part_m = stock_df[stock_df['차량번호'].astype(str).str.contains(input_c_no, na=False, regex=False)]
                            if not part_m.empty: target_row = part_m.iloc[0]

                    if target_row is not None:
                        _trigger_market_scan_from_inventory(target_row)
                    else:
                        st.error("입력한 차량번호에 해당하는 보유 재고를 찾을 수 없습니다.")

        if use_filter and filter_info:
            st.caption(f"ℹ️ 적용된 조건: **{filter_info}** (총 {len(stock_df):,}건)")
        else:
            st.caption(f"ℹ️ 자사 전체 보유재고 데이터: **총 {len(stock_df):,}건**")
            
        st.dataframe(stock_df, use_container_width=True, hide_index=True, height=600, column_config=ccfg)
    elif stock_df is not None:
        st.warning("⚠️ 현재 조건에 일치하는 보유 재고 데이터가 없습니다. 상단의 '현재 검색 차량 조건 필터 적용' 체크를 해제하면 전체 재고를 확인할 수 있습니다.")
    else:
        st.info("👈 자사 재고 엑셀/CSV 파일(`autoplus_inventory.csv`)이 없거나 데이터가 비어 있습니다.")
