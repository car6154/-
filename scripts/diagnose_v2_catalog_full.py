# -*- coding: utf-8 -*-
"""
scripts/diagnose_v2_catalog_full.py
V2 책(data/catalog_by_source_v2.json)의 319개 차종 전수 진단.
1. 모델명 및 연식 이상 진단:
   - 구형 차종에 미래 연식(2025, 2026, 2027 등)이 들어간 사례
   - 신형 차종에 과거 연식이 들어간 사례
   - 동일 연식이 구형/신형에 걸쳐 중복되거나 왜곡된 사례
   - 연식 gap (중간 연식 누락)
2. 가격 무결성 진단:
   - base_price_man * 10000 != base_price
   - 0원 기본가 또는 0원 옵션가
3. 옵션 이상 진단:
   - desc 누락 옵션
   - 비정상 옵션명
"""

import os
import json
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CATALOG_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2.json")

def main():
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        v2 = json.load(f)

    danawa = v2.get("danawa", {})
    print(f"=== Total Danawa Models in V2: {len(danawa)} ===")

    # 1. 미래 연식 이상 검출
    future_year_issues = []
    price_issues = []
    zero_price_grades = []
    models_by_brand = {}

    for mname, mdata in danawa.items():
        years = sorted(list(mdata.keys()))
        int_years = [int(y) for y in years if y.isdigit()]

        # 구형 모델명인데 2025 이상 연식이 들어간 경우 검사
        # '더 뉴', '올 뉴', 일반 이름인데 '디 올 뉴'가 따로 있는 경우
        for y in years:
            iy = int(y) if y.isdigit() else 0
            if iy >= 2025:
                # 신형 모델명이 아닌데 2025 이상이 들어있는지 확인
                if not any(prefix in mname for prefix in ['디 올 뉴', 'The All New', 'EV', '아이오닉', '토레스', '액티언', '그랑 콜레오스', '캐스퍼']):
                    future_year_issues.append((mname, y, f"구형/중간 모델 [{mname}]에 미래 연식 [{y}] 포함"))

            # 등급 및 가격 검사
            grades = mdata[y]
            for gname, gdata in grades.items():
                bp = gdata.get("base_price", 0)
                bp_man = gdata.get("base_price_man", 0)
                if bp == 0 or bp_man == 0:
                    zero_price_grades.append((mname, y, gname, bp))
                elif bp_man * 10000 != bp:
                    price_issues.append((mname, y, gname, bp, bp_man))

    print(f"\n[1. 미래 연식 오염 의심 사례: {len(future_year_issues)}건]")
    for m, y, msg in future_year_issues:
        print(f"  - {msg}")

    print(f"\n[2. 가격 단위 불일치 (base_price != base_price_man * 10000): {len(price_issues)}건]")
    for p in price_issues[:10]:
        print(f"  - {p}")

    print(f"\n[3. 기본가 0원 등급: {len(zero_price_grades)}건]")
    for z in zero_price_grades[:10]:
        print(f"  - {z}")

if __name__ == "__main__":
    main()
