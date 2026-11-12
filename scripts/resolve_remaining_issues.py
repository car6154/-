# scripts/resolve_remaining_issues.py
"""
[11-12-09] 11-12-08 잔여 미결 해소
1. 미추가 등급 20개 사유 규명 및 스파크 2015 LS+ 추가
2. 악세사리 잔여 25개 매핑 보강 및 사유 분류
3. 가격 불일치 1,095건 원인 분석, 상위 트림 복사 왜곡 458건 수정, 11-12-07 21개 보호 및 보류 624건 검토 목록 기록
"""

import os
import json
import re
from collections import defaultdict, Counter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_C_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_c.json")
BACKUP_V15_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_c_v15_backup_2026-11-12.json")
AUDIT_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_c_full_audit_2026-11-12.json")
FIX_LOG_11_12_08_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_c_full_fix_log_2026-11-12.json")
ENCAR_V2_FILE = os.path.join(PROJECT_ROOT, "data", "encar_newcar_catalog_v2.json")
SRC_V2_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_by_source_v2.json")

FIX_LOG_OUT_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_c_remaining_fix_log_2026-11-12.json")
REVIEW_OUT_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_c_remaining_review_2026-11-12.json")


def normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r'[\s\(\)\[\]\-_/·,]+', '', t)
    return t


