# services/catalog_c_service.py
"""
[11-11-15] 제이책(C) 카탈로그 서비스
- data/catalog_c.json 및 가격 충돌 로그 data/catalog_c_price_conflicts_v2_2026-11-12.json 조회
- 엔드포인트:
  - get_catalog_c_tree(): 6대 브랜드 -> 차종 -> 연식 계층 트리 반환
  - get_catalog_c_spec(car_name, year, grade): 모델·연식의 전체 등급 스펙 및 지정 등급 조회
"""

import os
import json
import re
from typing import Dict, Any, Optional, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CATALOG_C_FILE = os.path.join(DATA_DIR, "catalog_c.json")
CONFLICTS_FILE = os.path.join(DATA_DIR, "catalog_c_price_conflicts_v3_2026-11-12.json")
TARGETS_INDEX_FILE = os.path.join(DATA_DIR, "encar_crawl_targets_index.json")
MODEL_GROUPS_FILE = os.path.join(DATA_DIR, "catalog_c_model_groups_2026-11-12.json")

_CATALOG_C_CACHE: Optional[Dict[str, Any]] = None
_CONFLICTS_INDEX_CACHE: Optional[Dict[str, Any]] = None
_CATALOG_C_TREE_CACHE: Optional[Dict[str, Any]] = None
_CATALOG_C_STATS_CACHE: Optional[Dict[str, Any]] = None
_CATALOG_C_HIERARCHY_CACHE: Optional[Dict[str, Any]] = None


def load_catalog_c() -> Dict[str, Any]:
    global _CATALOG_C_CACHE
    if _CATALOG_C_CACHE is not None:
        return _CATALOG_C_CACHE
    if not os.path.exists(CATALOG_C_FILE):
        return {}
    try:
        with open(CATALOG_C_FILE, "r", encoding="utf-8") as f:
            _CATALOG_C_CACHE = json.load(f)
            return _CATALOG_C_CACHE
    except Exception as e:
        print(f"[CatalogC] catalog_c.json 로드 실패: {e}")
        return {}


def load_conflicts_index() -> Dict[str, Any]:
    """
    (model, year, grade_name) -> 충돌 정보 딕셔너리 매핑
    """
    global _CONFLICTS_INDEX_CACHE
    if _CONFLICTS_INDEX_CACHE is not None:
        return _CONFLICTS_INDEX_CACHE
    if not os.path.exists(CONFLICTS_FILE):
        return {}
    try:
        with open(CONFLICTS_FILE, "r", encoding="utf-8") as f:
            conflicts_list = json.load(f)
        idx = {}
        for c in conflicts_list:
            m = c.get("model", "")
            y = str(c.get("year", ""))
            trim = c.get("trim", "")
            fuel = c.get("fuel", "")
            grades = c.get("grades", [])
            for g in grades:
                gname = g.get("name", "")
                key = f"{m}::{y}::{gname}"
                idx[key] = {
                    "trim": trim,
                    "fuel": fuel,
                    "conflict_grades": grades
                }
        _CONFLICTS_INDEX_CACHE = idx
        return _CONFLICTS_INDEX_CACHE
    except Exception as e:
        print(f"[CatalogC] conflicts index 로드 실패: {e}")
        return {}


def get_catalog_c_stats() -> Dict[str, Any]:
    """
    제이책(C) 실시간 요약 통계 (차종 수, 연식 수, 등급 수, 옵션 수)
    """
    global _CATALOG_C_STATS_CACHE
    if _CATALOG_C_STATS_CACHE is not None:
        return _CATALOG_C_STATS_CACHE

    catalog = load_catalog_c()
    if not catalog:
        return {"total_models": 0, "total_years": 0, "total_grades": 0, "total_options": 0}

    total_models = len(catalog)
    total_years = sum(len(yrs) for yrs in catalog.values())
    total_grades = sum(len(g) for yrs in catalog.values() for g in yrs.values())
    total_options = sum(len(gdata.get("options", {})) for yrs in catalog.values() for grades in yrs.values() for gdata in grades.values())

    _CATALOG_C_STATS_CACHE = {
        "total_models": total_models,
        "total_years": total_years,
        "total_grades": total_grades,
        "total_options": total_options,
        "summary_text": f"{total_models:,}개 차종 · {total_years:,}개 연식 · {total_grades:,}개 등급 탑재"
    }
    return _CATALOG_C_STATS_CACHE


