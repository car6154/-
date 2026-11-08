# services/catalog_by_source_service.py
# 💡 [11-05 시범]: 다나와 책 쏘렌토 2022 등급별 가격 파일 시범 서비스 (크롤링 금지, 로컬 파일만 사용)

import os
import json
import re
from typing import Dict, Any, Optional

from services.data_processor import DataProcessor

CATALOG_V2_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "catalog_by_source_v2.json")

_CATALOG_V2_CACHE: Optional[Dict[str, Any]] = None

# [11-05-08] 통합 규격(build_car_spec) 비교 항목: 모두 같으면 같은 등급 판정
SPEC_COMPARE_KEYS = ("fuel", "disp", "drive", "seats", "grade_base", "grade_suffix", "is_turbo")


def load_catalog_by_source_v2() -> Dict[str, Any]:
    """로컬 catalog_by_source_v2.json 로드 (네트워크 요청 없음)"""
    global _CATALOG_V2_CACHE
    if _CATALOG_V2_CACHE is not None:
        return _CATALOG_V2_CACHE

    if not os.path.exists(CATALOG_V2_PATH):
        return {}

    try:
        with open(CATALOG_V2_PATH, "r", encoding="utf-8") as f:
            _CATALOG_V2_CACHE = json.load(f)
            return _CATALOG_V2_CACHE
    except Exception as e:
        print(f"[catalog_by_source_service] JSON 로드 오류: {e}")
        return {}


def get_pilot_catalog_spec(
    source: Optional[str],
    car_name: Optional[str],
    year: Any,
    grade: Optional[str]
) -> Dict[str, Any]:
    """
    시범 경로: 출처·차종·연식·등급 4가지가 모두 정확히 일치할 때만 스펙 및 등급별 옵션 목록 반환.
    - 하나라도 누락되거나 불일치 시 '가격 미확인' 반환.
    - 다른 출처, 다른 연식, 다른 등급의 가격으로 대체하거나 메우지 않음.
    - 별칭 추가, 기본 사전 추정치, 단어 수 폴백 일절 금지.
    """
    # 1. 필수 입력값 검증 (하나라도 비어있으면 가격 미확인)
    s_source = str(source or "").strip().lower()
    s_car = str(car_name or "").strip()
    s_year = str(year or "").strip()
    s_grade = str(grade or "").strip()

    if not s_source or not s_car or not s_year or not s_grade:
        return {
            "found": False,
            "reason": "가격 미확인 (출처·차종·연식·등급 필수 입력 누락)",
            "source": s_source or None,
            "car_name": s_car or None,
            "year": s_year or None,
            "grade": s_grade or None,
            "base_price": None,
            "base_price_man": None,
            "options": {},
            "standard_features": []
        }

    # 2. 로컬 카탈로그 탐색
    catalog = load_catalog_by_source_v2()

    # 1단계: 출처 (danawa, encar 등)
    source_book = catalog.get(s_source)
    if not source_book or not isinstance(source_book, dict):
        return {
            "found": False,
            "reason": f"가격 미확인 (출처 '{s_source}' 미등록)",
            "source": s_source,
            "car_name": s_car,
            "year": s_year,
            "grade": s_grade
        }

    # 2단계: 차종 (직접 일치 우선, 불일치 시 _find_model_in_catalog 단일 진실 공급원 적용)
    matched_car_key = None
    car_book = None

    if s_car in source_book and isinstance(source_book[s_car], dict):
        from services.option_package_service import _find_model_in_catalog
        res_model = _find_model_in_catalog(source_book, s_car, year=s_year)
        if res_model:
            matched_car_key, car_book = res_model
        else:
            matched_car_key = s_car
            car_book = source_book[s_car]
    else:
        from services.option_package_service import _find_model_in_catalog
        res_model = _find_model_in_catalog(source_book, s_car, year=s_year)
        if res_model:
            matched_car_key, car_book = res_model

    if not car_book or not isinstance(car_book, dict) or not matched_car_key:
        return {
            "found": False,
            "reason": f"가격 미확인 (차종 '{s_car}' 미등록)",
            "source": s_source,
            "car_name": s_car,
            "year": s_year,
            "grade": s_grade
        }

    # 3단계: 연식 (정규화 후 매칭)
    # 문자열에서 4자리 연도(19xx·20xx)를 먼저 찾고, 없으면 2자리 숫자에서 20xx로 변환
    m4 = re.search(r'\b(19\d{2}|20\d{2})\b', s_year) or re.search(r'(19\d{2}|20\d{2})', s_year)
    if m4:
        norm_year = m4.group(1)
    else:
        m2 = re.search(r'(\d{2})', s_year)
        if m2:
            norm_year = f"20{m2.group(1)}"
        else:
            norm_year = s_year
    year_book = car_book.get(norm_year)
    if not year_book or not isinstance(year_book, dict):
        return {
            "found": False,
            "reason": f"가격 미확인 (연식 '{norm_year}' 미등록)",
            "source": s_source,
            "car_name": s_car,
            "year": norm_year,
            "grade": s_grade
        }

    # 4단계: 등급 (통합 규격 DataProcessor.build_car_spec 기반 비교)
    matched_grade_key = None
    grade_spec = None

    # 4-1. 직접 일치 우선 확인
    if s_grade in year_book and isinstance(year_book[s_grade], dict):
        matched_grade_key = s_grade
        grade_spec = year_book[s_grade]
    else:
        # 4-2. DataProcessor.build_car_spec 기반 스펙 동등성 비교
        # 비교 항목: (fuel, disp, drive, seats, grade_base, grade_suffix, is_turbo)
        target_spec = DataProcessor.build_car_spec(text=s_grade)
        target_tuple = tuple(target_spec.get(k) for k in SPEC_COMPARE_KEYS)

        target_seats = target_spec.get("seats") or ""
        keys_no_seats = tuple(k for k in SPEC_COMPARE_KEYS if k != "seats")
        target_6_tuple = tuple(target_spec.get(k) for k in keys_no_seats)

        exact_spec_matches = []
        relaxed_seats_matches = []

        for book_g_key, book_g_spec in year_book.items():
            if isinstance(book_g_spec, dict):
                cand_spec = DataProcessor.build_car_spec(text=book_g_key)
                cand_tuple = tuple(cand_spec.get(k) for k in SPEC_COMPARE_KEYS)
                if target_tuple == cand_tuple:
                    exact_spec_matches.append((book_g_key, book_g_spec))
                else:
                    cand_seats = cand_spec.get("seats") or ""
                    one_seat_empty = bool(target_seats) ^ bool(cand_seats)
                    if one_seat_empty:
                        cand_6_tuple = tuple(cand_spec.get(k) for k in keys_no_seats)
                        if target_6_tuple == cand_6_tuple:
                            relaxed_seats_matches.append((book_g_key, book_g_spec))

        if exact_spec_matches:
            matched_grade_key, grade_spec = exact_spec_matches[0]
        elif len(relaxed_seats_matches) == 1:
            matched_grade_key, grade_spec = relaxed_seats_matches[0]

    if not grade_spec or not matched_grade_key:
        return {
            "found": False,
            "reason": f"가격 미확인 (등급 '{s_grade}' 미등록)",
            "source": s_source,
            "car_name": s_car,
            "year": norm_year,
            "grade": s_grade
        }

    # 일치 확인: 해당 등급의 기본가와 선택옵션 목록만 반환
    return {
        "found": True,
        "source": s_source,
        "car_name": matched_car_key,
        "query_car_name": s_car,
        "year": norm_year,
        "grade": matched_grade_key,
        "query_grade": s_grade,
        "base_price": grade_spec.get("base_price"),
        "base_price_man": grade_spec.get("base_price_man"),
        "options": grade_spec.get("options", {}),
        "standard_features": grade_spec.get("standard_features", [])
    }


