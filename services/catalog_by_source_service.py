# services/catalog_by_source_service.py
# 💡 [11-05 시범]: 다나와 책 쏘렌토 2022 등급별 가격 파일 시범 서비스 (크롤링 금지, 로컬 파일만 사용)

import os
import json
import re
from typing import Dict, Any, Optional

from services.data_processor import DataProcessor

CATALOG_C_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "catalog_c.json")
CATALOG_V2_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "catalog_by_source_v2.json")

_CATALOG_V2_CACHE: Optional[Dict[str, Any]] = None

# [11-05-08] 통합 규격(build_car_spec) 비교 항목: 모두 같으면 같은 등급 판정
SPEC_COMPARE_KEYS = ("fuel", "disp", "drive", "seats", "grade_base", "grade_suffix", "is_turbo")

# [11-06-52] 연료 및 파워트레인 명칭 정규화 맵 (LPe=LPG, GDe/TCe=가솔린, dCi=디젤 등 통합)
FUEL_NORM_MAP = {
    # LPG 계열
    'lpg': 'LPG', 'lpe': 'LPG', 'lpi': 'LPG',
    # 가솔린 계열
    '가솔린': '가솔린', 'gasoline': '가솔린', 'gde': '가솔린', 'tce': '가솔린',
    'gdi': '가솔린', 'tgdi': '가솔린', 't-gdi': '가솔린', 'mpi': '가솔린',
    'tsi': '가솔린', 'tfsi': '가솔린',
    # 디젤 계열
    '디젤': '디젤', 'diesel': '디젤', 'dci': '디젤', 'crdi': '디젤',
    'vgt': '디젤', 'e-vgt': '디젤', 'tdi': '디젤',
    # 하이브리드 계열
    '하이브리드': '하이브리드', 'hybrid': '하이브리드', 'hev': '하이브리드', 'phev': '하이브리드',
    # 전기 계열
    '전기': '전기', 'electric': '전기', 'ev': '전기',
    # 수소 계열
    '수소': '수소', 'fcev': '수소',
    # CNG
    'cng': 'CNG'
}


def extract_fuel_norm(raw: str) -> str:
    """연료 별칭을 표준 명칭(LPG, 가솔린, 디젤, 하이브리드, 전기, 수소, CNG)으로 정규화"""
    clean = str(raw or "").lower()
    for k, v in FUEL_NORM_MAP.items():
        if re.search(rf'(?:\b|[^a-zA-Z0-9가-힣]){re.escape(k)}(?:\b|[^a-zA-Z0-9가-힣]|$)', clean):
            return v
    for k in ['가솔린', '디젤', '하이브리드', '전기', '수소']:
        if k in clean:
            return FUEL_NORM_MAP[k]
    from services.model_matcher import ModelMatcher
    f = ModelMatcher.extract_fuel(raw) or ""
    return FUEL_NORM_MAP.get(f.lower(), f)


def get_base_model_family(car_name: str) -> str:
    """차종명에서 세대 수식어(더 뉴, 올 뉴, 뉴, 디 올 뉴, F/L, FL, 페이스리프트 등)를 제거하여 기본 모델 패밀리명 추출"""
    s = str(car_name or "").strip()
    s = re.sub(r'\([^\)]*\)', ' ', s)
    s = re.sub(r'(?i)\b(f/l|fl|facelift|페이스리프트)\b', ' ', s)
    s = re.sub(r'(?i)(f/l|fl|facelift|페이스리프트)', ' ', s)
    s = re.sub(r'\b(더\s*뉴|올\s*뉴|디\s*올\s*뉴|뉴|new|the\s*new|all\s*new)\b', ' ', s, flags=re.IGNORECASE)
    s = re.sub(r'\b\d+세대\b', ' ', s)
    return s.strip()


