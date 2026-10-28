"""J-PRO 회귀테스트 묶음 (순수 로직 – 세션·네트워크 불필요).
실행: python tests/test_jpro_regressions.py  (종료 코드 0 = 전부 통과)
기준값 (2026-10-28 Phase 1~5 검증에서 확정):
- XM3 옵션: 휠 39만·블랙 가죽시트 106만·합계 145만·미분류 잔액 15만
- 정렬: 점검 유무 → 성능일 최신 → 가격 낮은 → 연식 최신
- 부위 코드: 외판 14·골격 20·교집합 0
- 헤이딜러: 신차 추가옵션 마커 상단/하단/없음 3케이스 + loaded 폴백
- 케이카 3D 분류: 외판/골격 구분 (part_codes 기준, 승격 if/elif의 전제)
실측 API(차얼마·엔카·노트북)는 이 파일에서 다루지 않는다 (세션 필요).
가격만 단언하고 출처 라벨은 단언하지 않는다 (어느 카탈로그가 먼저 맞아도 가격은 같아야 함).
"""
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILURES.append(name)


def test_chaolma_xm3():
    print("[1] 차얼마 XM3 옵션 (Phase 1 기준)")
    from services.chaolma_service import ChaolmaService
    c_data = {
        "carMakePrice": 24530000,
        "year": "2020",
        "modelName": "XM3",
        "optionSelectList": [
            {"name": '18" 투톤 알로이 휠 &215/55 R18 타이어 +듀얼 디퓨저 형상 리어 크롬 가니시', "price": 390000},
            {"name": "블랙 가죽시트 패키지Ⅲ", "price": 1060000},
        ],
        "jsonFullText": {
            "newprice": 22930000,
            "optlist": [
                {"name": '18" 투톤 알로이 휠 215/55 R18+듀얼 크롬 디퓨저 형상 리어 크롬 가니시', "price": 0},
                {"name": "블랙 가죽시트 패키지 III", "price": 0},
            ],
        },
    }
    res = ChaolmaService.parse_carmart_json(c_data, "REGRESSION-DUMMY")
    check("신차가 2453만", res.get("new_car_price") == 24530000, str(res.get("new_car_price")))
    check("기본가 2293만", res.get("base_car_price") == 22930000, str(res.get("base_car_price")))
    check("옵션 합계 145만", res.get("total_option_price") == 1450000, str(res.get("total_option_price")))
    check("미분류 잔액 15만", res.get("unclassified_balance") == 150000, str(res.get("unclassified_balance")))
    opts = {o.get("name", ""): o.get("price") for o in res.get("options", [])}
    wheel = [v for k, v in opts.items() if "휠" in k]
    seat = [v for k, v in opts.items() if "가죽시트" in k]
    check("휠 39만", wheel == [390000], str(wheel))
    check("가죽시트 106만", seat == [1060000], str(seat))


def test_chaolma_unpriced():
    print("[2] 미수록 옵션 덤터기 금지 (Phase 1)")
    from services.chaolma_service import ChaolmaService
    c_data = {
        "carMakePrice": 24530000,
        "year": "2020",
        "modelName": "XM3",
        "optionSelectList": [],
        "jsonFullText": {
            "newprice": 22930000,
            "optlist": [{"name": "아무데도 없는 가상 옵션 XYZ", "price": 0}],
        },
    }
    res = ChaolmaService.parse_carmart_json(c_data, "REGRESSION-DUMMY")
    opts = res.get("options", [])
    check("미수록 옵션 가격 0 유지", len(opts) == 1 and opts[0].get("price") == 0, str(opts))
    check("미분류 잔액이 옵션에 배정 안 됨", res.get("unclassified_balance") == 1600000, str(res.get("unclassified_balance")))


def test_sort():
    print("[3] 정렬 (Phase 3 기준)")
    import pandas as pd
    from services.data_processor import DataProcessor
    rows = [
        {"성능일": "24-10-01", "판매가": 1500, "연식": 2021, "name": "A"},
        {"성능일": "24-10-01", "판매가": 1400, "연식": 2020, "name": "B"},
        {"성능일": "24-09-01", "판매가": 1200, "연식": 2022, "name": "C"},
        {"성능일": "미검사/사진", "판매가": 1000, "연식": 2023, "name": "D"},
        {"성능일": "24-10-01", "판매가": 1400, "연식": 2022, "name": "E"},
        {"성능일": "24-10-01", "판매가": None, "연식": 2024, "name": "F"},
        {"성능일": "-", "판매가": 900, "연식": 2024, "name": "G"},
    ]
    out = DataProcessor.sort_by_perf_and_year(pd.DataFrame(rows))
    check("정렬 E>B>A>F>C>G>D", out["name"].tolist() == ["E", "B", "A", "F", "C", "G", "D"], str(out["name"].tolist()))


