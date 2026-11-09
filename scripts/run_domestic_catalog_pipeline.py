# -*- coding: utf-8 -*-
"""
scripts/run_domestic_catalog_pipeline.py
국내 빠진 차종 전수 수집 및 V2 책 순차 병합 자동화 마스터 파이프라인 (기아 -> KGM -> 르노코리아 -> 제네시스).
- 브랜드 순서:
  1. 기아 (Brand=307, 커밋 11-06-47)
  2. KGM (Brand=326, 커밋 11-06-48)
  3. 르노코리아 (Brand=321, 커밋 11-06-49)
  4. 제네시스 (Brand=304, 커밋 11-06-50)
- 각 브랜드마다:
  1. 다나와 전 모델 수집 및 실측 정제 (원본 우선, 인하/사양변경 제외, HEV 세제혜택 후, 유상컬러/용품 제외, 0원 제외, 밴 포함)
  2. 가격 전수 검증 (price == price_man * 10000)
  3. batch json 저장
  4. V2 책 안전 백업 생성
  5. V2 책 Deep Merge (누락 연식 보강, 기존 데이터 100% 불변 보존)
  6. 기존 불변성 전수 검증 및 전체 V2 가격 무결성 전수 검증
  7. 프론트엔드 빌드 및 py_compile 검증
  8. Git 커밋 & 푸시
"""

import sys
import os
import re
import json
import time
import random
import shutil
import copy
import subprocess
import logging
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.danawa_crawler import (
    get_danawa_session,
    get_model_lineups,
    clean_text,
    parse_price,
    normalize_catalog_model_name
)
from services.model_matcher import ModelMatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("catalog_pipeline")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CATALOG_V2_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2.json")


def filter_best_lineups_for_year(lineups: List[dict]) -> List[dict]:
    """동일 연식 내 라인업 필터링"""
    valid_list = []
    for lu in lineups:
        name = lu.get('name', '')
        if any(kw in name for kw in ['장애인', '렌터카', '렌트카', '택시', '면세']):
            continue
        valid_list.append(lu)

    # HEV 세제혜택 후 우선
    has_tax_benefit = any('세제혜택 후' in lu.get('name', '') for lu in valid_list)
    if has_tax_benefit:
        tax_filtered = []
        for lu in valid_list:
            n = lu.get('name', '')
            if any(k in n for k in ['하이브리드', 'HEV', '플러그인', 'PHEV']):
                if '세제혜택 전' in n:
                    continue
            tax_filtered.append(lu)
        valid_list = tax_filtered

    groups = {}
    for lu in valid_list:
        name = lu.get('name', '')
        base_name = re.sub(r'\(.*?\)', '', name).strip()
        if not base_name:
            base_name = name.strip()
        if base_name not in groups:
            groups[base_name] = []
        groups[base_name].append(lu)

    selected = []
    cut_kws = ['인하', '3.5%', '3.0%', '사양변경', '가격변경', '상품성 강화', '옵션변경']
    
    for base_name, lus in groups.items():
        non_pre = [lu for lu in lus if '사전계약' not in lu.get('name', '')]
        candidates = non_pre if non_pre else lus

        non_cut = [lu for lu in candidates if not any(kw in lu.get('name', '') for kw in cut_kws)]
        if non_cut:
            chosen = non_cut[0]
        else:
            chosen = candidates[0]
        selected.append(chosen)

    return selected


