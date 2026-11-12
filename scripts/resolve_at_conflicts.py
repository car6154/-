# scripts/resolve_at_conflicts.py
"""
[11-11-21] 제이책(C) 잔여 기본가 충돌 정리 스크립트
- 같은 (차종, 연식, 트림 핵심, 연료, 구동방식, 변속기) 기본가 충돌 정리
- 'A/T' 표기 차이 및 세금 가산 가격 제거, 공식 정가 유지
- 백업: data/catalog_c_v6_backup_2026-11-12.json
- 산출: data/catalog_c.json
- 제거 로그: data/catalog_c_price_conflict_removed_v2_2026-11-12.json
- 검토 목록: data/catalog_c_price_conflict_review_2026-11-12.json
"""

import os
import sys
import json
import re
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
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_c_v6_backup_2026-11-12.json")
REMOVED_FILE = os.path.join(DATA_DIR, "catalog_c_price_conflict_removed_v2_2026-11-12.json")
REVIEW_FILE = os.path.join(DATA_DIR, "catalog_c_price_conflict_review_2026-11-12.json")


def log(msg: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


def extract_features(gname: str) -> dict:
    g_raw = str(gname).lower().strip()

    # 1. 인승 추출
    m_seat = re.search(r'([0-9]+)\s*인승', g_raw)
    seating = f"{m_seat.group(1)}인승" if m_seat else None

    # 2. 구동방식 추출 (4wd vs 2wd)
    if any(k in g_raw for k in ['4wd', 'awd', '4륜', '사륜']):
        drive = '4wd'
    else:
        drive = '2wd'

    # 3. 변속기 표기 (수동 vs 자동)
    if re.search(r'\bm/t\b|\bmt\b|수동', g_raw):
        trans = 'manual'
    else:
        trans = 'auto'

    # 4. 유종 추출
    fuel = 'gasoline'
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

    # 5. 배기량 추출
    m_disp = re.search(r'\b([1-9]\.[0-9])\b', g_raw)
    displacement = m_disp.group(1) if m_disp else None

    # 6. 트림 핵심 정규화 (변속기 a/t, m/t 표기 및 구동방식, 인승, 유종 등 제거)
    t = re.sub(r'\(?\s*[am]/t\s*\)?', '', g_raw, flags=re.I)
    t = re.sub(r'\b(tce|gde|gte|lpe|lpi|gdi|hev|ev|2wd|4wd|awd|fwd|rwd|mpi|a/t|m/t|at|mt)\b', '', t)
    t = re.sub(r'([0-9]+)\s*인승', '', t)
    t = re.sub(r'\b([1-9]\.[0-9])\b', '', t)
    t = re.sub(r'(가솔린|디젤|하이브리드|전기|lpg|퀘스트)', '', t)
    t = re.sub(r'[\s\-_/·・\.\(\)]+', '', t)
    t = t.replace('signature', '시그니처').replace('plus', '플러스').replace('비지니스', '비즈니스')

    return {
        'seating': seating,
        'fuel': fuel,
        'drive': drive,
        'trans': trans,
        'displacement': displacement,
        'trim': t
    }


def is_manual_grade(gname: str, gdata: dict) -> bool:
    gn = str(gname).lower()
    mv = str(gdata.get('mission') or '').lower()
    return bool(re.search(r'\bm/t\b|\bmt\b|수동', gn) or re.search(r'\bm/t\b|\bmt\b|수동', mv))


def run_resolution():
    log("==================================================")
    log("🚀 [11-11-21] 제이책(C) 잔여 기본가 충돌 정리 시작")
    log("==================================================")

    # 1. v6 백업 생성
    if not os.path.exists(BACKUP_FILE):
        log(f"1. v6 백업 생성 중 -> {BACKUP_FILE}")
        shutil.copyfile(CATALOG_C_FILE, BACKUP_FILE)
    else:
        log(f"1. v6 백업 파일 확인됨: {BACKUP_FILE}")

    with open(CATALOG_C_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    before_grades = sum(len(y) for y in catalog.values() for y in y.values())
    log(f"  - 정리 전 총 등급 수: {before_grades:,}개")

    # 2. 그룹핑 (변속기 trans를 키에 포함하여 수동과 자동 완벽 분리)
    groups = {}
    for model, yrs in catalog.items():
        for yr, grades in yrs.items():
            for gname, gdata in grades.items():
                bp = gdata.get('base_price')
                if bp is None: continue
                
                feat = extract_features(gname)
                trans = 'manual' if is_manual_grade(gname, gdata) else 'auto'
                
                # 같은 (모델, 연식, 유종, 배기량, 구동방식, 인승, 변속기, 트림)
                key = (model, yr, feat['fuel'], feat['displacement'], feat['drive'], feat['seating'], trans, feat['trim'])
                if key not in groups:
                    groups[key] = []
                groups[key].append((gname, gdata, feat))

    to_resolve = []
    to_review = []

    for key, glist in groups.items():
        if len(glist) >= 2:
            prices = set(item[1]['base_price'] for item in glist)
            if len(prices) > 1:
                m, y, fuel, disp, drive, seat, trans, trim = key
                
                # 1. 100만원 미만 비정상 이상치 확인
                if any(item[1].get('base_price', 0) < 1000000 for item in glist):
                    to_review.append({
                        'model': m, 'year': y, 'trim': trim, 'trans': trans,
                        'reason': "100만원 미만 비정상 기본가 존재로 검토 보존",
                        'grades': [{'name': item[0], 'base_price': item[1].get('base_price'), 'source': item[1].get('source'), 'mission': item[1].get('mission')} for item in glist]
                    })
                    continue

                to_resolve.append((key, glist))

    log(f"2. 스캔 완료:")
    log(f"   - 정리 대상 충돌 그룹: {len(to_resolve):,}개")
    log(f"   - 검토 목록 보존 그룹: {len(to_review):,}개")

    # 3. 정가 선정 및 제거 목록 산출
    removed_logs = []
    to_delete_from_catalog = {} # (model, yr) -> set of grade_names

    for key, glist in to_resolve:
        m, y, fuel, disp, drive, seat, trans, trim = key
        
        # 정가 1개 선정 규칙:
        # (1) 엔카 등급 존재 여부
        encar_candidates = [item for item in glist if item[1].get('source') == 'encar']
        if encar_candidates:
            # 엔카 등급 중 정가 선택 (최저가 -> 이름 긴 것)
            encar_candidates.sort(key=lambda x: (
                x[1].get('base_price') if x[1].get('base_price') is not None else 999999999,
                -len(x[0])
            ))
            chosen = encar_candidates[0]
            reason = "엔카 공식 가격표 정가 우선 적용으로 다나와 세금 가격 제거"
        else:
            # 다나와 내부 충돌 -> 최저가 선택 (세금 미반영 정가 -> 이름 긴 것)
            glist.sort(key=lambda x: (
                x[1].get('base_price') if x[1].get('base_price') is not None else 999999999,
                -len(x[0])
            ))
            chosen = glist[0]
            reason = "다나와 내부 충돌: 최저가(세금 미반영 정가) 우선 적용으로 상위 세금 가격 제거"

        chosen_name = chosen[0]
        chosen_price = chosen[1].get('base_price')

        # chosen을 제외한 나머지 제거
        m_y_key = (m, y)
        if m_y_key not in to_delete_from_catalog:
            to_delete_from_catalog[m_y_key] = set()

        for gname, gdata, feat in glist:
            if gname != chosen_name:
                to_delete_from_catalog[m_y_key].add(gname)
                removed_logs.append({
                    'model': m,
                    'year': y,
                    'trim': trim,
                    'fuel': fuel,
                    'drive': drive,
                    'trans': trans,
                    'seating': seat,
                    'removed_grade': gname,
                    'removed_price': gdata.get('base_price'),
                    'removed_source': gdata.get('source'),
                    'retained_grade': chosen_name,
                    'retained_price': chosen_price,
                    'retained_source': chosen[1].get('source'),
                    'reason': reason
                })

    log(f"\n3. 제이책(C) 데이터에서 {len(removed_logs):,}개 등급 제거 적용 중...")
    for (m, y), names_to_del in to_delete_from_catalog.items():
        for gname in names_to_del:
            if gname in catalog[m][y]:
                del catalog[m][y][gname]

    after_grades = sum(len(y) for y in catalog.values() for y in y.values())

    # 4. 파일 저장
    log("\n4. 정제 결과 파일 저장 중...")
    with open(CATALOG_C_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    log(f"  - 갱신된 제이책(C) 저장 완료: {CATALOG_C_FILE}")

    with open(REMOVED_FILE, "w", encoding="utf-8") as f:
        json.dump(removed_logs, f, ensure_ascii=False, indent=2)
    log(f"  - 제거 로그 저장: {REMOVED_FILE} ({len(removed_logs):,}건)")

    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(to_review, f, ensure_ascii=False, indent=2)
    log(f"  - 검토 목록 저장: {REVIEW_FILE} ({len(to_review):,}개 그룹)")

    # 5. 검증 리포트
    log("\n==================================================")
    log("📋 [11-11-21] 제이책(C) 잔여 기본가 충돌 정리 검증 보고서")
    log("==================================================")
    log("1. 수치 요약:")
    log(f"   - 정리 전 총 등급 수: {before_grades:,}개")
    log(f"   - 제거한 등급 수: {len(removed_logs):,}개")
    log(f"   - 정리 후 총 등급 수: {after_grades:,}개 (순감소: {before_grades - after_grades:,}개)")
    log(f"   - 검토 목록 보존 그룹 수: {len(to_review):,}개")

    # 아반떼 (CN7) 2020 필수 검증
    log("\n2. [필수 검증] 아반떼 (CN7) 2020 스마트 계열 확인:")
    avante_grades = catalog.get('아반떼 (CN7)', {}).get('2020', {})
    for g, data in avante_grades.items():
        if '스마트' in g and '가솔린' in g:
            log(f"   * [{data.get('source')}] {g}: {data.get('base_price'):,}원")
    assert '가솔린 1.6 2WD 스마트 A/T' in avante_grades, "정가 16,740,000원 '스마트 A/T'가 유지되어야 합니다."
    assert '가솔린 1.6 2WD 스마트' not in avante_grades, "세금 가격 17,490,000원 '스마트'가 제거되어야 합니다."
    log("   ✅ 아반떼 (CN7) 2020 스마트 계열 정가(16,740,000원) 단일화 100% 확인!")

    log("\n✅ [11-11-21] 모든 충돌 정리 및 필수 검증 100% 성공!")


if __name__ == '__main__':
    run_resolution()
