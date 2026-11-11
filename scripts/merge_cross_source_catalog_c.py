# scripts/merge_cross_source_catalog_c.py
"""
[11-11-14] 제이책(C) 출처 간 중복 병합
- 같은 (차종, 연식)에서 기본가가 같고 등급 핵심(인승, 유종, 구동, 배기량, 트림)이 동일한 등급들을 하나로 병합
- 인승(5인승/6인승/7인승 등)은 등급을 가르는 필수 속성이므로 절대 합치지 않고 보존
- 대표 등급명: 엔카 v2 우선, 기본가: 엔카 v2 가격
- 옵션: 합집합 (동일 옵션 시 엔카 우선, 다나와 옵션은 source: danawa 보존)
- 기본가가 다른 등급은 합치지 않고 충돌 로그로 분리 기록
- 산출물:
  - 갱신: data/catalog_c.json
  - 중복 병합 로그: data/catalog_c_cross_source_merge_log_2026-11-12.json
  - 가격 충돌 로그: data/catalog_c_price_conflicts_v2_2026-11-12.json
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
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_c_v1_backup_2026-11-12.json")
MERGE_LOG_FILE = os.path.join(DATA_DIR, "catalog_c_cross_source_merge_log_2026-11-12.json")
PRICE_CONFLICT_FILE = os.path.join(DATA_DIR, "catalog_c_price_conflicts_v2_2026-11-12.json")


def log(msg: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


def extract_grade_features(gname: str) -> dict:
    g_raw = gname.lower()

    # 1. 인승 추출 (5인승, 6인승, 7인승, 8인승, 9인승, 11인승 등 엄격 보존)
    m_seat = re.search(r'([0-9]+)\s*인승', g_raw)
    seating = f"{m_seat.group(1)}인승" if m_seat else None

    # 2. 구동방식 추출 (4wd vs 2wd)
    if any(k in g_raw for k in ['4wd', 'awd', '4륜']):
        drive = '4wd'
    else:
        # 엔카는 국산 2WD 표기를 생략하는 경우가 많으므로 기본 2WD로 통일
        drive = '2wd'

    # 3. 유종 추출
    fuel = 'gasoline'  # 기본 가솔린
    if any(k in g_raw for k in ['하이브리드', 'hev', 'hybrid']):
        fuel = 'hybrid'
    elif any(k in g_raw for k in ['lpg', 'lpe', 'lpi']):
        fuel = 'lpg'
    elif any(k in g_raw for k in ['디젤', 'diesel', 'crd', 'vgt', '2.2d', '2.0d']):
        fuel = 'diesel'
    elif any(k in g_raw for k in ['전기', 'ev', 'electric']):
        fuel = 'ev'
    elif any(k in g_raw for k in ['가솔린', 'gdi', 'tce', 'gde', 'gte', 't-gdi', 'turbo', '터보', 'mpi']):
        fuel = 'gasoline'

    # 4. 배기량 추출 (예: 1.0, 1.3, 1.5, 1.6, 2.0, 2.2, 2.5, 3.0, 3.3, 3.5, 3.8 등)
    m_disp = re.search(r'\b([1-9]\.[0-9])\b', g_raw)
    displacement = m_disp.group(1) if m_disp else None

    # 5. 핵심 트림명 추출
    t = re.sub(r'\b(tce|gde|gte|lpe|lpi|gdi|hev|ev|2wd|4wd|awd|fwd|rwd|mpi)\b', '', g_raw)
    t = re.sub(r'([0-9]+)\s*인승', '', t)
    t = re.sub(r'\b([1-9]\.[0-9])\b', '', t)
    t = re.sub(r'(가솔린|디젤|하이브리드|전기|lpg|퀘스트)', '', t)
    t = re.sub(r'[\s\-_/·・\.\(\)]+', '', t)
    t = t.replace('signature', '시그니처').replace('plus', '플러스').replace('비지니스', '비즈니스')

    return {
        'seating': seating,
        'fuel': fuel,
        'drive': drive,
        'displacement': displacement,
        'trim': t
    }


def norm_opt_name(s: str) -> str:
    if not s:
        return ""
    t = re.sub(r'\(.*?\)', '', s)
    t = re.sub(r'[\s\-_/·・\.]+', '', t)
    return t.lower().strip()


def run_cross_source_merge():
    log("==================================================")
    log("🚀 [11-11-14] 제이책(C) 출처 간 중복 병합 시작")
    log("==================================================")

    # 1. 1차본 백업 확인 및 로드
    if not os.path.exists(BACKUP_FILE):
        log(f"1. 1차본 백업 생성 중 -> {BACKUP_FILE}")
        shutil.copyfile(CATALOG_C_FILE, BACKUP_FILE)
    else:
        log(f"1. 1차본 백업 확인됨: {BACKUP_FILE}")

    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
        catalog_raw = json.load(f)

    before_grades = sum(len(grades) for yrs in catalog_raw.values() for grades in yrs.values())
    before_options = sum(len(gdata.get('options', {})) for yrs in catalog_raw.values() for grades in yrs.values() for gdata in grades.values())
    log(f"  - 병합 전: 모델 {len(catalog_raw)}개, 연식 {sum(len(y) for y in catalog_raw.values())}개, 등급 {before_grades}개, 옵션 {before_options}개")

    merged_catalog = {}
    merge_logs = []
    price_conflicts = []

    total_merged_groups = 0

    for model, yrs in catalog_raw.items():
        merged_catalog[model] = {}
        for yr, grades in yrs.items():
            merged_catalog[model][yr] = {}

            # 그룹핑: (base_price, seating, fuel, drive, displacement, trim)
            groups = {}
            # 가격 충돌 추적용: (trim, seating, fuel) -> [(gname, base_price, source)]
            trim_prices = {}

            for gname, gdata in grades.items():
                bp = gdata.get('base_price')
                feat = extract_grade_features(gname)

                # 가격 충돌 추적용 키
                conflict_key = (feat['trim'], feat['seating'], feat['fuel'], feat['displacement'])
                if conflict_key not in trim_prices:
                    trim_prices[conflict_key] = []
                trim_prices[conflict_key].append((gname, bp, gdata.get('source')))

                # 기본가가 없는 경우는 병합하지 않고 단독 유지
                if bp is None:
                    key = ('NONE_PRICE', gname)
                else:
                    key = (
                        bp,
                        feat['seating'],
                        feat['fuel'],
                        feat['drive'],
                        feat['displacement'],
                        feat['trim']
                    )

                if key not in groups:
                    groups[key] = []
                groups[key].append((gname, gdata, feat))

            # 그룹별 병합 수행
            for key, items in groups.items():
                if len(items) == 1:
                    orig_name, orig_data, _ = items[0]
                    merged_catalog[model][yr][orig_name] = orig_data
                else:
                    # 출처 간 동일 등급 병합!
                    total_merged_groups += 1

                    # 대표 등급 선정: 엔카 출처 우선, 엔카 중에서도 이름이 간결한 것
                    items.sort(key=lambda x: (
                        1 if x[1].get('source') == 'encar' else 0,
                        -len(x[0])  # 동일 출처면 안정적 정렬
                    ), reverse=True)

                    rep_name, rep_data, _ = items[0]

                    # 옵션 합집합
                    merged_options = {}
                    # 먼저 엔카 옵션 우선 적재
                    for it_name, it_data, _ in items:
                        if it_data.get('source') == 'encar':
                            for oname, oinfo in it_data.get('options', {}).items():
                                if oname not in merged_options:
                                    merged_options[oname] = oinfo

                    # 다나와 옵션 보강 (엔카에 없는 옵션 추가)
                    encar_opt_norms = {norm_opt_name(k) for k in merged_options.keys()}
                    for it_name, it_data, _ in items:
                        if it_data.get('source') != 'encar':
                            for oname, oinfo in it_data.get('options', {}).items():
                                o_norm = norm_opt_name(oname)
                                if o_norm not in encar_opt_norms:
                                    merged_options[oname] = oinfo
                                    encar_opt_norms.add(o_norm)

                    # 병합 결과 등급 객체 생성
                    merged_grade_entry = {
                        'base_price': rep_data.get('base_price'),
                        'mission': rep_data.get('mission', ''),
                        'source': rep_data.get('source', 'encar'),
                        'options': merged_options
                    }
                    merged_catalog[model][yr][rep_name] = merged_grade_entry

                    merge_logs.append({
                        'model': model,
                        'year': yr,
                        'chosen_name': rep_name,
                        'base_price': rep_data.get('base_price'),
                        'merged_names': [it[0] for it in items],
                        'sources': [it[1].get('source') for it in items],
                        'final_options_count': len(merged_options)
                    })

            # 기본가가 다른데 이름(트림/엔진)이 같은 충돌 건 기록
            for c_key, p_list in trim_prices.items():
                trim_val, seat_val, fuel_val, disp_val = c_key
                # 서로 다른 기본가를 가진 항목 추출
                distinct_prices = set(p[1] for p in p_list if p[1] is not None)
                if len(distinct_prices) > 1 and len(trim_val) >= 2:
                    price_conflicts.append({
                        'model': model,
                        'year': yr,
                        'trim': trim_val,
                        'seating': seat_val,
                        'fuel': fuel_val,
                        'displacement': disp_val,
                        'grades': [{'name': p[0], 'base_price': p[1], 'source': p[2]} for p in p_list]
                    })

    after_grades = sum(len(grades) for yrs in merged_catalog.values() for grades in yrs.values())
    after_options = sum(len(gdata.get('options', {})) for yrs in merged_catalog.values() for grades in yrs.values() for gdata in grades.values())

    # 3. 파일 저장
    log("\n2. 병합 결과 저장 중...")
    with open(CATALOG_C_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_catalog, f, ensure_ascii=False, indent=2)
    log(f"  - 갱신된 제이책(C) 저장 완료: {CATALOG_C_FILE} ({os.path.getsize(CATALOG_C_FILE)/(1024*1024):.2f} MB)")

    with open(MERGE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(merge_logs, f, ensure_ascii=False, indent=2)
    log(f"  - 중복 병합 로그 저장: {MERGE_LOG_FILE} ({len(merge_logs)}개 그룹)")

    with open(PRICE_CONFLICT_FILE, "w", encoding="utf-8") as f:
        json.dump(price_conflicts, f, ensure_ascii=False, indent=2)
    log(f"  - 기본가 상이 충돌 로그 저장: {PRICE_CONFLICT_FILE} ({len(price_conflicts)}건)")

    # 4. 검증 리포트
    log("\n==================================================")
    log("📋 [11-11-14] 제이책(C) 출처 간 중복 병합 검증 보고서")
    log("==================================================")
    log("1. 수치 요약:")
    log(f"   - 합친 중복 그룹 수: {total_merged_groups}개")
    log(f"   - 등급 수 변화: {before_grades}개 -> {after_grades}개 (순감소: {before_grades - after_grades}개 등급)")
    log(f"   - 옵션 수 변화: {before_options}개 -> {after_options}개")
    log(f"   - 기본가 상이 충돌 건수: {len(price_conflicts)}건 (합치지 않고 독립 보존)")

    # 2. 필수 검증 케이스 1: XM3 2021 RE
    log("\n2. XM3 2021 등급 검증 (RE 단일화 확인):")
    xm3_grades = merged_catalog.get('XM3', {}).get('2021', {})
    for gname, gdata in xm3_grades.items():
        prc = gdata.get('base_price')
        log(f"   - [{gdata.get('source')}] '{gname}': {prc:,}원 (옵션 {len(gdata.get('options', {}))}개)")

    # 3. 필수 검증 케이스 2: 더 뉴 QM6 2024 RE
    log("\n3. 더 뉴 QM6 2024 등급 검증 (공식 가격 32,200,000원 대조):")
    qm6_grades = merged_catalog.get('더 뉴 QM6', {}).get('2024', {})
    for gname, gdata in qm6_grades.items():
        if 'RE' in gname:
            prc = gdata.get('base_price')
            log(f"   - [{gdata.get('source')}] '{gname}': {prc:,}원 (옵션 {len(gdata.get('options', {}))}개)")

    # 4. 필수 검증 케이스 3: 쏘렌토 4세대 2022 인승 보존 확인
    log("\n4. 쏘렌토 4세대 2022 인승 보존 확인 (5인승/6인승/7인승 분리 유지):")
    sorento_grades = merged_catalog.get('쏘렌토 4세대', {}).get('2022', {})
    seating_counts = {'5인승': 0, '6인승': 0, '7인승': 0, '미표기': 0}
    for gname, gdata in sorento_grades.items():
        if '5인승' in gname:
            seating_counts['5인승'] += 1
        elif '6인승' in gname:
            seating_counts['6인승'] += 1
        elif '7인승' in gname:
            seating_counts['7인승'] += 1
        else:
            seating_counts['미표기'] += 1
    log(f"   - 쏘렌토 2022 인승별 등급 분포: {seating_counts} (인승별 분리 완전 보존)")


if __name__ == '__main__':
    run_cross_source_merge()
