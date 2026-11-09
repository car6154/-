# -*- coding: utf-8 -*-
"""
scripts/merge_batch51_into_v2.py
batch-51-kgm-lineup.json의 16개 KGM 차종을 catalog_by_source_v2.json에 deep merge.
- 기존 69개 차종 불변성 엄격 검증
- 병합 전 백업 생성
"""

import sys
import os
import json
import shutil
import copy

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
BATCH_FILE = os.path.join(DATA_DIR, "batch-51-kgm-lineup.json")
CATALOG_V2_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2.json")
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2_backup_before_batch51.json")

def main():
    print("=== Merging batch-51 into catalog_by_source_v2.json ===")

    # 1. 안전 백업
    shutil.copy2(CATALOG_V2_FILE, BACKUP_FILE)
    print(f"1. Backup created: {BACKUP_FILE}")

    # 2. 원본 로드
    with open(CATALOG_V2_FILE, "r", encoding="utf-8") as f:
        v2_data = json.load(f)

    with open(BATCH_FILE, "r", encoding="utf-8") as f:
        batch_data = json.load(f)

    v2_danawa = v2_data.get("danawa", {})
    batch_danawa = batch_data.get("danawa", {})

    initial_car_count = len(v2_danawa)
    batch_car_count = len(batch_danawa)
    print(f"2. Initial cars in V2: {initial_car_count}")
    print(f"   Cars in batch-51: {batch_car_count}")

    # 기존 69개 차종 스냅샷 (불변성 검증용)
    original_snapshot = copy.deepcopy(v2_danawa)

    # 3. Deep Merge
    # batch_danawa의 차종들을 v2_danawa에 병합
    for car_name, year_dict in batch_danawa.items():
        if car_name not in v2_danawa:
            v2_danawa[car_name] = {}
        for year, grade_dict in year_dict.items():
            if year not in v2_danawa[car_name]:
                v2_danawa[car_name][year] = {}
            for g_name, g_val in grade_dict.items():
                v2_danawa[car_name][year][g_name] = g_val

    # 4. 불변성 전수 검증: 기존 69개 차종이 1비트도 변하지 않았는지 확인
    for car_name, orig_years in original_snapshot.items():
        curr_years = v2_danawa[car_name]
        assert orig_years == curr_years, f"Immutability check failed for existing car '{car_name}'!"

    final_car_count = len(v2_danawa)
    print(f"3. Immutability verified: all {initial_car_count} existing cars 100% unchanged.")
    print(f"4. Final cars in V2: {final_car_count} (expected: {initial_car_count + batch_car_count})")
    assert final_car_count == initial_car_count + batch_car_count, f"Car count mismatch: {final_car_count}"

    # 5. 저장
    with open(CATALOG_V2_FILE, "w", encoding="utf-8") as f:
        json.dump(v2_data, f, ensure_ascii=False, indent=2)

    print(f"5. Saved successfully to: {CATALOG_V2_FILE}")
    print("=== Merge Completed Successfully ===")

if __name__ == "__main__":
    main()
