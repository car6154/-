# -*- coding: utf-8 -*-
"""
scripts/crawl_kgm_batch51.py
쌍용/KG모빌리티 16개 차종 다나와 신차 카탈로그 수집 및 정제 (batch-51)
- 대상 차종:
  더 뉴 티볼리, 더 뉴 토레스, 토레스 EVX, 렉스턴 뉴 아레나, 티볼리, 코란도 C,
  코란도 이모션, 코란도 EV, 코란도, 토레스, 슈퍼 렉스턴, 렉스턴 W,
  G4 렉스턴, 올 뉴 렉스턴, 렉스턴 스포츠, 베리 뉴 티볼리
- 수집 및 정제 규칙:
  1. 다나와 실제 값만 사용 (추정/더미 금지)
  2. 403/429 발생 시 즉시 중단 및 보고
  3. 가격표 버전이 여러 개면 첫 번째(원본) 사용, 인하 버전 제외
  4. 제외: 유상 외장 컬러 전부(단, 투톤 루프/익스테리어 포함), TUON/TUIX/KGA/커스터마이징/용품,
          LPG 렌터카/장애인/택시, 가격 0원 옵션
  5. 검증: price == price_man * 10000 전수 일치
  6. 베리 뉴 티볼리 2020년식 1.5 가솔린 2WD V3 5인승 (20,500,000원) 필수 포함
"""

import sys
import os
import re
import json
import time
import random
import logging
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.danawa_crawler import get_danawa_session, get_model_lineups, clean_text, parse_price
from services.data_processor import DataProcessor
from services.model_matcher import ModelMatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("crawl_kgm_batch51")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_BATCH_FILE = os.path.join(DATA_DIR, "batch-51-kgm-lineup.json")
CATALOG_V2_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2.json")

# 16개 차종과 다나와 model_id 매핑
KGM_MODELS = {
    '더 뉴 티볼리': ['4545'],
    '더 뉴 토레스': ['4646'],
    '토레스 EVX': ['4492'],
    '렉스턴 뉴 아레나': ['4518'],
    '티볼리': ['3154', '3505'],
    '코란도 C': ['2146', '3105', '3442'],
    '코란도 이모션': ['4089'],
    '코란도 EV': ['4605'],
    '코란도': ['3635'],
    '토레스': ['4092'],
    '슈퍼 렉스턴': ['2058'],
    '렉스턴 W': ['2214'],
    'G4 렉스턴': ['3419'],
    '올 뉴 렉스턴': ['4006'],
    '렉스턴 스포츠': ['3544', '4050', '4519'],
    '베리 뉴 티볼리': ['3723'],
}

def is_excluded_lineup(name: str) -> bool:
    """영업용/렌터카/장애인/택시/면세 라인업 제외"""
    name_clean = name.replace(" ", "")
    exclude_kws = ['렌터카', '렌트카', '장애인', '택시', '면세', '조달']
    return any(kw in name_clean for kw in exclude_kws)

