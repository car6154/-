# -*- coding: utf-8 -*-
"""
tests/simulation/run_10cars_simulation.py
오토플러스 전사 판매완료 10대 대표 차량 대상 실시간 소매가 추정 시뮬레이션

[규칙]
1. 국산 1~10위 차종 대표 차량 1대씩, 총 10대 (S01~S10)
2. 엔카 쿠키는 services/cookie_server.py의 get_current_encar_cookie()로 읽음 (값 하드코딩/커밋 금지)
3. 1대씩 조회, 차량 간 간격 60초 유지, 상세 조회 pacing 2초
4. 407 감지 시 즉시 전체 실행 멈춤 (재시도 금지, 다음 차 금지, 추가 요청 금지)
5. 엔카 0건이면 케이카 값으로 메우지 않고 '데이터 없음' 처리 및 엔카 순위 제외
6. 원가 기반 모델은 시장 방법 순위에서 제외
7. 정답값: 판매 파일의 실제 판매가 (할인적용가 = 지점판매가 동일)
"""
import sys
import os
import time
import json
import re
import numpy as np
import pandas as pd
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath("."))
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import warnings
warnings.filterwarnings('ignore')

from services.master_mapping import MasterMappingService
from services.encar_service import Scraper
from services.kcar_service import fetch_kcar_market_stats
from services.data_processor import DataProcessor
from services.cookie_server import get_current_encar_cookie

MAKER_MAP = {
    '스타리아': '현대',
    '그랜저': '현대',
    '아반떼': '현대',
    '레이': '기아',
    'G80': '제네시스',
    '쏘렌토': '기아',
    'GV70': '제네시스',
    '싼타페': '현대',
    '카니발': '기아',
    '쏘나타': '현대'
}

def calc_streamlit_ai(df: pd.DataFrame, target_mil: int, target_acc: str = "무사고", target_opts: str = "") -> Dict[str, Any]:
    if df.empty:
        return {"streamlit_ai": None, "streamlit_no_acc_mean": None}
    price_col = "판매가" if "판매가" in df.columns else "Price"
    mil_col = "주행거리" if "주행거리" in df.columns else "Mileage"
    pdf = df.copy()
    pdf["_p"] = pd.to_numeric(pdf[price_col].astype(str).str.replace(",", "").str.replace("만원", ""), errors="coerce").fillna(0)
    pdf["_m"] = pd.to_numeric(pdf[mil_col].astype(str).str.replace(",", "").str.replace("km", ""), errors="coerce").fillna(0)
    pdf = pdf[pdf["_p"] > 0]
    if pdf.empty:
        return {"streamlit_ai": None, "streamlit_no_acc_mean": None}
    
    acc_col = "사고유무" if "사고유무" in pdf.columns else "accident"
    if acc_col in pdf.columns:
        is_no_acc = pdf[acc_col].astype(str).str.contains("무사고")
        no_acc_df = pdf[is_no_acc] if is_no_acc.any() else pdf
    else:
        no_acc_df = pdf
    base_price = int(round(no_acc_df["_p"].mean()))
    base_mil = int(round(no_acc_df["_m"].mean())) if not no_acc_df.empty else target_mil
    
    slope = -0.005
    reg_df = no_acc_df if len(no_acc_df) >= 3 else pdf
    if len(reg_df) >= 2:
        try:
            fit_z = np.polyfit(reg_df["_m"], reg_df["_p"], 1)
            if -0.02 <= fit_z[0] <= -0.001:
                slope = fit_z[0]
        except Exception:
            pass
            
    mil_diff = target_mil - base_mil
    mil_adj = int(round(mil_diff * slope))
    acc_adj = -80 if ("사고" in target_acc and "무사고" not in target_acc) else (-30 if any(k in target_acc for k in ["단순", "교환", "판금"]) else 0)
    opt_adj = 0
    if target_opts:
        opts_list = [o.strip() for o in re.split(r'[,·/]', target_opts) if o.strip()]
        opt_adj = min(50, len(opts_list) * 15)
    final_ai = max(10, base_price + mil_adj + acc_adj + opt_adj)
    return {
        "streamlit_ai": final_ai,
        "streamlit_no_acc_mean": base_price
    }