def get_catalog_c_tree() -> Dict[str, Any]:
    """
    브랜드 -> 차종 -> 연식 목록 계층 트리 반환
    """
    global _CATALOG_C_TREE_CACHE
    if _CATALOG_C_TREE_CACHE is not None:
        return _CATALOG_C_TREE_CACHE

    catalog = load_catalog_c()
    if not catalog:
        return {}

    # 브랜드 매핑 로드
    model_to_brand = {}
    if os.path.exists(TARGETS_INDEX_FILE):
        try:
            with open(TARGETS_INDEX_FILE, "r", encoding="utf-8") as f:
                targets = json.load(f)
            for t in targets:
                mname = t.get("model_name")
                bname = t.get("mfg_name")
                if mname and bname:
                    model_to_brand[mname] = bname
        except Exception:
            pass

    ordered_brands = ["현대", "기아", "제네시스", "쉐보레", "KGM", "르노코리아"]
    tree: Dict[str, Dict[str, List[str]]] = {b: {} for b in ordered_brands}

    for model, yrs in catalog.items():
        brand = model_to_brand.get(model, "현대")
        if brand not in tree:
            tree[brand] = {}
        sorted_years = sorted(list(yrs.keys()), key=lambda x: int(re.sub(r'\D', '', x) or 0), reverse=True)
        tree[brand][model] = sorted_years

    # 빈 브랜드 제거 및 정렬
    clean_tree = {b: tree[b] for b in ordered_brands if tree.get(b)}
    _CATALOG_C_TREE_CACHE = clean_tree
    return _CATALOG_C_TREE_CACHE


def get_catalog_c_hierarchy() -> Dict[str, Any]:
    """
    [11-11-23] 제조사 -> 차종묶음 -> 세부모델 -> 연식 목록 4계층 반환
    """
    global _CATALOG_C_HIERARCHY_CACHE
    if _CATALOG_C_HIERARCHY_CACHE is not None:
        return _CATALOG_C_HIERARCHY_CACHE

    catalog = load_catalog_c()
    if not catalog:
        return {}

    ordered_brands = ["현대", "기아", "제네시스", "쉐보레", "KGM", "르노코리아"]
    hierarchy: Dict[str, Dict[str, Dict[str, List[str]]]] = {b: {} for b in ordered_brands}

    if os.path.exists(MODEL_GROUPS_FILE):
        try:
            with open(MODEL_GROUPS_FILE, "r", encoding="utf-8") as f:
                group_data = json.load(f)
            raw_hierarchy = group_data.get("hierarchy", {})
            for b in ordered_brands:
                b_groups = raw_hierarchy.get(b, {})
                for gname, models in b_groups.items():
                    hierarchy[b][gname] = {}
                    for m in models:
                        yrs = catalog.get(m, {})
                        sorted_years = sorted(list(yrs.keys()), key=lambda x: int(re.sub(r'\D', '', x) or 0), reverse=True)
                        hierarchy[b][gname][m] = sorted_years
        except Exception as e:
            print(f"[CatalogC] hierarchy 파일 로드 실패: {e}")

    # 데이터가 비어있을 경우 폴백 (TARGETS_INDEX_FILE 기반)
    if not any(hierarchy[b] for b in ordered_brands):
        model_to_target = {}
        if os.path.exists(TARGETS_INDEX_FILE):
            try:
                with open(TARGETS_INDEX_FILE, "r", encoding="utf-8") as f:
                    targets = json.load(f)
                for t in targets:
                    m = t.get("model_name")
                    if m and m not in model_to_target:
                        model_to_target[m] = t
            except Exception:
                pass

        for m, yrs in catalog.items():
            t = model_to_target.get(m, {})
            b = t.get("mfg_name", "현대")
            g = t.get("group_name", m)
            if b not in hierarchy:
                hierarchy[b] = {}
            if g not in hierarchy[b]:
                hierarchy[b][g] = {}
            sorted_years = sorted(list(yrs.keys()), key=lambda x: int(re.sub(r'\D', '', x) or 0), reverse=True)
            hierarchy[b][g][m] = sorted_years

    # 빈 브랜드 정리
    clean_hierarchy = {b: hierarchy[b] for b in ordered_brands if hierarchy.get(b)}
    _CATALOG_C_HIERARCHY_CACHE = clean_hierarchy
    return _CATALOG_C_HIERARCHY_CACHE