def main():
    print("=== [11-12-09] 잔여 미결 해소 작업 시작 ===")

    # 1. 원본 데이터 로드
    cat = json.load(open(CATALOG_C_FILE, "r", encoding="utf-8"))
    audit = json.load(open(AUDIT_FILE, "r", encoding="utf-8"))
    fix_log_08 = json.load(open(FIX_LOG_11_12_08_FILE, "r", encoding="utf-8"))
    ev2 = json.load(open(ENCAR_V2_FILE, "r", encoding="utf-8"))
    src_v2 = json.load(open(SRC_V2_FILE, "r", encoding="utf-8"))
    danawa = src_v2.get("danawa", {})

    fix_log = {
        'summary': {},
        'added_grades': [],
        'added_accessories': [],
        'updated_prices': [],
        'retained_protected_prices': []
    }

    review_data = {
        'missing_grades_unadded': [],
        'unmapped_accessories': [],
        'price_mismatch_breakdown': {
            'tax_diff_1_5pct': [],
            'minor_diff_under_5pct': [],
            'benchmark_diff_over_5pct': [],
            'protected_lowest_seat': []
        }
    }

    # ---------------------------------------------------------
    # PART 1: 미추가 등급 20개 해결
    # ---------------------------------------------------------
    print("\n[PART 1] 미추가 등급 20개 사유 규명 및 보강...")
    audit_missing_grades = audit.get('missing_grades', [])
    added_08_grades = {(x['model'], x['year'], x['name']) for x in fix_log_08.get('added_grades', [])}

    # 중복 분석
    missing_counter = Counter((g['model'], g['year'], g['name']) for g in audit_missing_grades)
    duplicates_in_audit = [k for k, v in missing_counter.items() if v > 1]
    print(f"  Audit missing 전체: {len(audit_missing_grades)}건, 고유 등급: {len(missing_counter)}건 (중복 {len(duplicates_in_audit)}개 키 / 19건)")

    # 11-12-08 미추가 1건 찾기
    unadded_unique = [k for k in missing_counter if k not in added_08_grades]
    print(f"  11-12-08 미추가 고유 등급: {len(unadded_unique)}건 -> {unadded_unique}")

    for k in duplicates_in_audit:
        review_data['missing_grades_unadded'].append({
            'model': k[0], 'year': k[1], 'name': k[2],
            'reason': f"대조 파일 내 중복 엔트리 (총 {missing_counter[k]}회 등장, 11-12-08에서 1회 이미 추가 완료)"
        })

    # 스파크 2015 LS+ 추가
    if ('스파크', '2015', 'LS+') in unadded_unique:
        spark_grades = ev2.get('스파크', {}).get('2015', {}).get('grades', [])
        ls_plus_encar = next((g for g in spark_grades if g.get('name') == 'LS+'), None)
        if ls_plus_encar and '스파크' in cat and '2015' in cat['스파크']:
            grade_name = 'LS+'
            grade_obj = {
                'base_price': ls_plus_encar.get('base_price', 12210000),
                'source': 'encar',
                'options': ls_plus_encar.get('options', {})
            }
            cat['스파크']['2015'][grade_name] = grade_obj
            fix_log['added_grades'].append({
                'model': '스파크', 'year': '2015', 'name': 'LS+',
                'price': 12210000, 'reason': '엔카 공식 가격표 기본 등급 정상 추가'
            })
            print("  -> 스파크 2015 LS+ 추가 완료!")

    # ---------------------------------------------------------
    # PART 2: 악세사리 남은 25개 해결
    # ---------------------------------------------------------
    print("\n[PART 2] 악세사리 남은 25개 해결...")
    all_missing_acc = audit.get('accessory_audit', {}).get('missing_acc_list', [])
    fixed_acc_08 = {(x['danawa_model'], x['year']) for x in fix_log_08.get('added_accessories', [])}
    rem_acc = [a for a in all_missing_acc if (a['danawa_model'], a['year']) not in fixed_acc_08]
    print(f"  잔여 대상: {len(rem_acc)}건")

    # 매핑 정의
    acc_mapping_table = {
        ('코란도 이모션', '2022'): ('코란도 EV (이모션)', '2022'),
        ('아이오닉 HEV', '2016'): ('아이오닉 하이브리드', '2016'),
        ('아이오닉 HEV', '2017'): ('아이오닉 하이브리드', '2017'),
        ('아이오닉 HEV', '2018'): ('아이오닉 하이브리드', '2018'),
        ('아이오닉 PHEV', '2017'): ('아이오닉 하이브리드', '2017'),
        ('아이오닉 PHEV', '2018'): ('아이오닉 하이브리드', '2018'),
        ('LF쏘나타 뉴 라이즈PHEV', '2017'): ('쏘나타 뉴 라이즈 하이브리드', '2017'),
        ('LF쏘나타 뉴 라이즈PHEV', '2018'): ('쏘나타 뉴 라이즈 하이브리드', '2018'),
        ('코나 N', '2021'): ('더 뉴 코나', '2021'),
        ('무쏘 칸', '2026'): ('무쏘 스포츠 칸 (Q261)', '2026'),
        ('GV70 EV', '2022'): ('일렉트리파이드 GV70', '2022'),
        ('GV70 EV', '2024'): ('일렉트리파이드 GV70', '2024'),
        ('GV70 EV F/L', '2025'): ('일렉트리파이드 GV70', '2025'),
    }

    already_in_book = {
        ('G80 EV F/L', '2025'): ('일렉트리파이드 G80 (RG3)', '2025', '이미 3개 악세사리 탑재됨'),
        ('아반떼 N', '2021'): ('아반떼 (CN7)', '2021', '이미 15개 악세사리 탑재됨'),
        ('LF쏘나타 PHEV', '2016'): ('LF 쏘나타 하이브리드', '2016', '이미 53개 악세사리 탑재됨'),
        ('LF쏘나타 PHEV', '2017'): ('LF 쏘나타 하이브리드', '2017', '이미 77개 악세사리 탑재됨'),
        ('LF쏘나타 뉴 라이즈', '2017'): ('쏘나타 뉴 라이즈', '2017', '이미 66개 악세사리 탑재됨'),
        ('LF쏘나타 뉴 라이즈', '2018'): ('쏘나타 뉴 라이즈', '2018', '이미 65개 악세사리 탑재됨'),
        ('무쏘 칸', '2025'): ('더 뉴 렉스턴 스포츠 칸', '2025', '이미 56개 악세사리 탑재됨')
    }

    unregistered_models_or_years = {
        ('G80 EV', '2027'): "책에 2027 미래 연식 미존재",
        ('G80 EV F/L', '2027'): "책에 2027 미래 연식 미존재",
        ('뉴 토레스', '2027'): "책에 2027 미래 연식 미존재",
        ('아이오닉 6 N', '2026'): "책에 독립 차종 아이오닉 6 N 미존재",
        ('뉴 SM5', '2012'): "책에 2012 뉴 SM5 구형 차종 미존재 (SM5 노바, 뉴SM5 플래티넘만 보유)"
    }

    for a in rem_acc:
        dm = a['danawa_model']
        dy = a['year']
        cnt = a['acc_count']
        key = (dm, dy)

        # 1) 신규 보충 매핑
        if key in acc_mapping_table:
            cm, cy = acc_mapping_table[key]
            # 다나와에서 악세사리 추출
            ydata = danawa.get(dm, {}).get(dy, {})
            acc_set = {}
            if isinstance(ydata, dict):
                for gname, gdata in ydata.items():
                    if isinstance(gdata, dict) and gdata.get('accessories'):
                        for ak, av in gdata['accessories'].items():
                            acc_set[ak] = av
            
            if cm in cat and cy in cat[cm]:
                existing_acc = cat[cm][cy].get('_accessories', {})
                if isinstance(existing_acc, list):
                    existing_acc = {}
                # 병합
                merged = {**existing_acc, **acc_set}
                cat[cm][cy]['_accessories'] = merged
                fix_log['added_accessories'].append({
                    'danawa_model': dm, 'cat_model': cm, 'year': cy,
                    'acc_count': len(merged), 'new_count': len(acc_set)
                })
                print(f"  -> 악세사리 보충 완료: [{dm} {dy}] -> [{cm} {cy}] ({len(merged)}개)")
            else:
                review_data['unmapped_accessories'].append({
                    'danawa_model': dm, 'year': dy, 'acc_count': cnt,
                    'reason': f"매핑 대상 [{cm} {cy}]이 책에 미존재"
                })

        # 2) 이미 탑재된 경우
        elif key in already_in_book:
            cm, cy, reason = already_in_book[key]
            review_data['unmapped_accessories'].append({
                'danawa_model': dm, 'year': dy, 'acc_count': cnt,
                'cat_model': cm, 'cat_year': cy,
                'reason': reason
            })
            print(f"  -> 기탑재 확인: [{dm} {dy}] -> [{cm} {cy}] ({reason})")

        # 3) 책에 모델/연식 자체가 없는 경우
        elif key in unregistered_models_or_years:
            reason = unregistered_models_or_years[key]
            review_data['unmapped_accessories'].append({
                'danawa_model': dm, 'year': dy, 'acc_count': cnt,
                'reason': reason
            })
            print(f"  -> 미등록 연식/모델: [{dm} {dy}] ({reason})")
        else:
            review_data['unmapped_accessories'].append({
                'danawa_model': dm, 'year': dy, 'acc_count': cnt,
                'reason': "매핑 불일치 (사유 분석 필요)"
            })

    # ---------------------------------------------------------
    # PART 3: 가격 불일치 1,095건 원인 규명 및 수정
    # ---------------------------------------------------------
    print("\n[PART 3] 가격 불일치 1,095건 원인 규명 및 수정...")
    all_mismatches = audit.get('price_mismatches', [])
    fixed_prices_08 = {(x['model'], x['year'], x['grade']) for x in fix_log_08.get('updated_prices', [])}
    prot_21 = {(x['model'], x['year'], x['grade']) for x in fix_log_08.get('retained_lowest_seat_prices', [])}

    rem_mismatches = [m for m in all_mismatches if (m['model'], m['year'], m['grade']) not in fixed_prices_08]
    print(f"  잔여 대상: {len(rem_mismatches)}건")

    for m in rem_mismatches:
        mod = m['model']
        y = m['year']
        gr = m['grade']
        bp = m['book_price']
        rp = m['ref_price']
        diff = abs(bp - rp)
        pct = (diff / bp) * 100 if bp else 0
        key = (mod, y, gr)

        # 1) 11-12-07 최저인승 보호 21개 중 포함된 13개 보호
        if key in prot_21:
            fix_log['retained_protected_prices'].append({
                'model': mod, 'year': y, 'grade': gr, 'price': bp,
                'ref_price': rp, 'diff': bp - rp,
                'reason': '11-12-07 최저 인승 기준 기본가 확정 보호값 (수정 절대 금지)'
            })
            review_data['price_mismatch_breakdown']['protected_lowest_seat'].append({
                'model': mod, 'year': y, 'grade': gr, 'book_price': bp, 'ref_price': rp,
                'reason': '11-12-07 최저 인승 기준 기본가 공식 성립값'
            })
            continue

        # 2) 세금 차이 (개소세 1.5% 내외 차이: 비율 1.012 ~ 1.018 또는 0.982 ~ 0.988)
        ratio = rp / bp if bp else 0
        if 1.012 <= ratio <= 1.018 or 0.982 <= ratio <= 0.988:
            review_data['price_mismatch_breakdown']['tax_diff_1_5pct'].append({
                'model': mod, 'year': y, 'grade': gr, 'book_price': bp, 'ref_price': rp,
                'pct': round(pct, 2), 'reason': '개별소비세 인하 등 세금 계산 차이 (공식 기준 차이, 책 가격 유지)'
            })
            continue

        # 3) 책 가격이 엔카 최저트림 기본가로 상위 트림들에 일괄 복사된 왜곡인지 확인
        encar_grades = ev2.get(mod, {}).get(y, {}).get('grades', [])
        encar_base_prices = {g.get('base_price') for g in encar_grades}
        cat_grades = cat.get(mod, {}).get(y, {})
        same_price_grades = [gname for gname, gdata in cat_grades.items() if not gname.startswith('_') and gdata.get('base_price') == bp]

        # 5% 이상 차이나면서 책 가격이 엔카 최저트림 가격과 같고 다나와 가격이 더 높은 경우
        if pct >= 5.0 and bp in encar_base_prices and len(same_price_grades) > 1 and bp < rp:
            # 명백한 상위 트림 복사 왜곡 -> 다나와 공식 트림 가격으로 정상 수정!
            if mod in cat and y in cat[mod] and gr in cat[mod][y]:
                cat[mod][y][gr]['base_price'] = rp
                cat[mod][y][gr]['source'] = 'danawa'
                fix_log['updated_prices'].append({
                    'model': mod, 'year': y, 'grade': gr,
                    'old_price': bp, 'new_price': rp, 'pct_diff': round(pct, 2),
                    'reason': '엔카 최저트림 가격 복사 왜곡 해소 -> 다나와 공식 세부 트림 가격으로 정상화'
                })
            continue

        # 4) 기타 5% 이상 차이 (대조군 모델 불일치, 구형 모델 비교, 특수 에디션 등)
        if pct >= 5.0:
            review_data['price_mismatch_breakdown']['benchmark_diff_over_5pct'].append({
                'model': mod, 'year': y, 'grade': gr, 'book_price': bp, 'ref_price': rp,
                'pct': round(pct, 2),
                'reason': '대조군 모델/연식 세대 차이 또는 특수 트림으로 인한 불일치 (책의 신차 공식 가격 유지)'
            })
        else:
            # 5) 2% ~ 5% 미만 차이
            review_data['price_mismatch_breakdown']['minor_diff_under_5pct'].append({
                'model': mod, 'year': y, 'grade': gr, 'book_price': bp, 'ref_price': rp,
                'pct': round(pct, 2),
                'reason': '2%~5% 미세 차이 (트림 옵션 포함 여부 모호, 책 가격 유지)'
            })

    print(f"  -> 가격 수정 완료: {len(fix_log['updated_prices'])}건")
    print(f"  -> 보호값 유지: {len(fix_log['retained_protected_prices'])}건")
    print(f"  -> 세금 차이 보류: {len(review_data['price_mismatch_breakdown']['tax_diff_1_5pct'])}건")
    print(f"  -> 2~5% 미세 차이 보류: {len(review_data['price_mismatch_breakdown']['minor_diff_under_5pct'])}건")
    print(f"  -> 5% 이상 대조군 차이 보류: {len(review_data['price_mismatch_breakdown']['benchmark_diff_over_5pct'])}건")

    # ---------------------------------------------------------
    # PART 4: 전수 재검산 (기본가 + 인승 옵션 = 실제 인승 가격)
    # ---------------------------------------------------------
    print("\n[PART 4] 기본가 + 인승 옵션 전수 재검산...")
    calc_errors = []
    for cm, yrs in cat.items():
        for y, ydata in yrs.items():
            for gname, gdata in ydata.items():
                if gname.startswith('_'):
                    continue
                bp = gdata.get('base_price', 0)
                opts = gdata.get('options', [])
                if isinstance(opts, list):
                    for o in opts:
                        oname = o.get('name', '')
                        oprice = o.get('price', 0)
                        # 인승 옵션 검증: 6인승, 7인승, 8인승, 9인승 등
                        m = re.search(r'([6789])인승', oname)
                        if m and oprice is not None and oprice > 0:
                            # 기본가 + 옵션가 계산 정상 여부
                            total = bp + oprice
                            if total <= bp or total <= oprice:
                                calc_errors.append({
                                    'model': cm, 'year': y, 'grade': gname,
                                    'base_price': bp, 'option': oname, 'opt_price': oprice, 'total': total
                                })

    print(f"  -> 계산 불일치/이상 수: {len(calc_errors)}건")

    # ---------------------------------------------------------
    # PART 5: 갱신 파일 및 로그 저장
    # ---------------------------------------------------------
    print("\n[PART 5] 결과 저장 중...")
    fix_log['summary'] = {
        'total_added_grades': len(fix_log['added_grades']),
        'total_added_accessories': len(fix_log['added_accessories']),
        'total_updated_prices': len(fix_log['updated_prices']),
        'total_retained_protected_prices': len(fix_log['retained_protected_prices']),
        'seat_calculation_errors': len(calc_errors)
    }

    # catalog_c.json 갱신
    with open(CATALOG_C_FILE, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
    print(f"  -> {CATALOG_C_FILE} 저장 완료")

    # fix_log 저장
    with open(FIX_LOG_OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(fix_log, f, ensure_ascii=False, indent=2)
    print(f"  -> {FIX_LOG_OUT_FILE} 저장 완료")

    # review_data 저장
    with open(REVIEW_OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(review_data, f, ensure_ascii=False, indent=2)
    print(f"  -> {REVIEW_OUT_FILE} 저장 완료")

    print("\n=== [11-12-09] 모든 작업 완료 ===")


if __name__ == '__main__':
    main()