def extract_pure_trim(text: str) -> str:
    """연료, 배기량, 구동, 인승, 밴, 변속기 및 연료별칭(LPe, GDe 등) 규격 요소를 제외한 순수 트림명 추출"""
    s = str(text or "").strip()
    s = re.sub(r'\([^\)]*\)', ' ', s)
    s = re.sub(r'\d+인승', ' ', s)
    s = re.sub(r'(?i)\b(2wd|4wd|awd|fwd|rwd|4륜|2륜|htrac)\b', ' ', s)
    # [11-06-52] 연료 및 파워트레인 약어 완전 제거
    fuel_patterns = r'(?i)\b(가솔린|디젤|lpg|lpe|lpi|gde|tce|gdi|tgdi|t-gdi|mpi|tsi|tfsi|dci|crdi|vgt|e-vgt|tdi|하이브리드|hybrid|hev|phev|전기|electric|ev|수소|fcev|cng)\b'
    s = re.sub(fuel_patterns, ' ', s)
    s = re.sub(r'(가솔린|디젤|lpg|하이브리드|전기|cng|수소)', ' ', s, flags=re.IGNORECASE)
    s = re.sub(r'\b\d+\.\d+\b', ' ', s)
    s = re.sub(r'\b\d{3,4}\s*cc\b', ' ', s, flags=re.IGNORECASE)
    s = re.sub(r'(?i)\b(밴|van|카고)\b', ' ', s)
    s = re.sub(r'(?i)\b(m/t|a/t|cvt|dct|수동|오토)\b', ' ', s)
    # [11-06-68] 단일 트림 및 기본 수식어 제거 ("기본형", "기본", "표준형")
    s = re.sub(r'(?i)\b(기본형|기본|표준형)\b', ' ', s)
    s = re.sub(r'(기본형|기본|표준형)', ' ', s)

    tokens = [t.strip().lower() for t in s.split() if t.strip()]
    return ' '.join(tokens)


def parse_grade_tokens(text: str) -> dict:
    """등급 문자열에서 다차원 스펙 토큰 파싱 (연료 별칭 정규화, 배기량, 구동, 인승, 바디타입, 변속기, 트림)"""
    raw = str(text or "").strip()
    clean = raw.lower()

    # 1. body_type (밴/승용 구분)
    is_van = bool(re.search(r'(?:\b|[^a-zA-Z0-9가-힣])(?:밴|van|카고)(?:\b|[^a-zA-Z0-9가-힣]|$)', clean))
    body_type = 'van' if is_van else 'passenger'

    # 2. transmission (수동 여부)
    is_manual = bool(re.search(r'(?i)(?:\b|[^a-zA-Z0-9가-힣])(?:m/t|mt|수동)(?:\b|[^a-zA-Z0-9가-힣]|$)', clean))

    # 3. fuel (연료 별칭 표준화: LPe=LPG, GDe=가솔린 등)
    fuel = extract_fuel_norm(raw)

    # 4. disp (소수점 첫째 자리 반올림 / 1.35L 등 오차 정규화)
    disp = ""
    m_disp = re.search(r'(\d+\.\d+)', raw)
    if m_disp:
        try:
            val = float(m_disp.group(1))
            if 1.33 <= val <= 1.36:
                disp = "1.3"
            else:
                disp = f"{round(val, 1):.1f}"
        except Exception:
            disp = ""
    else:
        m_cc = re.search(r'(\d{3,4})\s*cc', raw, re.IGNORECASE)
        if m_cc:
            try:
                cc_val = int(m_cc.group(1))
                if 1300 <= cc_val <= 1360:
                    disp = "1.3"
                else:
                    disp = f"{round(cc_val / 1000.0, 1):.1f}"
            except Exception:
                disp = ""

    # 5. drive
    m_drive = re.search(r'(2wd|4wd|awd|htrac|4륜|2륜|fwd|rwd)', clean)
    if m_drive:
        d_val = m_drive.group(1)
        if d_val in ['4wd', 'awd', 'htrac', '4륜']:
            drive = '4wd'
        else:
            drive = '2wd'
    else:
        drive = None

    # 6. seats
    m_seat = re.search(r'(\d+인승)', raw)
    seats = m_seat.group(1) if m_seat else ""

    # 7. grade_base & grade_suffix
    spec = DataProcessor.build_car_spec(text=raw)
    grade_base = spec.get("grade_base") or ""
    grade_suffix = spec.get("grade_suffix") or ""

    # 8. pure_trim (사전에 없는 신규/영문/숫자 트림명 대응)
    pure_trim = extract_pure_trim(raw)

    # 9. [11-06-59] 특수 바디(쿠페) 및 블랙 에디션 구분 플래그
    is_coupe = bool(re.search(r'(?i)(?:쿠페|coupe)', clean))
    is_black = bool(re.search(r'(?i)(?:블랙|black)', clean))

    return {
        "fuel": fuel,
        "disp": disp,
        "drive": drive,
        "seats": seats,
        "body_type": body_type,
        "is_manual": is_manual,
        "is_coupe": is_coupe,
        "is_black": is_black,
        "grade_base": grade_base,
        "grade_suffix": grade_suffix,
        "pure_trim": pure_trim,
        "raw_text": raw
    }


