"""
[11-12-06] 제이책(C) 중복 등급 수정 — SUV 136쌍 단일화 + 스타렉스 13쌍 인승 라벨 부여
"""

import json
import re
import shutil
from collections import defaultdict

def main():
    catalog_path = 'data/catalog_c.json'
    backup_path = 'data/catalog_c_v12_backup_2026-11-12.json'
    diagnosis_path = 'data/catalog_c_duplicate_diagnosis_2026-11-12.json'
    encar_path = 'data/encar_newcar_catalog_v2.json'
    log_path = 'data/catalog_c_duplicate_resolve_log_2026-11-12.json'
    review_path = 'data/catalog_c_duplicate_resolve_review_2026-11-12.json'

    # 1. 작업 전 백업
    print(f"[1/6] 작업 전 백업 생성: {backup_path}")
    shutil.copyfile(catalog_path, backup_path)
    print("  -> 백업 완료.")

    # 2. 데이터 로드
    print("[2/6] 원천 데이터 로드 중...")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        cat = json.load(f)

    with open(diagnosis_path, 'r', encoding='utf-8') as f:
        diag = json.load(f)

    with open(encar_path, 'r', encoding='utf-8') as f:
        ev2 = json.load(f)

    initial_grades_count = sum(
        len([g for g in grades.keys() if not g.startswith('_')])
        for m in cat.values() for grades in m.values()
    )
    print(f"  -> 초기 책 전체 등급 수: {initial_grades_count}개")

    resolve_logs = []
    review_logs = []

    # 3. 부류 B: 더 뉴 그랜드 스타렉스 13쌍 인승 라벨 부여
    print("[3/6] 부류 B (스타렉스 RV 13쌍) 인승 라벨 부여 중...")
    starex_label_map = {
        # 2018년형
        ('2018', '디젤 2.5 2WD 스타일 (M/T)'): '디젤 2.5 2WD 스타일(11인승) (M/T)',
        ('2018', '디젤 2.5 2WD 스타일'): '디젤 2.5 2WD 스타일(11인승)',
        ('2018', '디젤 2.5 2WD 스마트 (M/T)'): '디젤 2.5 2WD 스마트(11인승) (M/T)',
        ('2018', '디젤 2.5 2WD 스마트'): '디젤 2.5 2WD 스마트(11인승)',
        ('2018', '디젤 2.5 2WD 모던'): '디젤 2.5 2WD 모던(11인승)',
        ('2018', '디젤 2.5 2WD 익스클루시브'): '디젤 2.5 2WD 어반 익스클루시브(9인승)',
        # 2020년형
        ('2020', '디젤 2.5 2WD 스타일 (M/T)'): '디젤 2.5 2WD 스타일(11인승) (M/T)',
        ('2020', '디젤 2.5 2WD 스타일'): '디젤 2.5 2WD 스타일(11인승)',
        ('2020', '디젤 2.5 2WD 스마트 (M/T)'): '디젤 2.5 2WD 스마트(11인승) (M/T)',
        ('2020', '디젤 2.5 2WD 스마트'): '디젤 2.5 2WD 스마트(11인승)',
        ('2020', '디젤 2.5 2WD 모던'): '디젤 2.5 2WD 모던(11인승)',
        ('2020', '디젤 2.5 2WD 익스클루시브'): '디젤 2.5 2WD 어반 익스클루시브(9인승)',
        ('2020', '디젤 2.5 4WD 익스클루시브'): '디젤 2.5 4WD 어반 익스클루시브(9인승)',
    }

    starex_relabeled_count = 0
    starex_data = cat.get('더 뉴 그랜드 스타렉스', {})
    for (year, old_name), new_name in starex_label_map.items():
        if year in starex_data and old_name in starex_data[year]:
            gdata = starex_data[year].pop(old_name)
            gdata['name'] = new_name
            starex_data[year][new_name] = gdata
            starex_relabeled_count += 1
            resolve_logs.append({
                'type': 'B_relabel',
                'model': '더 뉴 그랜드 스타렉스',
                'year': year,
                'old_name': old_name,
                'new_name': new_name,
                'base_price': gdata.get('base_price')
            })

    print(f"  -> 스타렉스 인승 라벨 부여 완료: {starex_relabeled_count}/13건")

    # 4. 맥스크루즈 특별 처리 (4쌍)
    print("[4/6] 맥스크루즈 특별 정상화 처리 중...")
    maxcruz_fixed_count = 0
    mc_data = cat.get('맥스크루즈', {})

    # 2014년형 & 2013년형
    for year in ['2014', '2013']:
        if year not in mc_data:
            continue
        y_grades = mc_data[year]

        # 2WD & 4WD
        drivetrains = [
            ('2WD', '34580000' if year == '2014' else '35000000', '38730000' if year == '2014' else '39200000'),
            ('4WD', '36700000' if year == '2014' else '37150000', '40850000' if year == '2014' else '41350000')
        ]

        for dt, exc_price_str, spc_price_str in drivetrains:
            exc_target_price = int(exc_price_str)
            spc_target_price = int(spc_price_str)

            exc_base_name = f"디젤 2.2 {dt} Exclusive"
            spc_base_name = f"디젤 2.2 {dt} Special"

            # 기존 등급들 탐색
            seat_6 = f"{exc_base_name}(6인승)"
            seat_7 = f"{exc_base_name}(7인승)"
            spc_seat_7 = f"{spc_base_name}(7인승)"

            # 1) Exclusive 단일화
            exc_gdata = None
            if seat_6 in y_grades:
                exc_gdata = y_grades.pop(seat_6)
            elif exc_base_name in y_grades:
                exc_gdata = dict(y_grades[exc_base_name])

            if exc_gdata is not None:
                exc_gdata['name'] = exc_base_name
                exc_gdata['base_price'] = exc_target_price
                exc_gdata['base_price_man'] = int(exc_target_price / 10000)
                exc_opts = dict(exc_gdata.get('options', {}))
                exc_opts['7인승'] = {
                    'price': 200000,
                    'price_man': 20,
                    'kind': 'optional',
                    'desc': '7인승(러기지 스크린 포함)',
                    'source': 'encar'
                }
                # 7인승 등급 옵션 병합
                if seat_7 in y_grades:
                    for ok, ov in y_grades.pop(seat_7).get('options', {}).items():
                        if ok not in exc_opts:
                            exc_opts[ok] = ov
                exc_gdata['options'] = exc_opts
                exc_gdata['options_count'] = len(exc_opts)
                y_grades[exc_base_name] = exc_gdata

            # 2) Special 정상화
            spc_gdata = None
            # 오기된 무표기 Exclusive에서 데이터 복사
            if exc_base_name in y_grades and y_grades[exc_base_name].get('base_price') == spc_target_price:
                # 무표기 Exclusive가 상위트림 오기였던 경우
                spc_gdata = y_grades.pop(exc_base_name)
            elif spc_base_name in y_grades:
                spc_gdata = y_grades.pop(spc_base_name)

            if spc_gdata is not None:
                spc_gdata['name'] = spc_base_name
                spc_gdata['base_price'] = spc_target_price
                spc_gdata['base_price_man'] = int(spc_target_price / 10000)
                spc_opts = dict(spc_gdata.get('options', {}))
                spc_opts['7인승'] = {
                    'price': 200000,
                    'price_man': 20,
                    'kind': 'optional',
                    'desc': '7인승(러기지 스크린 포함)',
                    'source': 'encar'
                }
                if spc_seat_7 in y_grades:
                    for ok, ov in y_grades.pop(spc_seat_7).get('options', {}).items():
                        if ok not in spc_opts:
                            spc_opts[ok] = ov
                spc_gdata['options'] = spc_opts
                spc_gdata['options_count'] = len(spc_opts)
                y_grades[spc_base_name] = spc_gdata

            maxcruz_fixed_count += 1
            resolve_logs.append({
                'type': 'A_maxcruz_fixed',
                'model': '맥스크루즈',
                'year': year,
                'drivetrain': dt,
                'exclusive_price': exc_target_price,
                'special_price': spc_target_price
            })

    print(f"  -> 맥스크루즈 4쌍 정상화 완료: {maxcruz_fixed_count}쌍")

    # 5. 부류 A 일반 처리 (쏘렌토 4세대, 팰리세이드, 더 뉴 팰리세이드 총 132쌍)
    print("[5/6] 부류 A (SUV 132쌍) 단일화 처리 중...")
    suv_resolved_count = 0

    suv_items = [d for d in diag if d['category'] == 'A' and d['model'] != '맥스크루즈']

    for item in suv_items:
        m = item['model']
        y = item['year']
        base_name = item['base_grade']
        seat_names = list(item.get('seat_items', {}).keys())

        if m not in cat or y not in cat[m]:
            review_logs.append({'reason': '모델/연식 미존재', 'item': item})
            continue

        y_grades = cat[m][y]
        if base_name not in y_grades:
            # 이미 합쳐졌거나 없을 때
            continue

        # 1) 기준 등급 데이터
        base_gdata = y_grades[base_name]
        new_opts = dict(base_gdata.get('options', {}))

        # 2) 각 인승 등급 수집 및 인승 번호 추출
        seat_gdata_list = []
        for sname in seat_names:
            if sname in y_grades:
                seat_gdata_list.append((sname, y_grades.pop(sname)))

        if not seat_gdata_list:
            continue

        seat_dict = {}
        for sname, sdata in seat_gdata_list:
            m_s = re.search(r'\((\d+)인승\)', sname)
            if m_s:
                s_num = int(m_s.group(1))
                seat_dict[s_num] = (sname, sdata)

        if not seat_dict:
            continue

        # 3) 기준 기본가 결정
        # 무표기 등급에 이미 기본가가 존재하면 기존의 검증된 정가를 우선 유지
        # 없거나 0인 경우에만 다나와 최저 인승(5인승 또는 8인승) 가격 사용
        existing_base_price = base_gdata.get('base_price')
        if existing_base_price and existing_base_price > 0:
            ref_base_price = existing_base_price
        else:
            if 5 in seat_dict:
                target_seat = 5
            elif 8 in seat_dict:
                target_seat = 8
            else:
                target_seat = min(seat_dict.keys())
            ref_base_price = seat_dict[target_seat][1].get('base_price', 0)

        # 대표 등급 기본가 확정
        base_gdata['base_price'] = ref_base_price
        base_gdata['base_price_man'] = int(ref_base_price / 10000)

        # 4) 인승 옵션화
        # 다나와 인승별 차액 또는 엔카 옵션가 계산
        # 베이스 인승(5인승 또는 8인승, 없으면 최저 인승)
        base_seat_num = 5 if 5 in seat_dict else (8 if 8 in seat_dict else min(seat_dict.keys()))
        base_seat_price = seat_dict[base_seat_num][1].get('base_price', ref_base_price)

        seat_opts_added = {}
        for s_num, (sname, sdata) in sorted(seat_dict.items()):
            if s_num == base_seat_num:
                continue
            diff = sdata.get('base_price', 0) - base_seat_price
            if diff > 0:
                opt_key = f"{s_num}인승"
                new_opts[opt_key] = {
                    'price': diff,
                    'price_man': int(diff / 10000),
                    'kind': 'optional',
                    'desc': f"{s_num}인승 시트 패키지",
                    'source': 'seat_restructure'
                }
                seat_opts_added[opt_key] = diff

            # 일반 옵션 병합
            for ok, ov in sdata.get('options', {}).items():
                if ok not in new_opts and not re.match(r'^\d+인승$', ok):
                    new_opts[ok] = ov

        base_gdata['options'] = new_opts
        base_gdata['options_count'] = len(new_opts)
        y_grades[base_name] = base_gdata

        suv_resolved_count += 1
        resolve_logs.append({
            'type': 'A_suv_resolved',
            'model': m,
            'year': y,
            'grade': base_name,
            'base_price': ref_base_price,
            'merged_seats': list(seat_dict.keys()),
            'seat_options': seat_opts_added
        })

    print(f"  -> 부류 A 일반 SUV 해소 완료: {suv_resolved_count}/132쌍")

    # 6. 동일 가격 터보 등급 정리 (규칙 4)
    print("[6/6] 동일 가격 '가솔린 터보' 중복 등급 정리 중...")
    turbo_merged_count = 0
    for m, yrs in cat.items():
        for y, grades in yrs.items():
            to_delete = []
            for gname, gdata in list(grades.items()):
                if gname.startswith('_'): continue
                if '가솔린 터보' in gname:
                    simplified = gname.replace('가솔린 터보', '가솔린')
                    if simplified in grades:
                        sim_data = grades[simplified]
                        if gdata.get('base_price') == sim_data.get('base_price'):
                            # 옵션 병합 후 '가솔린 터보' 삭제
                            for ok, ov in gdata.get('options', {}).items():
                                if ok not in sim_data.get('options', {}):
                                    sim_data['options'][ok] = ov
                            sim_data['options_count'] = len(sim_data['options'])
                            to_delete.append((gname, simplified, gdata.get('base_price')))

            for del_name, keep_name, prc in to_delete:
                del grades[del_name]
                turbo_merged_count += 1
                resolve_logs.append({
                    'type': 'turbo_merged',
                    'model': m,
                    'year': y,
                    'deleted': del_name,
                    'kept': keep_name,
                    'base_price': prc
                })

    print(f"  -> 동일 가격 터보 등급 정리 완료: {turbo_merged_count}건")

    # 최종 집계 및 파일 저장
    final_grades_count = sum(
        len([g for g in grades.keys() if not g.startswith('_')])
        for m in cat.values() for grades in m.values()
    )
    print("\n=== 최종 처리 결과 ===")
    print(f"작업 전 등급 수: {initial_grades_count}개")
    print(f"작업 후 등급 수: {final_grades_count}개")
    print(f"감소된 등급 수: {initial_grades_count - final_grades_count}개")
    print(f"해소된 부류 A 쌍: {suv_resolved_count + maxcruz_fixed_count}/136쌍")
    print(f"라벨 부여된 부류 B 쌍: {starex_relabeled_count}/13쌍")
    print(f"검토 목록 잔여 수: {len(review_logs)}건")

    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)

    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(resolve_logs, f, ensure_ascii=False, indent=2)

    with open(review_path, 'w', encoding='utf-8') as f:
        json.dump(review_logs, f, ensure_ascii=False, indent=2)

    print("모든 산출물 저장 완료.")

if __name__ == '__main__':
    main()