def filter_best_lineups_for_year(lineup_list: List[dict]) -> List[dict]:
    """
    한 연식 내의 라인업 목록에서:
    1. 영업용/렌터카/장애인/택시 제외
    2. 엔진/유종별로 그룹화
    3. 각 그룹 내에서 '첫 번째(원본)' 라인업 선택 (인하 버전 제외)
    """
    valid_list = [lu for lu in lineup_list if not is_excluded_lineup(lu.get('name', ''))]
    if not valid_list:
        return []

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
        # 사전계약이 아닌 정식 출시 라인업 우선
        non_pre = [lu for lu in lus if '사전계약' not in lu.get('name', '')]
        candidates = non_pre if non_pre else lus

        # 인하/변경 키워드가 없는 '원본' 우선
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

    # Tab=item 폴백 시도
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
    """
    표준 등급키 생성: {유종} {배기량} {구동} {트림명}
    예: '가솔린 1.5 2WD V3'
    """
    clean_lineup = re.sub(r'\(.*?\)', '', lineup_name).strip()
    full_text = f"{car_name} {clean_lineup} {trim_raw} {sub_label}".strip()
    
    # 1. 유종 추출 (ModelMatcher 활용 및 KGM 모델 보완)
    fuel = ModelMatcher.extract_fuel(full_text)
    if not fuel:
        fl = full_text.lower()
        if any(k in fl for k in ['evx', '이모션', 'ev', '전기', '일렉트릭']):
            fuel = '전기'
        elif any(k in fl for k in ['e-xdi', 'xdi', '디젤', 'crd', 'cdi']):
            fuel = '디젤'
        elif any(k in fl for k in ['바이퓨얼', 'lpg', 'lpi']):
            fuel = 'LPG'
        elif any(k in car_name for k in ['렉스턴', '코란도 C']):
            fuel = '디젤'
        else:
            fuel = '가솔린'

    # 2. 배기량 추출
    disp = ModelMatcher.extract_disp(full_text)
    if not disp and fuel != '전기':
        m_cc = re.search(r'(\d\.\d)', full_text)
        if m_cc:
            disp = m_cc.group(1)

    # 3. 구동방식 추출 (한글 접두사 대응 위해 단어 경계 \b 없이 매칭)
    m_drive = re.search(r'(2WD|4WD|AWD)', trim_raw, re.I)
    if not m_drive:
        m_drive = re.search(r'(2WD|4WD|AWD)', clean_lineup, re.I)
    drive = m_drive.group(1).upper() if m_drive else '2WD'
    if drive == 'AWD':
        drive = '4WD'

    # 4. 순수 트림명 정리 (2WD/4WD/AWD 및 불필요 문자열 제거)
    trim_clean = re.sub(r'(2WD|4WD|AWD)', '', trim_raw, flags=re.I).strip()
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
    """
    단일 라인업 HTML에서 등급별 base_price, standard_features, options 파싱
    """
    soup = BeautifulSoup(html, 'html.parser')
    spec_table = soup.select_one('table.tableBlock.specTable')
    if not spec_table:
        return {}

    # 1. 패키지 상세 설명 테이블 수집
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
        # trimsName 체크
        td_trim = None
        for td in tr.find_all('td'):
            cls = td.get('class', [])
            if any('trimsName' in c for c in cls):
                td_trim = td
                break
        
        if td_trim:
            current_trim_raw = clean_text(td_trim.get_text())

        # 가격 확인
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
                
                # standard_features 수집
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

                # base_price_man 계산 (만 단위 미만 단수 보존)
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

        # choices (선택 옵션) 행
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

                # 0원 옵션 제외
                if opt_price <= 0:
                    continue

                # 유상 외장 컬러 제외 (단, 투톤 루프/익스테리어는 포함)
                is_twotone = any(kw in opt_name for kw in ['투톤 루프', '투톤루프', '투톤 익스테리어', '투톤익스테리어', '투톤'])
                if not is_twotone and any(kw in opt_name for kw in ['외장 컬러', '외장칼라', '외장 색상', '원톤', '스노우 화이트', '메탈릭', '펄']):
                    continue

                # 용품/커스터마이징/KGA/TUON/TUIX 제외
                if any(kw in opt_name.upper() for kw in ['KGA', 'TUON', 'TUIX', '커스터마이징', '용품', '액세서리', '사이드스텝', '블랙박스']):
                    continue

                # desc 추출
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

                current_grade_data["options"][opt_name] = {
                    "price": opt_price,
                    "price_man": opt_price // 10000,
                    "desc": desc
                }

    return grades_result

def crawl_all_kgm_lineups() -> dict:
    session = get_danawa_session()
    result_catalog = {}

    total_cars = len(KGM_MODELS)
    total_grades_collected = 0
    total_options_collected = 0

    logger.info(f"Starting crawl for {total_cars} KGM cars...")

    for c_idx, (car_name, mids) in enumerate(KGM_MODELS.items(), 1):
        logger.info(f"[{c_idx}/{total_cars}] Crawling '{car_name}' (mids={mids})...")
        car_dict = {}

        for mid in mids:
            try:
                title, lineups_by_year = get_model_lineups(mid, session)
                time.sleep(random.uniform(0.4, 0.7))
            except Exception as e:
                logger.error(f"Failed to get lineups for mid={mid}: {e}")
                continue

            for year in sorted(lineups_by_year.keys()):
                lus = lineups_by_year[year]
                best_lus = filter_best_lineups_for_year(lus)
                if not best_lus:
                    continue

                if year not in car_dict:
                    car_dict[year] = {}

                for lu in best_lus:
                    lu_id = lu['lineup_id']
                    lu_name = lu.get('name', '')
                    
                    time.sleep(random.uniform(0.5, 0.8))
                    html = fetch_lineup_page(session, mid, lu_id)
                    if not html:
                        continue

                    parsed_grades = parse_lineup_html_v2(html, car_name, lu_name)
                    if parsed_grades:
                        for g_key, g_val in parsed_grades.items():
                            if g_key not in car_dict[year]:
                                car_dict[year][g_key] = g_val
                                total_grades_collected += 1
                                total_options_collected += len(g_val.get('options', {}))
                            else:
                                for opt_k, opt_v in g_val.get('options', {}).items():
                                    if opt_k not in car_dict[year][g_key]['options']:
                                        car_dict[year][g_key]['options'][opt_k] = opt_v
                                        total_options_collected += 1

        car_dict = {y: g for y, g in car_dict.items() if g}
        if car_dict:
            result_catalog[car_name] = car_dict
            g_count = sum(len(g) for g in car_dict.values())
            logger.info(f" -> '{car_name}' collected: {len(car_dict)} years, {g_count} grades")
        else:
            logger.warning(f" -> '{car_name}' has NO data collected!")

    logger.info(f"Crawl finished: {len(result_catalog)} cars, {total_grades_collected} grades, {total_options_collected} options.")
    return result_catalog