def match_catalog_grade(query_grade: str, year_book: dict):
    """
    [11-06-51, 11-06-59] 통합 등급 매칭 엔진 (단일 진실 공급원)
    - 1단계: 완전 일치 (Exact match) 우선
    - 2단계: 다차원 규격(바디타입, 쿠페여부, 블랙에디션여부, 수동변속기, 연료, 배기량, 구동, 트림) 필터링
      * [11-06-59] 수동(M/T) 전용 상용차(포터2/봉고3/라보/마이티 등) 변속기 미명시 쿼리 자동 Fallback 지원
      * [11-06-59] 배기량 명시 쿼리 시 배기량 누락 키 배제 우선순위 적용
    - 3단계: 인승(seats) 우선순위 정제 (동일 인승 일치 -> 책에 인승 없는 승용차 -> 기본 5인승 순서)
    - 4단계: 복수 후보 정제
      * 구동방식 명시 토큰 일치 (AWD vs 4WD 우선순위)
      * 연료 명시 토큰 일치 (하이브리드 vs HEV 우선순위)
      * A/T 표기가 없는 순수 트림 우선 선택
      * pure_trim 완전 일치 우선 선택
      * 동일 스펙/동일 가격 복수 키 수렴
      * 동일 스펙 연식변경/신차가격 개정 복수 키 최종 수렴 (Fail-Safe)
    """
    if not query_grade or not year_book:
        return None

    # 1. 완전 일치
    if query_grade in year_book and isinstance(year_book[query_grade], dict):
        return query_grade, year_book[query_grade]

    q = parse_grade_tokens(query_grade)
    clean_q = query_grade.lower()
    effective_q_drive = q["drive"] if q["drive"] else "2wd"

    candidates = []
    for book_key, book_spec in year_book.items():
        if isinstance(book_spec, dict):
            c = parse_grade_tokens(book_key)
            candidates.append((book_key, book_spec, c))

    # 1단계: 기본 스펙(바디타입, 쿠페, 블랙, 연료, 배기량, 구동, 트림) 필터링
    # [11-06-59] 오토/수동 후보군 분리 수집 (상용차 수동 전용 차종 Fallback 지원)
    auto_matched = []
    manual_matched = []

    for b_key, b_spec, c in candidates:
        # 바디타입 불일치 제외 (밴 vs 승용)
        if q["body_type"] != c["body_type"]:
            continue
        # 쿠페 불일치 제외 (일반 SUV/세단 vs 쿠페 바디)
        if q["is_coupe"] != c["is_coupe"]:
            continue
        # 블랙 에디션 불일치 제외 (일반 트림 vs 블랙 전용 에디션)
        if q["is_black"] != c["is_black"]:
            continue
        # 연료 불일치 제외
        if q["fuel"] and c["fuel"] and q["fuel"] != c["fuel"]:
            continue
        # 배기량 불일치 제외
        if q["disp"] and c["disp"] and q["disp"] != c["disp"]:
            continue
        # 구동방식 매칭: 쿼리에 구동방식이 명시되었으면 엄격 일치, 없으면 2WD 우선
        cand_drive = c["drive"] if c["drive"] else "2wd"
        if q["drive"]:
            if q["drive"] != cand_drive:
                continue
        else:
            if effective_q_drive != cand_drive:
                continue

        # 트림 일치 검사 (grade_base 또는 pure_trim)
        trim_matched = False
        if q["grade_base"] and c["grade_base"]:
            if q["grade_base"] == c["grade_base"]:
                q_suf = (q["grade_suffix"] or "").strip().lower()
                c_suf = (c["grade_suffix"] or "").strip().lower()
                if q_suf == c_suf:
                    trim_matched = True
        elif q["pure_trim"] and c["pure_trim"]:
            if q["pure_trim"] == c["pure_trim"]:
                trim_matched = True
            elif q["pure_trim"] in c["pure_trim"] or c["pure_trim"] in q["pure_trim"]:
                trim_matched = True
        elif not q["grade_base"] and not q["pure_trim"]:
            # [11-06-59] 단일 트림 모델 (제네시스 등 서브트림명 없이 배기량/구동으로만 구성된 차종)
            if not c["grade_base"] and not c["pure_trim"]:
                trim_matched = True

        if not trim_matched:
            continue

        if c["is_manual"]:
            manual_matched.append((b_key, b_spec, c))
        else:
            auto_matched.append((b_key, b_spec, c))

    # [11-06-59] 변속기 결정:
    if q["is_manual"]:
        pre_matched = manual_matched
    else:
        # 쿼리에 수동이 없으면 오토 후보 우선, 오토 후보가 없으면 수동 전용 차종 허용
        if auto_matched:
            pre_matched = auto_matched
        else:
            pre_matched = manual_matched

    if not pre_matched:
        return None

    # [11-06-59] 배기량 명시 우선: 쿼리에 배기량이 있을 때, 후보 중 배기량이 일치하는 후보가 있으면 배기량 빈 후보 제외 (레이, 모닝 등)
    if q["disp"]:
        disp_exact = [item for item in pre_matched if item[2]["disp"] == q["disp"]]
        if disp_exact:
            pre_matched = disp_exact

    # 2단계: 인승(seats) 우선순위 정제
    if q["seats"]:
        seat_matches = [item for item in pre_matched if item[2]["seats"] == q["seats"]]
        if seat_matches:
            final_cands = seat_matches
        else:
            final_cands = [item for item in pre_matched if not item[2]["seats"]]
    else:
        no_seat_matches = [item for item in pre_matched if not item[2]["seats"]]
        if no_seat_matches:
            final_cands = no_seat_matches
        else:
            # [11-06-59] 책에 5/6/7인승이 있고 쿼리에 인승이 없으면 기본 승용 5인승 우선
            standard_5_seats = [item for item in pre_matched if item[2]["seats"] == "5인승"]
            if standard_5_seats:
                final_cands = standard_5_seats
            else:
                final_cands = pre_matched

    if len(final_cands) == 1:
        return final_cands[0][0], final_cands[0][1]

    # [11-06-59] 구동방식 명시 토큰 일치 (AWD vs 4WD 복수 키 충돌 해결)
    if 'awd' in clean_q:
        awd_matches = [item for item in final_cands if 'awd' in item[0].lower()]
        if len(awd_matches) == 1:
            return awd_matches[0][0], awd_matches[0][1]
        elif len(awd_matches) > 1:
            final_cands = awd_matches
    elif '4wd' in clean_q or '4륜' in clean_q:
        four_wd_matches = [item for item in final_cands if '4wd' in item[0].lower() or '4륜' in item[0].lower()]
        if len(four_wd_matches) == 1:
            return four_wd_matches[0][0], four_wd_matches[0][1]
        elif len(four_wd_matches) > 1:
            final_cands = four_wd_matches

    # [11-06-59] 연료 명시 토큰 일치 (하이브리드 vs HEV 복수 키 충돌 해결)
    if '하이브리드' in clean_q:
        hyb_matches = [item for item in final_cands if '하이브리드' in item[0]]
        if len(hyb_matches) == 1:
            return hyb_matches[0][0], hyb_matches[0][1]
        elif len(hyb_matches) > 1:
            final_cands = hyb_matches
    elif 'hev' in clean_q:
        hev_matches = [item for item in final_cands if 'hev' in item[0].lower()]
        if len(hev_matches) == 1:
            return hev_matches[0][0], hev_matches[0][1]
        elif len(hev_matches) > 1:
            final_cands = hev_matches

    # pure_trim 완전 일치 우선
    if q["pure_trim"]:
        pure_exact = [item for item in final_cands if item[2]["pure_trim"] == q["pure_trim"]]
        if len(pure_exact) == 1:
            return pure_exact[0][0], pure_exact[0][1]
        elif len(pure_exact) > 1:
            final_cands = pure_exact

    # 3단계: 후보가 2개 이상일 때 (예: '모던' vs '모던 A/T')
    # A/T 표기가 없는 순수 트림 우선 선택
    no_at_cands = [item for item in final_cands if 'a/t' not in item[0].lower()]
    if len(no_at_cands) == 1:
        return no_at_cands[0][0], no_at_cands[0][1]
    elif len(no_at_cands) > 1:
        final_cands = no_at_cands

    # 4) 동일 스펙·동일 가격의 표기 변형 복수 키인 경우 (예: '2.0 LPG 2WD RE' vs 'lpg 2.0 2WD RE')
    prices = [item[1].get('base_price') for item in final_cands if isinstance(item[1], dict)]
    if len(prices) == len(final_cands) and len(set(prices)) == 1 and prices[0] is not None:
        return final_cands[0][0], final_cands[0][1]

    # 5) 완전 일치 후보가 있는지
    for b_key, b_spec, _ in final_cands:
        if b_key == query_grade:
            return b_key, b_spec

    # 6) [11-06-59] 2WD vs RWD 등 표기 변형 중 2WD 기본형 우선 선택
    two_wd_cands = [item for item in final_cands if '2wd' in item[0].lower()]
    if len(two_wd_cands) == 1:
        return two_wd_cands[0][0], two_wd_cands[0][1]
    elif len(two_wd_cands) > 1:
        final_cands = two_wd_cands

    # 💡 [11-11-17]: 엔카(encar) 출처 우선 선택 (11-11-13 규칙)
    # 복수 후보(예: QM6 RE 엔카 32,200,000원 vs 다나와 32,900,000원/33,400,000원) 중 엔카 공식 출처 우선 확정
    encar_cands = [item for item in final_cands if item[1].get('source') == 'encar']
    if len(encar_cands) == 1:
        return encar_cands[0][0], encar_cands[0][1]
    elif len(encar_cands) > 1:
        final_cands = encar_cands

    # [11-06-59] 동일 트림 연식변경/신차가격 개정 등으로 동일 규격 내 복수 가격 공존 시 첫 번째 유효 후보 확정
    if final_cands:
        return final_cands[0][0], final_cands[0][1]

    return None


