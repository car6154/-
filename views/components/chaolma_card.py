# views/components/chaolma_card.py
"""
오토플러스 차얼마2 신차 출고가 & 순정 옵션 렌더링 독립 UI 컴포넌트
- 신차 기본가, 순정 옵션 목록, 연식별 감가율 적용 잔존가치 시각화
- 원클릭으로 메인 시세 분석 화면의 신차가/옵션가에 자동 주입
"""

import streamlit as st
from typing import Dict, Any, Callable, Optional
from services.chaolma_service import ChaolmaService


def render_chaolma_section(
    default_car_no: str = "",
    default_mileage: int = 50000,
    show_input: bool = True,
    key_prefix: str = "chaolma",
    on_apply_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None
):
    """
    차얼마2 신차 및 옵션 정보 섹션 렌더링 함수
    :param default_car_no: 기본 차량번호
    :param default_mileage: 기본 주행거리
    :param show_input: 차량번호 입력창 노출 여부
    :param key_prefix: 위젯 고유 키 접두사
    :param on_apply_callback: 신차가/옵션가를 상위 뷰에 전달하는 콜백 함수
    """
    st.markdown("#### 🚗 신차 제원 & 순정옵션 견적조회")

    if not ChaolmaService.is_authenticated():
        st.caption("⚠️ 쿠키 미등록 상태입니다. 확장프로그램에서 **[견적조회 쿠키 전송]** 을 눌러주세요.")

    target_car_no = default_car_no
    fetch_btn = False

    if show_input:
        c_in1, c_in2 = st.columns([3, 1.2])
        with c_in1:
            target_car_no = st.text_input(
                "조회할 차량번호",
                value=default_car_no,
                placeholder="예: 299마3212",
                key=f"{key_prefix}_car_no_box",
                label_visibility="collapsed"
            ).replace(" ", "").strip()
        with c_in2:
            fetch_btn = st.button("🔍 조회", key=f"{key_prefix}_fetch_btn", use_container_width=True)
    else:
        if target_car_no:
            fetch_btn = st.button(f"🚗 {target_car_no} 견적조회", key=f"{key_prefix}_btn", use_container_width=True)

    cache_key = f"chaolma_data_{target_car_no}" if target_car_no else ""

    if fetch_btn and target_car_no:
        with st.spinner(f"[{target_car_no}] 신차 출고가 및 순정 옵션을 조회 중..."):
            res = ChaolmaService.fetch_car_info(target_car_no, mileage=default_mileage)
            if res.get("success"):
                st.session_state[cache_key] = res
                st.session_state["last_chaolma_data"] = res
                st.success(f"✅ [{target_car_no}] 제원 조회 완료! (출고가: {res.get('new_car_price', 0):,}원, 옵션: {len(res.get('options', []))}개)")
            else:
                st.error(f"❌ {res.get('message', '조회 실패')}")

    # 데이터가 로드된 경우 카드 렌더링
    if cache_key:
        data = st.session_state.get(cache_key)
        if data and data.get("success"):
            render_chaolma_card_ui(data, on_apply_callback)


