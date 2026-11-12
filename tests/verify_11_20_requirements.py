# tests/verify_11_20_requirements.py
"""
[11-11-20] 제이책(C) 뷰어 표시 정리 검증 스크립트
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from api_server import app
from services.catalog_c_service import get_catalog_c_spec, get_catalog_c_stats

def run_verification():
    client = TestClient(app)

    print("==================================================")
    print("🚀 [11-11-20] 제이책(C) 뷰어 표시 정리 필수 검증 시작")
    print("==================================================")

    # 1. 뷰어 머리말 및 통계 검증
    print("\n--- [검증 1] 뷰어 머리말 및 통계 API 검증 ---")
    stats = get_catalog_c_stats()
    print("get_catalog_c_stats 결과:", stats)
    assert stats["total_grades"] == 14644, f"Expected 14,644 grades, got {stats['total_grades']}"
    assert "14,644개 등급" in stats["summary_text"]

    with open("frontend/public/catalog-c.html", "r", encoding="utf-8") as f:
        c_html = f.read()
    assert "14,644개 등급" in c_html, "catalog-c.html에 14,644개 등급이 포함되어야 합니다."
    assert "15,216" not in c_html, "catalog-c.html에 15,216이 남아있지 않아야 합니다."

    with open("frontend/public/newcar-catalog-c.html", "r", encoding="utf-8") as f:
        nc_html = f.read()
    assert "14,644개 등급" in nc_html, "newcar-catalog-c.html에 14,644개 등급이 포함되어야 합니다."
    assert "15,216" not in nc_html, "newcar-catalog-c.html에 15,216이 남아있지 않아야 합니다."
    print("✅ 검증 1 통과: 머리말 '14,644개 등급' 반영 확인!")

    # 2. 더 뉴 QM6 2025 '2.0 LPe RE 2WD' 충돌 표시 소멸 및 옵션 수 검증
    print("\n--- [검증 2] 더 뉴 QM6 2025 '2.0 LPe RE 2WD' 충돌 및 옵션 검증 ---")
    qm6_res = get_catalog_c_spec("더 뉴 QM6", "2025", "2.0 LPe RE 2WD")
    assert qm6_res["found"] is True
    target_qm6 = qm6_res["target_grade"]
    qm6_grade = qm6_res["grades"][target_qm6]
    print(f"QM6 목표 등급: {target_qm6}")
    print(f"기본가: {qm6_grade['base_price']:,}원")
    print(f"is_conflict: {qm6_grade['is_conflict']}")
    print(f"conflict_info: {qm6_grade['conflict_info']}")
    print(f"options_count: {qm6_grade['options_count']}개")
    print(f"실제 options 개수: {len(qm6_grade['options'])}개")
    for ok, ov in qm6_grade["options"].items():
        print(f"  - [{ov.get('source')}] {ok}: {ov.get('price'):,}원")

    assert qm6_grade["is_conflict"] is False, "QM6 2025 RE에 충돌 표시가 없어야 합니다."
    assert qm6_grade["conflict_info"] is None, "QM6 2025 RE conflict_info는 None이어야 합니다."
    assert qm6_grade["options_count"] == 6, f"QM6 2025 RE options_count는 6개여야 합니다. (실제: {qm6_grade['options_count']})"
    assert len(qm6_grade["options"]) == 6, "QM6 2025 RE 실제 options 목록 개수도 6개여야 합니다."
    print("✅ 검증 2 통과: QM6 2025 RE 충돌 소멸 및 옵션 6개 일치 확인!")

    # 3. GV80 2025 '2.5T 가솔린 2WD'와 '2.5T 가솔린 AWD' 충돌 소멸 검증
    print("\n--- [검증 3] GV80 2025 '2.5T 가솔린 2WD'와 'AWD' 충돌 소멸 검증 ---")
    gv80_res = get_catalog_c_spec("GV80", "2025")
    assert gv80_res["found"] is True
    g_2wd = gv80_res["grades"].get("2.5T 가솔린 2WD")
    g_awd = gv80_res["grades"].get("2.5T 가솔린 AWD")
    assert g_2wd is not None, "2.5T 가솔린 2WD 등급이 존재해야 합니다."
    assert g_awd is not None, "2.5T 가솔린 AWD 등급이 존재해야 합니다."

    print(f"GV80 2.5T 2WD: base_price={g_2wd['base_price']:,}원, is_conflict={g_2wd['is_conflict']}")
    print(f"GV80 2.5T AWD: base_price={g_awd['base_price']:,}원, is_conflict={g_awd['is_conflict']}")

    assert g_2wd["is_conflict"] is False, "GV80 2WD에 충돌 표시가 없어야 합니다."
    assert g_awd["is_conflict"] is False, "GV80 AWD에 충돌 표시가 없어야 합니다."
    print("✅ 검증 3 통과: GV80 2025 2WD와 AWD 충돌 소멸 확인!")

    print("\n🎉 [11-11-20] 3대 핵심 검증 100% 통과!")

if __name__ == "__main__":
    run_verification()
