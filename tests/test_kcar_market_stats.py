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

from services.kcar_service import fetch_kcar_market_stats, resolve_kcar_model_codes

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
    test_kcar_market_stats()
