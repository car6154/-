# scripts/merge_options_in_catalog_c.py
"""
[11-11-16] 제이책(C) 등급 안 옵션 중복 병합 스크립트
- 같은 등급 내에서 정규화된 옵션명이 같고 가격이 같으면 엔카 기준 단일화
- 가격이 다르면 합치지 않고 충돌 로그에 기록
- 백업: data/catalog_c_v2_backup_2026-11-12.json
- 산출: data/catalog_c.json
- 로그: data/catalog_c_option_merge_log_2026-11-12.json
- 충돌: data/catalog_c_option_price_conflicts_2026-11-12.json
"""

import os
import sys
import re
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
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_c_v2_backup_2026-11-12.json")
MERGE_LOG_FILE = os.path.join(DATA_DIR, "catalog_c_option_merge_log_2026-11-12.json")
CONFLICT_FILE = os.path.join(DATA_DIR, "catalog_c_option_price_conflicts_2026-11-12.json")


def log(msg: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


def norm_opt_name(name: str) -> str:
    """
    옵션명 정규화 규칙:
    1. 로마 숫자 유니코드 및 영문 표기 통일 (Ⅰ, Ⅱ, Ⅲ -> 1, 2, 3)
    2. 인치 표기 통일 ('"' / '인치' / 'inch' -> 인치)
    3. 외장컬러/외장색상 접미사 제거
    4. 공백, 특수문자, 대소문자 제거
    """
    s = str(name or "").strip()

    # 1. 로마 숫자 유니코드 변환
    roman_dict = {
        'Ⅰ': '1', 'Ⅱ': '2', 'Ⅲ': '3', 'Ⅳ': '4', 'Ⅴ': '5', 'Ⅵ': '6',
        'ⅰ': '1', 'ⅱ': '2', 'ⅲ': '3', 'ⅳ': '4', 'ⅴ': '5', 'ⅵ': '6',
    }
    for r, a in roman_dict.items():
        s = s.replace(r, a)

    s = s.lower()

    # 영문 로마자 (끝이나 공백 뒤, 패키지 뒤에 오는 I, II, III, IV, V)
    s = re.sub(r'\biii\b|(?<=\s)iii(?=$|\s)|(?<=패키지)iii', '3', s)
    s = re.sub(r'\bii\b|(?<=\s)ii(?=$|\s)|(?<=패키지)ii', '2', s)
    s = re.sub(r'\biv\b|(?<=\s)iv(?=$|\s)|(?<=패키지)iv', '4', s)
    s = re.sub(r'\bi\b|(?<=\s)i(?=$|\s)|(?<=패키지)i', '1', s)

    # 2. 인치 표기 통일
    s = re.sub(r'(\d+)\s*(?:\"|\'|인치|inch)', r'\1인치', s)

    # 3. 외장컬러 유무 통일 (제거)
    s = re.sub(r'외장\s*(?:컬러|색상)', '', s)

    # 4. 공백, 특수문자 제거
    s = re.sub(r'[\s\-_/·・\.\(\)\&+,]+', '', s)
    return s


def run_option_merge():
    log("==================================================")
    log("🚀 [11-11-16] 제이책(C) 등급 안 옵션 중복 병합 시작")
    log("==================================================")

    # 1. 백업 생성
    if not os.path.exists(BACKUP_FILE):
        log(f"1. 백업 생성 중 -> {BACKUP_FILE}")
        shutil.copyfile(CATALOG_C_FILE, BACKUP_FILE)
    else:
        log(f"1. 백업 파일 확인됨: {BACKUP_FILE}")

    with open(CATALOG_C_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    before_options = sum(len(gdata.get('options', {})) for yrs in catalog.values() for grades in yrs.values() for gdata in grades.values())
    log(f"  - 병합 전 총 옵션 수: {before_options:,}개")

    merged_catalog = {}
    merge_logs = []
    price_conflicts = []

    merged_groups_count = 0

    for model, yrs in catalog.items():
        merged_catalog[model] = {}
        for yr, grades in yrs.items():
            merged_catalog[model][yr] = {}
            for gname, gdata in grades.items():
                opts = gdata.get('options', {})

                # 정규화명 기준 그룹핑
                groups = {}
                for oname, oinfo in opts.items():
                    norm = norm_opt_name(oname)
                    if norm not in groups:
                        groups[norm] = []
                    groups[norm].append((oname, oinfo))

                new_options = {}

                for norm, items in groups.items():
                    if len(items) == 1:
                        oname, oinfo = items[0]
                        new_options[oname] = oinfo
                    else:
                        # 중복 후보! 가격 동일 여부 체크
                        prices = set(it[1].get('price') for it in items)

                        if len(prices) == 1:
                            # 🎯 가격 동일 -> 병합 수행!
                            merged_groups_count += 1

                            # 엔카 항목 우선 정렬 (source=='encar' 우선)
                            items.sort(key=lambda x: (
                                1 if x[1].get('source') == 'encar' else 0,
                                -len(x[0])
                            ), reverse=True)

                            rep_oname, rep_oinfo = items[0]

                            # 설명(desc)은 가장 긴 것 선택
                            all_descs = [it[1].get('desc') or '' for it in items]
                            longest_desc = max(all_descs, key=len) or None

                            # 출처는 엔카 포함 시 무조건 'encar'
                            has_encar = any(it[1].get('source') == 'encar' for it in items)
                            final_source = 'encar' if has_encar else rep_oinfo.get('source', 'danawa')

                            merged_opt_entry = {
                                'price': rep_oinfo.get('price'),
                                'kind': rep_oinfo.get('kind', 'optional'),
                                'desc': longest_desc,
                                'source': final_source
                            }

                            new_options[rep_oname] = merged_opt_entry

                            merge_logs.append({
                                'model': model,
                                'year': yr,
                                'grade': gname,
                                'chosen_name': rep_oname,
                                'price': rep_oinfo.get('price'),
                                'merged_names': [it[0] for it in items],
                                'sources': [it[1].get('source') for it in items],
                                'has_desc': bool(longest_desc)
                            })
                        else:
                            # ⚠️ 가격 상이 -> 합치지 않고 개별 유지 + 충돌 로그 기록
                            price_conflicts.append({
                                'model': model,
                                'year': yr,
                                'grade': gname,
                                'norm_name': norm,
                                'items': [
                                    {
                                        'name': it[0],
                                        'price': it[1].get('price'),
                                        'source': it[1].get('source'),
                                        'kind': it[1].get('kind'),
                                        'desc': it[1].get('desc')
                                    } for it in items
                                ]
                            })
                            # 각각 원래 옵션으로 유지
                            for it_name, it_info in items:
                                new_options[it_name] = it_info

                merged_catalog[model][yr][gname] = {
                    'base_price': gdata.get('base_price'),
                    'mission': gdata.get('mission', ''),
                    'source': gdata.get('source', 'encar'),
                    'options': new_options
                }

    after_options = sum(len(gdata.get('options', {})) for yrs in merged_catalog.values() for grades in yrs.values() for gdata in grades.values())

    # 파일 저장
    log("\n2. 병합 결과 저장 중...")
    with open(CATALOG_C_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_catalog, f, ensure_ascii=False, indent=2)
    log(f"  - 갱신된 제이책(C) 저장 완료: {CATALOG_C_FILE} ({os.path.getsize(CATALOG_C_FILE)/(1024*1024):.2f} MB)")

    with open(MERGE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(merge_logs, f, ensure_ascii=False, indent=2)
    log(f"  - 옵션 중복 병합 로그 저장: {MERGE_LOG_FILE} ({len(merge_logs)}개 그룹)")

    with open(CONFLICT_FILE, "w", encoding="utf-8") as f:
        json.dump(price_conflicts, f, ensure_ascii=False, indent=2)
    log(f"  - 옵션 가격 상이 충돌 로그 저장: {CONFLICT_FILE} ({len(price_conflicts)}건)")

    # 검증 리포트
    log("\n==================================================")
    log("📋 [11-11-16] 제이책(C) 등급 안 옵션 중복 병합 검증 보고서")
    log("==================================================")
    log("1. 수치 요약:")
    log(f"   - 합친 옵션 중복 그룹 수: {merged_groups_count:,}개")
    log(f"   - 옵션 수 변화: {before_options:,}개 -> {after_options:,}개 (순감소: {before_options - after_options:,}개 옵션)")
    log(f"   - 가격 상이 충돌 건수: {len(price_conflicts)}건 (합치지 않고 독립 보존)")

    # 필수 검증 케이스: XM3 2021 RE
    log("\n2. XM3 2021 RE 옵션 상세 검증:")
    xm3_re_opts = merged_catalog.get('XM3', {}).get('2021', {}).get('1.3 TCe RE', {}).get('options', {})
    log(f"   - XM3 2021 RE 최종 옵션 수: {len(xm3_re_opts)}개 (11개에서 7개로 감소 여부)")
    for oname, oinfo in xm3_re_opts.items():
        prc = oinfo.get('price')
        prc_str = f"{prc:,}원" if prc is not None else "-"
        src = oinfo.get('source')
        log(f"     * [{src}] {oname}: {prc_str}")


if __name__ == '__main__':
    run_option_merge()
