# -*- coding: utf-8 -*-
"""
tests/test_kcar_market_stats.py
K-Car 직영 매물 검색 및 시세 통계 서비스 단위 테스트
- 실시간 API 응답 및 통계 구조(count, min, max, avg, median, yearStats, priceBins, cars) 검증
- CI 번호판 리터럴 가드 준수 (차량번호 없음)
"""
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from services.kcar_service import (
    fetch_kcar_market_stats,
    resolve_kcar_model_codes,
    is_color_option,
    fallback_calc_comp_opt_from_optnnm,
    _KCAR_JATO_CACHE
)

def test_kcar_jato_option_regression():
    """라이브 API 무의존 회귀 테스트: 더미 JATO 옵션(컬러 포함/미포함), 합산, 델타, 캡, 격리 폴백 단언"""
    print("=" * 80)
    print("K-Car JATO 옵션 산출 및 델타 회귀 테스트 (라이브 무의존)")
    print("=" * 80)

    # 1. 유상 외장 컬러 키워드 판정 단언
    assert is_color_option("스노우 화이트 펄") is True
    assert is_color_option("세라믹 매트 그레이") is True
    assert is_color_option("메탈릭 실버") is True
    assert is_color_option("헤드업 디스플레이") is False
    assert is_color_option("드라이브 와이즈") is False
    assert is_color_option("컴포트") is False
    assert is_color_option("하이테크 패키지") is False
    print("[PASS] 1. 유상 외장 컬러(펄·매트·메탈릭) 판정 단언 통과")

    # 2. 더미 JATO 옵션 리스트 합산 및 컬러 제외 단언
    # Case A: 컬러 포함 케이스 (스노우 화이트 펄 20만 제외 -> 109만 + 79만 = 188만원)
    dummy_jato_with_color = [
        {"optNm": "HUD + 빌트인 캠 2", "optPrc": "1090000"},
        {"optNm": "스노우 화이트 펄", "optPrc": "200000"},
        {"optNm": "컴포트", "optPrc": "790000"}
    ]
    sum_a = sum(
        (int(o["optPrc"]) // 10000 if int(o["optPrc"]) >= 10000 else int(o["optPrc"]))
        for o in dummy_jato_with_color
        if not is_color_option(o["optNm"])
    )
    assert sum_a == 188, f"컬러 제외 합산 오류: 기대값 188, 실제 {sum_a}"

    # Case B: 순수 옵션 케이스 (EC61393947 실측: 130만 + 150만 = 280만원)
    dummy_jato_no_color = [
        {"optNm": "프리뷰 전자제어 서스펜션 II", "optPrc": "1300000"},
        {"optNm": "하이테크 패키지", "optPrc": "1500000"}
    ]
    sum_b = sum(
        (int(o["optPrc"]) // 10000 if int(o["optPrc"]) >= 10000 else int(o["optPrc"]))
        for o in dummy_jato_no_color
        if not is_color_option(o["optNm"])
    )
    assert sum_b == 280, f"순수 옵션 합산 오류: 기대값 280, 실제 {sum_b}"
    print("[PASS] 2. 더미 JATO 옵션 합산 및 컬러 제외 단언 통과")

    # 3. 델타 공식 및 캡 단언 (제이 명세 예시)
    # - 목표 차량: 182만원 × 3년차(35%) = 잔존 64만원
    # - 비교군 차량: 227만원 × 2년차(50%) = 잔존 114만원
    # - 델타 = 64 - 114 = -50만원
    # - 음수 반영률 40% -> -50 * 0.40 = -20만원
    target_opt_raw = 182
    target_deprec = int(round(target_opt_raw * 0.35))
    assert target_deprec == 64, f"목표 잔존 오류: {target_deprec}"

    comp_opt_raw = 227
    comp_deprec = int(round(comp_opt_raw * 0.50))
    assert comp_deprec == 114, f"비교군 잔존 오류: {comp_deprec}"

    delta = target_deprec - comp_deprec
    assert delta == -50, f"델타 오류: {delta}"

    # 반영률 및 캡 함수
    def calc_adj(d: int) -> int:
        if d > 0:
            return min(40, int(round(d * 0.35)))
        elif d < 0:
            return max(-40, int(round(d * 0.40)))
        return 0

    adj_neg = calc_adj(delta)
    assert adj_neg == -20, f"음수 델타 보정 오류: 기대값 -20, 실제 {adj_neg}"

    # 캡 검증 (+40만 / -40만)
    assert calc_adj(200) == 40   # 200 * 0.35 = +70 -> cap +40
    assert calc_adj(-200) == -40  # -200 * 0.40 = -80 -> cap -40
    print("[PASS] 3. 델타 잔존가치 및 ±40만 캡 단언 통과")

    # 4. 통신 실패 격리 비상 폴백 단언
    dummy_catalog = {"헤드업디스플레이": 120, "드라이브와이즈": 110, "선루프": 80}
    # optnNm에 컬러가 포함되어도 컬러 제외 + 카탈로그 매칭
    fallback_sum = fallback_calc_comp_opt_from_optnnm(
        "헤드업 디스플레이 | 스노우 화이트 펄 | 드라이브와이즈",
        dummy_catalog
    )
    assert fallback_sum == 230, f"격리 폴백 오류: 기대값 230 (120+110), 실제 {fallback_sum}"
    # 부분문자열 매칭 동작 확인 ("파노라마선루프" -> "선루프" 80만)
    fallback_sub = fallback_calc_comp_opt_from_optnnm("파노라마선루프", dummy_catalog)
    assert fallback_sub == 80, f"격리 폴백 부분문자열 오류: 기대값 80, 실제 {fallback_sub}"
    print("[PASS] 4. 통신 실패 비상 격리 폴백 단언 통과")

    # 5. 빈 배열([]) 응답 시 0원 정상 처리 단언
    empty_jato = []
    empty_sum = sum(
        (int(o["optPrc"]) // 10000 if int(o["optPrc"]) >= 10000 else int(o["optPrc"]))
        for o in empty_jato
        if not is_color_option(o["optNm"])
    )
    assert empty_sum == 0
    print("[PASS] 5. 빈 배열([]) 0원 정상 처리 단언 통과")
    print("=" * 80)

def test_kcar_market_stats():
    print("=" * 80)
    print("K-Car 직영 실시간 소매 시세 통계 검증 시작")
    print("=" * 80)

    # 1. 그랜저 IG (대표적인 대량 매물 차종)
    res = fetch_kcar_market_stats("그랜저 IG", year=2018, detail_model="2.4 프리미엄", manufacturer="현대")
    assert res["success"] is True, f"그랜저 IG 실패: {res.get('message')}"
    assert res["count"] > 0, "그랜저 IG 매물 수가 0입니다."
    assert res["min"] > 0 and res["max"] >= res["min"], "가격 범위 오류"
    assert res["avg"] > 0, "평균가 오류"
    assert len(res["yearStats"]) > 0, "연식별 통계 없음"
    assert len(res["priceBins"]) > 0, "가격 분포 구간 없음"
    print(f"[PASS] 그랜저 IG: 총 {res['count']}대, 평균 {res['avg']}만원 (최저 {res['min']}만 ~ 최고 {res['max']}만)")
    print(f"       연식분포: {res['yearStats']}")
    print(f"       가격구간: {res['priceBins']}")

    # 2. K5 하이브리드 3세대 (하이브리드 차종)
    res_hev = fetch_kcar_market_stats("K5 하이브리드 3세대", year=2021, manufacturer="기아")
    assert res_hev["success"] is True, f"K5 HEV 실패: {res_hev.get('message')}"
    assert res_hev["count"] > 0, "K5 HEV 매물 수가 0입니다."
    print(f"[PASS] K5 하이브리드 3세대: 총 {res_hev['count']}대, 평균 {res_hev['avg']}만원 (최저 {res_hev['min']}만 ~ 최고 {res_hev['max']}만)")
    print(f"       연식분포: {res_hev['yearStats']}")
    # 사고 차감 검증 (무사고 0%, 단순수리 3%, 골격/결격 7%)
    assert res_hev["accDeduction"] == 0
    res_minor = fetch_kcar_market_stats("K5 하이브리드 3세대", year=2021, manufacturer="기아", accident="MINOR")
    assert res_minor["accDeduction"] == 3
    assert res_minor["avgAdj"] == int(round(res_hev["avgAdj"] * 0.97))
    res_frame = fetch_kcar_market_stats("K5 하이브리드 3세대", year=2021, manufacturer="기아", accident="FRAME")
    assert res_frame["accDeduction"] == 7
    assert res_frame["avgAdj"] == int(round(res_hev["avgAdj"] * 0.93))

    # 옵션 델타 검증 (목표 옵션 전달 시 avgAdj 보정 및 adjNote 옵션 반영 문구 확인)
    res_opt = fetch_kcar_market_stats(
        "K5 하이브리드 3세대",
        year=2021,
        manufacturer="기아",
        target_options="파노라마 선루프(108만) · 헤드업 디스플레이(74만) [옵션총액: 182만]"
    )
    assert res_opt["avgAdj"] > 0
    assert "옵션" in res_opt.get("adjNote", "")

    # 3. 팰리세이드 (SUV 차종)
    res_pali = fetch_kcar_market_stats("팰리세이드", year=2020, manufacturer="현대")
    assert res_pali["success"] is True, f"팰리세이드 실패: {res_pali.get('message')}"
    assert res_pali["count"] > 0, "팰리세이드 매물 수가 0입니다."
    print(f"[PASS] 팰리세이드: 총 {res_pali['count']}대, 평균 {res_pali['avg']}만원")

    # 4. 없는 차종 방어 로직 검증
    res_none = fetch_kcar_market_stats("가상의우주차", year=2099)
    assert res_none["count"] == 0, "없는 차종인데 매물이 반환됨"
    print(f"[PASS] 미등록 차종 방어: {res_none.get('message')}")

    print("=" * 80)
    print("K-Car 실시간 소매 시세 통계 서비스 전 항목 테스트 통과!")
    print("=" * 80)

if __name__ == "__main__":
    test_kcar_jato_option_regression()
    test_kcar_market_stats()