def run_simulation():
    # 1. 10대 대표 차량 로드
    rep_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scratch", "selected_representatives.json")
    with open(rep_file, "r", encoding="utf-8") as f:
        cars = json.load(f)
        
    print("=" * 75)
    print(f"오토플러스 전사 판매완료 10대 대표 차량 대상 소매가 추정 시뮬레이션 시작")
    print(f"총 {len(cars)}대 (S01~S10), 차종당 1대 (연식/주행거리 중앙값 차량)")
    print("규칙:")
    print("  1. 1대씩 순차 조회, 차량 간 간격 60초")
    print("  2. w5 상세 조회 스킵 금지, pacing 2.0초")
    print("  3. 407 감지 시 즉시 중단 (재시도 금지, 다음 차 금지, 추가 요청 금지)")
    print("  4. 엔카 0건 시 케이카 값 대체 금지 ('데이터 없음' 처리 및 엔카 순위 제외)")
    print("=" * 75)
    
    encar_cookie = get_current_encar_cookie()
    cookie_len = len(encar_cookie) if encar_cookie else 0
    print(f"[사전 점검] get_current_encar_cookie() 확인: {cookie_len}자리")
    if cookie_len == 0:
        print("❌ [중단] 엔카 쿠키가 0자이므로 실행하지 않고 즉시 종료합니다.")
        return
        
    results = []
    blocked_info = None
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tests", "simulation")
    os.makedirs(output_dir, exist_ok=True)
    live_res_file = os.path.join(output_dir, "simulation_results_10cars_live.json")
    masked_res_file = os.path.join(output_dir, "simulation_results_10cars_masked.json")
    
    for idx, c in enumerate(cars):
        mask_id = c['mask_id']
        model_group = c['model_group']
        maker = MAKER_MAP.get(model_group, '국산')
        car_name = c['car_name']
        sub_model = c['sub_model']
        year = c['year']
        mileage = c['mileage']
        actual_price = int(round(c['disc_price'] / 10000)) # 만원 단위
        
        print(f"\n[{idx+1}/{len(cars)}] 차량 조회 시작: {mask_id} ({model_group})")
        print(f"  제원: {maker} {car_name} | {sub_model} | {year}년식 | {mileage:,}km")
        print(f"  실제 판매가(정답): {actual_price:,}만원 (원문: {c['disc_price']:,}원)")
        
        # 1. 엔카 검색 URL 생성
        encar_url = MasterMappingService.generate_smart_encar_url(
            car_name=car_name,
            sub_model=sub_model,
            year=year,
            mileage=mileage,
            car_number=""
        )
        print(f"  엔카 URL: {encar_url[:90]}...")
        
        # 2. 엔카 Scraper.run 실행 (pacing=True, 2.0초 간격)
        print(f"  엔카 Scraper.run 실행 [pacing=True, 2.0초 간격]...")
        df, msg = Scraper.run(encar_url, encar_cookie, pacing=True, detail_interval=2.0)
        encar_count = len(df)
        print(f"  엔카 수집 결과: {encar_count}건 (msg: {msg})")
        
        # 3. 407 감지 시 즉시 중단 검사
        is_407 = ("407" in str(msg)) or (encar_count == 0 and "407" in str(msg))
        if is_407:
            print("\n" + "!" * 75)
            print(f"🛑 [407 감지 즉시 중단] {mask_id} ({model_group}) 조회 중 HTTP 407 발생!")
            print(f"   => 규칙에 따라 재시도 금지, 다음 차 진행 금지, 추가 요청 없이 그 자리에서 전체 실행을 즉시 멈춥니다.")
            print("!" * 75)
            blocked_info = {
                "blocked_index": idx + 1,
                "blocked_car_id": mask_id,
                "blocked_model": f"{maker} {car_name} {sub_model}",
                "msg": msg
            }
            results.append({
                "mask_id": mask_id,
                "model_group": model_group,
                "maker": maker,
                "car_name": car_name,
                "sub_model": sub_model,
                "year": year,
                "mileage": mileage,
                "actual_price": actual_price,
                "encar_count": 0,
                "encar_strict_count": 0,
                "kcar_count": 0,
                "status": "BLOCKED_BY_407",
                "encar_models": {
                    "EN_01_엔카_단순평균": None,
                    "EN_02_엔카_중앙값": None,
                    "EN_03_React_벤치마크": None,
                    "EN_04_Streamlit_벤치마크": None
                },
                "kcar_models": {
                    "KC_01_케이카_평균": None
                },
                "ens_models": {
                    "ENS_01_엔카케이카_앙상블": None
                }
            })
            break
            
        # 4. 엔카 표준화 및 엄격 필터링
        df = DataProcessor.standardize(df)
        df = Scraper.dedupe_after_scan(df)
        df = DataProcessor.filter_strictly_by_submodel(df, target_car_name=car_name, target_sub_model=sub_model)
        df = DataProcessor.sort_by_perf_and_year(df)
        wide_encar_count = len(df)
        
        strict_df = DataProcessor.filter_strictly_same_year_and_grade(
            df,
            target_year=year,
            target_detail_model=sub_model
        )
        strict_encar_count = len(strict_df)
        print(f"  엔카 매물 변화: [수집] {encar_count}건 -> [넓은필터] {wide_encar_count}건 -> [엄격필터] {strict_encar_count}건")
        
        # 5. 엔카 추정치 산출
        if strict_encar_count > 0:
            price_col = "판매가" if "판매가" in strict_df.columns else "Price"
            prices = pd.to_numeric(strict_df[price_col].astype(str).str.replace(",", "").str.replace("만원", ""), errors="coerce").dropna()
            prices = prices[prices > 0]
            encar_avg = int(round(prices.mean())) if not prices.empty else None
            encar_median = int(round(prices.median())) if not prices.empty else None
            
            bench = Scraper.get_benchmarked_valuation(
                chart_base=df,
                target_mil=mileage,
                target_accident="무사고",
                target_year=year,
                target_options="",
                target_opt_adj=0,
                target_sub_model=sub_model
            )
            react_bench = bench.get("calc_individual_price") if bench.get("has_data") else None
            st_res = calc_streamlit_ai(strict_df, mileage, "무사고", "")
            st_bench = st_res.get("streamlit_ai")
        else:
            print(f"  ⚠️ 엔카 엄격 필터 매물 0건 => '데이터 없음' 처리")
            encar_avg = None
            encar_median = None
            react_bench = None
            st_bench = None
            
        encar_models = {
            "EN_01_엔카_단순평균": encar_avg,
            "EN_02_엔카_중앙값": encar_median,
            "EN_03_React_벤치마크": react_bench,
            "EN_04_Streamlit_벤치마크": st_bench
        }
        
        # 6. 케이카 실시간 조회
        kcar_stats = fetch_kcar_market_stats(
            car_name=car_name,
            year=year,
            detail_model=sub_model,
            mileage=mileage,
            manufacturer=maker
        )
        kcar_strict_count = kcar_stats.get("strictCount", 0)
        kcar_wide_count = kcar_stats.get("wideCount", 0)
        kcar_avg = kcar_stats.get("avg")
        kcar_adj = kcar_stats.get("avgAdj")
        print(f"  케이카 매물 변화: [수집/넓은필터] {kcar_wide_count}건 -> [엄격필터] {kcar_strict_count}건 | avg: {kcar_avg} | avgAdj: {kcar_adj}")
        
        kcar_models = {
            "KC_01_케이카_평균": kcar_avg,
            "KC_02_케이카_마일리지보정가": kcar_adj
        }
        
        # 7. 엔카+케이카 앙상블 (둘 다 있을 때만)
        if encar_avg is not None and kcar_avg is not None:
            ens_price = int(round((encar_avg + kcar_avg) / 2))
        elif react_bench is not None and kcar_adj is not None:
            ens_price = int(round((react_bench + kcar_adj) / 2))
        else:
            ens_price = None
            
        ens_models = {
            "ENS_01_엔카케이카_앙상블": ens_price
        }
        
        car_result = {
            "mask_id": mask_id,
            "model_group": model_group,
            "maker": maker,
            "car_name": car_name,
            "sub_model": sub_model,
            "year": year,
            "mileage": mileage,
            "actual_price": actual_price,
            "encar_count": encar_count,
            "encar_strict_count": strict_encar_count,
            "kcar_count": kcar_strict_count,
            "status": "COMPLETED",
            "encar_models": encar_models,
            "kcar_models": kcar_models,
            "ens_models": ens_models
        }
        results.append(car_result)
        
        # 실시간 저장 (중간 유실 방지)
        with open(live_res_file, "w", encoding="utf-8") as f:
            json.dump({"results": results, "blocked_info": blocked_info}, f, ensure_ascii=False, indent=2)
            
        print(f"  [중간 결과] 실제가: {actual_price}만 | 엔카평균: {encar_avg} | 엔카중앙값: {encar_median} | React: {react_bench} | Streamlit: {st_bench} | 케이카평균: {kcar_avg} | 앙상블: {ens_price}")
        
        # 차량 간 간격 60초 대기 (마지막 차량 제외)
        if idx < len(cars) - 1:
            print(f"  ⏳ [Pacing] 지시사항(3번)에 따라 다음 차 조회 전 60초간 대기합니다...")
            time.sleep(60)

    # 마스킹 결과 저장
    with open(masked_res_file, "w", encoding="utf-8") as f:
        json.dump({"results": results, "blocked_info": blocked_info}, f, ensure_ascii=False, indent=2)
        
    print("\n" + "=" * 75)
    print("시뮬레이션 완료. 결과 분석 및 요약 지표 산출 시작...")
    print("=" * 75)
    
    # 지표 산출 및 리포트 생성
    evaluate_results(results, blocked_info)

