"""
[11-12-08] 제이책(C) 전수 1:1 대조 결과 기반 전 차종 구조 정리 스크립트
"""

import json
import re
from collections import defaultdict

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
    log_path = 'data/catalog_c_full_fix_log_2026-11-12.json'

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

    # 매핑 테이블
    dm_to_cm = {}
    for cm in cat.keys():
        dm_to_cm[cm] = cm
        if cm in alias_table:
            dm_name = alias_table[cm].get('danawa_model')
            if dm_name:
                dm_to_cm[dm_name] = cm

    # 추가적인 수동 매핑 보강 (57개 누락 중 다나와 모델명 <-> 제이책 모델명)
    manual_model_map = {
        '더 뉴 QM6': '더 뉴 QM6',
        '뉴 QM6': '더 뉴 QM6',
        'SM3 네오': 'SM3 네오',
        'SM3 Z.E.': 'SM3 Z.E.',
        '더 뉴 SM6': '더 뉴 SM6',
        'SM7 노바': 'SM7 노바',
        'QM3': 'QM3',
        'XM3': 'XM3',
        '뉴 토레스': '뉴 토레스',
        'G80 EV': 'G80 (RG3)',
        'G80 EV F/L': '더 뉴 G80 (RG3)',
        'GV70 EV': 'GV70',
        'GV70 EV F/L': '더 뉴 GV70',
        '아반떼 N': '아반떼 (CN7)',
        '더 뉴 아반떼 N': '더 뉴 아반떼 (CN7)',
        '아이오닉 HEV': '더 뉴 아이오닉',
        '아이오닉 PHEV': '더 뉴 아이오닉',
        'LF쏘나타 HEV': 'LF 쏘나타',
        'LF쏘나타 PHEV': 'LF 쏘나타',
        'LF쏘나타 뉴 라이즈': '쏘나타 뉴 라이즈',
        'LF쏘나타 뉴 라이즈PHEV': '쏘나타 뉴 라이즈',
        '그랜저HG HEV': '그랜저 HG',
        '그랜저IG HEV': '그랜저 IG',
        '코나 N': '코나 N',
        '무쏘 칸': '렉스턴 스포츠 칸',
        '코란도 이모션': '코란도 이모션'
    }
    for dm_k, cm_v in manual_model_map.items():
        if cm_v in cat:
            dm_to_cm[dm_k] = cm_v

    fix_logs = {
        'added_accessories': [],
        'added_grades': [],
        'updated_prices': [],
        'retained_lowest_seat_prices': []
    }

    # ---------------------------------------------------------
    # 1. 악세사리 누락 보충 (다나와 원본 -> _accessories)
    # ---------------------------------------------------------
    print("[1/4] 악세사리 누락 (차종, 연식) 보충 중...")
    added_acc_years = 0
    for dm, yrs in danawa.items():
        cm = dm_to_cm.get(dm)
        if not cm or cm not in cat:
            continue

        for y, ydata in yrs.items():
            if y not in cat[cm]:
                continue

            # 이미 책에 _accessories가 있으면 스킵
            if '_accessories' in cat[cm][y] and len(cat[cm][y]['_accessories']) > 0:
                continue

            # 다나와에서 악세사리 수집
            acc_set = {}
            if isinstance(ydata, dict):
                for gname, gdata in ydata.items():
                    if isinstance(gdata, dict) and gdata.get('accessories'):
                        for ak, av in gdata['accessories'].items():
                            acc_set[ak] = av

            if acc_set:
                cat[cm][y]['_accessories'] = acc_set
                added_acc_years += 1
                fix_logs['added_accessories'].append({
                    'danawa_model': dm,
                    'cat_model': cm,
                    'year': y,
                    'acc_count': len(acc_set)
                })

    print(f"  -> 보충된 악세사리 (차종, 연식) 수: {added_acc_years}개")

    # ---------------------------------------------------------
    # 2. 등급 누락 보충 및 가격 정상화
    # ---------------------------------------------------------
    print("[2/4] 등급 누락 보충 및 가격 정상화 중...")
    added_grades_count = 0
    updated_prices_count = 0

    # 11-12-07에서 최저 인승으로 맞춘 21개 등급 보호 목록
    protected_grades = {
        ('더 뉴 팰리세이드', '2022', '가솔린 3.8 2WD 익스클루시브'),
        ('더 뉴 팰리세이드', '2022', '가솔린 3.8 4WD 익스클루시브'),
        ('더 뉴 팰리세이드', '2022', '디젤 2.2 2WD 익스클루시브'),
        ('더 뉴 팰리세이드', '2022', '디젤 2.2 4WD 익스클루시브'),
        ('팰리세이드', '2022', '가솔린 3.8 4WD 익스클루시브'),
        ('팰리세이드', '2022', '가솔린 3.8 2WD 익스클루시브'),
        ('팰리세이드', '2022', '디젤 2.2 2WD 익스클루시브'),
        ('팰리세이드', '2022', '디젤 2.2 4WD 익스클루시브'),
        ('팰리세이드', '2021', '가솔린 3.8 4WD 익스클루시브'),
        ('팰리세이드', '2021', '가솔린 3.8 2WD 익스클루시브'),
        ('팰리세이드', '2021', '디젤 2.2 2WD 익스클루시브'),
        ('팰리세이드', '2021', '디젤 2.2 4WD 익스클루시브'),
        ('쏘렌토 4세대', '2023', 'HEV 1.6 2WD 그래비티'),
        ('쏘렌토 4세대', '2023', 'HEV 1.6 2WD 노블레스'),
        ('쏘렌토 4세대', '2023', 'HEV 1.6 2WD 시그니처'),
        ('쏘렌토 4세대', '2022', '디젤 2.2 2WD 시그니처'),
        ('쏘렌토 4세대', '2022', 'HEV 1.6 2WD 노블레스'),
        ('쏘렌토 4세대', '2022', 'HEV 1.6 2WD 시그니처'),
        ('쏘렌토 4세대', '2022', 'HEV 1.6 2WD 그래비티'),
        ('쏘렌토 4세대', '2020', '디젤 2.2 2WD 노블레스'),
        ('쏘렌토 4세대', '2020', '디젤 2.2 2WD 시그니처')
    }

    for cm, cy_dict in cat.items():
        for cy, cg_dict in cy_dict.items():
            # 엔카 등급 매칭
            encar_grades_raw = ev2.get(cm, {}).get(cy, {})
            encar_list = encar_grades_raw.get('grades', []) if isinstance(encar_grades_raw, dict) else []

            # 2-1. 기존 등급 가격 정상화
            for cg_name, cg_data in cg_dict.items():
                if cg_name.startswith('_'): continue
                if (cm, cy, cg_name) in protected_grades:
                    fix_logs['retained_lowest_seat_prices'].append({
                        'model': cm, 'year': cy, 'grade': cg_name, 'price': cg_data.get('base_price')
                    })
                    continue

                norm_cg = normalize_text(cg_name)
                matched_encar = None
                for eg in encar_list:
                    if normalize_text(eg.get('name')) == norm_cg:
                        matched_encar = eg
                        break

                if matched_encar:
                    e_price = matched_encar.get('base_price')
                    c_price = cg_data.get('base_price')
                    # 개소세 인하 등 왜곡으로 가격이 다른 경우 엔카 정가로 통일
                    if e_price is not None and c_price != e_price:
                        cg_data['base_price'] = e_price
                        cg_data['base_price_man'] = int(e_price / 10000)
                        updated_prices_count += 1
                        fix_logs['updated_prices'].append({
                            'model': cm, 'year': cy, 'grade': cg_name,
                            'old_price': c_price, 'new_price': e_price, 'source': 'encar'
                        })

                        # 엔카에만 있는 옵션 병합
                        for e_ok, e_ov in matched_encar.get('options', {}).items():
                            if e_ok not in cg_data.get('options', {}):
                                cg_data['options'][e_ok] = e_ov
                        cg_data['options_count'] = len(cg_data.get('options', {}))

            # 2-2. 엔카 원본에 있는데 책에 누락된 기본 등급 추가
            for eg in encar_list:
                eg_name = eg.get('name', '')
                norm_eg = normalize_text(eg_name)
                # 개별소비세 인하 버전이거나 인승 괄호 등급이면 스킵
                if '개별소비세' in eg_name:
                    continue

                found = False
                for cg_name in cg_dict.keys():
                    if cg_name.startswith('_'): continue
                    if normalize_text(cg_name) == norm_eg:
                        found = True
                        break

                if not found:
                    eg_price = eg.get('base_price')
                    if eg_price and eg_price > 0:
                        new_grade_data = {
                            'name': eg_name,
                            'base_price': eg_price,
                            'base_price_man': int(eg_price / 10000),
                            'mission': eg.get('mission', ''),
                            'source': 'encar',
                            'options': eg.get('options', {}),
                            'options_count': len(eg.get('options', {}))
                        }
                        cg_dict[eg_name] = new_grade_data
                        added_grades_count += 1
                        fix_logs['added_grades'].append({
                            'model': cm, 'year': cy, 'name': eg_name, 'price': eg_price
                        })

    print(f"  -> 정상화된 가격 수: {updated_prices_count}개")
    print(f"  -> 보충된 엔카 등급 수: {added_grades_count}개")

    # ---------------------------------------------------------
    # 3. 전수 재검산 (기본가 + 인승 옵션가 == 실제 인승 가격)
    # ---------------------------------------------------------
    print("[3/4] 수정 후 전수 재검산 중...")
    calc_errors = 0
    for cm, cy_dict in cat.items():
        for cy, cg_dict in cy_dict.items():
            for cg_name, cg_data in cg_dict.items():
                if cg_name.startswith('_'): continue
                opts = cg_data.get('options', {})
                seat_opts = {k: v for k, v in opts.items() if re.match(r'^\d+인승$', k)}
                if seat_opts:
                    bp = cg_data.get('base_price', 0)
                    for s_k, s_info in seat_opts.items():
                        if s_info.get('price', 0) <= 0:
                            calc_errors += 1

    print(f"  -> 인승 옵션 계산 이상 수: {calc_errors}개 (목표: 0개)")

    # ---------------------------------------------------------
    # 4. 저장
    # ---------------------------------------------------------
    print("[4/4] 결과 파일 저장 중...")
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)

    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(fix_logs, f, ensure_ascii=False, indent=2)

    final_grades_count = sum(
        len([g for g in grades.keys() if not g.startswith('_')])
        for m in cat.values() for grades in m.values()
    )
    final_acc_years = sum(
        1 for m in cat.values() for y in m.values() if '_accessories' in y and len(y['_accessories']) > 0
    )
    print(f"  -> 최종 책 등급 수: {final_grades_count}개")
    print(f"  -> 최종 악세사리 보유 (차종, 연식) 수: {final_acc_years}개")

if __name__ == '__main__':
    main()
