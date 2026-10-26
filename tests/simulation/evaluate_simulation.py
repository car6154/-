# -*- coding: utf-8 -*-
"""
tests/simulation/evaluate_simulation.py
재시뮬레이션 오차 및 편향 지표 평가 스크립트 (검증용)
- 입력: tests/simulation/simulation_results_masked.json (차량번호 마스킹)
- 평가지표: MAE, MAPE, Bias(Mean Error)
- 그룹별: 전체 (11대), 광고중 (7대), 판매완료 (4대)
- 224버2800 680만(장부 화면) vs 720만(CSV) 양방향 대조
"""
import json
import os
import numpy as np
import pandas as pd

def run_eval(results_path="tests/simulation/simulation_results_masked.json"):
    if not os.path.exists(results_path):
        print(f"Error: {results_path} not found")
        return None, None
        
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} masked cars from {results_path}")
    model_names = list(data[0]["estimates"].keys())
    
    groups = {
        "전체 (11대)": data,
        "광고중 (7대)": [d for d in data if d["category"] == "광고중"],
        "판매완료 (4대)": [d for d in data if d["category"] == "판매완료"]
    }
    
    # 1. 680만 기준 (장부 화면 정답값)
    summary_680 = []
    for m in model_names:
        row = {"model": m}
        for g_name, g_items in groups.items():
            diffs = []
            abs_diffs = []
            pct_diffs = []
            for item in g_items:
                actual = item["actual_sell"]
                est = item["estimates"][m]
                diff = est - actual
                abs_diff = abs(diff)
                pct = (abs_diff / actual) * 100.0 if actual > 0 else 0.0
                diffs.append(diff)
                abs_diffs.append(abs_diff)
                pct_diffs.append(pct)
            prefix = "전체" if "전체" in g_name else ("광고중" if "광고중" in g_name else "판매완료")
            row[f"{prefix}_MAE(만)"] = round(float(np.mean(abs_diffs)), 1)
            row[f"{prefix}_MAPE(%)"] = round(float(np.mean(pct_diffs)), 1)
            row[f"{prefix}_Bias(만)"] = round(float(np.mean(diffs)), 1)
        summary_680.append(row)
        
    df_680 = pd.DataFrame(summary_680).sort_values(by="전체_MAE(만)", ascending=True).reset_index(drop=True)
    
    # 2. 720만 기준 (CSV 기준)
    summary_720 = []
    for m in model_names:
        row_alt = {"model": m}
        for g_name, g_items in groups.items():
            diffs = []
            abs_diffs = []
            pct_diffs = []
            for item in g_items:
                actual = item["sell_alt"]
                est = item["estimates"][m]
                diff = est - actual
                abs_diff = abs(diff)
                pct = (abs_diff / actual) * 100.0 if actual > 0 else 0.0
                diffs.append(diff)
                abs_diffs.append(abs_diff)
                pct_diffs.append(pct)
            prefix = "전체" if "전체" in g_name else ("광고중" if "광고중" in g_name else "판매완료")
            row_alt[f"{prefix}_MAE(만)"] = round(float(np.mean(abs_diffs)), 1)
            row_alt[f"{prefix}_MAPE(%)"] = round(float(np.mean(pct_diffs)), 1)
            row_alt[f"{prefix}_Bias(만)"] = round(float(np.mean(diffs)), 1)
        summary_720.append(row_alt)
        
    df_720 = pd.DataFrame(summary_720).sort_values(by="전체_MAE(만)", ascending=True).reset_index(drop=True)
    
    print("\n" + "="*85)
    print("      [정정 재시뮬레이션 검증] 소매가 추정 모델 순위표 (680만 장부화면 기준 TOP 10)")
    print("="*85)
    print(df_680[["model", "전체_MAE(만)", "전체_MAPE(%)", "전체_Bias(만)", "광고중_MAE(만)", "판매완료_MAE(만)"]].head(10).to_string(index=False))
    
    return df_680, df_720

if __name__ == "__main__":
    run_eval()