def load_catalog_by_source_v2() -> Dict[str, Any]:
    """
    [11-11-17] 제이책(C) 로드 (우선) 및 구형 V2 책 폴백 (안전장치)
    - data/catalog_c.json 우선 로드하여 danawa/encar/c 키 및 모델 직접 접근 딕셔너리로 제공
    - data/catalog_c.json 로드 실패 시 기존 data/catalog_by_source_v2.json으로 폴백
    """
    global _CATALOG_V2_CACHE
    if _CATALOG_V2_CACHE is not None:
        return _CATALOG_V2_CACHE

    # 1. 제이책(C) 우선 로드 시도
    if os.path.exists(CATALOG_C_PATH):
        try:
            with open(CATALOG_C_PATH, "r", encoding="utf-8") as f:
                cat_c = json.load(f)
            if cat_c and isinstance(cat_c, dict):
                # 기존 코드가 .get("danawa") 또는 .get("encar") 또는 .get(source)를 호출하므로 모두 제이책 C로 연결
                wrapped = {
                    "c": cat_c,
                    "danawa": cat_c,
                    "encar": cat_c,
                    **cat_c
                }
                _CATALOG_V2_CACHE = wrapped
                return _CATALOG_V2_CACHE
        except Exception as e:
            print(f"[catalog_by_source_service] 제이책(C) 로드 실패: {e}, 구형 V2 책으로 폴백합니다.")

    # 2. 폴백: 기존 catalog_by_source_v2.json
    if os.path.exists(CATALOG_V2_PATH):
        try:
            with open(CATALOG_V2_PATH, "r", encoding="utf-8") as f:
                _CATALOG_V2_CACHE = json.load(f)
                return _CATALOG_V2_CACHE
        except Exception as e:
            print(f"[catalog_by_source_service] 구형 V2 책 JSON 로드 오류: {e}")
            return {}

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
            "standard_features": [],
            "accessories": {},
            "notices": []
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
    matched_grade_key = None
    grade_spec = None

    # 4단계: 등급 매칭 (1차: 현재 차종의 해당 연식 탐색)
    if year_book and isinstance(year_book, dict):
        res_grade = match_catalog_grade(s_grade, year_book)
        if res_grade:
            matched_grade_key = res_grade[0]
            grade_spec = res_grade[1]

    # [11-06-52] 4-2. 차종 패밀리 연식·등급 폴백:
    # 조회 차종에 해당 연식이 없거나 등급이 불일치할 때, 같은 계열의 다른 차종명(예: '더 뉴 QM6' -> 'QM6')에 해당 연식·등급이 있는지 확인
    if not grade_spec:
        base_family = get_base_model_family(s_car)
        if base_family:
            family_candidates = []
            for cand_name, cand_book in source_book.items():
                if cand_name == matched_car_key:
                    continue
                if isinstance(cand_book, dict):
                    cand_base = get_base_model_family(cand_name)
                    if cand_base and (cand_base.lower() == base_family.lower() or base_family.lower() in cand_name.lower()):
                        if norm_year in cand_book and isinstance(cand_book[norm_year], dict):
                            family_candidates.append((cand_name, cand_book, cand_book[norm_year]))

            # 패밀리 후보들 중 연식과 등급이 정확히 일치하는 단일 후보 탐색
            family_matches = []
            for f_name, f_book, f_ybook in family_candidates:
                f_res = match_catalog_grade(s_grade, f_ybook)
                if f_res:
                    family_matches.append((f_name, f_book, f_ybook, f_res))

            if len(family_matches) == 1:
                f_name, f_book, f_ybook, f_res = family_matches[0]
                matched_car_key = f_name
                car_book = f_book
                year_book = f_ybook
                matched_grade_key = f_res[0]
                grade_spec = f_res[1]

    if not year_book or not isinstance(year_book, dict):
        return {
            "found": False,
            "reason": f"가격 미확인 (연식 '{norm_year}' 미등록)",
            "source": s_source,
            "car_name": s_car,
            "year": norm_year,
            "grade": s_grade
        }

    if not grade_spec or not matched_grade_key:
        return {
            "found": False,
            "reason": f"가격 미확인 (등급 '{s_grade}' 미등록)",
            "source": s_source,
            "car_name": matched_car_key or s_car,
            "year": norm_year,
            "grade": s_grade
        }

    # 일치 확인: 해당 등급의 기본가와 선택옵션, 액세서리, 안내문구 목록 반환
    base_price = grade_spec.get("base_price") or grade_spec.get("price")
    base_price_man = grade_spec.get("base_price_man") or grade_spec.get("price_man")
    if base_price_man is None and base_price is not None:
        base_price_man = round(base_price / 10000)
    standard_features = grade_spec.get("standard_features") or grade_spec.get("standard_specs", [])

    # [11-11-17] 옵션별 price_man 자동 보충 (UI 표시 보장)
    raw_options = grade_spec.get("options", {})
    cleaned_options = {}
    if isinstance(raw_options, dict):
        for ok, ov in raw_options.items():
            if isinstance(ov, dict):
                op = ov.get("price")
                op_man = ov.get("price_man")
                if op_man is None and op is not None:
                    op_man = round(op / 10000)
                cleaned_options[ok] = {
                    **ov,
                    "price_man": op_man
                }
            else:
                cleaned_options[ok] = ov

    return {
        "found": True,
        "source": grade_spec.get("source", s_source),
        "car_name": matched_car_key,
        "query_car_name": s_car,
        "year": norm_year,
        "grade": matched_grade_key,
        "query_grade": s_grade,
        "base_price": base_price,
        "base_price_man": base_price_man,
        "options": cleaned_options,
        "standard_features": standard_features,
        "accessories": grade_spec.get("accessories", {}),
        "notices": grade_spec.get("notices") or (year_book.get("_notices") if isinstance(year_book, dict) else []) or []
    }


