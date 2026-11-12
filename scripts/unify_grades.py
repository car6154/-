import os
import json
import re
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CATALOG_C_FILE = os.path.join(DATA_DIR, "catalog_c.json")
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_c_v9_backup_2026-11-12.json")
LOG_FILE = os.path.join(DATA_DIR, "catalog_c_unified_log_2026-11-12.json")
REVIEW_FILE = os.path.join(DATA_DIR, "catalog_c_unified_review_2026-11-12.json")

TRIM_KEYWORDS = [
    '스마트', '모던', '프리미엄', '익스클루시브', '인스퍼레이션', '캘리그래피', '르블랑', '스타일',
    '트렌디', '프레스티지', '노블레스', '시그니처', '그래비티', '디럭스', '럭셔리', '스페셜',
    '기본형', '베이직', '플래티넘', '어드밴스드', '아이코닉', '테크노', '에스프리', '알핀',
    'LT', 'LTZ', 'RS', '프리미어', '액티브', '레드라인', '하이컨트리',
    'SE', 'LE', 'RE', 'ZE', 'GTe', 'LTe',
    'T3', 'T5', 'T7', 'V1', 'V3', 'V5', 'V7', 'TX', 'RX'
]

def has_trim_name(gname: str) -> bool:
    return any(tk in gname for tk in TRIM_KEYWORDS)

def parse_pt_smart(gname: str):
    if 'HEV' in gname: fuel = 'HEV'
    elif '디젤' in gname: fuel = '디젤'
    elif 'LPG' in gname or 'LPI' in gname or 'LPe' in gname: fuel = 'LPG'
    elif '전기' in gname or 'EV' in gname: fuel = '전기'
    elif '수소' in gname: fuel = '수소'
    else: fuel = '가솔린'

    m_disp = re.search(r'(\d+\.\d+)', gname)
    disp = m_disp.group(1) if m_disp else ''

    m_drv = re.search(r'(4WD|AWD|4륜)', gname, re.IGNORECASE)
    drive = '4WD' if m_drv else '2WD'

    return (fuel, disp, drive)

def clean_opt_desc(desc: str) -> str:
    if not desc:
        return ""
    # [패키지 구성]: ... 내용만 추출하여 2단 표의 깔끔한 세부 내용으로 정돈
    m = re.search(r'\[패키지\s*구성\]:\s*([^\|]+)', desc)
    if m:
        return m.group(1).strip()
    if '| [상세' in desc:
        return desc.split('| [상세')[0].strip()
    return desc.strip()

