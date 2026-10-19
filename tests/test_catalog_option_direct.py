# -*- coding: utf-8 -*-
"""
카탈로그 옵션 상세내역 차량명+연식 직접 조회 테스트
(팰리세이드 2020 컨비니언스 및 타 차종 3건)
"""
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.option_package_service import get_catalog_option_detail

def test_cases():
    test_data = [
        ("팰리세이드", 2020, "컨비니언스"),
        ("카니발 4세대", 2021, "드라이브 와이즈"),
        ("쏘나타 (DN8)", 2020, "현대 스마트센스 I"),
        ("그랜저 IG", 2018, "현대 스마트 센스 패키지 Ⅱ"),
    ]

    print("=" * 60)
    print("카탈로그 옵션 상세내역 차량명+연식 직접 조회 검증")
    print("=" * 60)

    all_passed = True
    for car_name, year, opt_name in test_data:
        res = get_catalog_option_detail(car_name, year, opt_name)
        print(f"\n[입력]: ({car_name}, {year}, '{opt_name}')")
        if res:
            price = res.get('price')
            desc = res.get('desc')
            price_str = f"{price:,}원" if price is not None else "가격 미표기"
            print(f"[조회 성공]: price={price_str}, desc={desc[:50]}...")
            print(f" -> 상세: {res}")
        else:
            print(f"[조회 실패]: 매칭 결과 없음")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print(">>> 모든 테스트 케이스 성공!")
    else:
        print(">>> 일부 테스트 케이스 실패")
    print("=" * 60)

if __name__ == "__main__":
    test_cases()
