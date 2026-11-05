# services/catalog_by_source_service.py
# 💡 [11-05 시범]: 다나와 책 쏘렌토 2022 등급별 가격 파일 시범 서비스 (크롤링 금지, 로컬 파일만 사용)

import os
import json
import re
from typing import Dict, Any, Optional

CATALOG_V2_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "catalog_by_source_v2.json")

_CATALOG_V2_CACHE: Optional[Dict[str, Any]] = None


def canonicalize_grade(grade_text: str) -> str:
    """
    [11-05-06] 카탈로그 V2 등급 표준화 (차종·등급별 예외 하드코딩 금지, 별칭 목록 금지)
    - 띄어쓰기 정리: 2.2WD -> 2.2 2WD 같은 붙은 표기 분리
    - 토큰 종류별 순서 재배열: 연료 -> 배기량 -> 구동방식 -> 트림/기타
    예: '2.2 디젤 2WD 시그니처' -> '디젤 2.2 2WD 시그니처'
        '디젤 2.2 2WD 시그니처' -> '디젤 2.2 2WD 시그니처'
    """
    if not grade_text or not str(grade_text).strip():
        return ""

    text = str(grade_text).strip()

    # 1. 붙어있는 배기량+구동방식 분리 (예: 2.2WD -> 2.2 2WD)
    text = re.sub(r'(\d\.\d)\s*(2WD|4WD|AWD)', r'\1 \2', text, flags=re.I)
    text = re.sub(r'(\d\.\d)(WD)', r'\1 2\2', text, flags=re.I)

    # 2. 토큰 분리 (공백 기준)
    raw_tokens = text.split()

    fuel_tokens = []
    disp_tokens = []
    drive_tokens = []
    trim_tokens = []

    FUEL_SET = {'디젤', '가솔린', '하이브리드', 'hev', 'phev', 'lpi', 'lpg', '전기', 'ev', '수소', 'fcev', 'diesel', 'gasoline'}
    DRIVE_SET = {'2wd', '4wd', 'awd', '2륜', '4륜', 'fwd', 'rwd'}

    for token in raw_tokens:
        tok_clean = token.strip()
        if not tok_clean:
            continue
        tok_lower = tok_clean.lower()

        # a) 배기량: 2.2, 2.0, 1.6, 2.2L 등
        if re.match(r'^\d\.\d(?:l|cc)?$', tok_lower):
            m = re.match(r'^\d\.\d', tok_lower)
            disp_tokens.append(m.group(0) if m else tok_lower)
        # b) 유종
        elif tok_lower in FUEL_SET:
            fuel_tokens.append(tok_clean)
        # c) 구동방식
        elif tok_lower in DRIVE_SET:
            drive_tokens.append(tok_clean.upper() if 'wd' in tok_lower else tok_clean)
        # d) 트림 및 나머지 모든 토큰 (시그니처, 트렌디, 5인승 등)
        else:
            trim_tokens.append(tok_clean)

    # 순서 재배열: 연료 -> 배기량 -> 구동방식 -> 트림
    ordered = fuel_tokens + disp_tokens + drive_tokens + trim_tokens
    return " ".join(ordered).strip().lower()


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

    # 2단계: 차종 (정확 일치만)
    car_book = source_book.get(s_car)
    if not car_book or not isinstance(car_book, dict):
        return {
            "found": False,
            "reason": f"가격 미확인 (차종 '{s_car}' 미등록)",
            "source": s_source,
            "car_name": s_car,
            "year": s_year,
            "grade": s_grade
        }

    # 3단계: 연식 (정확 일치만)
    # 2022, 22 등 문자열 변환 시 4자리 2022로 매칭
    norm_year = s_year if len(s_year) == 4 else (f"20{s_year}" if len(s_year) == 2 else s_year)
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

    # 4단계: 등급 (캐노니컬 표준화 비교)
    matched_grade_key = None
    grade_spec = None

    # 4-1. 직접 일치 우선 확인
    if s_grade in year_book and isinstance(year_book[s_grade], dict):
        matched_grade_key = s_grade
        grade_spec = year_book[s_grade]
    else:
        # 4-2. 토큰 종류별 순서 재배열(연료 -> 배기량 -> 구동방식 -> 트림) 캐노니컬 비교
        s_canonical = canonicalize_grade(s_grade)
        for book_g_key, book_g_spec in year_book.items():
            if isinstance(book_g_spec, dict) and canonicalize_grade(book_g_key) == s_canonical:
                matched_grade_key = book_g_key
                grade_spec = book_g_spec
                break

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
        "car_name": s_car,
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
