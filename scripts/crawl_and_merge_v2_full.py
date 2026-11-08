# -*- coding: utf-8 -*-
"""
scripts/crawl_and_merge_v2_full.py
V2 카탈로그 전체(69개 차종, 3,291등급, 19,715옵션)의 옵션 설명(desc) 및 등급 기본 출고 사양(standard_features)을
다나와 신차 정적 웹페이지에서 수집하여 단일 병합하는 배치 스크립트.
"""

import sys
import os
import json
import time
import re
import copy
import shutil
import logging
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.danawa_crawler import get_danawa_session, get_model_lineups, clean_text
from services.data_processor import DataProcessor
from services.catalog_by_source_service import SPEC_COMPARE_KEYS
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CATALOG_V2_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2.json")
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2_backup_before_desc.json")

# 69개 차종과 다나와 model_id 매핑 테이블 (전수 검증 완료)
MODEL_TO_MIDS = {
    '쏘렌토 4세대': ['3837'],
    '팰리세이드': ['3563'],
    '더 뉴 팰리세이드': ['4190'],
    '스포티지 5세대': ['4069'],
    '카니발 4세대': ['3910'],
    'G80': ['3656', '3375'],
    '더 뉴 G80': ['4603'],
    'GV70': ['3849'],
    '더 뉴 GV70': ['4609'],
    '디 올 뉴 그랜저': ['4188'],
    '더 뉴 그랜저': ['4802', '3737'],
    '그랜저': ['3332', '3443'],
    'K5': ['3742'],
    '더 뉴 K5': ['4585'],
    '더 뉴 캐스퍼': ['4671'],
    '캐스퍼': ['4086'],
    '더 뉴 아반떼': ['4455', '3600'],
    '아반떼': ['3821', '3259'],
    '더 뉴 레이': ['3548'],
    '레이': ['2183'],
    '더 뉴 모닝': ['3239'],
    '모닝': ['3333'],
    '모닝 어반': ['3871'],
    '더 뉴 셀토스': ['4391'],
    '디 올 뉴 셀토스': ['4763'],
    '쏘나타': ['3652'],
    '쏘나타 디 엣지': ['4466'],
    'K7': ['3266', '2106'],
    '디 올 뉴 코나': ['4361'],
    '코나': ['3445'],
    'G90': ['4016', '3602'],
    '스파크': ['3255'],
    'GV80': ['3657'],
    'GV80 F/L': ['4465'],
    'XM3': ['3701'],
    '아르카나': ['4560'],
    'EV6': ['4022'],
    '더 뉴 EV6': ['4641'],
    '트랙스 크로스오버': ['4429'],
    'QM6': ['3364'],
    '더 뉴 QM6': ['3732'],
    'K8': ['4017', '4665'],
    '더 뉴 스타리아': ['4765'],
    '스타리아': ['4014'],
    '카니발 3세대': ['3152', '3484'],
    '디 올 뉴 팰리세이드': ['4699'],
    '더 뉴 스포티지': ['4684'],
    '스포티지 더 볼드': ['3560'],
    '더 SUV 스포티지': ['3298'],
    'G80 EV': ['4401'],
    '아반떼 N': ['4078'],
    '더 뉴 아반떼 N': ['4564'],
    'K7 HEV': ['3415'],
    'K7 프리미어': ['3722'],
    '코나 일렉트릭': ['4510'],
    '더 뉴 스파크': ['3594'],
    '스파크 EV': ['3142'],
    '스파크 (M300)': ['2138'],
    '트랙스': ['3054'],
    '더 뉴 트랙스': ['3397'],
    'K5 2세대': ['3260'],
    '더 뉴 K5 2세대': ['3566'],
    'K5 1세대': ['2118'],
    '더 뉴 K5 1세대': ['3093'],
    'K5 HEV': ['3314', '2160'],
    '더 뉴 K5 HEV': ['3595'],
    'K5 PHEV': ['3390'],
    '셀토스': ['3699'],
    '디 올 뉴 싼타페': ['4435']
}