def get_pilot_option_price(
    source: Optional[str],
    car_name: Optional[str],
    year: Any,
    grade: Optional[str],
    option_name: Optional[str]
) -> Dict[str, Any]:
    """
    시범 경로: 출처·차종·연식·등급 내에서 특정 옵션의 가격 조회.
    - 해당 등급의 options 딕셔너리에 있는 가격만 반환.
    - 기존 뭉개진 가격(93만, 88만 등)이나 단어 수 폴백 일절 금지.
    """
    spec = get_pilot_catalog_spec(source, car_name, year, grade)
    if not spec.get("found"):
        return {
            "found": False,
            "price": None,
            "price_man": None,
            "desc": None,
            "reason": spec.get("reason", "가격 미확인")
        }

    opt_key = str(option_name or "").strip()
    if not opt_key:
        return {
            "found": False,
            "price": None,
            "price_man": None,
            "desc": None,
            "reason": "옵션명 누락"
        }

    options = spec.get("options", {})
    if opt_key in options:
        opt_info = options[opt_key]
        return {
            "found": True,
            "option_name": opt_key,
            "price": opt_info.get("price"),
            "price_man": opt_info.get("price_man"),
            "desc": opt_info.get("desc", ""),
            "grade": spec.get("grade")
        }

    return {
        "found": False,
        "option_name": opt_key,
        "price": None,
        "price_man": None,
        "desc": None,
        "reason": f"가격 미확인 (등급 '{spec.get('grade')}'에 선택옵션 '{opt_key}' 미적용)"
    }