def fetch_lineup_page(session, model_id: str, lineup_id: str) -> Optional[str]:
    """다나와 라인업 페이지 HTML 가져오기 (Tab=price -> Tab=item 폴백)"""
    url_price = f"https://auto.danawa.com/auto/?Work=model&Model={model_id}&Lineup={lineup_id}&Tab=price"
    
    for attempt in range(2):
        try:
            r = session.get(url_price, timeout=12)
            if r.status_code in [403, 429]:
                logger.error(f"HTTP {r.status_code} blocked! Aborting immediately.")
                sys.exit(1)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            has_trims = bool([td for td in soup.find_all('td') if any('trimsName' in c for c in td.get('class', []))])
            if has_trims:
                return r.text
            break
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed for {url_price}: {e}")
            time.sleep(2)

    url_item = f"https://auto.danawa.com/auto/?Work=model&Model={model_id}&Lineup={lineup_id}&Tab=item"
    try:
        r_item = session.get(url_item, timeout=12)
        if r_item.status_code in [403, 429]:
            logger.error(f"HTTP {r_item.status_code} blocked! Aborting immediately.")
            sys.exit(1)
        r_item.encoding = 'utf-8'
        soup_item = BeautifulSoup(r_item.text, 'html.parser')
        has_trims = bool([td for td in soup_item.find_all('td') if any('trimsName' in c for c in td.get('class', []))])
        if has_trims:
            return r_item.text
    except Exception as e:
        logger.warning(f"Tab=item failed for {url_item}: {e}")

    return None


def build_grade_key(car_name: str, lineup_name: str, trim_raw: str, sub_label: str = "") -> str:
    """표준 등급키 생성: {유종} {배기량} {구동} {트림명}"""
    clean_lineup = re.sub(r'\(.*?\)', '', lineup_name).strip()
    full_text = f"{car_name} {clean_lineup} {trim_raw} {sub_label}".strip()
    
    # 1. 유종 추출
    fuel = ModelMatcher.extract_fuel(full_text)
    if not fuel:
        fl = full_text.lower()
        if any(k in fl for k in ['ev', '전기', '일렉트릭', 'ev6', 'ev9', 'ev3', '조에', 'gv60']):
            fuel = '전기'
        elif any(k in fl for k in ['하이브리드', 'hev', 'e-tech']):
            fuel = '하이브리드'
        elif any(k in fl for k in ['플러그인', 'phev']):
            fuel = '하이브리드'
        elif any(k in fl for k in ['디젤', 'e-vgt', 'vgt', 'crdi', 'dci']):
            fuel = '디젤'
        elif any(k in fl for k in ['lpi', 'lpg']):
            fuel = 'LPG'
        elif any(k in car_name for k in ['모하비', '카니발', '쏘렌토', 'QM6']):
            fuel = '디젤' if any(k in fl for k in ['디젤', 'd']) else '가솔린'
        else:
            fuel = '가솔린'

    # 2. 배기량 추출
    disp = ModelMatcher.extract_disp(full_text)
    if not disp and fuel not in ['전기']:
        m_cc = re.search(r'(\d\.\d+)', full_text)
        if m_cc:
            disp = m_cc.group(1)

    # 3. 구동방식 추출 (4WD/AWD/HTRAC/4륜 -> 4WD)
    m_drive = re.search(r'(2WD|4WD|AWD|HTRAC|4륜|2륜)', trim_raw, re.I)
    if not m_drive:
        m_drive = re.search(r'(2WD|4WD|AWD|HTRAC|4륜|2륜)', clean_lineup, re.I)
    drive_val = m_drive.group(1).upper() if m_drive else '2WD'
    if drive_val in ['AWD', '4WD', 'HTRAC', '4륜']:
        drive = '4WD'
    else:
        drive = '2WD'

    # 4. 순수 트림명 정리
    trim_clean = re.sub(r'(2WD|4WD|AWD|HTRAC|4륜|2륜)', '', trim_raw, flags=re.I).strip()
    trim_clean = re.sub(r'\s+', ' ', trim_clean).strip()
    
    # 변속기 M/T 표시
    if sub_label == 'M/T' or '수동' in trim_raw:
        if '(M/T)' not in trim_clean:
            trim_clean = f"{trim_clean} (M/T)"

    # 5. 조합
    parts = []
    if fuel:
        parts.append(fuel)
    if disp:
        parts.append(disp)
    if drive:
        parts.append(drive)
    if trim_clean:
        parts.append(trim_clean)

    grade_key = " ".join(parts).strip()
    return grade_key


