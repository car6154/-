# tests/test_catalog_c_api.py
"""
[11-11-15] 제이책(C) API 및 뷰어 데이터 검증 스크립트
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from api_server import app

def run_tests():
    client = TestClient(app)

    print("=== 1. /api/catalog-c/tree 검증 ===")
    res_tree = client.get("/api/catalog-c/tree")
    assert res_tree.status_code == 200, f"tree status error: {res_tree.status_code}"
    tree_data = res_tree.json()
    print("Tree brands:", list(tree_data.keys()))
    total_models = sum(len(m) for m in tree_data.values())
    print(f"Total models in tree: {total_models}")
    assert total_models == 307, f"Expected 307 models, got {total_models}"

    print("\n=== 2. XM3 2021 RE 검증 ===")
    res_xm3 = client.get("/api/catalog-c/spec?car_name=XM3&year=2021&grade=RE")
    assert res_xm3.status_code == 200, f"xm3 spec status error: {res_xm3.status_code}"
    d_xm3 = res_xm3.json()
    assert d_xm3["found"] is True
    assert d_xm3["total_grades"] == 6, f"Expected 6 grades for XM3 2021, got {d_xm3['total_grades']}"
    assert d_xm3["target_grade"] == "1.3 TCe RE", f"Expected target_grade 1.3 TCe RE, got {d_xm3['target_grade']}"
    re_grade = d_xm3["grades"]["1.3 TCe RE"]
    print(f"Target grade: {d_xm3['target_grade']}")
    print(f"RE base_price: {re_grade['base_price']:,}원 ({re_grade['base_price_man']}만원), source: {re_grade['source']}")
    print("All 6 grades for XM3 2021:")
    for gname, ginfo in d_xm3["grades"].items():
        is_target = (gname == d_xm3["target_grade"])
        print(f"  - {gname}: {ginfo['base_price_man']}만원, options: {ginfo['options_count']}개, target={is_target}")

    print("\n=== 3. 더 뉴 QM6 2024 RE 검증 ===")
    res_qm6 = client.get("/api/catalog-c/spec?car_name=더%20뉴%20QM6&year=2024&grade=RE")
    assert res_qm6.status_code == 200
    d_qm6 = res_qm6.json()
    assert d_qm6["found"] is True
    target_qm6 = d_qm6["target_grade"]
    qm6_re_data = d_qm6["grades"][target_qm6]
    print(f"Target grade for QM6: {target_qm6}")
    print(f"Base price: {qm6_re_data['base_price']:,}원 ({qm6_re_data['base_price_man']}만원)")
    print(f"Source: {qm6_re_data['source']}, is_conflict: {qm6_re_data['is_conflict']}")
    assert qm6_re_data["base_price"] == 32200000, f"Expected 32,200,000 won, got {qm6_re_data['base_price']}"
    assert qm6_re_data["source"] == "encar"
    assert qm6_re_data["is_conflict"] is True

    print("\n✅ [11-11-15] 모든 필수 검증 100% 통과!")

if __name__ == "__main__":
    run_tests()