def merge_options_and_accessories(options: Optional[dict], accessories: Optional[dict]) -> dict:
    """
    신차 선택 옵션(options)과 커스터마이징 액세서리(accessories)를 안전하게 단일 풀로 병합.
    - options(출고 정규 옵션)가 최우선 순위이며, accessories의 0원/None 가격이 options의 정상 유효 가격(>0)을 덮어쓰지 않는다.
    - 동일 키가 양쪽에 존재할 때:
      1) options에 유효한 가격(>0)이 있으면 options 보존 (accessories의 0원 덮어쓰기 원천 차단)
      2) options 가격이 0/None이고 accessories에 유효한 가격(>0)이 있으면 accessories 가격 채택
      3) options에 없는 신규 액세서리는 그대로 풀에 추가
    """
    merged: Dict[str, Any] = {}
    if isinstance(options, dict):
        for k, v in options.items():
            merged[k] = dict(v) if isinstance(v, dict) else v

    if isinstance(accessories, dict):
        for k, v in accessories.items():
            if k not in merged:
                merged[k] = dict(v) if isinstance(v, dict) else v
            else:
                cur_item = merged[k]
                cur_p = cur_item.get("price") if isinstance(cur_item, dict) else cur_item
                new_p = v.get("price") if isinstance(v, dict) else v

                cur_valid = cur_p is not None and isinstance(cur_p, (int, float)) and cur_p > 0
                new_valid = new_p is not None and isinstance(new_p, (int, float)) and new_p > 0

                # options에 유효 가격이 없는데 accessories에 유효 가격이 있으면 갱신
                if not cur_valid and new_valid:
                    merged[k] = dict(v) if isinstance(v, dict) else v

    return merged


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

    opt_key = re.sub(r'^\++', '', str(option_name or "")).strip()
    if not opt_key:
        return {
            "found": False,
            "price": None,
            "price_man": None,
            "desc": None,
            "reason": "옵션명 누락"
        }

    # [11-06-75] options와 accessories를 안전하게 단일 풀로 병합 (0원 accessories의 options 가격 덮어쓰기 방어)
    items_pool = merge_options_and_accessories(spec.get("options", {}), spec.get("accessories", {}))

    # 1. 직접 일치
    if opt_key in items_pool:
        opt_info = items_pool[opt_key]
        return {
            "found": True,
            "option_name": opt_key,
            "price": opt_info.get("price") if isinstance(opt_info, dict) else opt_info,
            "price_man": opt_info.get("price_man") if isinstance(opt_info, dict) else None,
            "desc": opt_info.get("desc", "") if isinstance(opt_info, dict) else "",
            "grade": spec.get("grade")
        }

    # 2. 별칭 사전 적용
    from services.option_package_service import OPTION_ALIAS_MAP, normalize_opt_name

    clean_alias = OPTION_ALIAS_MAP.get(opt_key, opt_key)
    if clean_alias in items_pool:
        opt_info = items_pool[clean_alias]
        return {
            "found": True,
            "option_name": clean_alias,
            "price": opt_info.get("price") if isinstance(opt_info, dict) else opt_info,
            "price_man": opt_info.get("price_man") if isinstance(opt_info, dict) else None,
            "desc": opt_info.get("desc", "") if isinstance(opt_info, dict) else "",
            "grade": spec.get("grade")
        }

    # 3. 정규화 일치
    norm_key = normalize_opt_name(clean_alias)
    for off_k, off_v in items_pool.items():
        if normalize_opt_name(off_k) == norm_key:
            return {
                "found": True,
                "option_name": off_k,
                "price": off_v.get("price") if isinstance(off_v, dict) else off_v,
                "price_man": off_v.get("price_man") if isinstance(off_v, dict) else None,
                "desc": off_v.get("desc", "") if isinstance(off_v, dict) else "",
                "grade": spec.get("grade")
            }

    return {
        "found": False,
        "option_name": opt_key,
        "price": None,
        "price_man": None,
        "desc": None,
        "reason": f"가격 미확인 (등급 '{spec.get('grade')}'에 선택옵션/액세서리 '{opt_key}' 미적용)"
    }