def parse_lineup_html_full(html: str) -> tuple:
    soup = BeautifulSoup(html, 'html.parser')
    results = {}
    spec_table = soup.select_one('table.tableBlock.specTable')
    if not spec_table:
        return results, {}

    # 1. 하단 패키지 설명 테이블
    packages = {}
    for tr in spec_table.find_all('tr'):
        td_title = tr.select_one('td.tdTitle')
        if td_title and not any('trimsName' in c for c in td_title.get('class', [])):
            tds = tr.find_all(['td', 'th'])
            if len(tds) >= 2:
                p_name = clean_text(tds[0].get_text())
                p_desc = clean_text(tds[1].get_text())
                if p_name and p_name not in ['패키지 옵션', '선택품목', '세부 사양', '주요품목', '공통 옵션']:
                    packages[p_name] = p_desc

    # 2. 트림 행 순회
    trs = spec_table.find_all('tr')
    current_grade = None
    
    for tr in trs:
        td_trim = None
        for td in tr.find_all('td'):
            cls = td.get('class', [])
            if any('trimsName' in c for c in cls):
                td_trim = td
                break
        
        if td_trim:
            current_grade = clean_text(td_trim.get_text())
            results[current_grade] = {
                "standard_features": [],
                "options": {}
            }
            tds = tr.find_all(['td'])
            if len(tds) >= 3:
                std_td = tds[2]
                for br in std_td.find_all(['br', 'p']):
                    br.replace_with('\n')
                lines = [clean_text(l) for l in std_td.get_text().split('\n')]
                clean_lines = []
                for l in lines:
                    l = re.sub(r'^[▶•·\-\*]\s*', '', l).strip()
                    if l:
                        clean_lines.append(l)
                results[current_grade]["standard_features"] = clean_lines

        choices = tr.select('ul.pChkItemList .choice')
        if choices and current_grade:
            for ch in choices:
                info_span = ch.select_one('.choice__info .txt, label')
                opt_name = clean_text(info_span.get_text()) if info_span else ""
                code = ch.get('code')
                
                desc = packages.get(opt_name, "")
                if not desc and code:
                    opt_div = tr.select_one(f'#optionKey_{code}')
                    if opt_div:
                        sub_items = []
                        for cont in opt_div.select('.infodetail__cont'):
                            t_el = cont.select_one('.title')
                            if t_el:
                                t_text = clean_text(t_el.get_text())
                                t_text = re.sub(r'^\d+\.\s*', '', t_text)
                                if t_text:
                                    sub_items.append(t_text)
                        if sub_items:
                            desc = ", ".join(sub_items)
                            
                if opt_name:
                    results[current_grade]["options"][opt_name] = desc

    return results, packages

def match_grade_in_book(lineup_name: str, danawa_trim: str, book_grades: dict) -> Optional[str]:
    query_text = f"{lineup_name} {danawa_trim}"
    query_spec = DataProcessor.build_car_spec(text=query_text)
    
    # 1. 완전 일치 (7-tuple)
    q_7 = tuple(query_spec.get(k) for k in SPEC_COMPARE_KEYS)
    for bg_key in book_grades:
        bg_spec = DataProcessor.build_car_spec(text=bg_key)
        if q_7 == tuple(bg_spec.get(k) for k in SPEC_COMPARE_KEYS):
            return bg_key
            
    # 2. is_turbo 완화 (터보 여부 무시)
    keys_no_turbo = tuple(k for k in SPEC_COMPARE_KEYS if k != "is_turbo")
    q_no_turbo = tuple(query_spec.get(k) for k in keys_no_turbo)
    for bg_key in book_grades:
        bg_spec = DataProcessor.build_car_spec(text=bg_key)
        if q_no_turbo == tuple(bg_spec.get(k) for k in keys_no_turbo):
            return bg_key

    # 3. is_turbo + drive(기본 2wd) 완화
    q_drive = query_spec.get("drive")
    if not q_drive: # 쿼리에 2wd/4wd 명시 없으면 기본 2wd로 시도
        q_spec_2wd = dict(query_spec)
        q_spec_2wd["drive"] = "2wd"
        q_2wd_no_turbo = tuple(q_spec_2wd.get(k) for k in keys_no_turbo)
        for bg_key in book_grades:
            bg_spec = DataProcessor.build_car_spec(text=bg_key)
            if q_2wd_no_turbo == tuple(bg_spec.get(k) for k in keys_no_turbo):
                return bg_key

    # 4. is_turbo + seats 완화
    keys_no_turbo_no_seats = tuple(k for k in keys_no_turbo if k != "seats")
    q_no_t_no_s = tuple(query_spec.get(k) for k in keys_no_turbo_no_seats)
    for bg_key in book_grades:
        bg_spec = DataProcessor.build_car_spec(text=bg_key)
        if q_no_t_no_s == tuple(bg_spec.get(k) for k in keys_no_turbo_no_seats):
            if query_spec.get("grade_base") and query_spec.get("grade_base") == bg_spec.get("grade_base"):
                return bg_key

    # 5. 제네시스 등 단일 트림 / 스포츠패키지 매칭 (grade_base가 없거나 특수)
    c_lineup = re.sub(r'[\s\-/\(\)\.]', '', lineup_name).lower()
    c_trim = re.sub(r'[\s\-/\(\)\.]', '', danawa_trim).lower()
    for bg_key in book_grades:
        c_bg = re.sub(r'[\s\-/\(\)\.]', '', bg_key).lower()
        if c_trim in c_bg and (query_spec.get('disp') in c_bg if query_spec.get('disp') else True):
            if ('awd' in c_bg and 'awd' in c_trim) or ('2wd' in c_bg and '2wd' in c_trim):
                return bg_key

    return None

