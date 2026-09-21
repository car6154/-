# views/tab_settlement.py
import os
import re
from datetime import datetime
import pandas as pd
import streamlit as st
from sales_analysis import generate_encar_market_url, SalesDataAnalyzer
from services.encar_service import Scraper
from services.settlement_service import get_auto_fee_rate, recalc_settlement_df

def render_settlement_tab(SETTLEMENT_FILE="my_inventory_settlement.csv"):
        st.markdown("### 💰 실전 재고 및 정산 관리 (현재 보유 차량)")
        st.caption("📋 매입 확정 후 현재 보유 중인 재고 차량의 원가와 손익을 관리합니다. 판매가 완료되면 표 맨 끝의 **[판매완료]**를 체크하여 이동하세요.")

        # 1. 구간별 기본 수수료율 함수
        def get_auto_fee_rate(volume):
            if volume <= 12: return 0.10
            elif volume <= 18: return 0.30
            elif volume <= 31: return 0.40
            else: return 0.50

        total_bought_count = len(st.session_state.my_settlement_data)
        auto_fee_rate = get_auto_fee_rate(total_bought_count)

        # 2. 정산 데이터 정규화 및 재계산 단일 함수
        def recalc_settlement_df(df, default_rate):
            if df.empty:
                return df
            now_date = datetime.now()
            for idx, row in df.iterrows():
                if df.at[idx, '순차'] == 0:
                    df.at[idx, '순차'] = idx + 1

                p_sell = row.get('판매가', 0)
                p_buy = row.get('매입가', 0)
                ext_cnt = row.get('외판수리', 0)

                # 기본제경비가 없으면 15만원
                if row.get('기본제경비', 0) == 0:
                    df.at[idx, '기본제경비'] = 15

                # 외판수가 있고 상품화가 0이면 판수 * 13만원
                if row.get('상품화', 0) == 0 and ext_cnt > 0:
                    df.at[idx, '상품화'] = int(ext_cnt * 13)

                # 판매수수료: 판매가의 0.7% (0일 때 자동 계산)
                p_fee = row.get('판매수수료', 0)
                calc_fee = int(round(p_sell * 0.007)) if p_sell > 0 else 0
                if p_fee == 0 and calc_fee > 0:
                    p_fee = calc_fee
                    df.at[idx, '판매수수료'] = p_fee

                # 수수료율: 사용자가 직접 수정한 값이 있으면 그 값을 우선 유지
                curr_rate = row.get('수수료율', 0)
                try: curr_rate = float(curr_rate)
                except: curr_rate = 0.0

                if curr_rate <= 0:
                    curr_rate = default_rate
                    df.at[idx, '수수료율'] = curr_rate

                # 공헌손익 및 실수익 계산 (상태는 강제로 덮어쓰지 않음)
                if p_sell > 0:
                    vat_margin = (p_sell - p_buy) / 1.1
                    expenses = row.get('헤딜수수료', 0) + row.get('상품화', 0) + df.at[idx, '기본제경비'] + p_fee
                    net_profit = int(round(vat_margin - expenses))
                    df.at[idx, '공헌이익'] = net_profit
                    df.at[idx, '실수익'] = int(round(net_profit * curr_rate))
                else:
                    df.at[idx, '공헌이익'] = 0
                    df.at[idx, '실수익'] = 0

                # 상태 기본값 세팅 (기존 값이 없으면 '보유재고')
                if not str(row.get('상태', '')).strip() or str(row.get('상태', '')) == 'nan':
                    df.at[idx, '상태'] = '보유재고'

                # 재고일 계산
                m_date_str = str(row.get('매입일', '')).strip()
                try:
                    parts = m_date_str.replace(" ", "").split(".")
                    if len(parts) >= 2:
                        m_dt = datetime(now_date.year, int(parts[0]), int(parts[1]))
                        if m_dt > now_date:
                            m_dt = datetime(now_date.year - 1, int(parts[0]), int(parts[1]))
                        df.at[idx, '재고일'] = max(0, (now_date - m_dt).days)
                except:
                    pass
            return df

        # 초기 정규화 (1회 보정)
        if not st.session_state.my_settlement_data.empty:
            for c in ['순차', '판매가', '재고일', '매입가', '외판수리', '상품화', '헤딜수수료', '기본제경비', '공헌이익', '실수익', '판매수수료']:
                if c not in st.session_state.my_settlement_data.columns:
                    st.session_state.my_settlement_data[c] = 0
                st.session_state.my_settlement_data[c] = pd.to_numeric(st.session_state.my_settlement_data[c], errors='coerce').fillna(0).astype(int)
            if '수수료율' not in st.session_state.my_settlement_data.columns:
                st.session_state.my_settlement_data['수수료율'] = auto_fee_rate
            st.session_state.my_settlement_data['수수료율'] = pd.to_numeric(st.session_state.my_settlement_data['수수료율'], errors='coerce').fillna(auto_fee_rate)

            st.session_state.my_settlement_data = recalc_settlement_df(st.session_state.my_settlement_data, auto_fee_rate)

        # 3. 상단 성과 대시보드 카드 (현재 보유 재고 기준)
        stock_mask = (st.session_state.my_settlement_data['상태'] != '판매완료') if not st.session_state.my_settlement_data.empty else pd.Series(dtype=bool)
        stock_df = st.session_state.my_settlement_data[stock_mask].copy() if not st.session_state.my_settlement_data.empty else pd.DataFrame()
        completed_df = st.session_state.my_settlement_data[~stock_mask].copy() if not st.session_state.my_settlement_data.empty else pd.DataFrame()

        stock_count = len(stock_df)
        sold_count = len(completed_df)

        # 보유 재고 원가 합계 (매입가 + 상품화 + 헤딜수수료 + 기본제경비)
        total_stock_cost = int((stock_df['매입가'] + stock_df['상품화'] + stock_df['헤딜수수료'] + stock_df['기본제경비']).sum()) if not stock_df.empty else 0
        avg_stock_days = int(stock_df['재고일'].mean()) if not stock_df.empty else 0

        # 4. 장기 재고 및 마진 리스크 정밀 집계
        if not stock_df.empty:
            stock_days_s = pd.to_numeric(stock_df['재고일'], errors='coerce').fillna(0)
            over_30_count = int(((stock_days_s >= 30) & (stock_days_s < 60)).sum())
            over_60_count = int((stock_days_s >= 60).sum())

            sell_p_s = pd.to_numeric(stock_df['판매가'], errors='coerce').fillna(0)
            net_profit_s = pd.to_numeric(stock_df['공헌이익'], errors='coerce').fillna(0)
            margin_risk_count = int(((sell_p_s > 0) & (net_profit_s < 100)).sum())
        else:
            over_30_count = 0
            over_60_count = 0
            margin_risk_count = 0

        long_border = "#ef4444" if over_60_count > 0 else ("#f59e0b" if over_30_count > 0 else "#2e3038")
        margin_border = "#ef4444" if margin_risk_count > 0 else "#2e3038"

        st.markdown(f"""
        <div style='display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; margin-bottom: 16px;'>
            <div class='metric-card' style='flex: 1; min-width: 130px;'>
                <div class='metric-icon'>🚗</div>
                <div class='metric-content'>
                    <h4>보유 재고</h4>
                    <h2 style='color:#38bdf8;'>{stock_count:,} 대 <span style='font-size:0.55em; color:#94a3b8;'>(완료: {sold_count})</span></h2>
                </div>
            </div>
            <div class='metric-card' style='flex: 1; min-width: 120px;'>
                <div class='metric-icon'>⏱️</div>
                <div class='metric-content'>
                    <h4>평균 재고일</h4>
                    <h2><span style='color:{"#4ade80" if avg_stock_days < 15 else "#f59e0b"};'>{avg_stock_days:,}일</span></h2>
                </div>
            </div>
            <div class='metric-card' style='flex: 1.2; min-width: 160px; border: 1.5px solid {long_border} !important;'>
                <div class='metric-icon' style='background: {"rgba(239, 68, 68, 0.2)" if over_60_count > 0 else ("rgba(245, 158, 11, 0.2)" if over_30_count > 0 else "transparent")} !important;'>⚠️</div>
                <div class='metric-content'>
                    <h4>장기 재고 (30일+/60일+)</h4>
                    <h2>
                        <span style='color:{"#ef4444" if over_60_count > 0 else "#94a3b8"}; font-weight:800;'>{over_60_count}대</span>
                        <span style='font-size:0.6em; color:{"#f59e0b" if over_30_count > 0 else "#94a3b8"};'> (30일+: {over_30_count}대)</span>
                    </h2>
                </div>
            </div>
            <div class='metric-card' style='flex: 1.1; min-width: 150px; border: 1.5px solid {margin_border} !important;'>
                <div class='metric-icon' style='background: {"rgba(239, 68, 68, 0.2)" if margin_risk_count > 0 else "transparent"} !important;'>📉</div>
                <div class='metric-content'>
                    <h4>마진 주의 (100만↓)</h4>
                    <h2 style='color:{"#ef4444" if margin_risk_count > 0 else "#4ade80"}; font-weight:800;'>{margin_risk_count:,} 대</h2>
                </div>
            </div>
            <div class='metric-card' style='flex: 1.1; min-width: 140px;'>
                <div class='metric-icon'>💵</div>
                <div class='metric-content'>
                    <h4>재고 총 원가</h4>
                    <h2 style='color: #e2e8f0;'>{total_stock_cost:,} 만원</h2>
                </div>
            </div>
            <div class='metric-card' style='flex: 1.1; min-width: 140px; border: 1.5px solid #0284c7 !important;'>
                <div class='metric-icon' style='background: #0c4a6e !important;'>📦</div>
                <div class='metric-content'>
                    <h4 style='color:#38bdf8;'>총 매입 대수</h4>
                    <h2 style='color: #38bdf8; font-weight:900;'>{total_bought_count:,} 대 <span style='font-size:0.55em; color:#94a3b8;'>({int(auto_fee_rate*100)}%)</span></h2>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3-1. 🎯 보유 재고 실시간 엔카 동급 시세 정밀 분석 바 (메인 화면 역추적 자동 스캔 연동)
        if not stock_df.empty:
            st.markdown("""
            <div style='background: #181920; border: 1.5px solid #0284c7; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
                    <b style='color: #38bdf8; font-size: 1.05em;'>🎯 보유 재고 실시간 동급 시세 분석 (메인 화면 원클릭 연동)</b>
                    <span style='color: #94a3b8; font-size: 0.82em;'>💡 엔카 매물 URL(또는 carid)을 넣으면 필터링된 동급 매물 20~40대를 자동 스캔하여 메인 분석 화면으로 즉시 이동합니다.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c_options = [f"{row.get('차량번호', '')} | {row.get('차종', '')}" for _, row in stock_df.iterrows()]
            sc_col1, sc_col2, sc_col3 = st.columns([3, 4.5, 2.5])
            with sc_col1:
                sel_stock_str = st.selectbox("분석할 보유 차량 선택:", c_options, key="sel_stock_analysis_box")
            
            sel_c_no = sel_stock_str.split("|")[0].strip() if sel_stock_str else ""
            matched_stock = stock_df[stock_df['차량번호'] == sel_c_no]
            saved_encar_url = ""
            if not matched_stock.empty and '엔카URL' in matched_stock.columns:
                saved_encar_url = str(matched_stock.iloc[0].get('엔카URL', '')).strip()
                if saved_encar_url in ['nan', 'None', '-']: saved_encar_url = ""

            # 사내 재고(autoplus_inventory.csv)에서 실제 엔카 판매 URL 및 상세 스펙 자동 발굴
            auto_inv_row = None
            if os.path.exists("autoplus_inventory.csv"):
                try:
                    raw_inv = pd.read_csv("autoplus_inventory.csv")
                    m_inv = raw_inv[raw_inv['차량번호'].astype(str).str.strip() == sel_c_no]
                    if not m_inv.empty:
                        auto_inv_row = m_inv.iloc[0]
                        if not saved_encar_url:
                            for col_k in ['E URL', '엔카주소', '엔카링크', '엔카URL', 'EURL']:
                                if col_k in m_inv.columns:
                                    cand_url = str(auto_inv_row.get(col_k, '')).strip()
                                    if 'encar.com' in cand_url:
                                        saved_encar_url = cand_url
                                        break
                except Exception:
                    pass

            with sc_col2:
                in_encar_url = st.text_input(
                    "엔카 매물 URL 또는 carid 입력:",
                    value=saved_encar_url,
                    placeholder="예: https://fem.encar.com/cars/detail/42545600 또는 42545600 (비워두면 차종으로 자동 생성)",
                    key=f"in_encar_stock_url_{sel_c_no}"
                )

            with sc_col3:
                st.write("")
                st.write("")
                if st.button("🚀 메인 화면에서 동급 시세 분석", type="primary", use_container_width=True, key="btn_run_stock_analysis"):
                    with st.spinner("엔카 동급 매물 검색 쿼리 역생성 중..."):
                        target_search_url = ""
                        target_car_name = ""
                        target_sub_model = ""
                        target_mil = 0
                        target_year = 0
                        target_acc = "완전무사고"

                        # 0. 사내 재고 데이터(autoplus_inventory.csv 및 stock_df)에서 기본 스펙 추출 (무조건 보장)
                        src_row = auto_inv_row if auto_inv_row is not None else (matched_stock.iloc[0] if not matched_stock.empty else None)
                        if src_row is not None:
                            # 주행거리 추출
                            raw_mil = str(src_row.get('주행거리', 0)).replace(',', '').strip()
                            try:
                                m_val = int(float(raw_mil))
                                if m_val > 0: target_mil = m_val
                            except Exception:
                                pass
                            
                            # 연식 추출 (최초등록일 또는 연식)
                            reg_dt = str(src_row.get('최초등록일', '')).strip()
                            if len(reg_dt) >= 4 and reg_dt[:4].isdigit():
                                target_year = int(reg_dt[:4])
                            elif '연식' in src_row:
                                yr_cand = re.search(r'(\d{2,4})', str(src_row.get('연식', '')))
                                if yr_cand:
                                    y_num = int(yr_cand.group(1))
                                    target_year = (2000 + y_num) if y_num < 100 else y_num
                            
                            # 차종 및 세부모델
                            target_car_name = str(src_row.get('차량명', src_row.get('차종', ''))).strip()
                            for sub_col in ['세부 모델', '세부모델']:
                                if sub_col in src_row and str(src_row.get(sub_col, '')).strip():
                                    target_sub_model = str(src_row.get(sub_col, '')).strip()
                                    break

                        eval_url = in_encar_url.strip() if (in_encar_url and in_encar_url.strip()) else saved_encar_url

                        # 1순위: 엔카 URL/carid 정밀 역추적 (사내 재고 자동발굴 포함)
                        if eval_url:
                            res = Scraper.build_search_from_car_url(eval_url)
                            if res.get("success"):
                                target_search_url = res["search_url"]
                                if res.get("car_name"): target_car_name = res["car_name"]
                                if res.get("grade"): target_sub_model = res["grade"]
                                if res.get("mileage", 0) > 0: target_mil = res["mileage"]
                                if res.get("year", 0) > 0: target_year = res["year"]
                                target_acc = res.get("accident", target_acc)
                                
                                # 입력된 엔카 URL을 정산 데이터에 저장
                                if '엔카URL' not in st.session_state.my_settlement_data.columns:
                                    st.session_state.my_settlement_data['엔카URL'] = ""
                                st.session_state.my_settlement_data.loc[st.session_state.my_settlement_data['차량번호'] == sel_c_no, '엔카URL'] = eval_url
                                st.session_state.my_settlement_data.to_csv(SETTLEMENT_FILE, index=False, encoding='utf-8-sig')
                            else:
                                st.warning(f"엔카 URL 역추적 실패: {res.get('error')} ➔ 차종명으로 동급 검색을 진행합니다.")

                        # 2순위: 엔카 URL이 없거나 실패 시 차종명 기반 엔카 URL 자동 조립
                        if not target_search_url and target_car_name:
                            target_search_url = SalesDataAnalyzer.generate_encar_url(target_car_name, target_sub_model)

                        if target_search_url:
                            # 1. 폼 리셋 키 버전업 ➔ 기존 사이드바의 헤이딜러 URL 및 연식/키로수 위젯 캐시를 완전히 새것으로 리셋!
                            st.session_state.form_reset_key = st.session_state.get('form_reset_key', 0) + 1
                            new_k = st.session_state.form_reset_key

                            # 2. 이전 헤이딜러 세션 찌꺼기 완벽 클리어
                            stale_keys = [
                                'hd_target_url', 'hd_url_input', 'hd_detail_data', 'hd_target_options', 
                                'encar_target_options', 'hd_model_part_name', 'hd_grade_part_name', 
                                'hd_full_name', 'auto_encar_url', 'hd_comp_df', 'hd_car_spec_desc', 'hd_target_opt_price',
                                'hd_target_mil', 'hd_target_year', 'f_mil'
                            ]
                            for stale_k in stale_keys:
                                if stale_k in st.session_state:
                                    st.session_state[stale_k] = [] if 'options' in stale_k else ("" if 'part' in stale_k or 'desc' in stale_k or 'url' in stale_k or 'name' in stale_k else 0)

                            # 3. 사이드바 위젯 및 세션에 직접 대상 차량 스펙 주입
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

                            st.session_state[f"car_num_{new_k}"] = sel_c_no
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

                            # 메인 탭에 자동 스캔 URL 주입 & 화면 이동 플래그
                            st.session_state['auto_scan_url'] = target_search_url
                            st.session_state['nav_target'] = "📊 시세 분석 및 스캔"
                            st.session_state['nav_selection'] = "📊 시세 분석 및 스캔"
                            st.session_state['nav_selection_box'] = "📊 시세 분석 및 스캔"
                            st.rerun()
                        else:
                            st.error("❌ 동급 매물 검색 URL을 생성하지 못했습니다. 차종명을 확인해 주세요.")

        # 4. 보유 재고 정산 테이블 렌더링 (맨 끝에 [판매완료] 체크박스 컬럼 배치)
        if not stock_df.empty:
            col_st_title, col_st_filter = st.columns([1.6, 3.4])
            with col_st_title:
                st.markdown("#### 📝 현재 보유 재고 정산표")
            with col_st_filter:
                stock_filter_sel = st.radio(
                    "재고 필터",
                    [
                        f"전체 ({stock_count})",
                        f"⚠️ 30일+ ({over_30_count})",
                        f"🚨 60일+ ({over_60_count})",
                        f"📉 마진주의 ({margin_risk_count})"
                    ],
                    horizontal=True,
                    key="stock_settle_filter_radio",
                    label_visibility="collapsed"
                )

            st.caption("💡 30일/60일 경과 차량이나 마진주의 매물은 위 필터 버튼으로 빠르게 선별할 수 있습니다. 실제 판매 완료 시 맨 끝의 **[판매완료]**를 체크하세요.")

            # 순차, 매입일, 차량번호, 차종, 판매가, 재고일, 매입가, 외판수리, 상품화, 헤딜수수료, 기본제경비, 공헌이익, 실수익, 수수료율, 판매수수료, 엔카시세, 판매완료
            view_cols = [
                '순차', '매입일', '차량번호', '차종', '판매가', '재고일', '매입가', 
                '외판수리', '상품화', '헤딜수수료', '기본제경비', '공헌이익', '실수익', 
                '수수료율', '판매수수료', '엔카시세', '판매완료'
            ]

            # 에디터용 데이터프레임 구성 (판매완료 기본값 False, 엔카시세 링크 동적 생성)
            def _resolve_encar_market_link(r):
                c_no = str(r.get('차량번호', '')).strip()
                if os.path.exists("autoplus_inventory.csv") and c_no:
                    try:
                        raw_inv = pd.read_csv("autoplus_inventory.csv")
                        m_inv = raw_inv[raw_inv['차량번호'].astype(str).str.strip() == c_no]
                        if not m_inv.empty:
                            for col_k in ['E URL', '엔카주소', '엔카링크', '엔카URL']:
                                if col_k in m_inv.columns:
                                    u = str(m_inv.iloc[0].get(col_k, '')).strip()
                                    m_id = re.search(r'(\d{7,9})', u)
                                    if m_id:
                                        # 💡 엔카 공식 동급매물/팔린매물 팝업 직통 링크
                                        return f"https://www.encar.com/dc/dc_carsearchpop.do?method=equalCar&carid={m_id.group(1)}"
                    except Exception:
                        pass
                return generate_encar_market_url(r.get('차종', ''))

            edit_stock_df = stock_df.copy()
            edit_stock_df['판매완료'] = False
            edit_stock_df['엔카시세'] = edit_stock_df.apply(_resolve_encar_market_link, axis=1)

            # 필터 적용
            if "30일+" in stock_filter_sel:
                s_days = pd.to_numeric(edit_stock_df['재고일'], errors='coerce').fillna(0)
                view_stock_df = edit_stock_df[(s_days >= 30) & (s_days < 60)].copy()
            elif "60일+" in stock_filter_sel:
                s_days = pd.to_numeric(edit_stock_df['재고일'], errors='coerce').fillna(0)
                view_stock_df = edit_stock_df[s_days >= 60].copy()
            elif "마진주의" in stock_filter_sel:
                s_sell = pd.to_numeric(edit_stock_df['판매가'], errors='coerce').fillna(0)
                s_profit = pd.to_numeric(edit_stock_df['공헌이익'], errors='coerce').fillna(0)
                view_stock_df = edit_stock_df[(s_sell > 0) & (s_profit < 100)].copy()
            else:
                view_stock_df = edit_stock_df.copy()

            settle_cfg = {
                "순차": st.column_config.NumberColumn("순차", width=45, format="%d"),
                "매입일": st.column_config.TextColumn("매입일", width=65),
                "차량번호": st.column_config.TextColumn("차량번호", width=95),
                "차종": st.column_config.TextColumn("차종", width=160),
                "판매가": st.column_config.NumberColumn("판매가", width=70, format="%d"),
                "재고일": st.column_config.NumberColumn("재고일", width=55, format="%d일"),
                "매입가": st.column_config.NumberColumn("매입가", width=70, format="%d"),
                "외판수리": st.column_config.NumberColumn("외판수", width=55, format="%d", step=1, min_value=0),
                "상품화": st.column_config.NumberColumn("상품화", width=65, format="%d"),
                "헤딜수수료": st.column_config.NumberColumn("수수료", width=65, format="%d"),
                "기본제경비": st.column_config.NumberColumn("제경비", width=65, format="%d"),
                "공헌이익": st.column_config.NumberColumn("공헌이익", width=70, format="%d"),
                "실수익": st.column_config.NumberColumn("실수익", width=70, format="%d"),
                "수수료율": st.column_config.NumberColumn("수수료율", width=65, format="%.2f", step=0.05, min_value=0.0, max_value=1.0),
                "판매수수료": st.column_config.NumberColumn("판매수수료", width=70, format="%d"),
                "엔카시세": st.column_config.TextColumn("엔카시세 (복사용)", width=120),
                "판매완료": st.column_config.CheckboxColumn("판매완료", help="체크하면 즉시 [판매완료] 탭으로 이동합니다.", width=75, default=False),
            }

            edited_df = st.data_editor(
                view_stock_df[view_cols],
                use_container_width=False,
                height=380,
                hide_index=True,
                column_config=settle_cfg,
                key="stock_settlement_data_editor"
            )

            # 편집된 내용 감지: 실제 셀 값이 달라졌을 때만 처리
            current_view_df = view_stock_df[view_cols]
            has_changes = False
            for c in view_cols:
                if not (edited_df[c].fillna(0).astype(str) == current_view_df[c].fillna(0).astype(str)).all():
                    has_changes = True
                    break

            if has_changes:
                completed_car_num = None
                for idx in edited_df.index:
                    car_num = str(edited_df.at[idx, '차량번호'])

                    # 1. 판매완료 체크박스가 체크된 경우!
                    if edited_df.at[idx, '판매완료'] == True:
                        st.session_state.my_settlement_data.loc[st.session_state.my_settlement_data['차량번호'].astype(str) == car_num, '상태'] = '판매완료'
                        completed_car_num = car_num

                    # 2. 일반 항목 변경사항 원본에 동기화
                    old_ext = current_view_df.at[idx, '외판수리']
                    new_ext = edited_df.at[idx, '외판수리']

                    for c in [col for col in view_cols if col not in ['판매완료', '엔카시세']]:
                        st.session_state.my_settlement_data.loc[st.session_state.my_settlement_data['차량번호'].astype(str) == car_num, c] = edited_df.at[idx, c]

                    # 외판수 변경 시 상품화비용 판수 * 13만 동기화
                    if old_ext != new_ext and new_ext >= 0:
                        st.session_state.my_settlement_data.loc[st.session_state.my_settlement_data['차량번호'].astype(str) == car_num, '상품화'] = int(new_ext * 13)

                # 손익 재계산 및 저장
                st.session_state.my_settlement_data = recalc_settlement_df(st.session_state.my_settlement_data, auto_fee_rate)
                st.session_state.my_settlement_data.to_csv(SETTLEMENT_FILE, index=False, encoding='utf-8-sig')

                if completed_car_num:
                    st.success(f"🎉 {completed_car_num} 차량이 판매완료 처리되어 [🎉 판매완료 정산 내역] 탭으로 이동되었습니다!")
                st.rerun()

            # ==========================================
            # 🚨 [신규] 재고 리스크 케어 & 엔카 실시간 동급시세 비교 위젯
            # ==========================================
            st.markdown("---")
            st.markdown("#### 🚨 재고 리스크 케어 & 엔카 실시간 동급시세 비교 (헤이딜러 스타일)")
            st.caption("💡 보유 중인 재고 차량을 선택하면 경과일수 위험도(신호등)를 진단하고 **엔카에 현재 올라와 있는 동일 스펙 경쟁 매물**로 바로 이동하여 소매가를 즉시 재조정할 수 있습니다.")

            stock_car_list = list(stock_df['차량번호'].astype(str).unique())
            selected_inspect_car = st.selectbox("🔍 집중 케어 및 엔카 시세 비교할 차량 선택:", stock_car_list, key="select_inspect_stock_car")

            if selected_inspect_car:
                target_row = stock_df[stock_df['차량번호'].astype(str) == selected_inspect_car].iloc[0]
                t_name = str(target_row.get('차종', ''))
                t_days = int(pd.to_numeric(target_row.get('재고일', 0), errors='coerce') or 0)
                t_sell = int(pd.to_numeric(target_row.get('판매가', 0), errors='coerce') or 0)
                t_buy = int(pd.to_numeric(target_row.get('매입가', 0), errors='coerce') or 0)
                t_profit = int(pd.to_numeric(target_row.get('공헌이익', 0), errors='coerce') or 0)

                # 신호등 배지
                if t_days <= 30:
                    day_badge = f"<span style='background:#14532d; color:#86efac; padding:4px 12px; border-radius:12px; font-weight:bold;'>🟢 안전 회전구간 ({t_days}일차)</span>"
                    day_advice = "아직 정상 회전 구간(30일 이내)입니다. 기존 희망가를 유지하셔도 좋습니다."
                elif t_days <= 60:
                    day_badge = f"<span style='background:#713f12; color:#fde047; padding:4px 12px; border-radius:12px; font-weight:bold;'>🟡 주의 구간 ({t_days}일차)</span>"
                    day_advice = "30일이 경과했습니다! 엔카 동급 매물 시세를 확인하고 경쟁사보다 50~100만 원 인하를 고려하세요."
                else:
                    day_badge = f"<span style='background:#7f1d1d; color:#fca5a5; padding:4px 12px; border-radius:12px; font-weight:bold;'>🚨 위험 - 장기재고 ({t_days}일차)</span>"
                    day_advice = "60일 초과 악성 장기재고입니다! 자금 회전을 위해 원가 근접 빠른 급매 정리를 강력 권장합니다."

                encar_live_url = generate_encar_market_url(t_name)

                c_card1, c_card2 = st.columns([6.2, 3.8])
                with c_card1:
                    st.markdown(f"""
                    <div style='background-color:#121317; border:1px solid #2e3038; border-radius:8px; padding:16px;'>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                            <span style='font-size:1.15em; font-weight:bold; color:#ffffff;'>🚘 {selected_inspect_car} ({t_name})</span>
                            {day_badge}
                        </div>
                        <div style='color:#9194a1; font-size:0.9em; margin-bottom:12px;'>
                            매입가: <b style='color:#e2e8f0;'>{t_buy:,}만원</b> | 
                            현재판매가: <b style='color:#38bdf8;'>{t_sell:,}만원</b> | 
                            예상공헌이익: <b style='color:{"#4ade80" if t_profit > 0 else "#ef4444"};'>{t_profit:,}만원</b>
                        </div>
                        <div style='background:#1c1d22; padding:10px 14px; border-radius:6px; font-size:0.88em; color:#cbd5e1; margin-bottom:14px;'>
                            💡 <b>운영 가이드:</b> {day_advice}
                        </div>
                        <div>
                            <a href='{encar_live_url}' target='_blank' style='display:inline-block; background-color:#cc9166; color:#08080a; padding:9px 18px; border-radius:6px; font-weight:bold; text-decoration:none; font-size:0.95em;'>
                                🔗 엔카 실시간 동급 소매 매물 보러가기 ↗
                            </a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with c_card2:
                    with st.form(key=f"reprice_form_{selected_inspect_car}"):
                        st.markdown("**⚡ 판매가 즉시 재조정**")
                        new_adjusted_sell = st.number_input("새 판매가 (만원)", min_value=0, step=10, value=t_sell, key=f"adj_sell_val_{selected_inspect_car}")
                        if st.form_submit_button("💾 가격 조정 반영 및 저장", use_container_width=True):
                            st.session_state.my_settlement_data.loc[st.session_state.my_settlement_data['차량번호'].astype(str) == selected_inspect_car, '판매가'] = new_adjusted_sell
                            st.session_state.my_settlement_data = recalc_settlement_df(st.session_state.my_settlement_data, auto_fee_rate)
                            st.session_state.my_settlement_data.to_csv(SETTLEMENT_FILE, index=False, encoding='utf-8-sig')
                            st.success(f"✅ {selected_inspect_car} 판매가가 {new_adjusted_sell}만 원으로 조정되었습니다!")
                            st.rerun()

            # 데이터 삭제 부가 액션
            c_del1, c_del2, c_del3 = st.columns([2.5, 2, 5.5])
            with c_del1:
                del_target_car = st.selectbox("🗑️ 삭제할 재고 차량 선택:", ["선택..."] + list(stock_df['차량번호'].unique()), key="del_stock_car")
            with c_del2:
                st.write("")
                st.write("")
                if st.button("선택 차량 정산표에서 삭제", use_container_width=True, key="btn_del_stock"):
                    if del_target_car != "선택...":
                        st.session_state.my_settlement_data = st.session_state.my_settlement_data[st.session_state.my_settlement_data['차량번호'] != del_target_car].reset_index(drop=True)
                        st.session_state.my_settlement_data.to_csv(SETTLEMENT_FILE, index=False, encoding='utf-8-sig')
                        st.success(f"{del_target_car} 삭제 완료")
                        st.rerun()
        else:
            st.info("💡 현재 보유 중인 재고 차량이 없습니다. [📋 내 실전 장부 리스트]에서 차량의 [📦 매입 확정]을 누르면 여기에 등록됩니다.")


