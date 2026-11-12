"""
[11-12-04] 제이책(C) 등급을 엔카처럼 — 인승을 등급에서 빼고 옵션으로 + 다나와 순정 악세사리 추가 (책 전체)
"""

import json
import re
import shutil
from collections import defaultdict

def main():
    catalog_path = 'data/catalog_c.json'
    backup_path = 'data/catalog_c_v10_backup_2026-11-12.json'
    v2_path = 'data/catalog_by_source_v2.json'
    audit_path = 'data/encar-gap-audit-2026-11-11.json'
    log_path = 'data/catalog_c_seat_restructure_log_2026-11-12.json'
    review_path = 'data/catalog_c_seat_restructure_review_2026-11-12.json'

    # 1. 작업 전 백업
    print(f"[1/6] 백업 생성 중: {backup_path}")
    shutil.copyfile(catalog_path, backup_path)
    print("  -> 백업 완료.")

    # 2. 데이터 로드
    print("[2/6] 원천 데이터 로드 중...")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        cat = json.load(f)

    with open(v2_path, 'r', encoding='utf-8') as f:
        v2 = json.load(f)
    danawa = v2.get('danawa', {})

    with open(audit_path, 'r', encoding='utf-8') as f:
        audit = json.load(f)
    alias_table = audit.get('alias_table', {})
    print("  -> 로드 완료.")

    # 헬퍼 함수
    def norm_for_acc_match(name):
        s = name.replace('HEV', '하이브리드').replace('LPG', 'lpg').replace('전기', 'ev')
        s = re.sub(r'(\d+\.\d+)T', r'\1', s)
        s = re.sub(r'\(?\d+인승\)?', '', s)
        s = re.sub(r'[\s\(\)\-_]+', '', s)
        return s.lower()

    def extract_seat_num(name):
        m = re.search(r'\((\d+)인승\)', name)
        if m:
            return int(m.group(1))
        return None

    def remove_seat_str(name):
        s = re.sub(r'\s*\(\s*\d+인승\s*\)', '', name)
        return s.strip()

    # 3. 책 전체 재구성
    print("[3/6] 책 전체 인승 재구성 및 악세사리 결합 실행 중...")
    total_original_grades = 0
    seat_groups_count = 0
    acc_attached_grades = 0
    total_acc_count = 0

    new_cat = {}
    review_list = []
    log_list = []

    for m, yrs in cat.items():
        new_cat[m] = {}
        
        # 다나와 차종명 후보군 (alias_table 활용)
        danawa_m_names = [m]
        if m in alias_table:
            dm = alias_table[m].get('danawa_model')
            if dm and dm != m:
                danawa_m_names.append(dm)

        for y, grades in yrs.items():
            new_cat[m][y] = {}
            total_original_grades += len(grades)

            # 해당 연식의 다나와 매칭 딕셔너리 수집
            danawa_y_dicts = []
            for dm in danawa_m_names:
                if dm in danawa and y in danawa[dm]:
                    danawa_y_dicts.append(danawa[dm][y])

            # 3-1. 괄호 인승 등급과 비인승 등급 분리
            seat_groups = defaultdict(list)
            non_seat_grades = {}

            for gname, gdata in grades.items():
                seat_num = extract_seat_num(gname)
                if seat_num is not None:
                    base_name = remove_seat_str(gname)
                    seat_groups[base_name].append((seat_num, gname, gdata))
                else:
                    non_seat_grades[gname] = gdata

            # 3-2. 인승 그룹 병합
            for base_name, items in seat_groups.items():
                # 인승 제거 시 기존 비인승 등급명과 충돌하는 경우 (보존 후 review 기록)
                if base_name in non_seat_grades:
                    review_list.append({
                        "model": m, "year": y, "grade": base_name,
                        "conflict_with_original": True,
                        "items": [oname for _, oname, _ in items],
                        "reason": "인승 표기 제거 시 기존 비인승 등급명과 충돌하여 개별 보존함"
                    })
                    for snum, oname, odata in items:
                        # 악세사리 탐색 후 보존
                        acc_found = {}
                        norm_target = norm_for_acc_match(oname)
                        for dy in danawa_y_dicts:
                            for dk, dv in dy.items():
                                if norm_for_acc_match(dk) == norm_target and dv.get('accessories'):
                                    for ak, av in dv['accessories'].items():
                                        acc_found[ak] = av
                        odata_copy = dict(odata)
                        if acc_found:
                            odata_copy['accessories'] = acc_found
                            acc_attached_grades += 1
                            total_acc_count += len(acc_found)
                        new_cat[m][y][oname] = odata_copy
                    continue

                seat_groups_count += 1
                items_by_seat = {snum: (oname, odata) for snum, oname, odata in items}

                # 5인승 우선, 없으면 최저 인승 기준
                base_seat = 5 if 5 in items_by_seat else min(items_by_seat.keys())
                base_oname, base_odata = items_by_seat[base_seat]
                base_price = base_odata.get('base_price', 0)

                # 새 등급 생성
                new_gdata = dict(base_odata)
                new_gdata['name'] = base_name
                new_gdata['base_price'] = base_price
                new_gdata['base_price_man'] = int(base_price / 10000)

                # 옵션 목록 복사
                new_opts = dict(base_odata.get('options', {}))

                # 상위 인승(6인승, 7인승 등)을 옵션으로 추가
                seat_opts_added = {}
                for snum, (oname, odata) in sorted(items_by_seat.items()):
                    if snum == base_seat:
                        continue
                    diff_price = odata.get('base_price', 0) - base_price
                    if diff_price > 0:
                        opt_key = f"{snum}인승"
                        new_opts[opt_key] = {
                            "price": diff_price,
                            "price_man": int(diff_price / 10000),
                            "kind": "optional",
                            "desc": f"{snum}인승 시트 패키지",
                            "source": "seat_restructure"
                        }
                        seat_opts_added[opt_key] = diff_price

                    # 다른 인승 등급에만 있는 일반 옵션 병합
                    for ok, ov in odata.get('options', {}).items():
                        if ok not in new_opts and not re.match(r'^\d+인승$', ok):
                            new_opts[ok] = ov

                new_gdata['options'] = new_opts
                new_gdata['options_count'] = len(new_opts)

                # 악세사리 탐색
                acc_found = {}
                norm_target = norm_for_acc_match(base_name)
                for dy in danawa_y_dicts:
                    for dk, dv in dy.items():
                        if norm_for_acc_match(dk) == norm_target and dv.get('accessories'):
                            for ak, av in dv['accessories'].items():
                                acc_found[ak] = av

                if acc_found:
                    new_gdata['accessories'] = acc_found
                    acc_attached_grades += 1
                    total_acc_count += len(acc_found)

                new_cat[m][y][base_name] = new_gdata
                log_list.append({
                    "model": m, "year": y, "new_grade": base_name,
                    "merged_seats": list(items_by_seat.keys()),
                    "seat_options": seat_opts_added,
                    "accessories_count": len(acc_found)
                })

            # 3-3. 비인승 등급들에도 악세사리 추가
            for gname, gdata in non_seat_grades.items():
                new_gdata = dict(gdata)
                acc_found = {}
                norm_target = norm_for_acc_match(gname)
                for dy in danawa_y_dicts:
                    for dk, dv in dy.items():
                        if norm_for_acc_match(dk) == norm_target and dv.get('accessories'):
                            for ak, av in dv['accessories'].items():
                                acc_found[ak] = av

                if acc_found:
                    new_gdata['accessories'] = acc_found
                    acc_attached_grades += 1
                    total_acc_count += len(acc_found)

                new_cat[m][y][gname] = new_gdata

    final_grades_count = sum(len(y) for m in new_cat.values() for y in m.values())
    print("  -> 재구성 완료.")
    print(f"     * 원본 등급 수: {total_original_grades}")
    print(f"     * 최종 등급 수: {final_grades_count}")
    print(f"     * 병합된 인승 그룹 수: {seat_groups_count}")
    print(f"     * 악세사리 탑재 등급 수: {acc_attached_grades}")
    print(f"     * 총 악세사리 수: {total_acc_count}")
    print(f"     * 충돌 검토 항목 수: {len(review_list)}")

    # 4. 파일 저장
    print("[4/6] 새 카탈로그 및 로그 파일 저장 중...")
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(new_cat, f, ensure_ascii=False, indent=2)

    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log_list, f, ensure_ascii=False, indent=2)

    with open(review_path, 'w', encoding='utf-8') as f:
        json.dump(review_list, f, ensure_ascii=False, indent=2)
    print("  -> 파일 저장 완료.")

    # 5. 표본 검증
    print("[5/6] 쏘렌토 2025 표본 검증:")
    sor_2025 = new_cat.get('더 뉴 쏘렌토 4세대', {}).get('2025', {})
    print(f"  - 쏘렌토 2025 등급 개수: {len(sor_2025)}개 (기대값: 24개)")
    hev_p = sor_2025.get('HEV 1.6 2WD 프레스티지', {})
    print(f"  - HEV 1.6 2WD 프레스티지 기본가: {hev_p.get('base_price'):,}원 (기대값: 38,670,000원)")
    print(f"  - HEV 1.6 2WD 프레스티지 옵션 수: {hev_p.get('options_count')}개 (기대값: 8개)")
    print(f"    * 6인승: {hev_p.get('options', {}).get('6인승', {}).get('price', 0):,}원 (기대값: 840,000원)")
    print(f"    * 7인승: {hev_p.get('options', {}).get('7인승', {}).get('price', 0):,}원 (기대값: 690,000원)")
    print(f"  - HEV 1.6 2WD 프레스티지 악세사리 수: {len(hev_p.get('accessories', {}))}개 (기대값: 4개)")
    for ak, av in hev_p.get('accessories', {}).items():
        print(f"    * {ak}: {av.get('price'):,}원")

    gas_p = sor_2025.get('가솔린 2.5T 2WD 프레스티지', {})
    print(f"  - 가솔린 2.5T 2WD 프레스티지 기본가: {gas_p.get('base_price'):,}원 (기대값: 35,500,000원)")

    # 6. 책 전체 잔여 괄호 인승 수 확인
    remaining_seat_grades = 0
    for m, yrs in new_cat.items():
        for y, grades in yrs.items():
            for gname in grades.keys():
                if extract_seat_num(gname) is not None:
                    remaining_seat_grades += 1
    print(f"\n[6/6] 책 전체 잔여 괄호 인승 등급 수: {remaining_seat_grades}개 (충돌 보존 {len(review_list)}그룹 분량)")

if __name__ == '__main__':
    main()
