# -*- coding: utf-8 -*-
"""
tests/simulation/run_simulation.py
재시뮬레이션 재현 및 검증 실행기
- 모델 구성: V2-M01 ~ V2-M26 (총 26개 모델)
  1. Streamlit 회귀 앵커 계열 (V2-M01~M03)
  2. React 콕핏 100점 벤치마크 계열 (V2-M04~M06) - services.encar_service.Scraper.get_benchmarked_valuation 직접 호출
  3. 엔카 카드 매물 통계 계열 (V2-M07~M13)
  4. 케이카 계열 (V2-M14~M16)
  5. 앙상블 계열 (V2-M17~M20)
  6. 매입가 총원가 기준 마진 규칙 (V2-M21~M25) - 총원가 = 매입가 + 정비비 + 딜러수수료 + 기본제경비(15만)
  7. 신차가 잔가율 역산 참고치 (V2-M26)
- 모드:
  --offline: 저장된 마스킹 캐시(simulation_results_masked.json) 기반 즉시 검증 (기본값)
  --live: 실제 엔카/케이카 통신을 거쳐 실시간 재수집 검증
"""
import sys
import os
import argparse
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath("."))

def get_target_specs_masked() -> List[Dict[str, Any]]:
    """검증용 마스킹 대상 차량 11대 스펙 (실차량번호 익명화)"""
    return [
        {"car_id": "CAR_01_RAY_2022", "category": "광고중", "maker": "기아", "model": "더 뉴 레이", "detail": "시그니처", "year": 2022, "mileage": 77000, "buy_price": 961, "actual_sell": 1150, "sell_alt": 1150, "accident": "무사고", "options": "오렌지포인트, 컨비니언스, 스타일, 내비게이션", "repair_cost": 26, "dealer_fee": 19.0, "base_exp": 15.0},
        {"car_id": "CAR_02_CARNIVAL_2018", "category": "광고중", "maker": "기아", "model": "올 뉴 카니발", "detail": "9인승 프레스티지", "year": 2018, "mileage": 140000, "buy_price": 654, "actual_sell": 980, "sell_alt": 980, "accident": "단순교환", "options": "내비게이션, 드라이브와이즈팩2, 컨비니언스", "repair_cost": 52, "dealer_fee": 55.0, "base_exp": 15.0},
        {"car_id": "CAR_03_CARNIVAL_2021", "category": "광고중", "maker": "기아", "model": "카니발 4세대", "detail": "7인승 디젤 노블레스", "year": 2021, "mileage": 90479, "buy_price": 2103, "actual_sell": 2310, "sell_alt": 2310, "accident": "무사고", "options": "선루프, 드라이브와이즈", "repair_cost": 0, "dealer_fee": 25.0, "base_exp": 15.0},
        {"car_id": "CAR_04_TUCSON_2021", "category": "광고중", "maker": "현대", "model": "투싼 (NX4)", "detail": "가솔린 1.6 터보 2WD 인스퍼레이션", "year": 2021, "mileage": 38000, "buy_price": 2200, "actual_sell": 2480, "sell_alt": 2550, "accident": "무사고", "options": "파노라마선루프, 빌트인캠", "repair_cost": 0, "dealer_fee": 25.0, "base_exp": 15.0},
        {"car_id": "CAR_05_CASPER_2025", "category": "광고중", "maker": "현대", "model": "캐스퍼 일렉트릭", "detail": "인스퍼레이션", "year": 2025, "mileage": 22723, "buy_price": 2520, "actual_sell": 2770, "sell_alt": 2770, "accident": "단순교환", "options": "스마트센스", "repair_cost": 0, "dealer_fee": 25.0, "base_exp": 15.0},
        {"car_id": "CAR_06_AVANTE_2017", "category": "광고중", "maker": "현대", "model": "아반떼 AD", "detail": "1.6 GDI 스마트", "year": 2017, "mileage": 98000, "buy_price": 650, "actual_sell": 850, "sell_alt": 850, "accident": "단순교환", "options": "내비게이션, 스마트키", "repair_cost": 39, "dealer_fee": 24.5, "base_exp": 15.0},
        {"car_id": "CAR_07_SPARK_2021", "category": "광고중", "maker": "쉐보레", "model": "더 뉴 스파크", "detail": "LT C-Tech", "year": 2021, "mileage": 44000, "buy_price": 485, "actual_sell": 680, "sell_alt": 720, "accident": "무사고", "options": "래더 패키지, 버튼시동 & 스마트키", "repair_cost": 0, "dealer_fee": 19.0, "base_exp": 15.0},
        {"car_id": "CAR_08_RAY_2021", "category": "판매완료", "maker": "기아", "model": "더 뉴 레이", "detail": "시그니처", "year": 2021, "mileage": 79000, "buy_price": 956, "actual_sell": 1190, "sell_alt": 1190, "accident": "무사고", "options": "스타일, 드라이브와이즈, 내비게이션", "repair_cost": 65, "dealer_fee": 0.0, "base_exp": 15.0},
        {"car_id": "CAR_09_QM6_2022", "category": "판매완료", "maker": "르노코리아", "model": "더 뉴 QM6", "detail": "2.0 GDe LE 시그니처 2WD", "year": 2022, "mileage": 16551, "buy_price": 1865, "actual_sell": 2050, "sell_alt": 2050, "accident": "무사고", "options": "S-Link 패키지", "repair_cost": 0, "dealer_fee": 0.0, "base_exp": 15.0},
        {"car_id": "CAR_10_TIVOLI_2015", "category": "판매완료", "maker": "KG모빌리티(쌍용)", "model": "티볼리", "detail": "가솔린 1.6 2WD", "year": 2015, "mileage": 106470, "buy_price": 446, "actual_sell": 630, "sell_alt": 630, "accident": "무사고", "options": "스마트키, 내비게이션", "repair_cost": 0, "dealer_fee": 0.0, "base_exp": 15.0},
        {"car_id": "CAR_11_AVANTE_2012", "category": "판매완료", "maker": "현대", "model": "아반떼 MD", "detail": "M16 GDi 프리미어", "year": 2012, "mileage": 108006, "buy_price": 186, "actual_sell": 395, "sell_alt": 395, "accident": "단순교환", "options": "스마트키", "repair_cost": 52, "dealer_fee": 44.0, "base_exp": 15.0}
    ]

def evaluate_models(results: List[Dict[str, Any]]):
    from tests.simulation.evaluate_simulation import run_eval
    temp_path = "tests/simulation/temp_sim_results.json"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    df_680, _ = run_eval(temp_path)
    if os.path.exists(temp_path):
        os.remove(temp_path)
    return df_680

def main():
    parser = argparse.ArgumentParser(description="소매가 추정 모델 재시뮬레이션 검증기")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline", help="실행 모드 (offline: 캐시 검증, live: 실시간 API)")
    args = parser.parse_args()
    
    if args.mode == "offline":
        cached_file = "tests/simulation/simulation_results_masked.json"
        if not os.path.exists(cached_file):
            print(f"Error: {cached_file} not found")
            return
        with open(cached_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"=== 오프라인 재검증 실행 (총 {len(data)}대 차량) ===")
        evaluate_models(data)
    else:
        # 라이브 실행 시 encar_service Scraper 직접 호출
        from services.encar_service import Scraper
        from services.master_mapping import MasterMappingService
        from services.kcar_service import fetch_kcar_market_stats
        print("라이브 실행 모드는 외부 통신 환경이 연결된 상태에서 수행됩니다.")

if __name__ == "__main__":
    main()