_CATALOG_V2_TREE_CACHE: Optional[Dict[str, Any]] = None


def get_catalog_v2_tree() -> Dict[str, Any]:
    """
    V2 카탈로그(danawa)의 브랜드 -> 차종 -> 연식 -> 등급 목록 계층 트리 반환.
    뷰어 연쇄 드롭다운용 초경량 메타데이터.
    """
    global _CATALOG_V2_TREE_CACHE
    if _CATALOG_V2_TREE_CACHE is not None:
        return _CATALOG_V2_TREE_CACHE

    full_catalog = load_catalog_by_source_v2()
    danawa = full_catalog.get("danawa", {})

    targets_path = os.path.join(os.path.dirname(__file__), "..", "data", "danawa_model_targets.json")
    brand_lookup = {}
    brand_name_map = {
        '303': '현대', '307': '기아', '304': '제네시스', '306': '쉐보레', '326': 'KGM', '321': '르노코리아'
    }
    if os.path.exists(targets_path):
        try:
            with open(targets_path, "r", encoding="utf-8") as f:
                targets = json.load(f)
            for mid, t in targets.items():
                bid = str(t.get('brand_id'))
                bname = brand_name_map.get(bid)
                if bname:
                    name = t.get('name', '')
                    brand_lookup[name] = bname
        except Exception:
            pass

    from services.danawa_crawler import normalize_catalog_model_name
    norm_brand_lookup = {normalize_catalog_model_name(k): v for k, v in brand_lookup.items()}

    def _classify_brand(mname: str) -> str:
        if mname in brand_lookup:
            return brand_lookup[mname]
        norm = normalize_catalog_model_name(mname)
        if norm in norm_brand_lookup:
            return norm_brand_lookup[norm]
        if any(k in mname for k in ['G70', 'G80', 'G90', 'GV60', 'GV70', 'GV80']):
            return '제네시스'
        if any(k in mname for k in ['K3', 'K5', 'K7', 'K8', 'K9', '카니발', '쏘렌토', '스포티지', '셀토스', '모닝', '레이', '니로', 'EV', '봉고', '타스만', 'PV5', '스팅어', '스토닉', '모하비', '오피러스', '프라이드', '포르테', '로체', '카렌스', '쏘울']):
            return '기아'
        if any(k in mname for k in ['트레일블레이저', '트랙스', '스파크', '말리부', '이쿼녹스', '트래버스', '타호', '콜로라도', '볼트', '크루즈', '임팔라', '올란도', '아베오', '알페온', '카마로']):
            return '쉐보레'
        if any(k in mname for k in ['티볼리', '토레스', '렉스턴', '코란도', '액티언', '무쏘', '체어맨', '로디우스', '투리스모', '카이런']):
            return 'KGM'
        if any(k in mname for k in ['QM', 'SM', 'XM', '아르카나', '콜레오스', '세닉', '마스터', '캡처', '조에', '트위지', '클리오']):
            return '르노코리아'
        return '현대'

    ordered_brands = ["현대", "기아", "제네시스", "쉐보레", "KGM", "르노코리아"]
    tree: Dict[str, Dict[str, Dict[str, List[str]]]] = {b: {} for b in ordered_brands}

    for mname, mdata in danawa.items():
        brand = _classify_brand(mname)
        if brand not in tree:
            tree[brand] = {}
        tree[brand][mname] = {}
        for y, ydata in mdata.items():
            tree[brand][mname][y] = list(ydata.keys())

    _CATALOG_V2_TREE_CACHE = {
        "success": True,
        "brands": ordered_brands,
        "tree": tree
    }
    return _CATALOG_V2_TREE_CACHE