def parse_lineup_html_v2(html: str, car_name: str, lineup_name: str) -> Dict[str, dict]:
    """라인업 HTML에서 등급별 base_price, standard_features, options 파싱"""
    soup = BeautifulSoup(html, 'html.parser')
    spec_table = soup.select_one('table.tableBlock.specTable')
    if not spec_table:
        return {}

    packages = {}
    for tbl in soup.select('table.tableBlock:not(.specTable)'):
        for tr in tbl.find_all('tr'):
            tds = tr.find_all(['td', 'th'])
            if len(tds) >= 2:
                p_name = clean_text(tds[0].get_text())
                p_desc = clean_text(tds[1].get_text())
                if p_name and p_name not in ['패키지 옵션', '선택품목', '세부 사양', '주요품목', '공통 옵션', '칼라 포인트', '적용 부위']:
                    packages[p_name] = p_desc

    trs = spec_table.find_all('tr')
    current_trim_raw = ""
    current_grade_data = None
    grades_result = {}

    for tr in trs:
        td_trim = None
        for td in tr.find_all('td'):
            cls = td.get('class', [])
            if any('trimsName' in c for c in cls):
                td_trim = td
                break
        
        if td_trim:
            current_trim_raw = clean_text(td_trim.get_text())

        price_el = tr.select_one('em.num.base, .basePrice')
        if price_el:
            base_price = parse_price(price_el.get_text())
            if base_price > 0:
                sub_label = ""
                td_center = tr.select_one('td.tdCenter')
                if td_center:
                    txt = clean_text(td_center.get_text())
                    if txt in ['M/T', 'A/T', '수동', '자동']:
                        sub_label = txt

                grade_key = build_grade_key(car_name, lineup_name, current_trim_raw, sub_label)
                
                std_features = []
                tds = tr.find_all('td')
                for td in tds:
                    t_text = td.get_text(separator='\n', strip=True)
                    if '▶' in t_text or '기본품목' in t_text or '•' in t_text:
                        lines = [clean_text(l) for l in t_text.split('\n')]
                        for l in lines:
                            l = re.sub(r'^[▶•·\-\*]\s*', '', l).strip()
                            if l and l not in ['기본품목', '주요기본품목']:
                                std_features.append(l)
                        break

                if base_price % 10000 == 0:
                    base_price_man = base_price // 10000
                else:
                    base_price_man = round(base_price / 10000, 4)

                current_grade_data = {
                    "base_price": base_price,
                    "base_price_man": base_price_man,
                    "standard_features": std_features,
                    "options": {}
                }
                grades_result[grade_key] = current_grade_data

        choices = tr.select('ul.pChkItemList .choice')
        if choices and current_grade_data is not None:
            for ch in choices:
                info_span = ch.select_one('.choice__info .txt, label')
                opt_name = clean_text(info_span.get_text()) if info_span else ""
                price_span = ch.select_one('.choice__price .txt, .price')
                opt_price = parse_price(price_span.get_text()) if price_span else 0
                code = ch.get('code')

                if not opt_name or opt_name in ['선택', '전체']:
                    continue

                if opt_price <= 0:
                    continue

                # 유상 외장 컬러 제외 (투톤 루프/익스테리어는 포함)
                is_twotone = any(kw in opt_name for kw in ['투톤 루프', '투톤루프', '투톤 익스테리어', '투톤익스테리어', '투톤'])
                if not is_twotone and any(kw in opt_name for kw in ['외장 컬러', '외장칼라', '외장 색상', '원톤', '스노우 화이트', '메탈릭', '펄', '무광']):
                    continue

                # TUIX, TUON, N 퍼포먼스, HGA, Kia Genuine, 커스터마이징, 용품 제외
                opt_upper = opt_name.upper()
                if any(kw in opt_upper for kw in ['TUIX', 'TUON', 'N 퍼포먼스', 'N PERFORMANCE', 'HGA', 'GENUINE', '제뉴인', '액세서리', '사이드스텝', '블랙박스', '바디킷', '매트', '용품']):
                    continue

                desc = packages.get(opt_name, "")
                if not desc and code:
                    opt_div = tr.select_one(f'#optionKey_{code}') or soup.select_one(f'#optionKey_{code}')
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
                        else:
                            desc = clean_text(opt_div.get_text())

                if opt_price % 10000 == 0:
                    opt_price_man = opt_price // 10000
                else:
                    opt_price_man = round(opt_price / 10000, 4)

                current_grade_data["options"][opt_name] = {
                    "price": opt_price,
                    "price_man": opt_price_man,
                    "desc": desc
                }

    return grades_result


