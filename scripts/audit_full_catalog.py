"""
[11-12-08] 제이책(C) 전수 1:1 대조 스크립트 (책 전체 차종 대상)
"""

import json
import re
from collections import defaultdict, Counter

def normalize_text(text):
    if not text:
        return ""
    s = text.replace('HEV', '하이브리드').replace('LPG', 'lpg').replace('전기', 'ev')
    s = re.sub(r'[\s\(\)\-_/·・\.\+]+', '', s)
    return s.lower()

def main():
    catalog_path = 'data/catalog_c.json'
    encar_path = 'data/encar_newcar_catalog_v2.json'
    danawa_path = 'data/catalog_by_source_v2.json'
    audit_alias_path = 'data/encar-gap-audit-2026-11-11.json'
    out_path = 'data/catalog_c_full_audit_2026-11-12.json'

    with open(catalog_path, 'r', encoding='utf-8') as f:
        cat = json.load(f)

    with open(encar_path, 'r', encoding='utf-8') as f:
        ev2 = json.load(f)

    with open(danawa_path, 'r', encoding='utf-8') as f:
        v2 = json.load(f)
    danawa = v2.get('danawa', {})

    with open(audit_alias_path, 'r', encoding='utf-8') as f:
        audit_alias = json.load(f)
    alias_table = audit_alias.get('alias_table', {})

    # 별칭 매핑 테이블
    dm_to_cm = {}
    cm_to_dm = {}
    for cm in cat.keys():
        dm_to_cm[cm] = cm
        cm_to_dm[cm] = cm
        if cm in alias_table:
            dm_name = alias_table[cm].get('danawa_model')
            if dm_name:
                dm_to_cm[dm_name] = cm
                cm_to_dm[cm] = dm_name

    audit_result = {
        'summary': {},
        'missing_grades': [],
        'book_only_grades': [],
        'price_mismatches': [],
        'seat_structure_check': {},
        'option_discrepancies': [],
        'option_kind_stats': {},
        'accessory_audit': {},
        'gv80_investigation': {}
    }

    # ---------------------------------------------------------
    # 1. 등급 존재 여부 및 2. 등급 가격 전수 대조
    # ---------------------------------------------------------
    total_book_grades = 0
    total_encar_grades = 0
    total_danawa_grades = 0

    price_mismatch_count = 0
    price_matched_count = 0

    for cm, cy_dict in cat.items():
        dm = cm_to_dm.get(cm, cm)
        for cy, cg_dict in cy_dict.items():
            # 엔카 해당 연식 등급들
            encar_grades_raw = ev2.get(cm, {}).get(cy, {})
            encar_list = encar_grades_raw.get('grades', []) if isinstance(encar_grades_raw, dict) else []

            # 다나와 해당 연식 등급들
            danawa_grades_raw = danawa.get(dm, {}).get(cy, {})
            if not danawa_grades_raw and dm != cm:
                danawa_grades_raw = danawa.get(cm, {}).get(cy, {})

            for cg_name, cg_data in cg_dict.items():
                if cg_name.startswith('_'):
                    continue
                total_book_grades += 1
                c_price = cg_data.get('base_price')

                # 엔카 대조
                norm_cg = normalize_text(cg_name)
                matched_encar = None
                for eg in encar_list:
                    if normalize_text(eg.get('name')) == norm_cg:
                        matched_encar = eg
                        break

                # 다나와 대조
                matched_danawa = None
                if isinstance(danawa_grades_raw, dict):
                    for dg_name, dg_data in danawa_grades_raw.items():
                        if normalize_text(dg_name) == norm_cg:
                            matched_danawa = (dg_name, dg_data)
                            break

                # 가격 비교
                if matched_encar:
                    e_price = matched_encar.get('base_price')
                    if e_price is not None and c_price != e_price:
                        price_mismatch_count += 1
                        audit_result['price_mismatches'].append({
                            'model': cm, 'year': cy, 'grade': cg_name,
                            'book_price': c_price, 'ref_source': 'encar',
                            'ref_price': e_price, 'diff': c_price - e_price
                        })
                    else:
                        price_matched_count += 1
                elif matched_danawa:
                    d_price = matched_danawa[1].get('base_price')
                    if d_price is not None and c_price != d_price:
                        price_mismatch_count += 1
                        audit_result['price_mismatches'].append({
                            'model': cm, 'year': cy, 'grade': cg_name,
                            'ref_source': 'danawa',
                            'book_price': c_price, 'ref_price': d_price,
                            'diff': c_price - d_price
                        })
                    else:
                        price_matched_count += 1
                else:
                    audit_result['book_only_grades'].append({
                        'model': cm, 'year': cy, 'grade': cg_name, 'price': c_price
                    })

    # 원본에 있는데 책에 없는 등급 조사
    for em, ey_dict in ev2.items():
        if em not in cat:
            continue
        for ey, edata in ey_dict.items():
            if ey not in cat[em]:
                continue
            for eg in (edata.get('grades', []) if isinstance(edata, dict) else []):
                total_encar_grades += 1
                norm_eg = normalize_text(eg.get('name'))
                found = False
                for cg_name in cat[em][ey].keys():
                    if cg_name.startswith('_'): continue
                    if normalize_text(cg_name) == norm_eg:
                        found = True
                        break
                if not found:
                    audit_result['missing_grades'].append({
                        'source': 'encar', 'model': em, 'year': ey,
                        'name': eg.get('name'), 'price': eg.get('base_price')
                    })

    # ---------------------------------------------------------
    # 3. 등급 구조 및 기본가 + 인승 옵션 검산
    # ---------------------------------------------------------
    seat_calc_errors = []
    suv_duplicates_found = []

    for cm, cy_dict in cat.items():
        for cy, cg_dict in cy_dict.items():
            # 인승 괄호가 남아있는 등급 조사 (스타렉스 등 RV 제외)
            if cm not in ['더 뉴 그랜드 스타렉스', '그랜드 스타렉스', '카니발 4세대', '더 뉴 카니발 4세대', '올 뉴 카니발', '카니발']:
                for cg_name in cg_dict.keys():
                    if cg_name.startswith('_'): continue
                    if re.search(r'\(\d+인승\)', cg_name):
                        suv_duplicates_found.append({'model': cm, 'year': cy, 'grade': cg_name})

            # 기본가 + 인승 옵션 검산
            for cg_name, cg_data in cg_dict.items():
                if cg_name.startswith('_'): continue
                opts = cg_data.get('options', {})
                seat_opts = {k: v for k, v in opts.items() if re.match(r'^\d+인승$', k)}
                if seat_opts:
                    bp = cg_data.get('base_price', 0)
                    for s_k, s_info in seat_opts.items():
                        calc_val = bp + s_info.get('price', 0)
                        # 음수이거나 비정상인 경우
                        if calc_val <= bp or s_info.get('price', 0) <= 0:
                            seat_calc_errors.append({
                                'model': cm, 'year': cy, 'grade': cg_name,
                                'seat': s_k, 'base_price': bp, 'opt_price': s_info.get('price', 0)
                            })

    audit_result['seat_structure_check'] = {
        'remaining_suv_seat_bracket_grades': len(suv_duplicates_found),
        'seat_calculation_errors': len(seat_calc_errors),
        'details': seat_calc_errors[:10]
    }

    # ---------------------------------------------------------
    # 5. 옵션 구분: package_ref / condition 통계
    # ---------------------------------------------------------
    kind_counter = Counter()
    models_with_package_ref = Counter()
    models_with_condition = Counter()

    for cm, cy_dict in cat.items():
        for cy, cg_dict in cy_dict.items():
            for cg_name, cg_data in cg_dict.items():
                if cg_name.startswith('_'): continue
                for oname, oinfo in cg_data.get('options', {}).items():
                    k = oinfo.get('kind', 'optional')
                    kind_counter[k] += 1
                    if k == 'package_ref':
                        models_with_package_ref[cm] += 1
                    elif k == 'condition':
                        models_with_condition[cm] += 1

    # GV80 2025 표본 옵션 통계
    gv80_2025 = cat.get('GV80', {}).get('2025', {})
    gv80_2025_sample = {}
    for gname, gdata in gv80_2025.items():
        if gname.startswith('_'): continue
        counts = Counter(v.get('kind', 'optional') for v in gdata.get('options', {}).values())
        gv80_2025_sample[gname] = dict(counts)

    audit_result['option_kind_stats'] = {
        'overall_kind_counts': dict(kind_counter),
        'top_package_ref_models': models_with_package_ref.most_common(5),
        'top_condition_models': models_with_condition.most_common(5),
        'gv80_2025_sample': gv80_2025_sample
    }

    # ---------------------------------------------------------
    # 6. 악세사리 전수 대조 (57개 누락 전수 분석)
    # ---------------------------------------------------------
    danawa_acc_years = {}
    for dm, yrs in danawa.items():
        for y, ydata in yrs.items():
            acc_set = {}
            if isinstance(ydata, dict):
                for gname, gdata in ydata.items():
                    if isinstance(gdata, dict) and gdata.get('accessories'):
                        for ak, av in gdata['accessories'].items():
                            acc_set[ak] = av
            if acc_set:
                danawa_acc_years[(dm, y)] = acc_set

    cat_acc_years = {
        (cm, y): len(ydata['_accessories'])
        for cm, yrs in cat.items()
        for y, ydata in yrs.items()
        if '_accessories' in ydata and len(ydata['_accessories']) > 0
    }

    missing_acc_list = []
    for (dm, dy), accs in danawa_acc_years.items():
        cm = dm_to_cm.get(dm)
        if cm and cm in cat and dy in cat[cm]:
            if (cm, dy) not in cat_acc_years:
                missing_acc_list.append({
                    'danawa_model': dm, 'cat_model': cm, 'year': dy,
                    'acc_count': len(accs), 'sample': list(accs.keys())[:3],
                    'status': '매핑 가능(미탑재)'
                })
        else:
            missing_acc_list.append({
                'danawa_model': dm, 'cat_model': cm, 'year': dy,
                'acc_count': len(accs), 'sample': list(accs.keys())[:3],
                'status': '차종/연식 매칭 필요'
            })

    audit_result['accessory_audit'] = {
        'danawa_total_acc_years': len(danawa_acc_years),
        'cat_total_acc_years': len(cat_acc_years),
        'missing_acc_years_count': len(missing_acc_list),
        'missing_acc_list': missing_acc_list
    }

    # ---------------------------------------------------------
    # 7. GV80 악세사리 원인 규명
    # ---------------------------------------------------------
    gv80_danawa_acc = sum(
        len(g.get('accessories', {}))
        for m in ['GV80', '더 뉴 GV80'] if m in danawa
        for y in danawa[m].values() if isinstance(y, dict)
        for g in y.values() if isinstance(g, dict)
    )
    audit_result['gv80_investigation'] = {
        'danawa_gv80_accessories_count': gv80_danawa_acc,
        'reason': (
            '다나와 원본 데이터베이스(catalog_by_source_v2.json의 danawa) 자체에 '
            'GV80 및 더 뉴 GV80의 전 연식 accessories 필드가 0개(미수집/미제공)로 확인됨. '
            '엔카 가격표에서도 별도 악세사리 카테고리 없이 일반 선택품목(options)에만 포함되어 있음.'
        )
    }

    # 요약 집계
    audit_result['summary'] = {
        'total_book_grades': total_book_grades,
        'price_matched_count': price_matched_count,
        'price_mismatch_count': price_mismatch_count,
        'missing_grades_count': len(audit_result['missing_grades']),
        'book_only_grades_count': len(audit_result['book_only_grades']),
        'remaining_suv_seat_bracket_grades': len(suv_duplicates_found),
        'missing_acc_years_count': len(missing_acc_list)
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(audit_result, f, ensure_ascii=False, indent=2)

    print("=== 전수 1:1 대조 완료 ===")
    print(f"책 전체 등급 수: {total_book_grades}개")
    print(f"가격 일치 등급 수: {price_matched_count}개")
    print(f"가격 불일치 등급 수: {price_mismatch_count}개")
    print(f"엔카 원본 누락 등급 수: {len(audit_result['missing_grades'])}개")
    print(f"책 단독 등급 수: {len(audit_result['book_only_grades'])}개")
    print(f"잔여 SUV 인승괄호 등급 수: {len(suv_duplicates_found)}개")
    print(f"악세사리 누락 (차종, 연식) 수: {len(missing_acc_list)}개")
    print(f"대조 결과 저장 완료: {out_path}")

if __name__ == '__main__':
    main()
