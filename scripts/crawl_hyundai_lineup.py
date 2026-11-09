# -*- coding: utf-8 -*-
"""
scripts/crawl_hyundai_lineup.py
감사 보고서(docs/catalog-gap-audit-2026-11-09.md) 기준 현대 전 세대 라인업 다나와 신차 카탈로그 수집 및 정제.
- 대상: 다나와 현대(Brand=303) 전 모델 (164개 모델)
- 누락 연식(더 뉴 아반떼 2018, 디 올 뉴 싼타페 2026 등) 포함
- 수집 및 정제 규칙:
  1. 다나와 실제 값만 사용 (추정/더미 금지)
  2. 403/429 발생 시 즉시 중단 및 보고
  3. 가격표 버전이 여러 개면 첫 번째(원본) 사용, 인하 버전 제외
  4. HEV는 세제혜택 적용 후 가격 사용
  5. 제외: 유상 외장 컬러 전부(단, 투톤 루프/익스테리어 포함), TUIX/TUON/N 퍼포먼스/HGA/현대 제뉴인 액세서리/용품,
          LPG 렌터카/장애인/택시, 가격 0원 옵션
  6. 밴 등급 포함
  7. 검증: price == price_man * 10000 전수 일치
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
from services.danawa_crawler import get_danawa_session, get_model_lineups, clean_text, parse_price, normalize_catalog_model_name
from services.model_matcher import ModelMatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("crawl_hyundai")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_BATCH_FILE = os.path.join(DATA_DIR, "batch-hyundai-lineup.json")
CATALOG_V2_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2.json")


def filter_best_lineups_for_year(lineups: List[dict]) -> List[dict]:
    """
    동일 연식 내 라인업 필터링:
    1. 장애인/렌터카/택시/면세 제외 (일반인/자가용/승용/밴 포함)
    2. HEV 세제혜택 적용 후 우선
    3. '인하', '3.5%', '3.0%', '사양변경' 등 인하 버전 제외 (원본 우선)
    4. 사전계약 제외
    """
    valid_list = []
    for lu in lineups:
        name = lu.get('name', '')
        if any(kw in name for kw in ['장애인', '렌터카', '렌트카', '택시', '면세']):
            continue
        valid_list.append(lu)

    # HEV 세제혜택 전/후 구분: 세제혜택 후가 있으면 우선 선택
    has_tax_benefit = any('세제혜택 후' in lu.get('name', '') for lu in valid_list)
    if has_tax_benefit:
        tax_filtered = []
        for lu in valid_list:
            n = lu.get('name', '')
            if '하이브리드' in n or 'HEV' in n or '플러그인' in n or 'PHEV' in n:
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
    """
    표준 등급키 생성: {유종} {배기량} {구동} {트림명}
    예: '가솔린 1.6 터보 2WD 인스퍼레이션'
    """
    clean_lineup = re.sub(r'\(.*?\)', '', lineup_name).strip()
    full_text = f"{car_name} {clean_lineup} {trim_raw} {sub_label}".strip()
    
    # 1. 유종 추출
    fuel = ModelMatcher.extract_fuel(full_text)
    if not fuel:
        fl = full_text.lower()
        if any(k in fl for k in ['ev', '전기', '일렉트릭', '아이오닉', '수소', 'fcev', '넥쏘']):
            fuel = '전기'
        elif any(k in fl for k in ['하이브리드', 'hev']):
            fuel = '하이브리드'
        elif any(k in fl for k in ['플러그인', 'phev']):
            fuel = '하이브리드'
        elif any(k in fl for k in ['디젤', 'e-vgt', 'vgt', 'crdi']):
            fuel = '디젤'
        elif any(k in fl for k in ['lpi', 'lpg']):
            fuel = 'LPG'
        elif any(k in car_name for k in ['팰리세이드', '제네시스']):
            fuel = '가솔린'
        else:
            fuel = '가솔린'

    # 2. 배기량 추출
    disp = ModelMatcher.extract_disp(full_text)
    if not disp and fuel not in ['전기']:
        m_cc = re.search(r'(\d\.\d+)', full_text)
        if m_cc:
            disp = m_cc.group(1)

    # 3. 구동방식 추출 (HTRAC -> 4WD)
    m_drive = re.search(r'(2WD|4WD|AWD|HTRAC)', trim_raw, re.I)
    if not m_drive:
        m_drive = re.search(r'(2WD|4WD|AWD|HTRAC)', clean_lineup, re.I)
    drive_val = m_drive.group(1).upper() if m_drive else '2WD'
    if drive_val in ['AWD', '4WD', 'HTRAC']:
        drive = '4WD'
    else:
        drive = '2WD'

    # 4. 순수 트림명 정리
    trim_clean = re.sub(r'(2WD|4WD|AWD|HTRAC)', '', trim_raw, flags=re.I).strip()
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

                # TUIX, TUON, N 퍼포먼스, HGA, 현대 제뉴인 액세서리, 용품 제외
                opt_upper = opt_name.upper()
                if any(kw in opt_upper for kw in ['TUIX', 'TUON', 'N 퍼포먼스', 'N PERFORMANCE', 'HGA', '제뉴인', '액세서리', '사이드스텝', '블랙박스', '바디킷', '매트', '용품']):
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

                current_grade_data["options"][opt_name] = {
                    "price": opt_price,
                    "price_man": opt_price // 10000,
                    "desc": desc
                }

    return grades_result


def get_all_hyundai_models(session) -> List[Dict[str, str]]:
    """다나와 현대(Brand=303) 전체 모델 목록 수집"""
    url = 'https://auto.danawa.com/auto/?Work=brand&Brand=303'
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


def crawl_hyundai_all() -> dict:
    session = get_danawa_session()
    models = get_all_hyundai_models(session)
    logger.info(f"다나와 현대 등록 모델 총 {len(models)}개 수집 대상 확인.")

    result_catalog: Dict[str, Dict[str, Dict[str, Any]]] = {}
    total_grades_collected = 0
    total_options_collected = 0

    for idx, m_info in enumerate(models, 1):
        mid = m_info['model_id']
        raw_mname = m_info['model_name']
        clean_mname = normalize_catalog_model_name(raw_mname)

        try:
            title, lineups_by_year = get_model_lineups(mid, session)
            time.sleep(random.uniform(0.3, 0.6))
        except Exception as e:
            logger.error(f"[{idx}/{len(models)}] 라인업 조회 실패 (mid={mid}): {e}")
            continue

        if not lineups_by_year:
            logger.info(f"[{idx}/{len(models)}] '{clean_mname}' (mid={mid}): 가격표 없음 (건너뜀)")
            continue

        target_car_name = title if title else clean_mname
        target_car_name = normalize_catalog_model_name(target_car_name)

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
            logger.info(f"[{idx}/{len(models)}] ✅ '{target_car_name}' (mid={mid}) 수집 완료: {y_cnt}개 연식, {car_grades_count}개 등급")

    logger.info(f"\n==================================================")
    logger.info(f"현대 수집 최종 완료: 총 {len(result_catalog)}개 차종, {total_grades_collected}개 등급, {total_options_collected}개 옵션")
    logger.info(f"==================================================")

    # 무결성 전수 검증
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
        logger.error(f"가격 검증 불일치 {len(issues)}건 발견!")
        for iss in issues[:10]:
            logger.error(f"  - {iss}")
        raise ValueError("가격 전수 검증 실패!")
    else:
        logger.info("✅ 가격 전수 검증 (price == price_man * 10000): 불일치 0건 (100% 통과)")

    # 저장
    with open(OUTPUT_BATCH_FILE, 'w', encoding='utf-8') as f:
        json.dump({'danawa': result_catalog}, f, ensure_ascii=False, indent=2)
    logger.info(f"결과 저장 완료: {OUTPUT_BATCH_FILE}")

    return result_catalog


if __name__ == "__main__":
    crawl_hyundai_all()