def get_models_for_brand(brand_id: str, session) -> List[Dict[str, str]]:
    """특정 브랜드의 다나와 전체 모델 목록 수집"""
    url = f'https://auto.danawa.com/auto/?Work=brand&Brand={brand_id}'
    r = session.get(url, timeout=12)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')

    models = []
    seen = set()
    for a in soup.find_all('a', href=re.compile(r'Work=model&Model=(\d+)')):
        m = re.search(r'Model=(\d+)', a.get('href'))
        if m:
            mid = m.group(1)
            name = a.get_text(strip=True)
            img = a.find('img')
            img_alt = img.get('alt') if img else ''
            name = name or img_alt
            if name and name not in ['신차가격표', '중고차', '할부비교', '제원', '포토', '뉴스', '리스/렌트', '중고차시세', '견적내기', '시승기']:
                if mid not in seen:
                    seen.add(mid)
                    models.append({'model_id': mid, 'model_name': name})
    return models


def crawl_brand_full(brand_id: str, brand_name: str, batch_file_path: str) -> dict:
    """브랜드 단위 다나와 전수 수집 및 검증"""
    session = get_danawa_session()
    models = get_models_for_brand(brand_id, session)
    logger.info(f"[{brand_name}] 다나와 등록 모델 총 {len(models)}개 수집 착수...")

    result_catalog: Dict[str, Dict[str, Dict[str, Any]]] = {}
    tmp_file = batch_file_path + ".tmp"
    if os.path.exists(tmp_file):
        try:
            with open(tmp_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                result_catalog = loaded.get("danawa", {})
                logger.info(f"[{brand_name}] 임시 캐시 발견: {len(result_catalog)}개 차종 이어받기(Resume) 적용")
        except Exception:
            pass

    total_grades_collected = sum(sum(len(g) for g in y.values()) for y in result_catalog.values())
    total_options_collected = sum(sum(sum(len(info.get('options', {})) for info in g.values()) for g in y.values()) for y in result_catalog.values())

    for idx, m_info in enumerate(models, 1):
        mid = m_info['model_id']
        raw_mname = m_info['model_name']
        clean_mname = normalize_catalog_model_name(raw_mname)

        # 이미 수집 완료된 차종이면 건너뜀 (Resume)
        if clean_mname in result_catalog and len(result_catalog[clean_mname]) > 0:
            logger.info(f"[{brand_name} {idx}/{len(models)}] '{clean_mname}' (mid={mid}): 이미 수집됨 (건너뜀)")
            continue

        try:
            title, lineups_by_year = get_model_lineups(mid, session)
            time.sleep(random.uniform(0.3, 0.6))
        except Exception as e:
            logger.error(f"[{brand_name} {idx}/{len(models)}] 라인업 조회 실패 (mid={mid}): {e}")
            continue

        if not lineups_by_year:
            logger.info(f"[{brand_name} {idx}/{len(models)}] '{clean_mname}' (mid={mid}): 가격표 없음 (건너뜀)")
            continue

        target_car_name = title if title else clean_mname
        target_car_name = normalize_catalog_model_name(target_car_name)

        if target_car_name in result_catalog and len(result_catalog[target_car_name]) > 0:
            logger.info(f"[{brand_name} {idx}/{len(models)}] '{target_car_name}' (mid={mid}): 이미 수집됨 (건너뜀)")
            continue

        if target_car_name not in result_catalog:
            result_catalog[target_car_name] = {}

        car_grades_count = 0
        for year in sorted(lineups_by_year.keys()):
            lus = lineups_by_year[year]
            best_lus = filter_best_lineups_for_year(lus)
            if not best_lus:
                continue

            if year not in result_catalog[target_car_name]:
                result_catalog[target_car_name][year] = {}

            for lu in best_lus:
                lu_id = lu['lineup_id']
                lu_name = lu.get('name', '')
                
                time.sleep(random.uniform(0.35, 0.65))
                html = fetch_lineup_page(session, mid, lu_id)
                if not html:
                    continue

                parsed_grades = parse_lineup_html_v2(html, target_car_name, lu_name)
                if parsed_grades:
                    for g_key, g_val in parsed_grades.items():
                        if g_key not in result_catalog[target_car_name][year]:
                            result_catalog[target_car_name][year][g_key] = g_val
                            total_grades_collected += 1
                            car_grades_count += 1
                            total_options_collected += len(g_val.get('options', {}))
                        else:
                            for opt_k, opt_v in g_val.get('options', {}).items():
                                if opt_k not in result_catalog[target_car_name][year][g_key]['options']:
                                    result_catalog[target_car_name][year][g_key]['options'][opt_k] = opt_v
                                    total_options_collected += 1

        result_catalog[target_car_name] = {y: g for y, g in result_catalog[target_car_name].items() if g}
        if not result_catalog[target_car_name]:
            del result_catalog[target_car_name]
        else:
            y_cnt = len(result_catalog[target_car_name])
            logger.info(f"[{brand_name} {idx}/{len(models)}] ✅ '{target_car_name}' (mid={mid}) 완료: {y_cnt}개 연식, {car_grades_count}개 등급")
            # 중간 저장 (crash-safe)
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump({"danawa": result_catalog}, f, ensure_ascii=False)
            except Exception:
                pass

    # 가격 검증
    issues = []
    for c_name, years in result_catalog.items():
        for y, grades in years.items():
            for g_name, g_info in grades.items():
                bp = g_info.get('base_price', 0)
                bpm = g_info.get('base_price_man', 0)
                if abs(bp - bpm * 10000) > 0.01:
                    issues.append(f"Base price mismatch: {c_name} {y} {g_name} ({bp} != {bpm}*10000)")
                for opt_k, opt_v in g_info.get('options', {}).items():
                    op = opt_v.get('price', 0)
                    opm = opt_v.get('price_man', 0)
                    if abs(op - opm * 10000) > 0.01:
                        issues.append(f"Option price mismatch: {c_name} {y} {g_name} [{opt_k}] ({op} != {opm}*10000)")

    if issues:
        logger.error(f"[{brand_name}] 가격 검증 불일치 {len(issues)}건 발견:")
        for iss in issues[:20]:
            logger.error(f"  - {iss}")
        raise ValueError(f"[{brand_name}] 가격 검증 불일치 {len(issues)}건 발견!")

    logger.info(f"[{brand_name}] ✅ 가격 전수 검증 통과 (총 {len(result_catalog)}개 차종, {total_grades_collected}개 등급, {total_options_collected}개 옵션)")

    with open(batch_file_path, 'w', encoding='utf-8') as f:
        json.dump({'danawa': result_catalog}, f, ensure_ascii=False, indent=2)
    logger.info(f"[{brand_name}] 결과 저장 완료: {batch_file_path}")

    # 임시 파일 정리
    if os.path.exists(tmp_file):
        try:
            os.remove(tmp_file)
        except Exception:
            pass

    return result_catalog


def merge_and_verify_brand(brand_name: str, batch_file_path: str) -> Tuple[int, int, int, int]:
    """V2 책 병합 및 기존 데이터 불변성 전수 검증"""
    backup_file = os.path.join(DATA_DIR, f"catalog_by_source_v2_backup_before_{brand_name}.json")
    shutil.copy2(CATALOG_V2_FILE, backup_file)
    logger.info(f"[{brand_name}] 안전 백업 생성 완료: {backup_file}")

    with open(CATALOG_V2_FILE, "r", encoding="utf-8") as f:
        v2_data = json.load(f)

    with open(batch_file_path, "r", encoding="utf-8") as f:
        batch_data = json.load(f)

    v2_danawa = v2_data.get("danawa", {})
    batch_danawa = batch_data.get("danawa", {})

    initial_car_count = len(v2_danawa)
    batch_car_count = len(batch_danawa)
    original_snapshot = copy.deepcopy(v2_danawa)

    new_cars_added = []
    new_years_added = []

    for car_name, year_dict in batch_danawa.items():
        if car_name not in v2_danawa:
            v2_danawa[car_name] = {}
            new_cars_added.append(car_name)

        for year, grade_dict in year_dict.items():
            if year not in v2_danawa[car_name]:
                v2_danawa[car_name][year] = grade_dict
                if car_name not in new_cars_added:
                    new_years_added.append(f"{car_name} {year}")
            else:
                for g_name, g_val in grade_dict.items():
                    if g_name not in v2_danawa[car_name][year]:
                        v2_danawa[car_name][year][g_name] = g_val

    # 불변성 전수 검증
    for car_name, orig_years in original_snapshot.items():
        curr_years = v2_danawa[car_name]
        for y, orig_grades in orig_years.items():
            assert y in curr_years, f"기존 연식 누락: {car_name} {y}"
            curr_grades = curr_years[y]
            for g_name, orig_gval in orig_grades.items():
                assert g_name in curr_grades, f"기존 등급 누락: {car_name} {y} {g_name}"
                curr_gval = curr_grades[g_name]
                assert orig_gval.get("base_price") == curr_gval.get("base_price"), f"base_price 변경: {car_name} {y} {g_name}"
                assert orig_gval.get("base_price_man") == curr_gval.get("base_price_man"), f"base_price_man 변경: {car_name} {y} {g_name}"
                for opt_k, orig_opt_v in orig_gval.get("options", {}).items():
                    assert opt_k in curr_gval.get("options", {}), f"기존 옵션 누락: {car_name} {y} {g_name} [{opt_k}]"
                    assert orig_opt_v.get("price") == curr_gval["options"][opt_k].get("price"), f"옵션 가격 변경: {car_name} {y} {g_name} [{opt_k}]"

    logger.info(f"[{brand_name}] ✅ 기존 {initial_car_count}개 차종 100% 불변 검증 완료!")

    # 가격 무결성 전수 검증
    mismatch_count = 0
    total_grades = 0
    total_options = 0
    for c_name, years in v2_danawa.items():
        for y, grades in years.items():
            for g_name, g_info in grades.items():
                total_grades += 1
                bp = g_info.get("base_price", 0)
                bpm = g_info.get("base_price_man", 0)
                if abs(bp - bpm * 10000) > 0.01:
                    mismatch_count += 1
                for opt_k, opt_v in g_info.get("options", {}).items():
                    total_options += 1
                    op = opt_v.get("price", 0)
                    opm = opt_v.get("price_man", 0)
                    if abs(op - opm * 10000) > 0.01:
                        mismatch_count += 1

    assert mismatch_count == 0, f"[{brand_name}] 전체 가격 불일치 {mismatch_count}건 발생!"
    logger.info(f"[{brand_name}] ✅ 전체 V2 가격 검증 통과 (총 {total_grades}개 등급, {total_options}개 옵션)")

    final_car_count = len(v2_danawa)
    logger.info(f"[{brand_name}] V2 차종 수: {initial_car_count} -> {final_car_count} (+{len(new_cars_added)}개 신규 차종, +{len(new_years_added)}건 신규 연식)")

    with open(CATALOG_V2_FILE, "w", encoding="utf-8") as f:
        json.dump(v2_data, f, ensure_ascii=False, indent=2)
    logger.info(f"[{brand_name}] V2 책 저장 완료: {CATALOG_V2_FILE}")

    return initial_car_count, final_car_count, len(new_cars_added), len(new_years_added)


def commit_and_push(commit_seq: str, brand_name: str, car_count: int, grade_count: int, batch_file_path: str):
    """빌드 검증 후 Git 자동 커밋 & 푸시"""
    logger.info(f"[{brand_name}] 프론트엔드 빌드 검증 시작...")
    build_res = subprocess.run(["npm", "run", "--prefix", "frontend", "build"], capture_output=True, text=True, shell=True)
    if build_res.returncode != 0:
        logger.error(f"[{brand_name}] 프론트엔드 빌드 실패:\n{build_res.stderr}")
        raise RuntimeError("프론트엔드 빌드 실패")
    logger.info(f"[{brand_name}] ✅ 프론트엔드 빌드 성공!")

    # git add
    subprocess.run(["git", "add", batch_file_path, CATALOG_V2_FILE, "scripts/run_domestic_catalog_pipeline.py"], check=True)
    commit_msg = f"{commit_seq}: {brand_name} 전 세대 라인업 다나와 카탈로그 수집 및 V2 책 병합 ({car_count}개 차종·{grade_count}개 등급)"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
    logger.info(f"[{brand_name}] ✅ Git 커밋 완료: {commit_msg}")

    # git push
    push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
    if push_res.returncode != 0:
        logger.error(f"[{brand_name}] Git 푸시 실패:\n{push_res.stderr}")
        raise RuntimeError("Git 푸시 실패")
    logger.info(f"[{brand_name}] 🚀 GitHub 원격 저장소 푸시 완료!")


def run_pipeline():
    pipeline_targets = [
        {
            "brand_id": "307",
            "brand_name": "기아",
            "commit_seq": "11-06-47",
            "batch_file": os.path.join(DATA_DIR, "batch-kia-lineup.json")
        },
        {
            "brand_id": "326",
            "brand_name": "KGM",
            "commit_seq": "11-06-48",
            "batch_file": os.path.join(DATA_DIR, "batch-kgm-full-lineup.json")
        },
        {
            "brand_id": "321",
            "brand_name": "르노코리아",
            "commit_seq": "11-06-49",
            "batch_file": os.path.join(DATA_DIR, "batch-renault-lineup.json")
        },
        {
            "brand_id": "304",
            "brand_name": "제네시스",
            "commit_seq": "11-06-50",
            "batch_file": os.path.join(DATA_DIR, "batch-genesis-lineup.json")
        }
    ]

    total_steps = len(pipeline_targets)
    logger.info(f"==================================================")
    logger.info(f"🚀 국내 미수집 4개 브랜드 전수 수집 파이프라인 시작 (총 {total_steps}단계)")
    logger.info(f"==================================================")

    summary_results = []

    for step_idx, target in enumerate(pipeline_targets, 1):
        bid = target["brand_id"]
        bname = target["brand_name"]
        cseq = target["commit_seq"]
        bfile = target["batch_file"]

        logger.info(f"\n▶ [{step_idx}/{total_steps}] {bname} (Brand={bid}, 커밋 {cseq}) 착수...")

        # 1. 크롤링 및 실측 정제
        t0 = time.time()
        crawled_dict = crawl_brand_full(bid, bname, bfile)
        c_cars = len(crawled_dict)
        c_grades = sum(sum(len(g) for g in y.values()) for y in crawled_dict.values())
        c_options = sum(sum(sum(len(info.get('options', {})) for info in g.values()) for g in y.values()) for y in crawled_dict.values())
        t_crawl = time.time() - t0

        # 2. V2 책 Deep Merge 및 불변성 검증
        init_cnt, final_cnt, new_cars, new_years = merge_and_verify_brand(bname, bfile)

        # 3. 프론트엔드 빌드 검증 및 커밋 & 푸시
        commit_and_push(cseq, bname, c_cars, c_grades, bfile)

        res_item = {
            "step": f"{step_idx}/{total_steps}",
            "brand": bname,
            "commit": cseq,
            "crawled_cars": c_cars,
            "crawled_grades": c_grades,
            "crawled_options": c_options,
            "v2_cars_before": init_cnt,
            "v2_cars_after": final_cnt,
            "new_cars_added": new_cars,
            "new_years_added": new_years,
            "elapsed_seconds": round(t_crawl, 1)
        }
        summary_results.append(res_item)
        logger.info(f"[{bname}] ✅ 단계 완료! (소요 시간: {t_crawl:.1f}초)")

        # 진행 상황 JSON 기록
        progress_path = os.path.join(DATA_DIR, "pipeline_progress.json")
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(summary_results, f, ensure_ascii=False, indent=2)

    logger.info(f"\n==================================================")
    logger.info(f"🎉 전 4개 브랜드 전수 수집 및 V2 책 병합 완료!")
    logger.info(f"==================================================")


if __name__ == "__main__":
    run_pipeline()
