"""
[11-12-05] 제이책(C) 악세사리를 연식 레벨로 — 등급별 중복 제거
"""

import json

def main():
    catalog_path = 'data/catalog_c.json'

    with open(catalog_path, 'r', encoding='utf-8') as f:
        cat = json.load(f)

    total_models = len(cat)
    total_years = 0
    total_grades = 0
    years_with_acc = 0
    total_acc_count = 0
    review_diff_list = []

    for m, yrs in cat.items():
        total_years += len(yrs)
        for y, grades in yrs.items():
            # 1. 등급별 악세사리 수집
            acc_by_grade = {}
            for gname, gdata in grades.items():
                if gname.startswith('_'):
                    continue
                total_grades += 1
                if 'accessories' in gdata:
                    acc_by_grade[gname] = gdata['accessories']

            if not acc_by_grade:
                continue

            # 2. 등급별 악세사리가 서로 다른지 확인
            # 각 등급의 악세사리 키 및 가격 비교를 위한 튜플화
            serialized_accs = {
                gname: tuple(sorted((k, v.get('price')) for k, v in acc.items()))
                for gname, acc in acc_by_grade.items()
            }
            unique_sets = set(serialized_accs.values())

            if len(unique_sets) > 1:
                # 등급별 악세사리가 다른 예외 케이스: 등급별 유지하고 검토 목록 기록
                review_diff_list.append({
                    "model": m,
                    "year": y,
                    "reason": "등급별 악세사리 구성이 상이함",
                    "details": {gname: list(acc.keys()) for gname, acc in acc_by_grade.items()}
                })
                continue

            # 3. 모든 등급의 악세사리가 동일한 경우: 연식 레벨로 승격
            # 대표 악세사리 딕셔너리 추출 (첫 번째 등급 것)
            rep_acc = next(iter(acc_by_grade.values()))
            grades['_accessories'] = rep_acc
            years_with_acc += 1
            total_acc_count += len(rep_acc)

            # 등급별 accessories 필드 완전 제거
            for gname, gdata in grades.items():
                if gname.startswith('_'):
                    continue
                if 'accessories' in gdata:
                    del gdata['accessories']

    # 4. 저장
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)

    print("=== 데이터 정리 결과 ===")
    print(f"총 차종 수: {total_models}")
    print(f"총 연식 수: {total_years}")
    print(f"총 등급 수: {total_grades}")
    print(f"_accessories 추가된 (차종, 연식) 수: {years_with_acc}")
    print(f"_accessories 총 악세사리 개수 (단일 세트 합): {total_acc_count}")
    print(f"등급별 상이로 미처리된 검토 목록 수: {len(review_diff_list)}")

    # 5. 잔여 등급별 accessories 검증
    remaining_grade_accs = 0
    for m, yrs in cat.items():
        for y, grades in yrs.items():
            for gname, gdata in grades.items():
                if gname.startswith('_'):
                    continue
                if 'accessories' in gdata:
                    remaining_grade_accs += 1

    print(f"책 전체 등급에 남은 accessories 필드 수: {remaining_grade_accs} (목표: 0)")

if __name__ == '__main__':
    main()
