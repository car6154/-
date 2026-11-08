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


def test_package_bundle_matching():
    # 1. 묶음 매칭: "빌트인 캠 2, 증강현실 내비게이션" -> "빌트인 캠 2" exact
    res1 = match_car_options_detail(
        '디 올 뉴 싼타페', '2024',
        ['빌트인 캠 2, 증강현실 내비게이션', '현대 스마트센스', '6인승'],
        grade='1.6 HEV 2WD 캘리그래피 6인승'
    )
    r1_map = {r.get('raw_name'): r for r in res1}
    assert '빌트인 캠 2, 증강현실 내비게이션' in r1_map
    b2 = r1_map['빌트인 캠 2, 증강현실 내비게이션']
    assert b2.get('official_name') == '빌트인 캠 2'
    assert b2.get('match_type') == 'exact'
    assert b2.get('price') == 450000

    hs = r1_map['현대 스마트센스']
    assert hs.get('official_name') == '현대 스마트센스'
    assert hs.get('match_type') == 'exact'
    assert hs.get('price') == 790000

    s6 = r1_map['6인승']
    assert s6.get('match_type') == 'none'

    # 2. 회귀 확인: 2023년형 단품들
    res2 = match_car_options_detail(
        '디 올 뉴 싼타페', '2023',
        ['빌트인캠2', '현대스마트센스', '파킹어시스트플러스2'],
        grade='1.6 HEV 2WD 캘리그래피 6인승'
    )
    for r in res2:
        assert r.get('match_type') == 'exact'
    r2_map = {r.get('raw_name'): r for r in res2}
    assert r2_map['빌트인캠2'].get('price') == 450000
    assert r2_map['현대스마트센스'].get('price') == 790000
    assert r2_map['파킹어시스트플러스2'].get('price') == 790000

    # 3. 가드 테스트: 둘 다 책 옵션인 경우 묶음 규칙 스킵
    res3 = match_car_options_detail(
        '디 올 뉴 싼타페', '2024',
        ['현대 스마트센스, 파킹 어시스트 플러스Ⅱ'],
        grade='1.6 HEV 2WD 캘리그래피 6인승'
    )
    assert len(res3) == 1
    assert res3[0].get('match_type') != 'exact'


if __name__ == '__main__':
    test_package_bundle_matching()
    print("test_package_bundle_matching PASS!")
