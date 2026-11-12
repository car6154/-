# scripts/generate_conflicts_v3.py
"""
[11-11-20] 제이책(C) 가격 충돌 목록 v3 생성 스크립트
- catalog_c_price_conflicts_v2_2026-11-12.json 기반
- catalog_c.json에 실제로 존재하는 등급만 유지
- 구동방식(2WD vs 4WD/AWD), 변속기(M/T vs A/T) 차이 등 가짜 충돌 제거
- 새 파일 data/catalog_c_price_conflicts_v3_2026-11-12.json에 저장 (옛날 파일 보존)
"""

import os
import sys
import json
import re

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CATALOG_C_FILE = os.path.join(DATA_DIR, "catalog_c.json")
V2_CONFLICTS_FILE = os.path.join(DATA_DIR, "catalog_c_price_conflicts_v2_2026-11-12.json")
V3_CONFLICTS_FILE = os.path.join(DATA_DIR, "catalog_c_price_conflicts_v3_2026-11-12.json")


def get_drivetrain(name: str) -> str:
    n = name.lower()
    if re.search(r'4wd|awd|4륜|사륜', n):
        return '4WD'
    elif re.search(r'2wd|2륜|이륜|전륜|후륜', n):
        return '2WD'
    return 'UNKNOWN'


def get_transmission(name: str) -> str:
    n = name.lower()
    if re.search(r'\bm/t\b|\bmt\b|수동', n):
        return 'MT'
    elif re.search(r'\ba/t\b|\bat\b|자동|오토|dct|cvt|ivt', n):
        return 'AT'
    return 'UNKNOWN'


def generate_v3_conflicts():
    print(f"1. 제이책(C) 로드: {CATALOG_C_FILE}")
    with open(CATALOG_C_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    print(f"2. v2 충돌 목록 로드: {V2_CONFLICTS_FILE}")
    with open(V2_CONFLICTS_FILE, "r", encoding="utf-8") as f:
        v2_conflicts = json.load(f)

    total_v2 = len(v2_conflicts)
    print(f"   - v2 총 충돌 그룹 수: {total_v2:,}개")

    v3_conflicts = []
    removed_due_to_nonexistent = 0
    removed_due_to_drivetrain_trans = 0
    removed_due_to_same_price = 0

    for c in v2_conflicts:
        m = c.get("model", "")
        y = str(c.get("year", ""))

        if m not in catalog or y not in catalog[m]:
            removed_due_to_nonexistent += 1
            continue

        # 1. catalog_c에 실제로 존재하는 등급만 필터링
        existing_grades = []
        for g in c.get("grades", []):
            gname = g.get("name", "")
            if gname in catalog[m][y]:
                c_gdata = catalog[m][y][gname]
                existing_grades.append({
                    "name": gname,
                    "base_price": c_gdata.get("base_price"),
                    "source": c_gdata.get("source", g.get("source"))
                })

        if len(existing_grades) < 2:
            removed_due_to_nonexistent += 1
            continue

        # 2. 구동방식 및 변속기별 서브그룹 분류
        subgroups = {}
        for g in existing_grades:
            drive = get_drivetrain(g["name"])
            trans = get_transmission(g["name"])
            key = (drive, trans)
            if key not in subgroups:
                subgroups[key] = []
            subgroups[key].append(g)

        # 2개 이상 구동방식/변속기로 갈라져서 각각 1개씩만 남은 경우
        had_real_conflict = False
        for (drive, trans), s_grades in subgroups.items():
            if len(s_grades) < 2:
                continue
            prices = set(g["base_price"] for g in s_grades if g["base_price"] is not None)
            if len(prices) > 1:
                had_real_conflict = True
                v3_conflicts.append({
                    "model": m,
                    "year": y,
                    "trim": c.get("trim"),
                    "seating": c.get("seating"),
                    "fuel": c.get("fuel"),
                    "displacement": c.get("displacement"),
                    "drivetrain": drive if drive != "UNKNOWN" else None,
                    "transmission": trans if trans != "UNKNOWN" else None,
                    "grades": s_grades
                })
            else:
                removed_due_to_same_price += 1

        if not had_real_conflict:
            removed_due_to_drivetrain_trans += 1

    print(f"\n3. 정제 결과 요약:")
    print(f"   - v2 충돌 그룹: {total_v2:,}개")
    print(f"   - 현존 등급 1개 이하로 탈락: {removed_due_to_nonexistent:,}개")
    print(f"   - 구동방식/변속기 차이로 탈락: {removed_due_to_drivetrain_trans:,}개")
    print(f"   - 가격 동일로 탈락: {removed_due_to_same_price:,}개")
    print(f"   - 최종 v3 진짜 충돌 그룹: {len(v3_conflicts):,}개")

    with open(V3_CONFLICTS_FILE, "w", encoding="utf-8") as f:
        json.dump(v3_conflicts, f, ensure_ascii=False, indent=2)
    print(f"\n4. 새 파일 저장 완료: {V3_CONFLICTS_FILE}")


if __name__ == "__main__":
    generate_v3_conflicts()