def validate_collected_data(catalog_dict: dict) -> Tuple[bool, List[str]]:
    """수집 데이터 무결성 전수 검증"""
    issues = []
    
    for car_name, years in catalog_dict.items():
        for year, grades in years.items():
            for g_name, g_info in grades.items():
                bp = g_info.get('base_price', 0)
                bpm = g_info.get('base_price_man', 0)
                if abs(bp - bpm * 10000) > 0.01:
                    issues.append(f"Base price mismatch in {car_name} {year} {g_name}: {bp} != {bpm}*10000")
                
                for opt_name, opt_info in g_info.get('options', {}).items():
                    p = opt_info.get('price', 0)
                    pm = opt_info.get('price_man', 0)
                    if p != pm * 10000:
                        issues.append(f"Option price mismatch in {car_name} {year} {g_name} [{opt_name}]: {p} != {pm}*10000")

    if '베리 뉴 티볼리' not in catalog_dict:
        issues.append("'베리 뉴 티볼리' missing from collected catalog!")
    else:
        vnt = catalog_dict['베리 뉴 티볼리']
        if '2020' not in vnt:
            issues.append("'베리 뉴 티볼리' 2020 year missing!")
        else:
            vnt_2020 = vnt['2020']
            v3_grades = [k for k in vnt_2020.keys() if 'V3' in k and '2WD' in k]
            if not v3_grades:
                issues.append(f"'베리 뉴 티볼리' 2020 missing V3 2WD! Available: {list(vnt_2020.keys())}")
            else:
                v3_info = vnt_2020[v3_grades[0]]
                if v3_info.get('base_price') != 20500000:
                    issues.append(f"'베리 뉴 티볼리' 2020 V3 2WD base_price expected 20500000, got {v3_info.get('base_price')}")

    return len(issues) == 0, issues

def main():
    logger.info("=== Starting batch-51 KGM Lineup Crawling ===")
    
    # 1. 크롤링 실행
    catalog_data = crawl_all_kgm_lineups()

    # 2. JSON 유효성 및 무결성 검증
    is_valid, issues = validate_collected_data(catalog_data)
    if not is_valid:
        logger.error(f"Validation FAILED with {len(issues)} issues:")
        for iss in issues[:10]:
            logger.error(f" - {iss}")
        sys.exit(1)
    logger.info("Validation PASSED: all prices (price == price_man * 10000) and Tivoli V3 2WD confirmed!")

    # 3. data/batch-51-kgm-lineup.json 저장
    output_dict = {"danawa": catalog_data}
    with open(OUTPUT_BATCH_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_dict, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved batch file to: {OUTPUT_BATCH_FILE}")

    # 통계 출력
    car_count = len(catalog_data)
    grade_count = sum(sum(len(g) for g in y.values()) for y in catalog_data.values())
    total_opts = sum(sum(sum(len(g.get('options', {})) for g in y.values()) for y in c.values()) for c in catalog_data.values())
    print("\n" + "=" * 60)
    print(f" [batch-51 완료 통계]")
    print(f" - 수집 차종: {car_count}개")
    print(f" - 총 수집 등급: {grade_count}개")
    print(f" - 총 수집 옵션: {total_opts}개")
    print("=" * 60)

if __name__ == '__main__':
    main()
