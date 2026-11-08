# -*- coding: utf-8 -*-
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.option_package_service import match_car_options_detail
from services.catalog_by_source_service import get_pilot_catalog_spec

def test_grade_family_options():
    print("=== [검증 2-1: 엔카 옵션 매칭 (인승 모호 등급 'HEV 1.6 2WD 캘리그래피')] ===")
    encar_input = ['빌트인 캠 2, 증강현실 내비게이션', '현대 스마트센스', '파킹 어시스트 플러스 Ⅱ']
    res_encar = match_car_options_detail(
        '디 올 뉴 싼타페', '2024',
        encar_input,
        grade='HEV 1.6 2WD 캘리그래피'
    )
    for r in res_encar:
        print(f"  {r.get('raw_name')} -> official: {r.get('official_name')}, price: {r.get('price')}, match_type: {r.get('match_type')}")
    
    encar_map = {r.get('raw_name'): r for r in res_encar}
    assert encar_map['빌트인 캠 2, 증강현실 내비게이션']['official_name'] == '빌트인 캠 2'
    assert encar_map['빌트인 캠 2, 증강현실 내비게이션']['match_type'] == 'exact'
    assert encar_map['빌트인 캠 2, 증강현실 내비게이션']['price'] == 450000

    assert encar_map['현대 스마트센스']['official_name'] == '현대 스마트센스'
    assert encar_map['현대 스마트센스']['match_type'] == 'exact'
    assert encar_map['현대 스마트센스']['price'] == 790000

    assert encar_map['파킹 어시스트 플러스 Ⅱ']['official_name'] == '파킹 어시스트 플러스Ⅱ'
    assert encar_map['파킹 어시스트 플러스 Ⅱ']['match_type'] == 'exact'
    assert encar_map['파킹 어시스트 플러스 Ⅱ']['price'] == 790000
    assert len(res_encar) == 3, "증강현실 내비게이션이 별도 항목으로 분리됨"
    print(">>> 엔카 매칭 PASS!")

    print("\n=== [검증 2-2: 케이카 옵션 매칭 (optnNm '|' 분할 목록 + assembleFullGradeName 등급)] ===")
    kcar_raw_string = "빌트인 캠 2, 증강현실 내비게이션|현대 스마트센스|파킹 어시스트 플러스 Ⅱ"
    kcar_opt_list = [s.strip() for s in kcar_raw_string.split('|') if s.strip()]
    kcar_grade = 'HEV 1.6 2WD 캘리그래피'
    res_kcar = match_car_options_detail(
        '디 올 뉴 싼타페', '2024',
        kcar_opt_list,
        grade=kcar_grade
    )
    for r in res_kcar:
        print(f"  {r.get('raw_name')} -> official: {r.get('official_name')}, price: {r.get('price')}, match_type: {r.get('match_type')}")
    
    kcar_map = {r.get('raw_name'): r for r in res_kcar}
    assert kcar_map['빌트인 캠 2, 증강현실 내비게이션']['official_name'] == '빌트인 캠 2'
    assert kcar_map['빌트인 캠 2, 증강현실 내비게이션']['match_type'] == 'exact'
    assert kcar_map['빌트인 캠 2, 증강현실 내비게이션']['price'] == 450000

    assert kcar_map['현대 스마트센스']['official_name'] == '현대 스마트센스'
    assert kcar_map['현대 스마트센스']['match_type'] == 'exact'
    assert kcar_map['현대 스마트센스']['price'] == 790000

    assert kcar_map['파킹 어시스트 플러스 Ⅱ']['official_name'] == '파킹 어시스트 플러스Ⅱ'
    assert kcar_map['파킹 어시스트 플러스 Ⅱ']['match_type'] == 'exact'
    assert kcar_map['파킹 어시스트 플러스 Ⅱ']['price'] == 790000
    assert len(res_kcar) == 3, "케이카 항목 분리 오류"
    print(">>> 케이카 매칭 PASS!")

    print("\n=== [검증 2-3: 목표차 회귀 (2023 캘리그래피 6인승)] ===")
    res_target = match_car_options_detail(
        '디 올 뉴 싼타페', '2023',
        ['빌트인캠2', '현대스마트센스', '파킹어시스트플러스2'],
        grade='1.6 HEV 2WD 캘리그래피 6인승'
    )
    for r in res_target:
        print(f"  {r.get('raw_name')} -> official: {r.get('official_name')}, price: {r.get('price')}, match_type: {r.get('match_type')}")
        assert r.get('match_type') == 'exact'
    t_map = {r.get('raw_name'): r for r in res_target}
    assert t_map['빌트인캠2']['price'] == 450000
    assert t_map['현대스마트센스']['price'] == 790000
    assert t_map['파킹어시스트플러스2']['price'] == 790000
    print(">>> 목표차 회귀 PASS!")

    print("\n=== [검증 2-4: 쏘렌토 & MX5 스펙 판정 무변경 회귀] ===")
    sorento_spec = get_pilot_catalog_spec('danawa', '쏘렌토 4세대', '2022', '2.2 디젤 2WD 시그니처 5인승')
    print("  쏘렌토 5인승 found:", sorento_spec.get('found'), "base_price_man:", sorento_spec.get('base_price_man'))
    assert sorento_spec.get('found') is True
    assert sorento_spec.get('base_price_man') == 4021

    mx5_spec_none = get_pilot_catalog_spec('danawa', '디 올 뉴 싼타페', '2023', '1.6 HEV 2WD 캘리그래피')
    print("  MX5 인승없음 found:", mx5_spec_none.get('found'), "reason:", mx5_spec_none.get('reason'))
    assert mx5_spec_none.get('found') is False
    print(">>> 스펙 판정 무변경 회귀 PASS!")

if __name__ == '__main__':
    test_grade_family_options()
    print("\n모든 직접 실행 테스트 100% PASS!")
