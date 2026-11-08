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

print("=== [검증 1 (회귀 수정)] 쏘렌토 4세대 2022년형 (책에 인승 없는 등급) ===")
# services/chaolma_service.py parse_carmart_json에 gradeName "2.2 디젤 2WD"·gradeDetailName "시그니처"·origin_doc {"seating_capacity": 5}를 넣어 조립한 등급
c_data_sorento = {
    "makerName": "기아",
    "modelName": "쏘렌토",
    "modelDetailName": "쏘렌토 4세대",
    "gradeName": "2.2 디젤 2WD",
    "gradeDetailName": "시그니처",
    "year": "2022"
}
parsed_sorento = ChaolmaService.parse_carmart_json(
    c_data_sorento,
    "test_sorento",
    origin_doc={"seating_capacity": 5}
)
sorento_assembled_grade = f"{parsed_sorento.get('grade_name')} {parsed_sorento.get('grade_detail_name')}".strip()
print("조립된 쏘렌토 등급:", sorento_assembled_grade)

sorento_spec = get_pilot_catalog_spec(
    source="danawa",
    car_name="쏘렌토 4세대",
    year="2022",
    grade=sorento_assembled_grade
)
print("쏘렌토 카탈로그 조회 found:", sorento_spec.get("found"))
print("쏘렌토 카탈로그 matched_grade:", sorento_spec.get("grade"))
print("쏘렌토 카탈로그 base_price_man:", sorento_spec.get("base_price_man"))

assert sorento_spec.get("found") is True, f"검증 1 실패: found가 True가 아님 ({sorento_spec.get('reason')})"
assert sorento_spec.get("base_price_man") == 4021, f"검증 1 실패: 기본가가 4,021만이 아님 ({sorento_spec.get('base_price_man')})"
assert sorento_spec.get("grade") == "디젤 2.2 2WD 시그니처", f"검증 1 실패: 매칭된 등급명 불일치 ({sorento_spec.get('grade')})"
print(">>> [검증 1 PASS!]")

print("\n=== [검증 2 (MX5 유지)] 디 올 뉴 싼타페 2023년형 1.6 HEV 2WD 캘리그래피 5인승 ===")
santafe_spec_5 = get_pilot_catalog_spec(
    source="danawa",
    car_name="디 올 뉴 싼타페",
    year="2023",
    grade="1.6 HEV 2WD 캘리그래피 5인승"
)
print("싼타페 5인승 found:", santafe_spec_5.get("found"))
print("싼타페 5인승 matched_grade:", santafe_spec_5.get("grade"))
print("싼타페 5인승 base_price_man:", santafe_spec_5.get("base_price_man"))

assert santafe_spec_5.get("found") is True, f"검증 2 실패: found가 True가 아님 ({santafe_spec_5.get('reason')})"
assert santafe_spec_5.get("base_price_man") == 4664, f"검증 2 실패: 기본가가 4,664만이 아님 ({santafe_spec_5.get('base_price_man')})"
assert santafe_spec_5.get("grade") == "HEV 1.6 2WD 캘리그래피 5인승", f"검증 2 실패: 매칭된 등급명 불일치 ({santafe_spec_5.get('grade')})"
print(">>> [검증 2 PASS!]")

print("\n=== [검증 3 (모호 시 안전)] origin_doc이 없어 인승이 붙지 않은 1.6 HEV 2WD 캘리그래피 ===")
santafe_spec_none = get_pilot_catalog_spec(
    source="danawa",
    car_name="디 올 뉴 싼타페",
    year="2023",
    grade="1.6 HEV 2WD 캘리그래피"
)
print("싼타페 인승 누락 found:", santafe_spec_none.get("found"))
print("싼타페 인승 누락 reason:", santafe_spec_none.get("reason"))

assert santafe_spec_none.get("found") is False, "검증 3 실패: 5·6·7인승 후보가 여러 개인데 임의 매칭됨"
assert "미등록" in str(santafe_spec_none.get("reason")), f"검증 3 실패: reason 불일치 ({santafe_spec_none.get('reason')})"
print(">>> [검증 3 PASS!]")

print("\n=== [추가 검증: 옵션 매칭 정확도] ===")
test_options = ["현대 스마트센스", "빌트인 캠 2", "BOSE 프리미엄 사운드"]
matched_opts = match_car_options_detail(
    car_name="디 올 뉴 싼타페",
    year="2023",
    options_text_or_list=test_options,
    grade="1.6 HEV 2WD 캘리그래피 5인승"
)
for mo in matched_opts:
    assert mo.get("match_type") == "exact", f"옵션 매칭 실패: {mo.get('raw_name')}"
    assert mo.get("source") == "danawa"
none_count = sum(1 for mo in matched_opts if mo.get("match_type") == "none")
assert none_count == 0, f"none 매칭 존재 ({none_count}건)"
print(">>> [옵션 매칭 PASS! (none 0건)]")

print("\n==========================================")
print("모든 검증 (검증 1, 검증 2, 검증 3) 100% 통과!")
print("==========================================")