def main():
    logger.info("=== Starting V2 Catalog desc & standard_features Crawler ===")
    
    # 1. 안전 백업
    shutil.copy2(CATALOG_V2_FILE, BACKUP_FILE)
    logger.info(f"Backup created at: {BACKUP_FILE}")

    # 2. 책 원본 로드
    with open(CATALOG_V2_FILE, "r", encoding="utf-8") as f:
        full_catalog = json.load(f)
        
    danawa_book = full_catalog.get("danawa", {})
    total_models = len(danawa_book)
    logger.info(f"Total models in book: {total_models}")

    # 불변 기준 스냅샷 기록
    baseline_stats = {}
    for m, y_dict in danawa_book.items():
        baseline_stats[m] = {}
        for y, g_dict in y_dict.items():
            baseline_stats[m][y] = {}
            for g, g_info in g_dict.items():
                baseline_stats[m][y][g] = {
                    "base_price": g_info.get("base_price"),
                    "base_price_man": g_info.get("base_price_man"),
                    "options": {opt_k: (opt_v.get("price"), opt_v.get("price_man"), opt_v.get("desc", ""))
                                for opt_k, opt_v in g_info.get("options", {}).items()}
                }

    session = get_danawa_session()
    
    total_grades_updated = 0
    total_options_updated = 0
    
    model_keys = list(danawa_book.keys())
    for idx, model_name in enumerate(model_keys, 1):
        mids = MODEL_TO_MIDS.get(model_name, [])
        if not mids:
            logger.warning(f"[{idx}/{total_models}] No MIDs for '{model_name}', skipping")
            continue
            
        logger.info(f"[{idx}/{total_models}] Processing '{model_name}' (MIDs: {mids})...")
        model_years = danawa_book[model_name]
        
        m_grades_up = 0
        m_opts_up = 0
        
        for mid in mids:
            time.sleep(0.25)
            try:
                raw_name, lineups_by_year = get_model_lineups(mid, session)
            except Exception as e:
                logger.error(f"Error fetching lineups for mid {mid} ({model_name}): {e}")
                continue
                
            for year_str, lus in lineups_by_year.items():
                # 책에 해당 연식이 있는지 확인 (정규화 대조)
                target_book_years = [by for by in model_years.keys() if by == year_str or by.startswith(year_str) or year_str.startswith(by)]
                if not target_book_years:
                    continue
                    
                for by in target_book_years:
                    b_year_grades = model_years[by]
                    
                    for lu in lus:
                        lu_id = lu["lineup_id"]
                        lu_name = lu["name"]
                        url = f"https://auto.danawa.com/auto/?Work=model&Model={mid}&Lineup={lu_id}&Tab=price"
                        
                        time.sleep(0.2)
                        resp = None
                        for attempt in range(2):
                            try:
                                resp = session.get(url, timeout=12)
                                resp.encoding = "utf-8"
                                if resp.status_code in [403, 429]:
                                    logger.error(f"CRITICAL: HTTP {resp.status_code} received on {url}! Aborting.")
                                    sys.exit(1)
                                break
                            except Exception as req_err:
                                if attempt == 0:
                                    time.sleep(1.0)
                                    session = get_danawa_session()
                                    continue
                                logger.error(f"Request failed for {url}: {req_err}")
                                
                        if resp is None or resp.status_code != 200:
                            continue
                            
                        parsed_trims, parsed_packages = parse_lineup_html_full(resp.text)
                        
                        for trim_name, trim_data in parsed_trims.items():
                            matched_bg = match_grade_in_book(lu_name, trim_name, b_year_grades)
                            if matched_bg:
                                bg_data = b_year_grades[matched_bg]
                                
                                # 1. standard_features 채우기 (비어있을 때만)
                                if not bg_data.get("standard_features") and trim_data["standard_features"]:
                                    bg_data["standard_features"] = trim_data["standard_features"]
                                    m_grades_up += 1
                                    total_grades_updated += 1
                                    
                                # 2. options desc 채우기 (비어있을 때만)
                                bg_options = bg_data.get("options", {})
                                for opt_name, desc in trim_data["options"].items():
                                    if not desc:
                                        continue
                                    matched_opt_k = None
                                    if opt_name in bg_options:
                                        matched_opt_k = opt_name
                                    else:
                                        c_opt = re.sub(r'[\s\-/\(\)\.]', '', opt_name).lower()
                                        for bk in bg_options:
                                            c_bk = re.sub(r'[\s\-/\(\)\.]', '', bk).lower()
                                            if c_opt == c_bk or c_opt in c_bk or c_bk in c_opt:
                                                matched_opt_k = bk
                                                break
                                    if matched_opt_k:
                                        curr_opt = bg_options[matched_opt_k]
                                        if not curr_opt.get("desc") and desc:
                                            curr_opt["desc"] = desc
                                            m_opts_up += 1
                                            total_options_updated += 1

                                # 3. packages 테이블에서 직접 옵션명 매칭
                                for opt_k, opt_v in bg_options.items():
                                    if not opt_v.get("desc"):
                                        c_k = re.sub(r'[\s\-/\(\)\.]', '', opt_k).lower()
                                        for p_name, p_desc in parsed_packages.items():
                                            c_p = re.sub(r'[\s\-/\(\)\.]', '', p_name).lower()
                                            if (c_k == c_p or c_k in c_p or c_p in c_k) and p_desc:
                                                opt_v["desc"] = p_desc
                                                m_opts_up += 1
                                                total_options_updated += 1
                                                break

        logger.info(f"[{idx}/{total_models}] Finished '{model_name}': +{m_grades_up} grades standard_features, +{m_opts_up} options desc")

    logger.info("=== All models crawled. Running strict invariant verification... ===")
    
    # 3. 전수 불변 검증 (Invariants Verification)
    assert len(danawa_book) == len(baseline_stats), "Model count mismatch!"
    
    total_grades_count = 0
    total_options_count = 0
    final_desc_filled = 0
    final_std_filled = 0
    
    for m, y_dict in danawa_book.items():
        assert m in baseline_stats, f"Model {m} missing from baseline!"
        for y, g_dict in y_dict.items():
            assert y in baseline_stats[m], f"Year {y} missing from baseline in {m}!"
            for g, g_info in g_dict.items():
                assert g in baseline_stats[m][y], f"Grade {g} missing from baseline in {m}/{y}!"
                total_grades_count += 1
                if g_info.get("standard_features"):
                    final_std_filled += 1
                    
                base_g = baseline_stats[m][y][g]
                # 기본가 불변 검증
                assert g_info.get("base_price") == base_g["base_price"], f"Base price changed in {m}/{y}/{g}!"
                assert g_info.get("base_price_man") == base_g["base_price_man"], f"Base price man changed in {m}/{y}/{g}!"
                
                # 옵션 불변 검증
                for opt_k, opt_v in g_info.get("options", {}).items():
                    assert opt_k in base_g["options"], f"Option {opt_k} not in baseline {m}/{y}/{g}!"
                    total_options_count += 1
                    b_pr, b_pr_man, b_desc = base_g["options"][opt_k]
                    assert opt_v.get("price") == b_pr, f"Option price changed in {m}/{y}/{g}/{opt_k}!"
                    assert opt_v.get("price_man") == b_pr_man, f"Option price man changed in {m}/{y}/{g}/{opt_k}!"
                    if b_desc:
                        assert opt_v.get("desc") == b_desc, f"Existing desc overwritten in {m}/{y}/{g}/{opt_k}!"
                    if opt_v.get("desc"):
                        final_desc_filled += 1

    logger.info("=== Verification PASSED! ===")
    logger.info(f"Total Models: {len(danawa_book)} (expected: 69)")
    logger.info(f"Total Grades: {total_grades_count} (expected: 3,291)")
    logger.info(f"Total Options: {total_options_count} (expected: 19,715)")
    logger.info(f"standard_features filled: {final_std_filled}/{total_grades_count}")
    logger.info(f"options desc filled: {final_desc_filled}/{total_options_count} (initial: 3,840)")

    # 4. 저장
    with open(CATALOG_V2_FILE, "w", encoding="utf-8") as f:
        json.dump(full_catalog, f, ensure_ascii=False, indent=2)
    logger.info(f"Successfully saved updated catalog to: {CATALOG_V2_FILE}")

if __name__ == "__main__":
    main()