def get_catalog_c_spec(car_name: str = "", year: str = "", grade: str = "") -> Dict[str, Any]:
    """
    차종·연식 기준 전체 등급 목록 및 스펙 반환.
    특정 grade 전달 시 일치/유사 등급 하이라이트 매칭.
    """
    catalog = load_catalog_c()
    conflicts_idx = load_conflicts_index()

    s_car = str(car_name or "").strip()
    s_year = str(year or "").strip()
    s_grade = str(grade or "").strip()

    if not s_car or not s_year:
        return {
            "found": False,
            "reason": "차종명(car_name)과 연식(year)을 모두 입력해야 합니다.",
            "car_name": s_car,
            "year": s_year,
            "grades": {},
            "total_grades": 0
        }

    # 1. 모델 탐색 (정확 일치 또는 부분 일치)
    matched_model = None
    if s_car in catalog:
        matched_model = s_car
    else:
        # 괄호 제거 정규화 검색
        s_norm = re.sub(r'[\s\(\)\-_]+', '', s_car).lower()
        for m in catalog.keys():
            m_norm = re.sub(r'[\s\(\)\-_]+', '', m).lower()
            if s_norm == m_norm or s_norm in m_norm or m_norm in s_norm:
                matched_model = m
                break

    if not matched_model or matched_model not in catalog:
        return {
            "found": False,
            "reason": f"제이책(C)에 차종 '{s_car}'이 등록되어 있지 않습니다.",
            "car_name": s_car,
            "year": s_year,
            "grades": {},
            "total_grades": 0
        }

    model_data = catalog[matched_model]

    # 2. 연식 탐색 (숫자 4자리 추출)
    matched_year = None
    yr_digits = re.search(r'(20\d{2})', s_year)
    s_yr_num = yr_digits.group(1) if yr_digits else s_year

    if s_yr_num in model_data:
        matched_year = s_yr_num
    else:
        for y in model_data.keys():
            if s_yr_num in y:
                matched_year = y
                break

    if not matched_year or matched_year not in model_data:
        return {
            "found": False,
            "reason": f"'{matched_model}' 차종에 '{s_year}' 연식이 등록되어 있지 않습니다.",
            "car_name": matched_model,
            "year": s_year,
            "available_years": list(model_data.keys()),
            "grades": {},
            "total_grades": 0
        }

    grades_raw = model_data[matched_year]

    # 3. 등급별 스펙 및 충돌 여부 가공
    enriched_grades = {}
    for gname, gdata in grades_raw.items():
        bp = gdata.get("base_price")
        bp_man = round(bp / 10000) if bp is not None else None
        
        conflict_key = f"{matched_model}::{matched_year}::{gname}"
        conflict_info = conflicts_idx.get(conflict_key)

        options_map = {}
        for oname, oinfo in gdata.get("options", {}).items():
            oprc = oinfo.get("price")
            oprc_man = round(oprc / 10000) if oprc is not None else None
            options_map[oname] = {
                "price": oprc,
                "price_man": oprc_man,
                "kind": oinfo.get("kind", "optional"),
                "desc": oinfo.get("desc"),
                "source": oinfo.get("source", gdata.get("source", "encar"))
            }

        enriched_grades[gname] = {
            "name": gname,
            "base_price": bp,
            "base_price_man": bp_man,
            "mission": gdata.get("mission", ""),
            "source": gdata.get("source", "encar"),
            "options": options_map,
            "options_count": len(options_map),
            "is_conflict": bool(conflict_info),
            "conflict_info": conflict_info
        }

    # 4. 특정 등급 지정(target_grade) 매칭 판정
    target_grade_match = None
    if s_grade:
        if s_grade in enriched_grades:
            target_grade_match = s_grade
        else:
            s_grade_clean = re.sub(r'[\s\-_/·・\.\(\)]+', '', s_grade).lower()
            for gname in enriched_grades.keys():
                g_clean = re.sub(r'[\s\-_/·・\.\(\)]+', '', gname).lower()
                if s_grade_clean == g_clean or s_grade_clean in g_clean or g_clean in s_grade_clean:
                    target_grade_match = gname
                    break

    return {
        "found": True,
        "car_name": matched_model,
        "year": matched_year,
        "query_grade": s_grade or None,
        "target_grade": target_grade_match,
        "total_grades": len(enriched_grades),
        "grades": enriched_grades
    }
