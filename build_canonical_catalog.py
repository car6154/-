# -*- coding: utf-8 -*-
"""
신차가격표 캐노니컬 카탈로그 빌더 (build_canonical_catalog.py)
- 원본 다나와(danawa_newcar_catalog.json)와 엔카(encar_newcar_catalog.json)를 정제·병합
- 별칭 맵을 통한 파편화 키(F/L 등) 표준 차명 단일화
- 부분문자열 오염(현대차 키 내 BMW/렉서스 트림 등) 자동 탐지 및 제거
- 다나와 우선 + 엔카 빈 곳 메움 (기존 우선순위 유지)
- 옵션마다 출처(source: 'danawa' | 'encar') 명시 보존
- 최종 결과: data/canonical_newcar_catalog.json 생성
"""

import os
import re
import json
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

DANAWA_FILE = os.path.join(DATA_DIR, "danawa_newcar_catalog.json")
ENCAR_FILE = os.path.join(DATA_DIR, "encar_newcar_catalog.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "canonical_newcar_catalog.json")

# 표준 모델명 매핑 테이블 (별칭 및 F/L 파편화 통합)
MODEL_CANONICAL_MAP = {
    # 팰리세이드
    "팰리세이드(LX2) F/L": "더 뉴 팰리세이드",
    "팰리세이드 F/L": "더 뉴 팰리세이드",
    "더 뉴 팰리세이드 F/L": "더 뉴 팰리세이드",
    "더 뉴 팰리세이드(LX2)": "더 뉴 팰리세이드",
    "팰리세이드(LX2)": "팰리세이드",
    "팰리세이드 (LX3)": "디 올 뉴 팰리세이드",
    
    # 투싼
    "투싼(NX4) F/L": "더 뉴 투싼",
    "더 뉴 투싼(NX4)": "더 뉴 투싼",
    "더 뉴 투싼 F/L": "더 뉴 투싼",
    "투싼 F/L": "더 뉴 투싼",
    "투싼(NX4)": "투싼 (NX4)",
    "투싼 ix F/L": "뉴 투싼 ix",
    
    # 그랜저
    "더 뉴 그랜저 F/L": "더 뉴 그랜저",
    "더 뉴 그랜저(IG)": "더 뉴 그랜저",
    "더 뉴 그랜저IG": "더 뉴 그랜저",
    "그랜저(IG) F/L": "더 뉴 그랜저",
    "그랜저(IG)": "그랜저 IG",
    "그랜저(HG)": "그랜저 HG",
    "디 올 뉴 그랜저(GN7)": "디 올 뉴 그랜저",
    "디 올 뉴 그랜저 하이브리드(GN7)": "디 올 뉴 그랜저 하이브리드",
    "더 뉴 그랜저 하이브리드(IG)": "더 뉴 그랜저 하이브리드",
    "그랜저IG HEV": "그랜저 IG 하이브리드",
    "그랜저HG HEV": "그랜저 HG 하이브리드",
    
    # 싼타페
    "디 올 뉴 싼타페(MX5)": "디 올 뉴 싼타페",
    "더 뉴 싼타페(TM)": "더 뉴 싼타페",
    "더 뉴 싼타페 F/L": "더 뉴 싼타페",
    "싼타페(TM) F/L": "더 뉴 싼타페",
    "싼타페 더 프라임": "싼타페 더 프라임",
    "싼타페DM": "싼타페 DM",
    
    # 쏘렌토
    "더 뉴 쏘렌토(MQ4) F/L": "더 뉴 쏘렌토 4세대",
    "더 뉴 쏘렌토(MQ4)": "더 뉴 쏘렌토 4세대",
    "더 뉴 쏘렌토 4세대": "더 뉴 쏘렌토 4세대",
    "쏘렌토(MQ4) F/L": "더 뉴 쏘렌토 4세대",
    "쏘렌토 F/L": "더 뉴 쏘렌토 4세대",
    "더 뉴 쏘렌토 F/L": "더 뉴 쏘렌토 4세대",
    "쏘렌토(MQ4)": "쏘렌토 4세대",
    "쏘렌토 4세대": "쏘렌토 4세대",
    "더 뉴 쏘렌토": "더 뉴 쏘렌토",
    "올 뉴 쏘렌토": "올 뉴 쏘렌토",
    
    # 카니발
    "더 뉴 카니발(KA4) F/L": "더 뉴 카니발 4세대",
    "더 뉴 카니발(KA4)": "더 뉴 카니발 4세대",
    "더 뉴 카니발 4세대": "더 뉴 카니발 4세대",
    "카니발(KA4) F/L": "더 뉴 카니발 4세대",
    "카니발 F/L": "더 뉴 카니발 4세대",
    "카니발(KA4)": "카니발 4세대",
    "카니발 4세대": "카니발 4세대",
    "더 뉴 카니발": "더 뉴 카니발",
    "올 뉴 카니발": "올 뉴 카니발",
    "카니발R": "카니발 R",
    "카니발 R": "카니발 R",
    
    # 아반떼
    "더 뉴 아반떼(CN7) F/L": "더 뉴 아반떼 (CN7)",
    "더 뉴 아반떼(CN7)": "더 뉴 아반떼 (CN7)",
    "아반떼(CN7) F/L": "더 뉴 아반떼 (CN7)",
    "아반떼 F/L": "더 뉴 아반떼 (CN7)",
    "더 뉴 아반떼 (CN7)": "더 뉴 아반떼 (CN7)",
    "아반떼(CN7)": "아반떼 (CN7)",
    "더 뉴 아반떼 N": "더 뉴 아반떼 N",
    
    # K5
    "더 뉴 K5(DL3) F/L": "더 뉴 K5 3세대",
    "더 뉴 K5(DL3)": "더 뉴 K5 3세대",
    "K5(DL3) F/L": "더 뉴 K5 3세대",
    "K5 F/L": "더 뉴 K5 3세대",
    "더 뉴 K5 F/L": "더 뉴 K5 3세대",
    "더 뉴 K5 3세대": "더 뉴 K5 3세대",
    "K5(DL3)": "K5 3세대",
    "K5 3세대": "K5 3세대",
    "더 뉴 K5": "더 뉴 K5",
    "올 뉴 K5": "올 뉴 K5",
    
    # 스포티지
    "더 뉴 스포티지(NQ5) F/L": "더 뉴 스포티지 5세대",
    "더 뉴 스포티지(NQ5)": "더 뉴 스포티지 5세대",
    "스포티지(NQ5) F/L": "더 뉴 스포티지 5세대",
    "스포티지 F/L": "더 뉴 스포티지 5세대",
    "더 뉴 스포티지 5세대": "더 뉴 스포티지 5세대",
    "스포티지(NQ5)": "스포티지 5세대",
    "스포티지 5세대": "스포티지 5세대",
    "스포티지 더 볼드": "스포티지 더 볼드",
    "더 SUV 스포티지": "더 SUV 스포티지",
    
    # 제네시스
    "G80(RG3) F/L": "더 뉴 G80",
    "G80 F/L": "더 뉴 G80",
    "G80(RG3)": "G80 (RG3)",
    "GV70(JK1) F/L": "더 뉴 GV70",
    "GV70 F/L": "더 뉴 GV70",
    "GV70(JK1)": "GV70",
    "GV80(JX1) F/L": "더 뉴 GV80",
    "GV80 F/L": "더 뉴 GV80",
    "GV80(JX1)": "GV80",
    "G70 F/L": "더 뉴 G70",
    
    # 경차/소형
    "디 올 뉴 코나(SX2)": "디 올 뉴 코나",
    "토레스(J100)": "토레스",
    "더 뉴 토레스(J100)": "더 뉴 토레스",
    "더 뉴 토레스": "더 뉴 토레스",
    "더 뉴 모닝(JA)": "더 뉴 모닝 (JA)",
    "더 뉴 레이": "더 뉴 레이",
    "레이(TAM)": "레이",
}

# 국산 브랜드 모델 키에 섞여서는 안 되는 외제차 고유 트림 키워드 (오염 필터링용)
FOREIGN_CONTAMINATION_KEYWORDS = [
    "xdrive", "sdrive", "m35i", "m50i", "700h", "500h", "overtrail",
    "4matic", "avantgarde", "amg", "tdi", "tfsi", "quattro"
]

def is_contaminated_block(model_name: str, year_data: dict) -> bool:
    """국산차 키에 외제차 트림이 들어간 오염 데이터인지 판정"""
    grades = year_data.get("grades", [])
    grades_lower = " ".join([str(g).lower() for g in grades])
    
    # 국산 대표 브랜드 대상 모델인지 확인
    domestic_keywords = ["팰리세이드", "투싼", "그랜저", "싼타페", "쏘렌토", "카니발", "아반떼", "k5", "스포티지", "g80", "gv80", "gv70", "모닝", "레이"]
    is_domestic = any(dk in model_name.lower() for dk in domestic_keywords)
    
    if is_domestic:
        # 외제차 키워드가 트림에 다수 발견되면 오염 블록으로 판정
        for kw in FOREIGN_CONTAMINATION_KEYWORDS:
            if kw in grades_lower:
                return True
                
    return False

def normalize_model_name(raw_name: str) -> str:
    """원시 모델명을 캐노니컬 표준 모델명으로 정규화"""
    name = raw_name.strip()
    if name in MODEL_CANONICAL_MAP:
        return MODEL_CANONICAL_MAP[name]
        
    # 괄호 제거 후 재확인
    clean_n = re.sub(r'\([^\)]+\)', '', name).strip()
    if clean_n in MODEL_CANONICAL_MAP:
        return MODEL_CANONICAL_MAP[clean_n]
        
    return clean_n or name

def main():
    print("=== [캐노니컬 카탈로그 생성 시작] ===")
    
    danawa_raw = {}
    if os.path.exists(DANAWA_FILE):
        with open(DANAWA_FILE, "r", encoding="utf-8") as f:
            danawa_raw = json.load(f)
    print(f"다나와 원본 모델 수: {len(danawa_raw)}")

    encar_raw = {}
    if os.path.exists(ENCAR_FILE):
        with open(ENCAR_FILE, "r", encoding="utf-8") as f:
            encar_raw = json.load(f)
    print(f"엔카 원본 모델 수: {len(encar_raw)}")

    canonical_db: Dict[str, Dict[str, dict]] = {}
    contaminated_count = 0
    contaminated_log = []

    # 1. 다나와 데이터 1차 흡수 (별칭 병합 + 오염 필터링)
    for raw_model, years_dict in danawa_raw.items():
        std_model = normalize_model_name(raw_model)
        if std_model not in canonical_db:
            canonical_db[std_model] = {}

        for yr, ydata in years_dict.items():
            # 4자리 연도 검증
            if not re.match(r'^20\d{2}$', str(yr)):
                continue

            # 오염 검사
            if is_contaminated_block(std_model, ydata):
                contaminated_count += 1
                contaminated_log.append(f"[{std_model} - {yr}년형] 외제차 트림 오염 블록 제거: {ydata.get('grades', [])[:3]}")
                continue

            # 다나와 옵션에 source="danawa" 부착
            danawa_options = {}
            for opt_name, opt_val in ydata.get("options", {}).items():
                if isinstance(opt_val, dict):
                    opt_val_copy = dict(opt_val)
                    opt_val_copy["source"] = "danawa"
                    danawa_options[opt_name] = opt_val_copy
                elif isinstance(opt_val, (int, float)):
                    danawa_options[opt_name] = {"price": int(opt_val), "source": "danawa"}

            if yr not in canonical_db[std_model]:
                canonical_db[std_model][yr] = {
                    "grades": list(ydata.get("grades", [])),
                    "options": danawa_options,
                    "packages": dict(ydata.get("packages", {}))
                }
            else:
                # 이미 해당 연형이 존재하면(예: F/L 키와 기본 키가 병합된 경우)
                # 트림 리스트 병합
                existing_grades = canonical_db[std_model][yr]["grades"]
                for g in ydata.get("grades", []):
                    if g not in existing_grades:
                        existing_grades.append(g)
                # 옵션 병합 (기존 옵션 유지 + 새 옵션 추가)
                canonical_db[std_model][yr]["options"].update(danawa_options)
                # 패키지 병합
                canonical_db[std_model][yr]["packages"].update(ydata.get("packages", {}))

    print(f"\n[오염 필터링 결과] 제거된 오염 블록 수: {contaminated_count}건")
    for log_msg in contaminated_log[:10]:
        print(f"  {log_msg}")

    # 2. 엔카 데이터 보완 (다나와 우선 + 엔카 빈 곳 메움)
    encar_merged_count = 0
    encar_fallback_opts = 0

    for raw_model, years_dict in encar_raw.items():
        std_model = normalize_model_name(raw_model)
        if std_model not in canonical_db:
            canonical_db[std_model] = {}

        for yr, ydata in years_dict.items():
            if not re.match(r'^20\d{2}$', str(yr)):
                continue

            encar_options = {}
            for opt_name, opt_val in ydata.get("options", {}).items():
                if isinstance(opt_val, dict):
                    opt_val_copy = dict(opt_val)
                    opt_val_copy["source"] = "encar"
                    encar_options[opt_name] = opt_val_copy
                elif isinstance(opt_val, (int, float)):
                    encar_options[opt_name] = {"price": int(opt_val), "source": "encar"}

            if yr not in canonical_db[std_model]:
                # 다나와에 아예 없던 연형 ➔ 엔카 데이터로 통째로 메움!
                canonical_db[std_model][yr] = {
                    "grades": list(ydata.get("grades", [])),
                    "options": encar_options,
                    "packages": dict(ydata.get("packages", {}))
                }
                encar_merged_count += 1
            else:
                target_block = canonical_db[std_model][yr]
                # 다나와에 트림이 없으면 엔카 트림 보충
                if not target_block["grades"]:
                    target_block["grades"] = list(ydata.get("grades", []))
                else:
                    for g in ydata.get("grades", []):
                        if g not in target_block["grades"]:
                            target_block["grades"].append(g)

                # 다나와 옵션에 없는 옵션은 엔카 옵션으로 보충
                for opt_name, opt_info in encar_options.items():
                    if opt_name not in target_block["options"]:
                        target_block["options"][opt_name] = opt_info
                        encar_fallback_opts += 1

                # 패키지 설명 보충
                for pkg_name, pkg_desc in ydata.get("packages", {}).items():
                    if pkg_name not in target_block["packages"]:
                        target_block["packages"][pkg_name] = pkg_desc

    # 3. 빈 껍데기(옵션 0개 & 트림 0개) 연형 정리
    cleaned_db = {}
    total_valid_models = 0
    total_valid_years = 0
    models_with_options = 0

    for model_name, years in canonical_db.items():
        valid_years = {}
        has_any_opt = False
        for yr, ydata in years.items():
            if len(ydata.get("options", {})) > 0 or len(ydata.get("grades", [])) > 0:
                valid_years[yr] = ydata
                total_valid_years += 1
                if len(ydata.get("options", {})) > 0:
                    has_any_opt = True

        if valid_years:
            cleaned_db[model_name] = valid_years
            total_valid_models += 1
            if has_any_opt:
                models_with_options += 1

    # 파일 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_db, f, ensure_ascii=False, indent=2)

    print("\n=== [캐노니컬 카탈로그 생성 완료] ===")
    print(f"최종 저장 파일: {OUTPUT_FILE}")
    print(f"최종 모델 수: {total_valid_models}개")
    print(f"최종 연형(연도) 수: {total_valid_years}개")
    print(f"옵션이 1개 이상 있는 모델 수: {models_with_options}개")
    print(f"엔카에서 신규 보강된 연형 수: {encar_merged_count}개")
    print(f"엔카에서 빈 곳을 메운 개별 옵션 수: {encar_fallback_opts}개")

if __name__ == "__main__":
    main()