def render_chaolma_card_ui(data: Dict[str, Any], on_apply_callback: Optional[Callable] = None):
    """신차 정보 및 옵션 감가 카드 렌더링"""
    new_car_price = data.get("new_car_price", 0)
    base_price = data.get("base_car_price", 0)
    total_opt = data.get("total_option_price", 0)
    deprec_opt = data.get("total_depreciated_opt_price", 0)
    deprec_rate = data.get("depreciation_rate", 0.0)
    remain_rate = data.get("remain_rate", 0.0)
    options = data.get("options", [])
    model_name = data.get("model_name", "")
    grade_name = data.get("grade_name", "")
    trim_name = data.get("trim_name", "")
    release_date = data.get("release_date", "")
    vin = data.get("vin", "")

    rate_pct = int(deprec_rate * 100)

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.9));
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 12px;
        padding: 16px 20px;
        margin-top: 10px;
        margin-bottom: 14px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; margin-bottom: 12px;">
            <div style="font-size: 15px; font-weight: bold; color: #38bdf8;">
                🏷️ 신차 제원 & 순정 옵션
                <span style="font-size: 12px; color: #94a3b8; font-weight: normal; margin-left: 8px;">
                    {model_name} {grade_name} {trim_name} ({release_date})
                </span>
            </div>
            <div style="font-size: 12px; color: #cbd5e1;">
                차대번호: <span style="font-family: monospace; color: #e2e8f0;">{vin if vin else '-'}</span>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; text-align: center;">
            <div style="background: rgba(255,255,255,0.04); padding: 8px; border-radius: 8px;">
                <div style="font-size: 11px; color: #94a3b8;">총 신차출고가</div>
                <div style="font-size: 16px; font-weight: bold; color: #f8fafc;">{new_car_price:,}원</div>
                <div style="font-size: 10px; color: #64748b;">기본 {base_price:,}원</div>
            </div>
            <div style="background: rgba(255,255,255,0.04); padding: 8px; border-radius: 8px;">
                <div style="font-size: 11px; color: #94a3b8;">순정 옵션 총액</div>
                <div style="font-size: 16px; font-weight: bold; color: #38bdf8;">{total_opt:,}원</div>
                <div style="font-size: 10px; color: #64748b;">{len(options)}개 품목</div>
            </div>
            <div style="background: rgba(255,255,255,0.04); padding: 8px; border-radius: 8px;">
                <div style="font-size: 11px; color: #94a3b8;">옵션 잔존가치 ({rate_pct}%)</div>
                <div style="font-size: 16px; font-weight: bold; color: #34d399;">{deprec_opt:,}원</div>
                <div style="font-size: 10px; color: #64748b;">연식 감가 반영</div>
            </div>
            <div style="background: rgba(255,255,255,0.04); padding: 8px; border-radius: 8px;">
                <div style="font-size: 11px; color: #94a3b8;">차얼마 잔가율</div>
                <div style="font-size: 16px; font-weight: bold; color: #fbbf24;">{remain_rate}%</div>
                <div style="font-size: 10px; color: #64748b;">사내 기준 잔가</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 옵션 세부 내역
    if options:
        st.markdown("<div style='font-size: 13px; font-weight: bold; color: #e2e8f0; margin-bottom: 6px;'>📦 장착 순정 옵션 상세</div>", unsafe_allow_html=True)
        opt_cols = st.columns(min(len(options), 3))
        for idx, opt in enumerate(options):
            c_idx = idx % min(len(options), 3)
            with opt_cols[c_idx]:
                o_name = opt.get("name", "")
                o_price = opt.get("price", 0)
                o_deprec = opt.get("depreciated_price", 0)
                st.markdown(f"""
                <div style="
                    background: rgba(30, 41, 59, 0.6);
                    border-left: 3px solid #38bdf8;
                    border-radius: 4px;
                    padding: 6px 10px;
                    margin-bottom: 6px;
                    font-size: 12px;
                ">
                    <div style="font-weight: bold; color: #f1f5f9;">{o_name}</div>
                    <div style="color: #94a3b8; font-size: 11px;">
                        원가: <span style="color: #cbd5e1;">{o_price:,}원</span> ➔ 
                        잔존: <span style="color: #34d399; font-weight: bold;">{o_deprec:,}원</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # 원클릭 반영 버튼
    col_apply, col_dummy = st.columns([2, 3])
    with col_apply:
        if st.button("✨ 이 출고가 & 옵션가액을 시세 분석에 자동 반영", key=f"apply_chaolma_{data.get('car_no')}", use_container_width=True):
            if on_apply_callback:
                on_apply_callback(new_car_price, deprec_opt, data)
            else:
                # 기본 세션 주입
                st.session_state["target_new_price"] = new_car_price
                st.session_state["target_opt_price"] = deprec_opt
                st.session_state["target_opt_raw"] = total_opt
                st.success("✅ 시세 분석 입력값에 신차가 및 감가 옵션가가 반영되었습니다!")
                st.rerun()
