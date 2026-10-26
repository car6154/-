# -*- coding: utf-8 -*-
"""
tests/simulation/run_simulation.py
진짜 7대 대상 소매가 추정 재시뮬레이션 실행 및 검증기
- 규칙:
  1. 대상: 진짜 7대만 (재고 6대 + 팔린 차 1대)
  2. 제외: 없는 차 4대 (132고3133, 176고8859, 57거9350, 16무9109)
  3. 엔카 0건이면 케이카 값으로 메우지 않음 ("데이터 없음", 엔카 순위 제외)
  4. 케이카 순위는 케이카 데이터만으로 독립 산출
  5. 원가 기반 모델(매입가 사용)은 시장 방법 순위에서 제외
  6. 팔린 차는 1대뿐이라 순위 산출 제외, 별도 단독 오차 보고
  7. 성공 기준: 7대 전부 encar_count > 0일 것 (미달 시 무효 보고)
"""
import sys
import os
import argparse
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("."))

def main():
    parser = argparse.ArgumentParser(description="소매가 추정 모델 재시뮬레이션 검증기")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline", help="실행 모드 (offline: 캐시 검증, live: 실시간 API)")
    args = parser.parse_args()
    
    if args.mode == "offline":
        cached_file = "tests/simulation/simulation_results_masked.json"
        if not os.path.exists(cached_file):
            print(f"Error: {cached_file} not found")
            return
        from scratch.evaluate_7cars_simulation import evaluate_7cars
        print(f"=== 진짜 7대 오프라인 재검증 실행 ({cached_file}) ===")
        evaluate_7cars(cached_file)
    else:
        from scratch.run_7cars_live_simulation import run_cockpit_simulation
        from scratch.evaluate_7cars_simulation import evaluate_7cars
        print("=== 진짜 7대 실시간 라이브 시뮬레이션 실행 ===")
        run_cockpit_simulation()
        evaluate_7cars()

if __name__ == "__main__":
    main()