def test_part_codes():
    print("[4] 부위 코드 (Phase 4 기준)")
    from services.part_codes import (
        OUTER_PART_CODES, INNER_PART_CODES, resolve_part_code, is_outer_part, is_inner_part,
    )
    check("외판 14개", len(OUTER_PART_CODES) == 14, str(len(OUTER_PART_CODES)))
    check("골격 20개", len(INNER_PART_CODES) == 20, str(len(INNER_PART_CODES)))
    check("교집합 0", len(set(OUTER_PART_CODES) & set(INNER_PART_CODES)) == 0)
    cases = {
        "앞휀더(좌)": "F_FENDER_L", "사이드실(좌)": "SIDE_SILL_L", "A필러(좌)": "A_PILLAR_L",
        "리어 사이드 멤버(좌)": "SIDE_MEMBER_REAR_L", "프론트 사이드 멤버(우)": "SIDE_MEMBER_FRONT_R",
        "BACK_DOOR_RIGHT": "REAR_DOOR_R", "FRONT_SIDE_MEMBER_L": "SIDE_MEMBER_FRONT_L",
        "대쉬 패널": "DASH_PANEL", "플로어 패널": "FLOOR_PANEL", "리어 패널": "REAR_PANEL",
        "후드": "HOOD", "트렁크리드": "TRUNK",
    }
    bad = {k: resolve_part_code(k) for k, v in cases.items() if resolve_part_code(k) != v}
    check("resolve 12건", not bad, str(bad))
    check("후드=외판", is_outer_part("HOOD") and not is_inner_part("HOOD"))
    check("프론트 사이드멤버=골격", is_inner_part("SIDE_MEMBER_FRONT_L") and not is_outer_part("SIDE_MEMBER_FRONT_L"))


def test_heydealer():
    print("[5] 헤이딜러 파싱 (Phase 5 기준)")
    from services.heydealer_service import parse_heydealer_options, enrich_heydealer_options
    desc_a = "1) 선루프\n2) 내비게이션\n* 신차 추가옵션"
    desc_b = "* 신차 추가옵션\n1) 선루프\n2) 내비게이션\n* 등급 기본옵션\n1) 기본시트"
    desc_c = "1) 선루프\n2) 내비게이션\n* 기본품목\n1) 기본시트"
    check("케이스A (마커 상단)", parse_heydealer_options(desc_a) == ["선루프", "내비게이션"], str(parse_heydealer_options(desc_a)))
    check("케이스B (마커 하단, 기본 제외)", parse_heydealer_options(desc_b) == ["선루프", "내비게이션"], str(parse_heydealer_options(desc_b)))
    check("케이스C (마커 없음, 기본 제외)", parse_heydealer_options(desc_c) == ["선루프", "내비게이션"], str(parse_heydealer_options(desc_c)))
    car = {"car_spec": {"description": desc_b},
           "market_prices": [{"car_spec": {"description": desc_a}}]}
    out = enrich_heydealer_options(car)
    check("enrich 메인 parsed", out.get("parsed_options") == ["선루프", "내비게이션"], str(out.get("parsed_options")))
    check("enrich 메인 text", out.get("options_text") == "선루프 · 내비게이션", str(out.get("options_text")))
    check("enrich 메인 items 구조", len(out.get("options_items", [])) == 2 and all("source" in it for it in out["options_items"]), str(out.get("options_items")))
    check("enrich 시장 매물", out["market_prices"][0].get("parsed_options") == ["선루프", "내비게이션"], str(out["market_prices"][0].get("parsed_options")))
    fb = {"advanced_options": [{"choice": "loaded", "name": "선루프"}, {"choice": "not_loaded", "name": "기본시트"}]}
    out2 = enrich_heydealer_options(fb)
    check("loaded 폴백 (loaded만)", out2.get("parsed_options") == ["선루프"], str(out2.get("parsed_options")))


def test_kcar_3d_class():
    print("[6] 케이카 3D 분류 (Phase 5, part_codes 기준)")
    from services.part_codes import resolve_part_code, is_outer_part, is_inner_part
    # 승격 if/elif 자체는 kcar_service 인라인이라 여기서 직접 못 돌림 (cryptography 필요).
    # 대신 승격이 의존하는 분류(코드→외판/골격)를 단언한다. IDE 더미 테스트가 if/elif를 커버한다.
    check("후드=외판", is_outer_part(resolve_part_code("후드") or ""))
    check("프론트 사이드멤버=골격", is_inner_part(resolve_part_code("프론트 사이드 멤버(좌)") or ""))
    check("리어 패널=골격", is_inner_part(resolve_part_code("리어 패널") or ""))
    check("트렁크리드=외판", is_outer_part(resolve_part_code("트렁크리드") or ""))


if __name__ == "__main__":
    test_chaolma_xm3()
    test_chaolma_unpriced()
    test_sort()
    test_part_codes()
    test_heydealer()
    test_kcar_3d_class()
    print(f"\n{'ALL PASS' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
    sys.exit(1 if FAILURES else 0)
