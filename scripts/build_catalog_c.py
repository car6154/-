# scripts/build_catalog_c.py
"""
[11-11-13] 제이책(C) 제작 — 엔카 v2 기반에 다나와 결손 병합
1. 다나와 중복 등급 정리: (차종, 연식, 정규화등급명, 기본가) 동일 그룹 병합 및 옵션 합집합
2. 차종 매칭: encar-gap-audit-2026-11-11.json의 alias_table 적용 (미매칭 차종은 미확정 보류)
3. 병합: 엔카 v2를 뼈대로 하고 다나와 결손(누락 등급, 누락 연식, 누락 옵션) 보강
4. 충돌 감지: 엔카/다나와 가격 차이(기본가 3% 이상, 옵션가 5만원 이상) 충돌 로그 기록
5. 출력 구조: 모델 -> 연식 -> 등급 -> {base_price, source, options: {옵션명: {price, source, ...}}}
6. 산출물: data/catalog_c.json, data/catalog_c_conflicts_2026-11-12.json
"""

import os
import sys
import re
import json
from datetime import datetime

# 콘솔 UTF-8 출력 보장
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

ENCAR_V2_FILE = os.path.join(DATA_DIR, "encar_newcar_catalog_v2.json")
DANAWA_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2.json")
AUDIT_FILE = os.path.join(DATA_DIR, "encar-gap-audit-2026-11-11.json")

OUTPUT_CATALOG_C = os.path.join(DATA_DIR, "catalog_c.json")
OUTPUT_CONFLICTS = os.path.join(DATA_DIR, "catalog_c_conflicts_2026-11-12.json")
OUTPUT_DEDUP_LOG = os.path.join(DATA_DIR, "danawa_dedup_log_2026-11-12.json")


