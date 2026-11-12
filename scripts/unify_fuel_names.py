import os
import json
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CATALOG_C_FILE = os.path.join(DATA_DIR, "catalog_c.json")
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_c_v8_backup_2026-11-12.json")
RENAMED_FILE = os.path.join(DATA_DIR, "catalog_c_fuel_renamed_2026-11-12.json")
REVIEW_FILE = os.path.join(DATA_DIR, "catalog_c_fuel_review_2026-11-12.json")

def transform_grade_name(car_name: str, year: str, original_name: str) -> str:
    new_name = original_name

    # 1. 하이브리드 -> HEV
    if '하이브리드' in new_name:
        if 'HEV' in new_name:
            # 포르테 2013 '1.6 하이브리드 LPI HEV' 등 이미 HEV가 있는 경우 중복 방지
            new_name = re.sub(r'\s*하이브리드\s*', ' ', new_name)
            new_name = re.sub(r'\s+', ' ', new_name).strip()
        else:
            new_name = new_name.replace('하이브리드', 'HEV')

    # 2. LPe -> LPG (대소문자 무시, 2.0LPe 붙은 것 포함)
    if re.search(r'LPe', new_name, re.IGNORECASE):
        new_name = re.sub(r'(?<=[0-9])LPe', ' LPG', new_name, flags=re.IGNORECASE)
        new_name = re.sub(r'LPe', 'LPG', new_name, flags=re.IGNORECASE)
        new_name = re.sub(r'\s+', ' ', new_name).strip()

    # 3. EV -> 전기 (연료 토큰 단독 쓰인 경우)
    if re.search(r'(?<![A-Za-z0-9])EV(?![A-Za-z0-9])', new_name):
        if '전기' in new_name:
            # 쏘울 EV 2018 '전기 2WD EV' 등 이미 전기가 있는 경우
            new_name = re.sub(r'\s*(?<![A-Za-z0-9])EV(?![A-Za-z0-9])\s*', '', new_name).strip()
        else:
            new_name = re.sub(r'(?<![A-Za-z0-9])EV(?![A-Za-z0-9])', '전기', new_name)

    return new_name

def main():
    print("[1/5] 책 데이터 로드...")
    with open(CATALOG_C_FILE, "r", encoding="utf-8") as f:
        cat = json.load(f)

    print(f"[2/5] v8 백업 파일 생성: {BACKUP_FILE}...")
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
    print("      백업 완료!")

    renamed_records = []
    review_records = []
    new_cat = {}

    print("[3/5] 연료 이름 통일 및 충돌 검사 수행...")
    changed_count = 0
    conflict_count = 0

    for m, yrs in cat.items():
        new_cat[m] = {}
        for y, grades in yrs.items():
            new_cat[m][y] = {}
            seen_names = {}
            for gname, gdata in grades.items():
                new_gname = transform_grade_name(m, y, gname)
                
                # 이름이 바뀐 등급
                if new_gname != gname:
                    changed_count += 1
                    renamed_records.append({
                        "model": m,
                        "year": y,
                        "before": gname,
                        "after": new_gname,
                        "source": gdata.get("source", "")
                    })
                
                # 충돌 검사
                if new_gname in seen_names:
                    conflict_count += 1
                    review_records.append({
                        "model": m,
                        "year": y,
                        "original_grade": gname,
                        "target_grade": new_gname,
                        "conflicted_with": seen_names[new_gname],
                        "reason": "중복 등급명 충돌"
                    })
                    # 충돌 시 변경 보류 (원래 이름 유지)
                    new_cat[m][y][gname] = gdata
                else:
                    seen_names[new_gname] = gname
                    # grade 내부의 name 필드도 일관성 있게 업데이트
                    updated_gdata = dict(gdata)
                    updated_gdata["name"] = new_gname
                    new_cat[m][y][new_gname] = updated_gdata

    print(f"      변경 등급 수: {changed_count}개")
    print(f"      충돌 등급 수: {conflict_count}개")

    print(f"[4/5] 산출물 저장...")
    with open(CATALOG_C_FILE, "w", encoding="utf-8") as f:
        json.dump(new_cat, f, ensure_ascii=False, indent=2)
    print(f"      catalog_c.json 갱신 완료!")

    with open(RENAMED_FILE, "w", encoding="utf-8") as f:
        json.dump(renamed_records, f, ensure_ascii=False, indent=2)
    print(f"      {RENAMED_FILE} 저장 완료 ({len(renamed_records)}건)")

    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(review_records, f, ensure_ascii=False, indent=2)
    print(f"      {REVIEW_FILE} 저장 완료 ({len(review_records)}건)")

    print("[5/5] 변환 결과 검증...")
    post_hyb = sum(1 for m in new_cat.values() for y in m.values() for g in y if '하이브리드' in g)
    post_hev = sum(1 for m in new_cat.values() for y in m.values() for g in y if 'HEV' in g)
    post_lpg = sum(1 for m in new_cat.values() for y in m.values() for g in y if 'LPG' in g)
    post_lpe = sum(1 for m in new_cat.values() for y in m.values() for g in y if 'LPe' in g or 'lpe' in g.lower())
    post_elec = sum(1 for m in new_cat.values() for y in m.values() for g in y if '전기' in g)
    post_ev = sum(1 for m in new_cat.values() for y in m.values() for g in y if re.search(r'(?<![A-Za-z0-9])EV(?![A-Za-z0-9])', g))

    print(f"  - 하이브리드: {post_hyb}개 (목표: 0개)")
    print(f"  - HEV: {post_hev}개 (목표: 1070개)")
    print(f"  - LPe: {post_lpe}개 (목표: 0개)")
    print(f"  - LPG: {post_lpg}개 (목표: 340개)")
    print(f"  - EV(연료 토큰): {post_ev}개 (목표: 0개)")
    print(f"  - 전기: {post_elec}개 (목표: 312개)")

    sorento_2025_hev = [g for g in new_cat.get('더 뉴 쏘렌토 4세대', {}).get('2025', {}).keys() if 'HEV' in g]
    sorento_2025_hyb = [g for g in new_cat.get('더 뉴 쏘렌토 4세대', {}).get('2025', {}).keys() if '하이브리드' in g]
    print(f"  - 쏘렌토 2025 HEV: {len(sorento_2025_hev)}개 (목표: 26개)")
    print(f"  - 쏘렌토 2025 하이브리드: {len(sorento_2025_hyb)}개 (목표: 0개)")

    assert post_hyb == 0
    assert post_hev == 1070
    assert post_lpe == 0
    assert post_lpg == 340
    assert post_ev == 0
    assert post_elec == 312
    assert len(sorento_2025_hev) == 26
    assert len(sorento_2025_hyb) == 0
    print("🎉 모든 연료 키워드 검증 100% 통과!")

if __name__ == "__main__":
    main()
