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

from services.chaolma_service import ChaolmaService
from services.catalog_by_source_service import get_pilot_catalog_spec
from services.option_package_service import match_car_options_detail

print("=== [검증 1 (핵심)] 제이 목표차 (디 올 뉴 싼타페 HEV 1.6 2WD 캘리그래피, 2023) ===")
# 차얼마 mock 데이터: modelDetailName='디 올 뉴 싼타페', gradeName='1.6 HEV 2WD', gradeDetailName='캘리그래피'
c_data_santafe = {
    "makerName": "현대",
    "modelName": "싼타페",
    "modelDetailName": "디 올 뉴 싼타페",
    "gradeName": "1.6 HEV 2WD",
    "gradeDetailName": "캘리그래피",
    "year": "2023",
    "carMakePrice": 46640000,
    "jsonFullText": {"newprice": 46640000}
}
origin_doc_5 = {"success": True, "seating_capacity": 5}

parsed_5 = ChaolmaService.parse_carmart_json(c_data_santafe, "test_santafe", origin_doc=origin_doc_5)
print("parsed grade_name:", parsed_5.get("grade_name"))
print("parsed grade_detail_name:", parsed_5.get("grade_detail_name"))
print("parsed trim_name:", parsed_5.get("trim_name"))

full_g_5 = f"{parsed_5.get('grade_name')} {parsed_5.get('grade_detail_name')}".strip()
print("combined full grade:", full_g_5)

spec_res = get_pilot_catalog_spec(
    source="danawa",
    car_name=parsed_5.get("model_detail_name"),
    year="2023",
    grade=full_g_5
)
print("spec_res found:", spec_res.get("found"))
print("spec_res matched_grade:", spec_res.get("grade"))
print("spec_res base_price_man:", spec_res.get("base_price_man"))
assert spec_res.get("found") is True, "검증 1 실패: found가 True가 아님"
assert spec_res.get("base_price_man") == 4664, "검증 1 실패: 기본가가 4664만이 아님"
assert spec_res.get("grade") == "HEV 1.6 2WD 캘리그래피 5인승", "검증 1 실패: 등급 매칭 오류"
print(">>> [검증 1 PASS!]")

print("\n=== [검증 2 (옵션)] match_car_options_detail 매칭 ===")
# 책 옵션: 현대 스마트센스, 빌트인 캠 2, 듀얼 와이드 선루프, BOSE 프리미엄 사운드 등
test_options = ["현대 스마트센스", "빌트인 캠 2", "BOSE 프리미엄 사운드"]
matched_opts = match_car_options_detail(
    car_name="디 올 뉴 싼타페",
    year="2023",
    options_text_or_list=test_options,
    grade=full_g_5
)
for mo in matched_opts:
    print(f"  옵션: {mo.get('raw_name')} -> match_type: {mo.get('match_type')}, source: {mo.get('source')}")
    assert mo.get("match_type") == "exact", f"옵션 {mo.get('raw_name')} 매칭 실패: {mo.get('match_type')}"
    assert mo.get("source") == "danawa", f"옵션 {mo.get('raw_name')} 출처 오류: {mo.get('source')}"
none_count = sum(1 for mo in matched_opts if mo.get("match_type") == "none")
assert none_count == 0, f"none 매칭 존재 ({none_count}건)"
print(f"none 매칭 건수: {none_count}건")
print(">>> [검증 2 PASS!]")

print("\n=== [검증 3 (회귀)] 쏘렌토 2022 디젤 2.2 2WD 시그니처 (이미 인승/완성형 등급) ===")
# 쏘렌토 책 등급: "디젤 2.2 2WD 시그니처 5인승" 또는 인승 유무 확인
sorento_spec_1 = get_pilot_catalog_spec(
    source="danawa",
    car_name="쏘렌토",
    year="2022",
    grade="2.2 디젤 2WD 시그니처"
)
print("sorento_spec_1 found:", sorento_spec_1.get("found"), sorento_spec_1.get("grade"), sorento_spec_1.get("base_price_man"))

# origin_doc에 인승이 있더라도 기존 등급에 이미 인승이 있는 경우 중복 추가 방지 확인
c_data_sorento = {
    "makerName": "기아",
    "modelName": "쏘렌토",
    "modelDetailName": "쏘렌토",
    "gradeName": "2.2 디젤 2WD",
    "gradeDetailName": "시그니처 5인승",
    "year": "2022",
    "carMakePrice": 39500000,
    "jsonFullText": {"newprice": 39500000}
}
parsed_sorento = ChaolmaService.parse_carmart_json(c_data_sorento, "test_sorento", origin_doc={"seating_capacity": 5})
print("sorento parsed grade_detail_name:", parsed_sorento.get("grade_detail_name"))
assert parsed_sorento.get("grade_detail_name") == "시그니처 5인승", "중복 인승 추가 버그 발생"
print(">>> [검증 3 PASS!]")

print("\n=== [검증 4 (폴백)] origin_doc이 없는 차량 ===")
parsed_fallback = ChaolmaService.parse_carmart_json(c_data_santafe, "test_fallback", origin_doc=None)
print("fallback grade_name:", parsed_fallback.get("grade_name"))
print("fallback grade_detail_name:", parsed_fallback.get("grade_detail_name"))
assert parsed_fallback.get("grade_detail_name") == "캘리그래피", "origin_doc 없을 때 등급 변형됨"
assert not any("인승" in str(parsed_fallback.get(k)) for k in ["grade_name", "grade_detail_name"]), "인승 임의 주입 발생"
print(">>> [검증 4 PASS!]")

print("\n==========================================")
print("모든 검증 (검증 1, 검증 2, 검증 3, 검증 4) 100% 통과!")
print("==========================================")
