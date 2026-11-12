"""
[11-12-07] 제이책(C) 병합 등급 기본가 수정 스크립트
기본가 + 인승 옵션 = 실제 인승 가격으로 맞춤
"""

import json
import re

def get_base_seat_for_model(model, seat_grades):
    # 팰리세이드는 8인승 우선 (없으면 7인승)
    if '팰리세이드' in model:
        if 8 in seat_grades:
            return 8
        elif 7 in seat_grades:
            return 7
        return min(seat_grades.keys())
    # 쏘렌토 및 기타 SUV는 5인승 우선 (없으면 최저 인승)
    if 5 in seat_grades:
        return 5
    return min(seat_grades.keys())

def main():
    catalog_path = 'data/catalog_c.json'
    v12_path = 'data/catalog_c_v12_backup_2026-11-12.json'
    log_path = 'data/catalog_c_base_price_fix_log_2026-11-12.json'

    with open(catalog_path, 'r', encoding='utf-8') as f:
        cat = json.load(f)

    with open(v12_path, 'r', encoding='utf-8') as f:
        v12 = json.load(f)

    fixed_logs = []
    total_checked = 0
    mismatch_found = 0

    # 1. 전수 스캔 및 기본가 수정
    for m, yrs in cat.items():
        if m in ['더 뉴 그랜드 스타렉스', '맥스크루즈']:
            continue
        v12_m = v12.get(m, {})

        for y, grades in yrs.items():
            v12_y = v12_m.get(y, {})

            for gname, gdata in grades.items():
                if gname.startswith('_'):
                    continue

                opts = gdata.get('options', {})
                seat_opts = {k: v for k, v in opts.items() if re.match(r'^\d+인승$', k)}

                if not seat_opts:
                    continue

                total_checked += 1
                current_bp = gdata.get('base_price', 0)

                # v12에서 인승별 등급 탐색
                v12_seat_grades = {}
                for v12_gname, v12_gdata in v12_y.items():
                    clean_v12 = re.sub(r'\s*\(\s*\d+인승\s*\)', '', v12_gname).strip()
                    if clean_v12 == gname and '(' in v12_gname and '인승)' in v12_gname:
                        m_s = re.search(r'\((\d+)인승\)', v12_gname)
                        if m_s:
                            s_num = int(m_s.group(1))
                            v12_seat_grades[s_num] = v12_gdata.get('base_price')

                if not v12_seat_grades:
                    continue

                base_seat_num = get_base_seat_for_model(m, v12_seat_grades)
                target_bp = v12_seat_grades[base_seat_num]

                # 검산 불일치 여부 확인
                is_mismatch = False
                for s_num_str, opt_info in seat_opts.items():
                    s_int = int(s_num_str.replace('인승', ''))
                    actual_v12_price = v12_seat_grades.get(s_int)
                    if actual_v12_price is not None and (current_bp + opt_info.get('price', 0)) != actual_v12_price:
                        is_mismatch = True

                if current_bp != target_bp:
                    is_mismatch = True

                if is_mismatch:
                    mismatch_found += 1
                    # 기본가 수정
                    gdata['base_price'] = target_bp
                    gdata['base_price_man'] = int(target_bp / 10000)

                    # 검산 상세 기록
                    check_records = {}
                    for s_num_str, opt_info in seat_opts.items():
                        s_int = int(s_num_str.replace('인승', ''))
                        opt_price = opt_info.get('price', 0)
                        calc_price = target_bp + opt_price
                        actual_price = v12_seat_grades.get(s_int)
                        check_records[s_num_str] = {
                            'base_price': target_bp,
                            'opt_price': opt_price,
                            'sum': calc_price,
                            'actual_v12_price': actual_price,
                            'is_exact_match': (calc_price == actual_price)
                        }

                    fixed_logs.append({
                        'model': m,
                        'year': y,
                        'grade': gname,
                        'base_seat_num': base_seat_num,
                        'old_base_price': current_bp,
                        'new_base_price': target_bp,
                        'diff': target_bp - current_bp,
                        'verification': check_records
                    })

    print(f"=== 전수 재검증 및 수정 결과 ===")
    print(f"전수 재검증 등급 수: {total_checked}개")
    print(f"기본가 불일치 등급 수: {mismatch_found}개")
    print(f"수정 완료 등급 수: {len(fixed_logs)}개")

    # 2. 수정 후 전수 재검산
    post_mismatch = 0
    for m, yrs in cat.items():
        if m in ['더 뉴 그랜드 스타렉스', '맥스크루즈']:
            continue
        v12_m = v12.get(m, {})

        for y, grades in yrs.items():
            v12_y = v12_m.get(y, {})

            for gname, gdata in grades.items():
                if gname.startswith('_'): continue
                opts = gdata.get('options', {})
                seat_opts = {k: v for k, v in opts.items() if re.match(r'^\d+인승$', k)}
                if not seat_opts: continue

                bp = gdata.get('base_price', 0)
                v12_seat_grades = {}
                for v12_gname, v12_gdata in v12_y.items():
                    clean_v12 = re.sub(r'\s*\(\s*\d+인승\s*\)', '', v12_gname).strip()
                    if clean_v12 == gname and '(' in v12_gname and '인승)' in v12_gname:
                        m_s = re.search(r'\((\d+)인승\)', v12_gname)
                        if m_s:
                            v12_seat_grades[int(m_s.group(1))] = v12_gdata.get('base_price')

                if not v12_seat_grades: continue
                base_seat_num = get_base_seat_for_model(m, v12_seat_grades)
                if bp != v12_seat_grades[base_seat_num]:
                    post_mismatch += 1
                for s_num_str, opt_info in seat_opts.items():
                    s_int = int(s_num_str.replace('인승', ''))
                    act = v12_seat_grades.get(s_int)
                    if act is not None and (bp + opt_info.get('price', 0)) != act:
                        post_mismatch += 1

    print(f"수정 후 잔여 불일치 등급 수: {post_mismatch}개 (목표: 0개)")

    # 3. 파일 저장
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)

    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(fixed_logs, f, ensure_ascii=False, indent=2)

    print("파일 저장 완료.")

if __name__ == '__main__':
    main()