def main():
    print("[1/5] 책 데이터 로드...")
    with open(CATALOG_C_FILE, "r", encoding="utf-8") as f:
        cat = json.load(f)

    initial_grades_count = sum(len(y) for m in cat.values() for y in m.values())
    print(f"      작업 전 총 등급 수: {initial_grades_count:,}개")

    print(f"[2/5] v9 백업 생성: {BACKUP_FILE}...")
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
    print("      백업 완료!")

    # 모델별 터보 배기량 수집 (T 표기 통일용)
    turbo_disps_by_model = defaultdict(set)
    for m, yrs in cat.items():
        for y, grades in yrs.items():
            for g in grades:
                for d in re.findall(r'(\d+\.\d+)T', g):
                    turbo_disps_by_model[m].add(d)

    new_cat = {}
    unified_log = []
    review_list = []

    absorbed_encar_count = 0
    danawa_only_count = 0

    print("[3/5] 등급 통합 및 새 등급 생성 수행...")

    for m, yrs in cat.items():
        new_cat[m] = {}
        for y, grades in yrs.items():
            new_cat[m][y] = {}

            encar_g = {k: v for k, v in grades.items() if v.get('source') == 'encar'}
            danawa_g = {k: v for k, v in grades.items() if v.get('source') == 'danawa'}

            # Case 1: 다나와 등급이 없는 경우 (엔카만 있음)
            if not danawa_g:
                for ek, ev in encar_g.items():
                    new_cat[m][y][ek] = ev
                continue

            # Case 2: 엔카 등급이 없는 경우 (다나와만 있음 - 2025 이후 등급 등)
            if not encar_g:
                for dk, dv in danawa_g.items():
                    danawa_only_count += 1
                    # 엔진 표기 통일 (2.5 -> 2.5T)
                    new_dk = dk
                    for td in turbo_disps_by_model.get(m, set()):
                        new_dk = re.sub(rf'\b{re.escape(td)}(?!T|\d)', f'{td}T', new_dk)

                    cleaned_opts = {}
                    for ok, ov in dv.get('options', {}).items():
                        ov_copy = dict(ov)
                        ov_copy['desc'] = clean_opt_desc(ov.get('desc', ''))
                        if any(c in ok for c in ['펄', '컬러', '색상']):
                            ov_copy['is_color'] = True
                        cleaned_opts[ok] = ov_copy

                    dv_copy = dict(dv)
                    dv_copy['name'] = new_dk
                    dv_copy['options'] = cleaned_opts
                    dv_copy['options_count'] = len(cleaned_opts)
                    dv_copy['source'] = 'danawa_only'

                    new_cat[m][y][new_dk] = dv_copy
                    unified_log.append({
                        "model": m,
                        "year": y,
                        "grade": new_dk,
                        "source": "danawa_only",
                        "note": "엔카 가격표 없음으로 다나와 유지"
                    })
                continue

            # Case 3: 엔카와 다나와 둘 다 있는 경우 (핵심 통합 대상)
            encar_base = {}
            encar_trim = {}
            for ek, ev in encar_g.items():
                if has_trim_name(ek):
                    encar_trim[ek] = ev
                else:
                    encar_base[ek] = ev

            # 엔카 공통 옵션 가격 맵 (옵션명 -> 엔카 가격)
            encar_opt_prices = {}
            for ek, ev in encar_g.items():
                for ok, ov in ev.get('options', {}).items():
                    p = ov.get('price')
                    if p is not None:
                        encar_opt_prices[ok] = p

            # 엔카 기본 등급 매칭 검사
            used_encar_base = set()
            for eb_name, eb_data in encar_base.items():
                eb_pt = parse_pt_smart(eb_name)

                # 1) 완전 일치
                matching_keys = [dk for dk in danawa_g if parse_pt_smart(dk) == eb_pt]
                # 2) 전기/수소 배기량 생략
                if not matching_keys and eb_pt[0] in ['전기', '수소']:
                    matching_keys = [dk for dk in danawa_g if parse_pt_smart(dk)[0] == eb_pt[0] and parse_pt_smart(dk)[2] == eb_pt[2]]
                # 3) 연료 + 구동 일치
                if not matching_keys:
                    matching_keys = [dk for dk in danawa_g if parse_pt_smart(dk)[0] == eb_pt[0] and parse_pt_smart(dk)[2] == eb_pt[2]]

                if matching_keys:
                    used_encar_base.add(eb_name)
                    absorbed_encar_count += 1
                    unified_log.append({
                        "model": m,
                        "year": y,
                        "type": "encar_base_absorbed",
                        "encar_base_grade": eb_name,
                        "base_price": eb_data.get('base_price'),
                        "matched_danawa_count": len(matching_keys)
                    })

            # 다나와 등급들을 새 등급으로 재구성 및 기본가/옵션 적용
            for dk, dv in danawa_g.items():
                # 1) 엔진 표기 통일 (2.5 -> 2.5T)
                new_dk = dk
                for td in turbo_disps_by_model.get(m, set()):
                    new_dk = re.sub(rf'\b{re.escape(td)}(?!T|\d)', f'{td}T', new_dk)

                d_pt = parse_pt_smart(dk)

                # 대응되는 엔카 기본 등급 탐색
                matched_eb_name = None
                for eb_name in encar_base:
                    if parse_pt_smart(eb_name) == d_pt:
                        matched_eb_name = eb_name
                        break
                if not matched_eb_name:
                    for eb_name in encar_base:
                        if parse_pt_smart(eb_name)[0] == d_pt[0] and parse_pt_smart(eb_name)[2] == d_pt[2]:
                            matched_eb_name = eb_name
                            break

                target_price = dv.get('base_price', 0)
                is_base_trim = False

                if matched_eb_name:
                    eb_data = encar_base[matched_eb_name]
                    eb_price = eb_data.get('base_price', 0)
                    eb_opts = eb_data.get('options', {})

                    seat6_p = eb_opts.get('6인승', {}).get('price', 840000)
                    seat7_p = eb_opts.get('7인승', {}).get('price', 690000)

                    # 기본 트림 판정 (최저가 트림이거나 프레스티지/스마트/모던/스타일 등)
                    pt_danawa_prices = [danawa_g[k].get('base_price', 0) for k in danawa_g if parse_pt_smart(k) == d_pt]
                    min_pt_price = min(pt_danawa_prices) if pt_danawa_prices else 0

                    if dv.get('base_price', 0) <= min_pt_price + 1000000 or any(bt in dk for bt in ['프레스티지', '스마트', '모던', '스타일', '디럭스', '트렌디']):
                        is_base_trim = True
                        if '6인승' in dk:
                            target_price = eb_price + seat6_p
                        elif '7인승' in dk:
                            target_price = eb_price + seat7_p
                        elif '5인승' in dk or '인승' not in dk:
                            target_price = eb_price

                # 옵션 통합
                new_opts = {}
                conditions_list = []

                for ok, ov in dv.get('options', {}).items():
                    # 인승 옵션 제외 (등급 이름에 인승이 이미 들어있음)
                    if ok in ['5인승', '6인승', '7인승', '8인승', '9인승', '11인승']:
                        continue
                    # 조건 문구 제외 및 조건 리스트로 분리
                    if '선택 가능' in ok or '적용 시' in ok or ('미적용' in ok and (ov.get('price') == 0 or ov.get('price') is None)):
                        conditions_list.append(ok)
                        continue

                    ov_copy = dict(ov)
                    # 엔카 옵션 가격 우선 적용
                    if ok in encar_opt_prices:
                        ov_copy['price'] = encar_opt_prices[ok]
                        ov_copy['price_man'] = int(encar_opt_prices[ok] / 10000)
                        ov_copy['source'] = 'encar'

                    # 옵션 설명 2단 표 포맷팅 (핵심 요약)
                    ov_copy['desc'] = clean_opt_desc(ov.get('desc', ''))

                    # 유상 외장 컬러 마킹
                    if any(c in ok for c in ['펄', '컬러', '색상']):
                        ov_copy['is_color'] = True

                    new_opts[ok] = ov_copy

                dv_copy = dict(dv)
                dv_copy['name'] = new_dk
                dv_copy['base_price'] = target_price
                dv_copy['base_price_man'] = int(target_price / 10000)
                dv_copy['options'] = new_opts
                dv_copy['options_count'] = len(new_opts)
                if conditions_list:
                    dv_copy['conditions'] = conditions_list
                dv_copy['source'] = 'unified' if is_base_trim else 'danawa'

                new_cat[m][y][new_dk] = dv_copy

            # 흡수되지 않은 엔카 트림 등급들 보존
            for etk, etv in encar_trim.items():
                if etk not in new_cat[m][y]:
                    new_cat[m][y][etk] = etv

            # 짝을 찾지 못해 흡수되지 않은 엔카 기본 등급 검토 목록 기록 및 보존
            for eb_name in encar_base:
                if eb_name not in used_encar_base:
                    review_list.append({
                        "model": m,
                        "year": y,
                        "grade": eb_name,
                        "reason": "모든 매칭 단계(연식·연료·구동·배기량) 시도 후에도 다나와 짝을 찾지 못함"
                    })
                    new_cat[m][y][eb_name] = encar_base[eb_name]

    final_grades_count = sum(len(y) for m in new_cat.values() for y in m.values())
    print(f"      작업 후 총 등급 수: {final_grades_count:,}개")
    print(f"      흡수된 엔카 기본 등급 수: {absorbed_encar_count:,}개")
    print(f"      danawa_only 등급 수: {danawa_only_count:,}개")
    print(f"      검토 목록 등급 수: {len(review_list):,}개")

    print(f"[4/5] 산출물 파일 저장...")
    with open(CATALOG_C_FILE, "w", encoding="utf-8") as f:
        json.dump(new_cat, f, ensure_ascii=False, indent=2)
    print(f"      {CATALOG_C_FILE} 갱신 완료!")

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(unified_log, f, ensure_ascii=False, indent=2)
    print(f"      {LOG_FILE} 저장 완료 ({len(unified_log):,}건)!")

    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(review_list, f, ensure_ascii=False, indent=2)
    print(f"      {REVIEW_FILE} 저장 완료 ({len(review_list):,}건)!")

    print("[5/5] 표본 및 무결성 검증...")
    # 쏘렌토 2025 표본
    sor_2025 = new_cat.get('더 뉴 쏘렌토 4세대', {}).get('2025', {})
    hev_p5 = sor_2025.get('HEV 1.6 2WD 프레스티지(5인승)', {})
    hev_p6 = sor_2025.get('HEV 1.6 2WD 프레스티지(6인승)', {})
    hev_p7 = sor_2025.get('HEV 1.6 2WD 프레스티지(7인승)', {})

    print(f"  - 쏘렌토 2025 HEV 5인승 가격: {hev_p5.get('base_price'):,}원 (목표: 38,670,000원)")
    print(f"  - 쏘렌토 2025 HEV 6인승 가격: {hev_p6.get('base_price'):,}원 (목표: 39,510,000원)")
    print(f"  - 쏘렌토 2025 HEV 7인승 가격: {hev_p7.get('base_price'):,}원 (목표: 39,360,000원)")

    assert hev_p5.get('base_price') == 38670000
    assert hev_p6.get('base_price') == 39510000
    assert hev_p7.get('base_price') == 39360000

    opts_5 = hev_p5.get('options', {})
    assert '6인승' not in opts_5
    assert '7인승' not in opts_5
    print("  - 6인승/7인승 인승 옵션 제거 확인 완료")

    assert opts_5.get('스타일', {}).get('price') == 1140000
    assert opts_5.get('드라이브 와이즈', {}).get('price') == 1290000
    print("  - 스타일(1,140,000원), 드라이브 와이즈(1,290,000원) 엔카 가격 일치 확인 완료")

    # 가솔린 2.5T 표기 통일 확인
    gas_grades = [k for k in sor_2025 if '가솔린' in k]
    missing_t = [k for k in gas_grades if '2.5 ' in k]
    assert len(missing_t) == 0
    print(f"  - 가솔린 2.5T 표기 통일 완료 (누락: {len(missing_t)}개)")

    print("🎉 등급 통합 및 모든 표본 검증 100% 통과!")

if __name__ == "__main__":
    main()
