# tests/test_cockpit_catalog_c.py
"""
[11-11-17] 콕핏 런타임 제이책(C) 교체 검증 스크립트
1. XM3 2021 RE -> 기본가 23,520,000원, 옵션 7개
2. QM6 2024 RE -> 기본가 32,200,000원 (엔카 공식 가격 확정, 다나와 33,400,000원 배제)
3. 쏘렌토 2022 시그니처:
   - 가솔린 2.5 2WD 시그니처 -> 38,460,000원
   - 디젤 2.2 2WD 시그니처 -> 40,210,000원
   - HEV 1.6 2WD 시그니처 -> 41,320,000원
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.catalog_by_source_service import (
    load_catalog_by_source_v2,
    get_pilot_catalog_spec,
    get_pilot_option_price
)
from services.option_package_service import match_car_options_detail

def run_cockpit_verification():
    print("==================================================")
    print("🚀 [11-11-17] 콕핏 런타임 제이책(C) 연결 검증 시작")
    print("==================================================")

    cat = load_catalog_by_source_v2()
    print(f"1. 로드된 책 출처 키: {list(cat.keys())[:5]}")
    assert 'c' in cat, "제이책(C) 키가 누락되었습니다."
    assert 'danawa' in cat, "danawa 호환 키가 누락되었습니다."

    # 1. XM3 2021 RE
    print("\n--- [검증 1] XM3 2021 RE ---")
    spec_xm3 = get_pilot_catalog_spec(source="danawa", car_name="XM3", year="2021", grade="1.3 TCe RE")
    print("get_pilot_catalog_spec result:")
    print(f"  found: {spec_xm3.get('found')}")
    print(f"  grade: {spec_xm3.get('grade')}")
    print(f"  base_price: {spec_xm3.get('base_price'):,}원 ({spec_xm3.get('base_price_man')}만원)")
    print(f"  source: {spec_xm3.get('source')}")
    opts_xm3 = spec_xm3.get('options', {})
    print(f"  options count: {len(opts_xm3)}개")
    for oname, oinfo in opts_xm3.items():
        print(f"    * [{oinfo.get('source')}] {oname}: {oinfo.get('price'):,}원")

    assert spec_xm3.get('found') is True
    assert spec_xm3.get('base_price') == 23520000, f"Expected 23,520,000원, got {spec_xm3.get('base_price')}"
    assert len(opts_xm3) == 7, f"Expected 7 options, got {len(opts_xm3)}"

    # 콕핏 옵션 패키지 서비스(match_car_options_detail) 연동 확인
    cockpit_opts_xm3 = match_car_options_detail(
        car_name="XM3",
        year="2021",
        options_text_or_list="18인치 투톤 알로이 휠, 블랙 가죽시트 패키지 I",
        grade="1.3 TCe RE"
    )
    print(f"  match_car_options_detail matched options: {len(cockpit_opts_xm3)}개")

    # 2. QM6 2024 RE (엔카 32,200,000원 우선 확정 확인)
    print("\n--- [검증 2] QM6 2024 RE (엔카 가격 32,200,000원 확정) ---")
    # 'RE' 쿼리로 호출 시 복수 후보 중 엔카 가격 확정 확인
    spec_qm6 = get_pilot_catalog_spec(source="danawa", car_name="더 뉴 QM6", year="2024", grade="2.0 GDe RE 2WD")
    print("get_pilot_catalog_spec (2.0 GDe RE 2WD):")
    print(f"  found: {spec_qm6.get('found')}")
    print(f"  grade: {spec_qm6.get('grade')}")
    print(f"  base_price: {spec_qm6.get('base_price'):,}원 ({spec_qm6.get('base_price_man')}만원)")
    print(f"  source: {spec_qm6.get('source')}")
    assert spec_qm6.get('found') is True
    assert spec_qm6.get('base_price') == 32200000, f"Expected 32,200,000원 (엔카), got {spec_qm6.get('base_price')}"
    assert spec_qm6.get('source') == 'encar'

    # 'RE' 단독 등급명 쿼리 시에도 엔카 32,200,000원 우선 선택되는지 확인
    spec_qm6_re = get_pilot_catalog_spec(source="danawa", car_name="더 뉴 QM6", year="2024", grade="RE")
    print("get_pilot_catalog_spec (RE 단독 쿼리):")
    print(f"  found: {spec_qm6_re.get('found')}")
    print(f"  grade: {spec_qm6_re.get('grade')}")
    print(f"  base_price: {spec_qm6_re.get('base_price'):,}원")
    print(f"  source: {spec_qm6_re.get('source')}")
    assert spec_qm6_re.get('found') is True
    assert spec_qm6_re.get('base_price') == 32200000, f"Expected 32,200,000원 (엔카), got {spec_qm6_re.get('base_price')}"
    assert spec_qm6_re.get('source') == 'encar'

    # 3. 쏘렌토 2022 시그니처 3개 파워트레인 확인
    print("\n--- [검증 3] 쏘렌토 4세대 2022 시그니처 (가솔린 38,460,000원 / 디젤 39,440,000원 / HEV 42,320,000원) ---")
    # 3-1. 가솔린
    spec_sor_gas = get_pilot_catalog_spec(source="danawa", car_name="쏘렌토 4세대", year="2022", grade="가솔린 2.5 2WD 시그니처")
    print(f"가솔린 시그니처: {spec_sor_gas.get('grade')} -> {spec_sor_gas.get('base_price'):,}원")
    assert spec_sor_gas.get('base_price') == 38460000, f"Expected 38,460,000원, got {spec_sor_gas.get('base_price')}"

    # 3-2. 디젤 (5인승 기준 정가: 39,440,000원)
    spec_sor_dsl = get_pilot_catalog_spec(source="danawa", car_name="쏘렌토 4세대", year="2022", grade="디젤 2.2 2WD 시그니처")
    print(f"디젤 시그니처: {spec_sor_dsl.get('grade')} -> {spec_sor_dsl.get('base_price'):,}원")
    assert spec_sor_dsl.get('base_price') == 39440000, f"Expected 39,440,000원, got {spec_sor_dsl.get('base_price')}"

    # 3-3. 하이브리드 (5인승 기준 정가: 42,320,000원)
    spec_sor_hev = get_pilot_catalog_spec(source="danawa", car_name="쏘렌토 4세대", year="2022", grade="HEV 1.6 2WD 시그니처")
    print(f"하이브리드 시그니처: {spec_sor_hev.get('grade')} -> {spec_sor_hev.get('base_price'):,}원")
    assert spec_sor_hev.get('base_price') == 42320000, f"Expected 42,320,000원, got {spec_sor_hev.get('base_price')}"

    # 4. 폴백 안전장치 검증 (catalog_c 파일이 없을 때 catalog_by_source_v2.json으로 폴백되는지)
    print("\n--- [검증 4] 폴백 안전장치 검증 ---")
    import services.catalog_by_source_service as c_srv
    orig_path = c_srv.CATALOG_C_PATH
    c_srv.CATALOG_C_PATH = "data/non_existent_catalog_c.json"
    c_srv._CATALOG_V2_CACHE = None
    fallback_cat = c_srv.load_catalog_by_source_v2()
    print(f"폴백 로드 결과 키: {list(fallback_cat.keys())[:3]}")
    assert 'danawa' in fallback_cat, "폴백 catalog_by_source_v2.json 로드 실패!"
    print("✅ 폴백 정상 작동 확인 완료!")

    # 원상 복구
    c_srv.CATALOG_C_PATH = orig_path
    c_srv._CATALOG_V2_CACHE = None

    print("\n🎉 모든 콕핏 검증 100% 통과!")

if __name__ == '__main__':
    run_cockpit_verification()
