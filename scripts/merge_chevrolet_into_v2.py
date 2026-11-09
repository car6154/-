# -*- coding: utf-8 -*-
"""
scripts/merge_chevrolet_into_v2.py
data/batch-chevrolet-lineup.json의 쉐보레 카탈로그 데이터를 catalog_by_source_v2.json에 deep merge.
- 기존 V2 데이터 100% 불변성 엄격 검증 (기존 연식/등급 1비트도 훼손 금지)
- 스파크 EV 2015년 누락 연식 보강
- 병합 전 안전 백업 생성
"""

import sys
import os
import json
import shutil
import copy

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
BATCH_FILE = os.path.join(DATA_DIR, "batch-chevrolet-lineup.json")
CATALOG_V2_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2.json")
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2_backup_before_chevrolet.json")


def main():
    print("=== Merging Chevrolet Catalog into catalog_by_source_v2.json ===")

    if not os.path.exists(BATCH_FILE):
        print(f"[오류] 배치 파일이 존재하지 않습니다: {BATCH_FILE}")
        sys.exit(1)

    # 1. 안전 백업 생성
    shutil.copy2(CATALOG_V2_FILE, BACKUP_FILE)
    print(f"1. 안전 백업 생성 완료: {BACKUP_FILE}")

    # 2. 원본 및 배치 로드
    with open(CATALOG_V2_FILE, "r", encoding="utf-8") as f:
        v2_data = json.load(f)

    with open(BATCH_FILE, "r", encoding="utf-8") as f:
        batch_data = json.load(f)

    v2_danawa = v2_data.get("danawa", {})
    batch_danawa = batch_data.get("danawa", {})

    initial_car_count = len(v2_danawa)
    batch_car_count = len(batch_danawa)
    print(f"2. 병합 전 V2 총 차종 수: {initial_car_count}개")
    print(f"   쉐보레 수집 차종 수: {batch_car_count}개")

    # 기존 데이터 깊은 복사 (불변성 검증 스냅샷)
    original_snapshot = copy.deepcopy(v2_danawa)

    # 3. Deep Merge (순수 추가 - Additive Merge)
    new_cars_added = []
    new_years_added = []

    for car_name, year_dict in batch_danawa.items():
        if car_name not in v2_danawa:
            v2_danawa[car_name] = {}
            new_cars_added.append(car_name)

        for year, grade_dict in year_dict.items():
            if year not in v2_danawa[car_name]:
                # 신규 연식 추가 (예: 스파크 EV 2015년)
                v2_danawa[car_name][year] = grade_dict
                if car_name not in new_cars_added:
                    new_years_added.append(f"{car_name} {year}")
            else:
                # 기존에 이미 연식이 있는 경우: 기존 등급은 불변 유지, 신규 등급만 보완
                for g_name, g_val in grade_dict.items():
                    if g_name not in v2_danawa[car_name][year]:
                        v2_danawa[car_name][year][g_name] = g_val

    # 4. 불변성 전수 검증: 기존 V2에 존재하던 모든 차종·연식·등급·옵션이 100% 동일하게 보존되었는가?
    print("3. 기존 V2 책 데이터 불변성 전수 검증 시작...")
    for car_name, orig_years in original_snapshot.items():
        curr_years = v2_danawa[car_name]
        for y, orig_grades in orig_years.items():
            assert y in curr_years, f"기존 연식 누락 발견: {car_name} {y}"
            curr_grades = curr_years[y]
            for g_name, orig_gval in orig_grades.items():
                assert g_name in curr_grades, f"기존 등급 누락 발견: {car_name} {y} {g_name}"
                curr_gval = curr_grades[g_name]
                # base_price 불변
                assert orig_gval.get("base_price") == curr_gval.get("base_price"), f"base_price 변경 발견: {car_name} {y} {g_name}"
                # base_price_man 불변
                assert orig_gval.get("base_price_man") == curr_gval.get("base_price_man"), f"base_price_man 변경 발견: {car_name} {y} {g_name}"
                # 기존 옵션 불변
                for opt_k, orig_opt_v in orig_gval.get("options", {}).items():
                    assert opt_k in curr_gval.get("options", {}), f"기존 옵션 누락: {car_name} {y} {g_name} [{opt_k}]"
                    assert orig_opt_v.get("price") == curr_gval["options"][opt_k].get("price"), f"옵션 가격 변경: {car_name} {y} {g_name} [{opt_k}]"

    print(f"   => 기존 {initial_car_count}개 차종의 모든 연식/등급/옵션 100% 불변 검증 완료!")

    # 5. 가격 전수 검증 (price == price_man * 10000)
    print("4. 전체 V2 책 가격 무결성 전수 검증...")
    mismatch_count = 0
    total_grades_checked = 0
    total_options_checked = 0

    for c_name, years in v2_danawa.items():
        for y, grades in years.items():
            for g_name, g_info in grades.items():
                total_grades_checked += 1
                bp = g_info.get("base_price", 0)
                bpm = g_info.get("base_price_man", 0)
                if abs(bp - bpm * 10000) > 0.01:
                    mismatch_count += 1
                for opt_k, opt_v in g_info.get("options", {}).items():
                    total_options_checked += 1
                    op = opt_v.get("price", 0)
                    opm = opt_v.get("price_man", 0)
                    if abs(op - opm * 10000) > 0.01:
                        mismatch_count += 1

    assert mismatch_count == 0, f"가격 불일치 {mismatch_count}건 발생!"
    print(f"   => 검증 통과: 총 {total_grades_checked}개 등급, {total_options_checked}개 옵션 검사 (불일치 0건)")

    # 6. 통계 요약
    final_car_count = len(v2_danawa)
    print(f"\n5. 병합 통계 요약:")
    print(f"   - 신규 추가된 차종 수: {len(new_cars_added)}개")
    print(f"   - 신규 추가된 연식: {len(new_years_added)}건 (예: {new_years_added[:3]})")
    print(f"   - 최종 V2 총 차종 수: {initial_car_count} -> {final_car_count}개 (+{len(new_cars_added)})")

    # 7. 파일 저장
    with open(CATALOG_V2_FILE, "w", encoding="utf-8") as f:
        json.dump(v2_data, f, ensure_ascii=False, indent=2)

    print(f"6. 저장 완료: {CATALOG_V2_FILE}")
    print("=== Chevrolet Merge Completed Successfully ===")


if __name__ == "__main__":
    main()