def evaluate_results(results: List[Dict[str, Any]], blocked_info: Any):
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tests", "simulation")
    summary_file = os.path.join(output_dir, "simulation_summary_10cars.json")
    
    completed_cars = [r for r in results if r.get("status") == "COMPLETED"]
    encar_valid_cars = [r for r in completed_cars if r.get("encar_strict_count", 0) > 0]
    
    print(f"\n총 시뮬레이션 시도: {len(results)}대")
    print(f"정상 완료 차량: {len(completed_cars)}대")
    print(f"엔카 데이터 유효 차량: {len(encar_valid_cars)}대")
    if blocked_info:
        print(f"🛑 407 차단 정보: {blocked_info}")
        
    # 비교 대상 모델 6가지 (시장 방법)
    market_models = [
        ("EN_01_엔카_단순평균", "encar_models", "EN_01_엔카_단순평균"),
        ("EN_02_엔카_중앙값", "encar_models", "EN_02_엔카_중앙값"),
        ("EN_03_React_벤치마크", "encar_models", "EN_03_React_벤치마크"),
        ("EN_04_Streamlit_벤치마크", "encar_models", "EN_04_Streamlit_벤치마크"),
        ("KC_01_케이카_평균", "kcar_models", "KC_01_케이카_평균"),
        ("ENS_01_엔카케이카_앙상블", "ens_models", "ENS_01_엔카케이카_앙상블")
    ]
    
    metrics = {}
    for name, group, key in market_models:
        errors = []
        apes = []
        biases = []
        valid_count = 0
        
        for r in completed_cars:
            actual = r['actual_price']
            pred = r.get(group, {}).get(key)
            if pred is not None and pred > 0:
                err = pred - actual
                abs_err = abs(err)
                ape = (abs_err / actual) * 100
                errors.append(abs_err)
                apes.append(ape)
                biases.append(err)
                valid_count += 1
                
        if valid_count > 0:
            mae = float(np.mean(errors))
            mape = float(np.mean(apes))
            bias = float(np.mean(biases))
        else:
            mae = None
            mape = None
            bias = None
            
        metrics[name] = {
            "name": name,
            "valid_count": valid_count,
            "total_count": len(completed_cars),
            "mae": round(mae, 1) if mae is not None else None,
            "mape": round(mape, 2) if mape is not None else None,
            "bias": round(bias, 1) if bias is not None else None
        }
        
    summary_data = {
        "total_cars": len(results),
        "completed_count": len(completed_cars),
        "encar_valid_count": len(encar_valid_cars),
        "blocked_info": blocked_info,
        "metrics": metrics,
        "car_table": [
            {
                "mask_id": r["mask_id"],
                "model_group": r["model_group"],
                "actual_price": r["actual_price"],
                "encar_count": r.get("encar_count", 0),
                "encar_strict_count": r.get("encar_strict_count", 0),
                "kcar_count": r.get("kcar_count", 0),
                "encar_avg": r.get("encar_models", {}).get("EN_01_엔카_단순평균"),
                "encar_median": r.get("encar_models", {}).get("EN_02_엔카_중앙값"),
                "react_bench": r.get("encar_models", {}).get("EN_03_React_벤치마크"),
                "st_bench": r.get("encar_models", {}).get("EN_04_Streamlit_벤치마크"),
                "kcar_avg": r.get("kcar_models", {}).get("KC_01_케이카_평균"),
                "ens_price": r.get("ens_models", {}).get("ENS_01_엔카케이카_앙상블")
            }
            for r in completed_cars
        ]
    }
    
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
    print("\n=== 시장 방법별 성능 평가 요약 ===")
    ranked = sorted([m for m in metrics.values() if m['mae'] is not None], key=lambda x: x['mae'])
    for rank, m in enumerate(ranked, 1):
        print(f"[{rank}위] {m['name']:25s} | MAE: {m['mae']:5.1f}만원 | MAPE: {m['mape']:5.2f}% | 편향(bias): {m['bias']:+5.1f}만원 | 표본: {m['valid_count']}/{m['total_count']}대")

if __name__ == "__main__":
    run_simulation()
