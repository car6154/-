# scripts/resolve_price_conflicts.py
"""
[11-11-19] 제이책(C) 기본가 충돌 정리 스크립트
- 개별소비세 등 세금 가산 가격 제거 및 정가(엔카 공식가 / 다나와 최저가) 단일화
- 2WD vs 4WD 등 구동방식/변속기 상이 사양은 제거하지 않고 독립 보존
- 백업: data/catalog_c_v4_backup_2026-11-12.json
- 산출: data/catalog_c.json
- 제거 로그: data/catalog_c_price_conflict_removed_2026-11-12.json
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
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_c_v4_backup_2026-11-12.json")
CONFLICTS_FILE = os.path.join(DATA_DIR, "catalog_c_price_conflicts_v2_2026-11-12.json")
REMOVED_LOG_FILE = os.path.join(DATA_DIR, "catalog_c_price_conflict_removed_2026-11-12.json")


def log(msg: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


def get_drive(name: str) -> str:
    n = (name or "").lower()
    if '4wd' in n or 'awd' in n or '4륜' in n:
        return '4wd'
    return '2wd'


def get_mission(name: str) -> str:
    n = (name or "").lower()
    if 'm/t' in n or '수동' in n:
        return 'manual'
    return 'auto'


def run_conflict_resolution():
    log("==================================================")
    log("🚀 [11-11-19] 제이책(C) 기본가 충돌 정리 시작")
    log("==================================================")

    # 1. 1차본/이전본 백업 확인 및 v4 백업 생성
    if not os.path.exists(BACKUP_FILE):
        log(f"1. v4 백업 생성 중 -> {BACKUP_FILE}")
        shutil.copyfile(CATALOG_C_FILE, BACKUP_FILE)
    else:
        log(f"1. v4 백업 파일 확인됨: {BACKUP_FILE}")

    with open(CATALOG_C_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    with open(CONFLICTS_FILE, "r", encoding="utf-8") as f:
        conflicts = json.load(f)

    before_grades = sum(len(grades) for yrs in catalog.values() for grades in yrs.values())
    log(f"  - 정리 전 총 등급 수: {before_grades:,}개")
    log(f"  - 분석 대상 충돌 그룹 수: {len(conflicts):,}건")

    removed_list = []
    preserved_groups = []
    resolved_groups_count = 0

    # 제거 대상 키 수집용 셋: (model, year, grade_name)
    to_remove_keys = set()

    for c in conflicts:
        model = c.get('model')
        year = str(c.get('year'))
        trim = c.get('trim')
        fuel = c.get('fuel')
        grades = c.get('grades', [])

        # 서브그룹: 구동방식, 변속기별 분리
        subgroups = {}
        for g in grades:
            gname = g.get('name')
            s_key = (get_drive(gname), get_mission(gname))
            if s_key not in subgroups:
                subgroups[s_key] = []
            subgroups[s_key].append(g)

        group_resolved = False

        for s_key, s_grades in subgroups.items():
            if len(s_grades) <= 1:
                continue

            # 동일 사양 내 복수 가격 충돌 발생!
            group_resolved = True

            # 정가 1개 선정 규칙:
            # 1. 엔카 등급 존재 여부
            encar_grades = [g for g in s_grades if g.get('source') == 'encar']

            if encar_grades:
                # 엔카 등급 중 정가 선택 (최저가 -> 이름 긴 것)
                encar_grades.sort(key=lambda x: (
                    x.get('base_price') if x.get('base_price') is not None else 999999999,
                    -len(x.get('name', ''))
                ))
                chosen = encar_grades[0]
                reason_rule = "엔카 공식 가격표 정가 우선 적용으로 다나와 세금 가격 제거"
            else:
                # 다나와 내부 충돌 -> 최저가 선택 (세금 미반영 정가)
                s_grades.sort(key=lambda x: (
                    x.get('base_price') if x.get('base_price') is not None else 999999999,
                    -len(x.get('name', ''))
                ))
                chosen = s_grades[0]
                reason_rule = "최저가(세금 미반영 정가) 우선 적용으로 상위 세금 가산 가격 제거"

            # chosen을 제외한 나머지 등급 제거 목록에 추가
            for g in s_grades:
                gname = g.get('name')
                if gname != chosen.get('name'):
                    key_tuple = (model, year, gname)
                    if key_tuple not in to_remove_keys:
                        to_remove_keys.add(key_tuple)
                        removed_list.append({
                            'model': model,
                            'year': year,
                            'trim': trim,
                            'fuel': fuel,
                            'drive': s_key[0],
                            'mission': s_key[1],
                            'grade_name': gname,
                            'base_price': g.get('base_price'),
                            'source': g.get('source'),
                            'chosen_grade': chosen.get('name'),
                            'chosen_price': chosen.get('base_price'),
                            'reason': reason_rule
                        })

        if group_resolved:
            resolved_groups_count += 1
        else:
            preserved_groups.append({
                'model': model,
                'year': year,
                'trim': trim,
                'fuel': fuel,
                'grades_count': len(grades),
                'reason': "구동방식(2WD vs 4WD) 또는 변속기 상이 사양으로 각 등급 정상 보존"
            })

    # 2. catalog_c 데이터에서 제거 대상 등급 실제로 삭제
    log(f"\n2. 제이책(C) 데이터에서 {len(to_remove_keys):,}개 세금 등급 제거 적용 중...")
    for model, year, gname in to_remove_keys:
        if model in catalog and year in catalog[model]:
            if gname in catalog[model][year]:
                del catalog[model][year][gname]

    after_grades = sum(len(grades) for yrs in catalog.values() for grades in yrs.values())

    # 3. 파일 저장
    log("\n3. 정제 결과 파일 저장 중...")
    with open(CATALOG_C_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    log(f"  - 갱신된 제이책(C) 저장 완료: {CATALOG_C_FILE} ({os.path.getsize(CATALOG_C_FILE)/(1024*1024):.2f} MB)")

    with open(REMOVED_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(removed_list, f, ensure_ascii=False, indent=2)
    log(f"  - 제거 등급 로그 저장 완료: {REMOVED_LOG_FILE} ({len(removed_list):,}개)")

    # 4. 검증 리포트
    log("\n==================================================")
    log("📋 [11-11-19] 제이책(C) 기본가 충돌 정리 검증 보고서")
    log("==================================================")
    log("1. 수치 요약:")
    log(f"   - 총 충돌 그룹: {len(conflicts):,}건")
    log(f"   - 세금 중복 제거 처리된 그룹: {resolved_groups_count:,}건")
    log(f"   - 사양 상이(2WD vs 4WD 등)로 제거하지 않고 보존한 그룹: {len(preserved_groups):,}건")
    log(f"   - 제거한 세금 등급 수: {len(removed_list):,}개")
    log(f"   - 등급 수 변화: {before_grades:,}개 -> {after_grades:,}개 (순감소: {before_grades - after_grades:,}개)")

    # 필수 검증 1: 더 뉴 QM6 2024 RE
    log("\n2. 더 뉴 QM6 2024 RE 등급 검증 (6개 -> 2개 감소 확인):")
    qm6_2024_re = {k: v for k, v in catalog.get('더 뉴 QM6', {}).get('2024', {}).items() if 'RE' in k}
    log(f"   - QM6 2024 RE 최종 등급 수: {len(qm6_2024_re)}개")
    for k, v in qm6_2024_re.items():
        log(f"     * [{v.get('source')}] {k}: {v.get('base_price'):,}원")
    assert len(qm6_2024_re) == 2, f"Expected 2 grades, got {len(qm6_2024_re)}"
    assert all(v.get('source') == 'encar' for v in qm6_2024_re.values()), "모든 남은 등급이 엔카 출처여야 합니다."
    assert all(v.get('base_price') == 32200000 for v in qm6_2024_re.values()), "모든 남은 등급 가격이 32,200,000원이어야 합니다."

    # 필수 검증 2: 더 뉴 QM6 2025 RE
    log("\n3. 더 뉴 QM6 2025 RE 등급 검증 (엔카 2개 30,490,000원 확인):")
    qm6_2025_re = {k: v for k, v in catalog.get('더 뉴 QM6', {}).get('2025', {}).items() if 'RE' in k}
    log(f"   - QM6 2025 RE 최종 등급 수: {len(qm6_2025_re)}개")
    for k, v in qm6_2025_re.items():
        log(f"     * [{v.get('source')}] {k}: {v.get('base_price'):,}원")
    assert len(qm6_2025_re) == 2, f"Expected 2 grades, got {len(qm6_2025_re)}"
    assert all(v.get('source') == 'encar' for v in qm6_2025_re.values()), "모든 남은 등급이 엔카 출처여야 합니다."
    assert all(v.get('base_price') == 30490000 for v in qm6_2025_re.values()), "모든 남은 등급 가격이 30,490,000원이어야 합니다."

    log("\n✅ [11-11-19] 모든 충돌 정리 및 필수 검증 100% 성공!")


if __name__ == '__main__':
    run_conflict_resolution()