def log(msg: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


def norm_name(s: str) -> str:
    if not s:
        return ""
    # 괄호 세대 코드, 더 뉴, 올 뉴, 공백 및 특수문자 제거 후 소문자화
    t = re.sub(r'\(.*?\)', '', s)
    t = re.sub(r'[\s\-_/·・\.]+', '', t)
    return t.lower().strip()


def norm_grade(g: str) -> str:
    if not g:
        return ""
    t = re.sub(r'[\s\-_/·・\.]+', '', g)
    return t.lower().strip()


def extract_opt_price_and_desc(opt_val):
    if isinstance(opt_val, dict):
        return opt_val.get('price'), opt_val.get('desc')
    elif isinstance(opt_val, (int, float)):
        return int(opt_val), None
    return None, None


def deduplicate_danawa(danawa_raw: dict) -> tuple:
    """
    다나와 데이터에서 (차종, 연식, norm_grade, base_price)가 같은 등급을 1개로 병합
    옵션은 합집합으로 결합
    반환값: (정리된 danawa dict, 중복 제거 로그 리스트)
    """
    cleaned_danawa = {}
    dedup_logs = []
    total_raw_grades = 0
    total_cleaned_grades = 0

    for model, yrs in danawa_raw.items():
        if not isinstance(yrs, dict):
            continue
        cleaned_danawa[model] = {}
        for yr, grades in yrs.items():
            if not isinstance(grades, dict):
                continue
            cleaned_danawa[model][yr] = {}

            # 그룹핑 키: (norm_grade, base_price)
            grouped = {}
            for gname, gdata in grades.items():
                if gname.startswith('_') or not isinstance(gdata, dict):
                    continue
                total_raw_grades += 1
                ng = norm_grade(gname)
                bp = gdata.get('기본가') if '기본가' in gdata else gdata.get('base_price')
                key = (ng, bp)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append((gname, gdata))

            for (ng, bp), items in grouped.items():
                if len(items) == 1:
                    orig_name, orig_data = items[0]
                    raw_opts = orig_data.get('옵션') or orig_data.get('options') or {}
                    normed_opts = {}
                    for oname, oval in raw_opts.items():
                        oprc, odesc = extract_opt_price_and_desc(oval)
                        normed_opts[oname] = {'price': oprc, 'desc': odesc}
                    cleaned_danawa[model][yr][orig_name] = {
                        'base_price': bp,
                        'options': normed_opts,
                        'source': 'danawa'
                    }
                else:
                    items.sort(key=lambda x: (len(x[0]), x[0]), reverse=True)
                    rep_name, _ = items[0]

                    merged_options = {}
                    merged_names = [it[0] for it in items]
                    for _, it_data in items:
                        raw_opts = it_data.get('옵션') or it_data.get('options') or {}
                        for oname, oval in raw_opts.items():
                            oprc, odesc = extract_opt_price_and_desc(oval)
                            if oname not in merged_options:
                                merged_options[oname] = {'price': oprc, 'desc': odesc}
                            elif merged_options[oname]['price'] is None and oprc is not None:
                                merged_options[oname] = {'price': oprc, 'desc': odesc or merged_options[oname]['desc']}

                    cleaned_danawa[model][yr][rep_name] = {
                        'base_price': bp,
                        'options': merged_options,
                        'source': 'danawa'
                    }

                    dedup_logs.append({
                        'model': model,
                        'year': yr,
                        'norm_grade': ng,
                        'base_price': bp,
                        'merged_names': merged_names,
                        'chosen_name': rep_name,
                        'options_count': len(merged_options)
                    })

            total_cleaned_grades += len(cleaned_danawa[model][yr])

    return cleaned_danawa, dedup_logs, total_raw_grades, total_cleaned_grades


def build_catalog_c():
    log("==================================================")
    log("🚀 [11-11-13] 제이책(C) 제작 시작")
    log("==================================================")

    # 1. 원본 데이터 로드
    log("1. 원본 데이터 로드 중...")
    with open(ENCAR_V2_FILE, "r", encoding="utf-8") as f:
        encar_v2 = json.load(f)
    with open(DANAWA_FILE, "r", encoding="utf-8") as f:
        danawa_raw_all = json.load(f)
    danawa_raw = danawa_raw_all.get('danawa', {})
    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        audit_data = json.load(f)

    alias_table = audit_data.get('alias_table', {})
    unmatched_models = audit_data.get('unmatched_models', {})

    log(f"  - 엔카 v2: {len(encar_v2)}개 차종")
    log(f"  - 다나와 원본: {len(danawa_raw)}개 차종")
    log(f"  - 별칭표(alias_table): {len(alias_table)}개 매핑")

    # 2. 다나와 중복 등급 정리 (1번 요구사항)
    log("\n2. 다나와 중복 등급 정리 중...")
    cleaned_danawa, dedup_logs, raw_grades_cnt, clean_grades_cnt = deduplicate_danawa(danawa_raw)
    log(f"  - 다나와 원본 등급 수: {raw_grades_cnt}개 -> 중복 정리 후: {clean_grades_cnt}개 (감소: {raw_grades_cnt - clean_grades_cnt}개)")
    log(f"  - 병합된 중복 등급 그룹 수: {len(dedup_logs)}개")

    with open(OUTPUT_DEDUP_LOG, "w", encoding="utf-8") as f:
        json.dump(dedup_logs, f, ensure_ascii=False, indent=2)
    log(f"  - 중복 정리 로그 저장: {OUTPUT_DEDUP_LOG}")

    # 3. 차종 매칭 맵 구축 (danawa_model -> encar_model)
    # 별칭표(alias_table)에서 단방향 및 양방향 매핑 확인
    danawa_to_encar = {}
    for alias_key, info in alias_table.items():
        em = info.get('encar_model')
        dm = info.get('danawa_model')
        if dm and em and em in encar_v2:
            danawa_to_encar[dm] = em

    log(f"\n3. 차종 매칭 맵 구축: {len(danawa_to_encar)}개 다나와 모델이 엔카 v2 모델에 매핑됨")

    # 4. 제이책(C) 병합 및 가격 충돌 기록
    log("\n4. 엔카 v2 뼈대 기반 다나와 결손 병합 중...")
    catalog_c = {}
    conflicts = []

    # 통계용 카운터
    stats = {
        'total_models': 0,
        'total_years': 0,
        'total_grades': 0,
        'encar_grades': 0,
        'danawa_grades': 0,
        'total_options': 0,
        'encar_options': 0,
        'danawa_options': 0,
        'conflicts_count': 0
    }

    # Step A: 엔카 v2 전수 적재 (뼈대)
    for emodel, yrs in encar_v2.items():
        catalog_c[emodel] = {}
        for yr, ydata in yrs.items():
            catalog_c[emodel][yr] = {}
            grades_list = ydata.get('grades', [])
            pkgs = ydata.get('packages', {})

            for g in grades_list:
                gname = g['name']
                bp = g.get('base_price')
                mission = g.get('mission', '')
                raw_opts = g.get('options', {})

                c_opts = {}
                for oname, oinfo in raw_opts.items():
                    c_opts[oname] = {
                        'price': oinfo.get('price'),
                        'kind': oinfo.get('kind', 'optional'),
                        'desc': oinfo.get('desc'),
                        'source': 'encar'
                    }
                    stats['total_options'] += 1
                    stats['encar_options'] += 1

                catalog_c[emodel][yr][gname] = {
                    'base_price': bp,
                    'mission': mission,
                    'source': 'encar',
                    'options': c_opts
                }
                stats['total_grades'] += 1
                stats['encar_grades'] += 1

    # Step B: 다나와 결손 병합 (매핑된 차종만 처리, 미매칭은 미확정 보류)
    unmatched_danawa_models = []

    for dmodel, dyrs in cleaned_danawa.items():
        if dmodel not in danawa_to_encar:
            unmatched_danawa_models.append(dmodel)
            continue

        target_emodel = danawa_to_encar[dmodel]

        for yr, dgrades in dyrs.items():
            # 케이스 1: 엔카 v2에 해당 연식 자체가 없는 경우 -> 다나와 연식 전체 추가
            if yr not in catalog_c[target_emodel]:
                catalog_c[target_emodel][yr] = {}
                for dgname, dgdata in dgrades.items():
                    d_opts = {}
                    for doname, doval in dgdata.get('options', {}).items():
                        doprice = doval.get('price')
                        dodesc = doval.get('desc')
                        d_opts[doname] = {
                            'price': doprice,
                            'kind': 'optional' if doprice is not None else 'package_ref',
                            'desc': dodesc,
                            'source': 'danawa'
                        }
                        stats['total_options'] += 1
                        stats['danawa_options'] += 1

                    catalog_c[target_emodel][yr][dgname] = {
                        'base_price': dgdata.get('base_price'),
                        'mission': '',
                        'source': 'danawa',
                        'options': d_opts
                    }
                    stats['total_grades'] += 1
                    stats['danawa_grades'] += 1
                continue

            # 케이스 2: 엔카 v2에 해당 연식이 있는 경우 -> 등급 단위 대조 및 병합
            encar_grades_in_yr = catalog_c[target_emodel][yr]

            # 엔카 등급들의 정규화 인덱스 구축
            encar_norm_map = {}
            for egname, egdata in encar_grades_in_yr.items():
                encar_norm_map[norm_grade(egname)] = (egname, egdata)

            for dgname, dgdata in dgrades.items():
                d_ng = norm_grade(dgname)
                d_bp = dgdata.get('base_price')

                if d_ng in encar_norm_map:
                    # 등급이 둘 다 존재하는 경우 -> 기본가는 엔카 우선, 충돌 여부 검사
                    egname, egdata = encar_norm_map[d_ng]
                    e_bp = egdata.get('base_price')

                    # 4. 가격 충돌 검사 (기본가 차이 3% 이상)
                    if e_bp and d_bp:
                        diff_pct = abs(e_bp - d_bp) / max(e_bp, d_bp) * 100
                        if diff_pct >= 3.0:
                            conflicts.append({
                                'type': 'base_price',
                                'model': target_emodel,
                                'danawa_model': dmodel,
                                'year': yr,
                                'grade': egname,
                                'danawa_grade': dgname,
                                'encar_price': e_bp,
                                'danawa_price': d_bp,
                                'diff_percent': round(diff_pct, 2)
                            })
                            stats['conflicts_count'] += 1

                    # 옵션 대조 및 다나와 전용 옵션 보강
                    e_opts = egdata.get('options', {})
                    e_opt_norm = {norm_name(k): (k, v) for k, v in e_opts.items()}

                    for doname, doval in dgdata.get('options', {}).items():
                        doprice = doval.get('price')
                        dodesc = doval.get('desc')
                        d_onorm = norm_name(doname)
                        if d_onorm in e_opt_norm:
                            orig_oname, orig_oinfo = e_opt_norm[d_onorm]
                            e_oprc = orig_oinfo.get('price')
                            # 옵션가 차이 5만원 이상 검사
                            if e_oprc is not None and doprice is not None:
                                diff_won = abs(e_oprc - doprice)
                                if diff_won >= 50000:
                                    conflicts.append({
                                        'type': 'option_price',
                                        'model': target_emodel,
                                        'danawa_model': dmodel,
                                        'year': yr,
                                        'grade': egname,
                                        'option': orig_oname,
                                        'danawa_option': doname,
                                        'encar_price': e_oprc,
                                        'danawa_price': doprice,
                                        'diff_won': diff_won
                                    })
                                    stats['conflicts_count'] += 1
                        else:
                            # 엔카에 없는 다나와 옵션 보강
                            e_opts[doname] = {
                                'price': doprice,
                                'kind': 'optional' if doprice is not None else 'package_ref',
                                'desc': dodesc,
                                'source': 'danawa'
                            }
                            stats['total_options'] += 1
                            stats['danawa_options'] += 1
                else:
                    # 엔카 v2에 없는 다나와 전용 등급 추가
                    d_opts = {}
                    for doname, doval in dgdata.get('options', {}).items():
                        doprice = doval.get('price')
                        dodesc = doval.get('desc')
                        d_opts[doname] = {
                            'price': doprice,
                            'kind': 'optional' if doprice is not None else 'package_ref',
                            'desc': dodesc,
                            'source': 'danawa'
                        }
                        stats['total_options'] += 1
                        stats['danawa_options'] += 1

                    catalog_c[target_emodel][yr][dgname] = {
                        'base_price': d_bp,
                        'mission': '',
                        'source': 'danawa',
                        'options': d_opts
                    }
                    stats['total_grades'] += 1
                    stats['danawa_grades'] += 1

    stats['total_models'] = len(catalog_c)
    stats['total_years'] = sum(len(yrs) for yrs in catalog_c.values())

    # 5. 파일 저장
    log("\n5. 제이책(C) 및 충돌 로그 저장 중...")
    with open(OUTPUT_CATALOG_C, "w", encoding="utf-8") as f:
        json.dump(catalog_c, f, ensure_ascii=False, indent=2)
    log(f"  - 제이책(C) 저장 완료: {OUTPUT_CATALOG_C} ({os.path.getsize(OUTPUT_CATALOG_C)/(1024*1024):.2f} MB)")

    with open(OUTPUT_CONFLICTS, "w", encoding="utf-8") as f:
        json.dump(conflicts, f, ensure_ascii=False, indent=2)
    log(f"  - 충돌 로그 저장 완료: {OUTPUT_CONFLICTS} ({len(conflicts)}건)")

    # 6. 검증 및 결과 리포트
    log("\n==================================================")
    log("📋 [11-11-13] 제이책(C) 제작 검증 보고서")
    log("==================================================")
    log(f"1. 전체 규모:")
    log(f"   - 총 모델 수: {stats['total_models']}개")
    log(f"   - 총 연식 수: {stats['total_years']}개")
    log(f"   - 총 등급 수: {stats['total_grades']}개")
    log(f"     * 엔카 v2 출처: {stats['encar_grades']}개 ({stats['encar_grades']/stats['total_grades']*100:.1f}%)")
    log(f"     * 다나와 결손 보강: {stats['danawa_grades']}개 ({stats['danawa_grades']/stats['total_grades']*100:.1f}%)")
    log(f"   - 총 옵션 수: {stats['total_options']}개")
    log(f"     * 엔카 v2 출처: {stats['encar_options']}개 ({stats['encar_options']/stats['total_options']*100:.1f}%)")
    log(f"     * 다나와 결손 보강: {stats['danawa_options']}개 ({stats['danawa_options']/stats['total_options']*100:.1f}%)")
    log(f"   - 가격 충돌 로그 건수: {len(conflicts)}건")

    # 제이 필수 검증 차종 확인
    log("\n2. 필수 검증 차종 실측 대조:")
    # XM3 2021 RE / RE 시그니처
    xm3_grades = catalog_c.get('XM3', {}).get('2021', {})
    for gname, gdata in xm3_grades.items():
        if 'RE' in gname:
            prc = gdata.get('base_price')
            log(f"   - XM3 2021 [{gname}]: {prc:,}원 (출처: {gdata.get('source')})")

    # 더 뉴 QM6 2024 RE
    qm6_grades = catalog_c.get('더 뉴 QM6', {}).get('2024', {})
    for gname, gdata in qm6_grades.items():
        if 'RE' in gname:
            prc = gdata.get('base_price')
            log(f"   - 더 뉴 QM6 2024 [{gname}]: {prc:,}원 (출처: {gdata.get('source')})")

    # 쏘렌토 4세대 2022 시그니처
    sorento_grades = catalog_c.get('쏘렌토 4세대', {}).get('2022', {})
    for gname, gdata in sorento_grades.items():
        if '시그니처' in gname:
            prc = gdata.get('base_price')
            log(f"   - 쏘렌토 4세대 2022 [{gname}]: {prc:,}원 (출처: {gdata.get('source')})")

    log("\n3. 충돌 로그 샘플 10개:")
    for c in conflicts[:10]:
        if c['type'] == 'base_price':
            log(f"   [기본가] {c['model']} {c['year']} [{c['grade']}] -> 엔카: {c['encar_price']:,}원 vs 다나와: {c['danawa_price']:,}원 (차이: {c['diff_percent']}%)")
        else:
            log(f"   [옵션가] {c['model']} {c['year']} [{c['grade']}] - 옵션 '{c['option']}' -> 엔카: {c['encar_price']:,}원 vs 다나와: {c['danawa_price']:,}원 (차이: {c['diff_won']:,}원)")


if __name__ == '__main__':
    build_catalog_c()
