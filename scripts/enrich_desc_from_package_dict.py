# -*- coding: utf-8 -*-
"""
scripts/enrich_desc_from_package_dict.py
V2 카탈로그 내 패키지 이름만 있던 옵션 desc를 동일 브랜드/차종의 상세 구성품목 설명으로 2차 보완.
"""

import os
import re
import json
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger("EnrichDesc")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_V2_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_by_source_v2.json")

def normalize_key(s: str) -> str:
    return re.sub(r'[\s\-/\(\)\.,_·■\+ⅡⅠⅢⅣⅤⅥ1234567890]', '', str(s)).lower()

def normalize_strict(s: str) -> str:
    return re.sub(r'[\s\-/\(\)\.,_·■\+]', '', str(s)).lower()

def main():
    logger.info("=== 2차 패키지 구성품목 매핑 보완 착수 ===")
    with open(CATALOG_V2_FILE, "r", encoding="utf-8") as f:
        full_catalog = json.load(f)
    v2_danawa = full_catalog.get("danawa", {})

    # 1. 상세 패키지 사전 구축
    pkg_dict = {}
    for c, years in v2_danawa.items():
        if not isinstance(years, dict): continue
        for y, grades in years.items():
            if not isinstance(grades, dict): continue
            for g, spec in grades.items():
                if not isinstance(spec, dict): continue
                for opt_k, opt_v in spec.get('options', {}).items():
                    desc = str(opt_v.get('desc') or '').strip()
                    if desc and ('+' in desc or ',' in desc or '|' in desc) and len(desc) >= 20:
                        # 1) 옵션명 기준
                        k_strict = normalize_strict(opt_k)
                        if k_strict not in pkg_dict or len(desc) > len(pkg_dict[k_strict]):
                            pkg_dict[k_strict] = desc
                        # 2) desc 자체도 패키지명이면 매핑
                        d_strict = normalize_strict(desc.split('+')[0].split('|')[0])
                        if d_strict and (d_strict not in pkg_dict or len(desc) > len(pkg_dict[d_strict])):
                            pkg_dict[d_strict] = desc

    logger.info(f"상세 패키지 사전 구축 완료: {len(pkg_dict):,}개")

    # 2. 보완 적용
    updated_count = 0
    for c, years in v2_danawa.items():
        if not isinstance(years, dict): continue
        for y, grades in years.items():
            if not isinstance(grades, dict): continue
            for g, spec in grades.items():
                if not isinstance(spec, dict): continue
                for opt_k, opt_v in spec.get('options', {}).items():
                    desc = str(opt_v.get('desc') or '').strip()
                    need_enrich = (not desc) or (desc == opt_k.strip()) or ('+' not in desc and '|' not in desc and len(desc) <= 30)
                    if not need_enrich:
                        continue

                    # 1) desc 엄격 매칭
                    target_k = normalize_strict(desc) if desc else normalize_strict(opt_k)
                    new_desc = ""
                    if target_k in pkg_dict:
                        new_desc = pkg_dict[target_k]
                    elif normalize_strict(opt_k) in pkg_dict:
                        new_desc = pkg_dict[normalize_strict(opt_k)]

                    if new_desc and new_desc != desc and len(new_desc) > len(desc):
                        opt_v['desc'] = new_desc
                        updated_count += 1

    logger.info(f"2차 패키지 매핑으로 추가 보완된 옵션 수: {updated_count:,}개")

    # 3. 전수 불변성 검증
    initial_total_opts = 0
    final_valid_desc = 0
    final_empty_desc = 0
    final_same_desc = 0

    for c, years in v2_danawa.items():
        if not isinstance(years, dict): continue
        for y, grades in years.items():
            if not isinstance(grades, dict): continue
            for g, spec in grades.items():
                if not isinstance(spec, dict): continue
                for opt_k, opt_v in spec.get('options', {}).items():
                    initial_total_opts += 1
                    d = str(opt_v.get('desc') or '').strip()
                    if not d:
                        final_empty_desc += 1
                    elif d == opt_k.strip():
                        final_same_desc += 1
                    else:
                        final_valid_desc += 1

    logger.info(f"최종 총 옵션 수: {initial_total_opts:,}개")
    logger.info(f"최종 유효 desc: {final_valid_desc:,}개 ({final_valid_desc/initial_total_opts*100:.1f}%)")
    logger.info(f"최종 비어있는 desc: {final_empty_desc:,}개 ({final_empty_desc/initial_total_opts*100:.1f}%)")
    logger.info(f"최종 옵션명과 동일한 desc: {final_same_desc:,}개 ({final_same_desc/initial_total_opts*100:.1f}%)")

    # 4. 저장
    with open(CATALOG_V2_FILE, "w", encoding="utf-8") as f:
        json.dump(full_catalog, f, ensure_ascii=False, indent=2)
    logger.info("V2 책 최종 저장 완료")

if __name__ == "__main__":
    main()
