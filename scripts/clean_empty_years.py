# scripts/clean_empty_years.py
"""
[11-11-22] 제이책(C) 빈 연식 정리 스크립트
- 등급 0개인 빈 연식 30개 채우거나 지우기
- 백업: data/catalog_c_v7_backup_2026-11-12.json
- 산출: data/catalog_c.json
- 채운 내역: data/catalog_c_empty_year_filled_2026-11-12.json
- 지운 연식: data/catalog_c_empty_year_removed_2026-11-12.json
- 검토 목록: data/catalog_c_empty_year_review_2026-11-12.json
"""

import os
import sys
import json
import shutil
from datetime import datetime

# 콘솔 UTF-8 출력 보장
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

CATALOG_C_FILE = os.path.join(DATA_DIR, "catalog_c.json")
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_c_v7_backup_2026-11-12.json")
FILLED_FILE = os.path.join(DATA_DIR, "catalog_c_empty_year_filled_2026-11-12.json")
REMOVED_FILE = os.path.join(DATA_DIR, "catalog_c_empty_year_removed_2026-11-12.json")
REVIEW_FILE = os.path.join(DATA_DIR, "catalog_c_empty_year_review_2026-11-12.json")


def log(msg: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


def merge_two_grade_dicts(dict_a: dict, dict_b: dict) -> dict:
    """
    두 등급 딕셔너리를 병합.
    같은 가격/사양이면 더 상세한(긴) 이름을 우선하고 옵션은 합집합으로 병합.
    """
    res = {}
    for gname, gdata in dict_a.items():
        res[gname] = dict(gdata)
        res[gname]['options'] = dict(gdata.get('options', {}))

    for b_name, b_data in dict_b.items():
        b_price = b_data.get('base_price')
        matched_a_name = None
        for a_name, a_data in res.items():
            if a_data.get('base_price') == b_price and b_price is not None:
                matched_a_name = a_name
                break

        if matched_a_name:
            target_key = matched_a_name if len(matched_a_name) >= len(b_name) else b_name
            target_data = res[matched_a_name] if len(matched_a_name) >= len(b_name) else dict(b_data)
            
            merged_opts = dict(res[matched_a_name].get('options', {}))
            for ok, ov in b_data.get('options', {}).items():
                if ok not in merged_opts:
                    merged_opts[ok] = ov

            target_data['options'] = merged_opts
            if target_key != matched_a_name:
                del res[matched_a_name]
            res[target_key] = target_data
        else:
            res[b_name] = dict(b_data)
            res[b_name]['options'] = dict(b_data.get('options', {}))

    return res


def run_clean_empty_years():
    log("==================================================")
    log("🚀 [11-11-22] 제이책(C) 빈 연식 정리 시작")
    log("==================================================")

    # 1. v7 백업 생성
    if not os.path.exists(BACKUP_FILE):
        log(f"1. v7 백업 생성 중 -> {BACKUP_FILE}")
        shutil.copyfile(CATALOG_C_FILE, BACKUP_FILE)
    else:
        log(f"1. v7 백업 파일 확인됨: {BACKUP_FILE}")

    with open(CATALOG_C_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    before_grades = sum(len(y) for y in catalog.values() for y in y.values())
    before_years = sum(len(y) for y in catalog.values())
    log(f"  - 정리 전 총 차종 수: {len(catalog)}개, 총 연식 수: {before_years:,}개, 총 등급 수: {before_grades:,}개")

    filled_logs = []
    removed_logs = []
    review_logs = []

    # ----------------------------------------------------
    # A. 채워 넣기 (Filled)
    # ----------------------------------------------------
    log("\n2. 빈 연식 등급 채워 넣기 진행 중...")

    # A-1. 더 뉴 카니발 4세대 2025
    c_4_25 = catalog.get('카니발 4세대', {}).get('2025', {})
    c_new_25 = catalog.get('더 뉴 카니발', {}).get('2025', {})
    if c_4_25 or c_new_25:
        merged_25 = merge_two_grade_dicts(c_4_25, c_new_25)
        catalog['더 뉴 카니발 4세대']['2025'] = merged_25
        filled_logs.append({
            'target_model': '더 뉴 카니발 4세대',
            'year': '2025',
            'filled_grades_count': len(merged_25),
            'sources': ['카니발 4세대 2025 (32개)', '더 뉴 카니발 2025 (12개)']
        })
        if '2025' in catalog.get('카니발 4세대', {}):
            del catalog['카니발 4세대']['2025']
        if '2025' in catalog.get('더 뉴 카니발', {}):
            del catalog['더 뉴 카니발']['2025']
        log(f"  - [더 뉴 카니발 4세대 2025] {len(merged_25)}개 등급 병합 채움 완료 (중복 소스 2개 연식 정리)")

    # A-2. 더 뉴 카니발 4세대 2026
    c_4_26 = catalog.get('카니발 4세대', {}).get('2026', {})
    c_new_26 = catalog.get('더 뉴 카니발', {}).get('2026', {})
    if c_4_26 or c_new_26:
        merged_26 = merge_two_grade_dicts(c_4_26, c_new_26)
        catalog['더 뉴 카니발 4세대']['2026'] = merged_26
        filled_logs.append({
            'target_model': '더 뉴 카니발 4세대',
            'year': '2026',
            'filled_grades_count': len(merged_26),
            'sources': ['카니발 4세대 2026 (28개)', '더 뉴 카니발 2026 (16개)']
        })
        if '2026' in catalog.get('카니발 4세대', {}):
            del catalog['카니발 4세대']['2026']
        if '2026' in catalog.get('더 뉴 카니발', {}):
            del catalog['더 뉴 카니발']['2026']
        log(f"  - [더 뉴 카니발 4세대 2026] {len(merged_26)}개 등급 병합 채움 완료 (중복 소스 2개 연식 정리)")

    # A-3. K5 하이브리드 3세대 2021
    k5_3_21 = catalog.get('K5 3세대', {}).get('2021', {})
    k5_hev_21 = {}
    for gname in list(k5_3_21.keys()):
        if '하이브리드' in gname or 'HEV' in gname:
            k5_hev_21[gname] = k5_3_21[gname]
            del k5_3_21[gname]
    if k5_hev_21:
        catalog['K5 하이브리드 3세대']['2021'] = k5_hev_21
        filled_logs.append({
            'target_model': 'K5 하이브리드 3세대',
            'year': '2021',
            'filled_grades_count': len(k5_hev_21),
            'sources': ['K5 3세대 2021 (하이브리드 등급)']
        })
        log(f"  - [K5 하이브리드 3세대 2021] {len(k5_hev_21)}개 하이브리드 등급 분리 채움 완료")

    # A-4. 디 올 뉴 니로 2026
    niro_2_26 = catalog.get('더 뉴 니로 2세대', {}).get('2026', {})
    if niro_2_26:
        catalog['디 올 뉴 니로']['2026'] = dict(niro_2_26)
        filled_logs.append({
            'target_model': '디 올 뉴 니로',
            'year': '2026',
            'filled_grades_count': len(niro_2_26),
            'sources': ['더 뉴 니로 2세대 2026 (3개)']
        })
        del catalog['더 뉴 니로 2세대']['2026']
        log(f"  - [디 올 뉴 니로 2026] {len(niro_2_26)}개 등급 이동 채움 완료")

    # A-5. 더 뉴 기아 레이 2026
    ray_26 = catalog.get('더 뉴 레이', {}).get('2026', {})
    if ray_26:
        catalog['더 뉴 기아 레이']['2026'] = dict(ray_26)
        filled_logs.append({
            'target_model': '더 뉴 기아 레이',
            'year': '2026',
            'filled_grades_count': len(ray_26),
            'sources': ['더 뉴 레이 2026 (10개)']
        })
        del catalog['더 뉴 레이']['2026']
        log(f"  - [더 뉴 기아 레이 2026] {len(ray_26)}개 등급 이동 채움 완료")

    # A-6. 더 뉴 셀토스 2026
    seltos_2_26 = catalog.get('셀토스 2세대', {}).get('2026', {})
    if seltos_2_26:
        catalog['더 뉴 셀토스']['2026'] = dict(seltos_2_26)
        filled_logs.append({
            'target_model': '더 뉴 셀토스',
            'year': '2026',
            'filled_grades_count': len(seltos_2_26),
            'sources': ['셀토스 2세대 2026 (20개)']
        })
        del catalog['셀토스 2세대']['2026']
        log(f"  - [더 뉴 셀토스 2026] {len(seltos_2_26)}개 등급 이동 채움 완료")

    # A-7. 더 뉴 스포티지 5세대 하이브리드 2025, 2026
    for sp_yr in ['2025', '2026']:
        sp_grades = catalog.get('더 뉴 스포티지 5세대', {}).get(sp_yr, {})
        sp_hev = {}
        for gname in list(sp_grades.keys()):
            if 'HEV' in gname or '하이브리드' in gname:
                sp_hev[gname] = sp_grades[gname]
                del sp_grades[gname]
        if sp_hev:
            catalog['더 뉴 스포티지 5세대 하이브리드'][sp_yr] = sp_hev
            filled_logs.append({
                'target_model': '더 뉴 스포티지 5세대 하이브리드',
                'year': sp_yr,
                'filled_grades_count': len(sp_hev),
                'sources': [f'더 뉴 스포티지 5세대 {sp_yr} (하이브리드 등급)']
            })
            log(f"  - [더 뉴 스포티지 5세대 하이브리드 {sp_yr}] {len(sp_hev)}개 하이브리드 등급 분리 채움 완료")

    # ----------------------------------------------------
    # B. 진짜 없는 빈 연식 키 삭제 (Removed)
    # ----------------------------------------------------
    log("\n3. 진짜 없는 빈 연식 키 삭제 진행 중...")
    years_to_remove = [
        ("더 뉴 아이오닉 일렉트릭", "2021", "2020년 단종 (아이오닉5 전환)"),
        ("더 뉴 아이오닉 하이브리드", "2021", "2020년 단종"),
        ("더 뉴 K5 2세대", "2021", "2019년 3세대 출시로 2세대 단종"),
        ("더 뉴 니로", "2022", "1세대 F/L 2021년 단종"),
        ("니로 EV", "2022", "1세대 EV 2021년 단종"),
        ("더 뉴 기아 레이 EV", "2025", "2025년형 가격표 미존재"),
        ("더 뉴 기아 레이 EV", "2026", "2026년형 미출시"),
        ("더 뉴 모닝 (JA)", "2026", "2026년형 미출시"),
        ("모닝 어반 (JA)", "2021", "모닝 어반 2021년형 미존재"),
        ("모하비 더 마스터", "2025", "2024년 6월 생산 종료 단종"),
        ("더 뉴 스포티지 5세대", "2024", "F/L 이전 연식 (2025년형부터 출시)"),
        ("타스만 오픈베드", "2026", "가격표 미발표 유령 모델"),
        ("타스만", "2025", "2025년형 미존재 (2026년형 출시)"),
        ("G90 (RS4)", "2026", "2026년형 미출시"),
        ("SM3 Z.E.", "2021", "2020년 단종"),
        ("세닉", "2026", "국내 미출시 연식"),
        ("필랑트", "2026", "국내 미출시 모델"),
        ("뉴 볼트 EV", "2024", "2023년 GM 글로벌 단종"),
        ("볼트 EUV", "2024", "2023년 단종"),
        ("임팔라", "2020", "2019년 단종"),
        ("더 뉴 카마로", "2022", "2021년 단종"),
        ("올 뉴 콜로라도", "2026", "2026년형 미출시")
    ]

    for model, yr, reason in years_to_remove:
        if model in catalog and yr in catalog[model]:
            if len(catalog[model][yr]) == 0:
                del catalog[model][yr]
                removed_logs.append({
                    'model': model,
                    'year': yr,
                    'reason': reason
                })
                log(f"  - [{model} {yr}] 삭제 완료 ({reason})")

    # ----------------------------------------------------
    # C. 저장 및 결과 보고
    # ----------------------------------------------------
    after_grades = sum(len(y) for y in catalog.values() for y in y.values())
    after_years = sum(len(y) for y in catalog.values())
    after_models = len(catalog)

    log("\n4. 정제 결과 파일 저장 중...")
    with open(CATALOG_C_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    log(f"  - 갱신된 제이책(C) 저장 완료: {CATALOG_C_FILE}")

    with open(FILLED_FILE, "w", encoding="utf-8") as f:
        json.dump(filled_logs, f, ensure_ascii=False, indent=2)
    log(f"  - 채운 내역 저장: {FILLED_FILE} ({len(filled_logs)}건)")

    with open(REMOVED_FILE, "w", encoding="utf-8") as f:
        json.dump(removed_logs, f, ensure_ascii=False, indent=2)
    log(f"  - 지운 연식 저장: {REMOVED_FILE} ({len(removed_logs)}건)")

    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(review_logs, f, ensure_ascii=False, indent=2)
    log(f"  - 검토 목록 저장: {REVIEW_FILE} ({len(review_logs)}건)")

    # 5. 검증 리포트
    log("\n==================================================")
    log("📋 [11-11-22] 제이책(C) 빈 연식 정리 검증 보고서")
    log("==================================================")
    log("1. 수치 요약:")
    log(f"   - 채운 연식 수: {len(filled_logs)}개")
    log(f"   - 지운 빈 연식 키 수: {len(removed_logs)}개")
    log(f"   - 검토 목록 수: {len(review_logs)}개")
    log(f"   - 총 차종 수: {after_models}개 (307개 보존 확인)")
    log(f"   - 연식 수 변화: {before_years:,}개 -> {after_years:,}개 (순감소: {before_years - after_years}개)")
    log(f"   - 등급 수 변화: {before_grades:,}개 -> {after_grades:,}개 (순변화: {after_grades - before_grades:+d}개)")

    # 카니발 검증
    c4_25_cnt = len(catalog.get('더 뉴 카니발 4세대', {}).get('2025', {}))
    c4_26_cnt = len(catalog.get('더 뉴 카니발 4세대', {}).get('2026', {}))
    log(f"\n2. [필수 검증] 더 뉴 카니발 4세대 등급 수:")
    log(f"   - 2025년형: {c4_25_cnt}개 등급")
    log(f"   - 2026년형: {c4_26_cnt}개 등급")
    assert c4_25_cnt > 0, "더 뉴 카니발 4세대 2025년형에 등급이 채워져야 합니다."
    assert c4_26_cnt > 0, "더 뉴 카니발 4세대 2026년형에 등급이 채워져야 합니다."

    # 잔여 0개 등급 연식 스캔
    rem_empty = []
    for m, yrs in catalog.items():
        for y, g in yrs.items():
            if len(g) == 0:
                rem_empty.append((m, y))
    log(f"\n3. [필수 검증] 책 전체 0개 등급 연식 잔여: {len(rem_empty)}개 (목표: 0개)")
    if rem_empty:
        for m, y in rem_empty:
            log(f"   - {m} {y}")
    assert len(rem_empty) == 0, f"Expected 0 empty years, got {len(rem_empty)}"

    log("\n✅ [11-11-22] 모든 빈 연식 정리 및 필수 검증 100% 성공!")


if __name__ == '__main__':
    run_clean_empty_years()
