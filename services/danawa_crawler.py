# -*- coding: utf-8 -*-
"""
다나와 신차 카탈로그 수집 및 파서 모듈 (danawa_crawler.py)
- 다나와 자동차(auto.danawa.com)에서 정적 HTML(SSR)을 수집하여
  표준 카탈로그 형식(grades, options, packages)으로 파싱 및 저장.
- SSL Handshake 에러 방지를 위해 ciphers='DEFAULT' 커스텀 어댑터 사용.
- 빈 껍데기(내용 없는 키) 저장 방지.
- 5건마다 저장 및 중단 시 이어받기(재개) 지원.
- 1.5~2초 랜덤 딜레이 -> 차단 시 10초 딜레이 전환.
"""

import os
import sys
import io
import re
import json
import time
import random
import logging
from typing import Dict, List, Optional, Tuple, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 경로 설정
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DANAWA_CATALOG_FILE = os.path.join(DATA_DIR, "danawa_newcar_catalog.json")
DANAWA_TARGETS_FILE = os.path.join(DATA_DIR, "danawa_model_targets.json")

# 다나와 모델명/코드 -> 제이프로젝트 표준 카탈로그 모델명 매핑
MODEL_NAME_MAP = {
    # F/L(페이스리프트) 및 세부모델 표준명 매핑 (오염 방지 및 병합)
    "팰리세이드(LX2) F/L": "더 뉴 팰리세이드",
    "팰리세이드 F/L": "더 뉴 팰리세이드",
    "더 뉴 팰리세이드 F/L": "더 뉴 팰리세이드",
    "투싼(NX4) F/L": "더 뉴 투싼",
    "더 뉴 투싼 F/L": "더 뉴 투싼",
    "투싼 F/L": "더 뉴 투싼",
    "더 뉴 그랜저 F/L": "더 뉴 그랜저",
    "그랜저(IG) F/L": "더 뉴 그랜저",
    "쏘렌토(MQ4) F/L": "더 뉴 쏘렌토 4세대",
    "쏘렌토 F/L": "더 뉴 쏘렌토 4세대",
    "더 뉴 쏘렌토 F/L": "더 뉴 쏘렌토 4세대",
    "K5(DL3) F/L": "더 뉴 K5 3세대",
    "K5 F/L": "더 뉴 K5 3세대",
    "더 뉴 K5 F/L": "더 뉴 K5 3세대",
    "카니발(KA4) F/L": "더 뉴 카니발 4세대",
    "카니발 F/L": "더 뉴 카니발 4세대",
    "아반떼(CN7) F/L": "더 뉴 아반떼 (CN7)",
    "아반떼 F/L": "더 뉴 아반떼 (CN7)",
    "스포티지(NQ5) F/L": "더 뉴 스포티지 5세대",
    "스포티지 F/L": "더 뉴 스포티지 5세대",
    "G80(RG3) F/L": "더 뉴 G80",
    "G80 F/L": "더 뉴 G80",
    "GV70(JK1) F/L": "더 뉴 GV70",
    "GV70 F/L": "더 뉴 GV70",
    "GV80(JX1) F/L": "더 뉴 GV80",
    "GV80 F/L": "더 뉴 GV80",
    "G70 F/L": "더 뉴 G70",
    "더 뉴 카니발(KA4)": "더 뉴 카니발 4세대",
    "더 뉴 카니발 4세대": "더 뉴 카니발 4세대",
    "카니발(KA4)": "카니발 4세대",
    "카니발 4세대": "카니발 4세대",
    "더 뉴 카니발": "더 뉴 카니발",
    "올 뉴 카니발": "올 뉴 카니발",
    "카니발R": "카니발 R",
    "카니발 R": "카니발 R",
    "디 올 뉴 그랜저(GN7)": "디 올 뉴 그랜저",
    "디 올 뉴 그랜저 하이브리드(GN7)": "디 올 뉴 그랜저 하이브리드",
    "더 뉴 그랜저(IG)": "더 뉴 그랜저",
    "더 뉴 그랜저 하이브리드(IG)": "더 뉴 그랜저 하이브리드",
    "그랜저(IG)": "그랜저 IG",
    "그랜저(HG)": "그랜저 HG",
    "디 올 뉴 싼타페(MX5)": "디 올 뉴 싼타페",
    "더 뉴 팰리세이드(LX2)": "더 뉴 팰리세이드",
    "팰리세이드(LX2)": "팰리세이드",
    "더 뉴 쏘렌토(MQ4)": "더 뉴 쏘렌토 4세대",
    "쏘렌토(MQ4)": "쏘렌토 4세대",
    "더 뉴 쏘렌토": "더 뉴 쏘렌토",
    "올 뉴 쏘렌토": "올 뉴 쏘렌토",
    "더 뉴 아반떼(CN7)": "더 뉴 아반떼 (CN7)",
    "아반떼(CN7)": "아반떼 (CN7)",
    "더 뉴 투싼(NX4)": "더 뉴 투싼",
    "투싼(NX4)": "투싼 (NX4)",
    "더 뉴 K5(DL3)": "더 뉴 K5 3세대",
    "K5(DL3)": "K5 3세대",
    "더 뉴 스포티지(NQ5)": "더 뉴 스포티지 5세대",
    "스포티지(NQ5)": "스포티지 5세대",
    "스포티지 더 볼드": "스포티지 더 볼드",
    "G80(RG3)": "G80 (RG3)",
    "GV70(JK1)": "GV70",
    "GV80(JX1)": "GV80",
    "디 올 뉴 코나(SX2)": "디 올 뉴 코나",
    "토레스(J100)": "토레스",
    "더 뉴 토레스(J100)": "더 뉴 토레스",
    "트랙스 크로스오버": "트랙스 크로스오버",
    "올 뉴 모닝(TA)": "올 뉴 모닝",
    "더 뉴 모닝": "더 뉴 모닝",
    "모닝 어반": "모닝 어반",
    "더 뉴 모닝(JA)": "더 뉴 모닝 (JA)",
    "더 뉴 레이": "더 뉴 레이",
    "레이(TAM)": "레이",
}

class DanawaAdapter(HTTPAdapter):
    """다나와 웹서버의 SSL Alert Handshake Failure를 방지하는 커스텀 어댑터"""
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context(ciphers='DEFAULT')
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

def get_danawa_session() -> requests.Session:
    s = requests.Session()
    s.mount('https://', DanawaAdapter())
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Referer': 'https://auto.danawa.com/',
    })
    return s

def clean_text(s: str) -> str:
    """공백 정규화"""
    if not s:
        return ""
    return re.sub(r'\s+', ' ', s).strip()

def parse_price(val_str: str) -> int:
    """'48,320,000' -> 48320000"""
    digits = re.sub(r'[^\d]', '', val_str)
    return int(digits) if digits else 0

def extract_year_from_text(txt: str) -> str:
    """텍스트나 날짜에서 연형(MY) 4자리 연식 추출 (연형 표기 우선)"""
    if not txt:
        return ""
    m_my = re.search(r'(20\d{2})\s*(?:년형|년|MY)', txt, re.IGNORECASE)
    if m_my:
        return m_my.group(1)
    txt_no_date = re.sub(r'20\d{2}[\.\-\/]\d{1,2}[\.\-\/]\d{1,2}', '', txt)
    m = re.search(r'\b(20\d{2})\b', txt_no_date)
    return m.group(1) if m else ""

def normalize_catalog_model_name(raw_title: str) -> str:
    """다나와 타이틀에서 순수 모델명 추출 및 카탈로그 표준명 매핑 (정확 일치 기준)"""
    name = raw_title.split('가격')[0].split(':')[0].strip()
    if name in MODEL_NAME_MAP:
        return MODEL_NAME_MAP[name]
    
    clean_n = re.sub(r'\([^\)]+\)', '', name).strip()
    if clean_n in MODEL_NAME_MAP:
        return MODEL_NAME_MAP[clean_n]
    for k, v in MODEL_NAME_MAP.items():
        if k == clean_n:
            return v
            
    return clean_n or name

def parse_danawa_lineup_html(html: str) -> dict:
    """
    단일 라인업 페이지 HTML에서 grades, options, packages 파싱
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    grades = []
    options = {}
    packages = {}
    
    # 1. Spec table (트림, 옵션 가격, 패키지 설명)
    spec_table = soup.select_one('table.tableBlock.specTable')
    if spec_table:
        trs = spec_table.find_all('tr')
        
        for tr in trs:
            td_trim = tr.select_one('td[class*="trimsName"]')
            if td_trim:
                grade_name = clean_text(td_trim.get_text())
                if grade_name and grade_name not in grades:
                    grades.append(grade_name)
            
            td_title = tr.select_one('td.tdTitle')
            if td_title and not any('trimsName' in c for c in td_title.get('class', [])):
                tds = tr.find_all(['td', 'th'])
                if len(tds) >= 2:
                    p_name = clean_text(tds[0].get_text())
                    p_desc = clean_text(tds[1].get_text())
                    if p_name and p_name not in ['패키지 옵션', '선택품목', '세부 사양', '주요품목', '공통 옵션']:
                        packages[p_name] = p_desc

            choices = tr.select('ul.pChkItemList .choice')
            for ch in choices:
                info_span = ch.select_one('.choice__info .txt, label')
                opt_name = clean_text(info_span.get_text()) if info_span else ""
                
                price_span = ch.select_one('.choice__price .txt, .price')
                opt_price = parse_price(price_span.get_text()) if price_span else 0
                
                opt_desc = ""
                code = ch.get('code')
                if code:
                    detail_div = soup.select_one(f'#optionKey_{code}')
                    if detail_div:
                        titles = [clean_text(t.get_text()) for t in detail_div.select('.title')]
                        if titles:
                            opt_desc = ' + '.join([t for t in titles if t])
                        else:
                            opt_desc = clean_text(detail_div.get_text())
                
                if not opt_desc:
                    for pkg_k, pkg_v in packages.items():
                        if opt_name in pkg_k or pkg_k in opt_name:
                            opt_desc = pkg_v
                            break
                
                if opt_name and opt_name not in ['선택', '전체']:
                    if opt_name not in options:
                        options[opt_name] = {"price": opt_price}
                        if opt_desc:
                            options[opt_name]["desc"] = opt_desc
                    else:
                        if options[opt_name].get("price", 0) == 0 and opt_price > 0:
                            options[opt_name]["price"] = opt_price
                        if not options[opt_name].get("desc") and opt_desc:
                            options[opt_name]["desc"] = opt_desc

    # 2. 별도 패키지 테이블 보강
    for tbl in soup.select('table.tableBlock:not(.specTable)'):
        for tr in tbl.find_all('tr'):
            tds = tr.find_all(['td', 'th'])
            if len(tds) >= 2:
                p_name = clean_text(tds[0].get_text())
                p_desc = clean_text(tds[1].get_text())
                if p_name and p_name not in ['패키지 옵션', '선택품목', '세부 사양', '주요품목', '공통 옵션', '칼라 포인트', '적용 부위']:
                    packages[p_name] = p_desc

    return {
        "grades": grades,
        "options": options,
        "packages": packages
    }

def get_model_lineups(model_id: str, session: requests.Session) -> Tuple[str, Dict[str, List[dict]]]:
    """
    다나와 모델 메인 페이지에서 모델 타이틀과 연식별 라인업 목록을 추출.
    반환: (model_name, {year: [{"lineup_id": ..., "name": ..., "date": ...}]})
    """
    url = f"https://auto.danawa.com/auto/?Work=model&Model={model_id}&Tab=price"
    r = session.get(url, timeout=10)
    r.encoding = 'utf-8'
    
    soup = BeautifulSoup(r.text, 'html.parser')
    title_el = soup.find('title')
    raw_title = title_el.get_text(strip=True) if title_el else f"Model_{model_id}"
    model_name = normalize_catalog_model_name(raw_title)
    
    lineups_by_year: Dict[str, List[dict]] = {}
    choices = soup.select('.choice')
    
    for ch in choices:
        inp = ch.select_one('input[name="lineup_"]')
        if not inp:
            continue
        lu_id = inp.get('data-lineup') or inp.get('id', '').replace('lineup_', '')
        if not lu_id:
            continue
            
        date_el = ch.select_one('.txt-date')
        date_str = clean_text(date_el.get_text()) if date_el else ""
        info_el = ch.select_one('.choice__info .txt') or ch.select_one('label')
        name_str = clean_text(info_el.get_text()) if info_el else ""
        
        year = extract_year_from_text(name_str) or extract_year_from_text(ch.get_text()) or extract_year_from_text(date_str)
        if not year:
            continue
            
        if year not in lineups_by_year:
            lineups_by_year[year] = []
            
        lineups_by_year[year].append({
            "lineup_id": str(lu_id),
            "name": name_str,
            "date": date_str
        })
        
    return model_name, lineups_by_year

def crawl_model_catalog(
    model_id: str,
    session: Optional[requests.Session] = None,
    target_year: Optional[str] = None,
    delay_range: Tuple[float, float] = (1.5, 2.0)
) -> Tuple[str, Dict[str, dict]]:
    """
    특정 모델의 라인업들을 순회 수집하여 카탈로그 형식으로 반환.
    target_year가 지정되면 해당 연식만 수집.
    빈 껍데기는 저장하지 않음.
    """
    if session is None:
        session = get_danawa_session()
        
    model_name, lineups_by_year = get_model_lineups(model_id, session)
    years_to_crawl = [target_year] if target_year else sorted(list(lineups_by_year.keys()), reverse=True)
    
    model_catalog: Dict[str, dict] = {}
    
    for yr in years_to_crawl:
        if yr not in lineups_by_year:
            continue
            
        lus = lineups_by_year[yr]
        yr_grades = []
        yr_options = {}
        yr_packages = {}
        
        for lu in lus:
            lu_id = lu["lineup_id"]
            url = f"https://auto.danawa.com/auto/?Work=model&Model={model_id}&Lineup={lu_id}&Tab=price"
            
            time.sleep(random.uniform(*delay_range))
            
            try:
                resp = None
                for attempt in range(2):
                    try:
                        resp = session.get(url, timeout=12)
                        resp.encoding = 'utf-8'
                        if resp.status_code in [403, 429]:
                            raise requests.exceptions.HTTPError(f"HTTP {resp.status_code}")
                        break
                    except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as ce:
                        if attempt == 0:
                            time.sleep(1.0)
                            session = get_danawa_session()
                            continue
                        raise ce

                if resp is None or resp.status_code != 200:
                    logger.warning(f"Failed to fetch {url}, status: {resp.status_code if resp else 'None'}")
                    continue
                parsed = parse_danawa_lineup_html(resp.text)
                
                for g in parsed["grades"]:
                    if g not in yr_grades:
                        yr_grades.append(g)
                for opt_k, opt_v in parsed["options"].items():
                    if opt_k not in yr_options:
                        yr_options[opt_k] = opt_v
                    else:
                        if yr_options[opt_k].get("price", 0) == 0 and opt_v.get("price", 0) > 0:
                            yr_options[opt_k]["price"] = opt_v["price"]
                        if not yr_options[opt_k].get("desc") and opt_v.get("desc"):
                            yr_options[opt_k]["desc"] = opt_v["desc"]
                for pkg_k, pkg_v in parsed["packages"].items():
                    if pkg_k not in yr_packages and pkg_v:
                        yr_packages[pkg_k] = pkg_v
            except Exception as e:
                logger.error(f"Error fetching lineup {lu_id} for model {model_id}: {e}")
                raise e
                
        # [핵심] 빈 껍데기 저장 금지: grades와 options가 둘 다 비어있으면 키 생성 안 함
        if yr_grades or yr_options:
            model_catalog[yr] = {
                "grades": yr_grades,
                "options": yr_options,
                "packages": yr_packages
            }
            
    return model_name, model_catalog

def load_or_create_danawa_catalog() -> dict:
    if os.path.exists(DANAWA_CATALOG_FILE):
        try:
            with open(DANAWA_CATALOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_danawa_catalog(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_file = DANAWA_CATALOG_FILE + ".tmp"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, DANAWA_CATALOG_FILE)

def run_full_crawling(max_models: Optional[int] = None, target_mids: Optional[set] = None):
    """
    다나와 사이트의 신차 카탈로그 전수 수집 오케스트레이터.
    - 5건 완료마다 저장
    - 중단 시 이어받기(재개) 지원
    - 1.5~2초 랜덤 딜레이 -> 403/429/SSL 에러 시 10초 딜레이 자동 전환
    - 빈 껍데기 저장 방지
    """
    if not os.path.exists(DANAWA_TARGETS_FILE):
        logger.error(f"Targets file not found: {DANAWA_TARGETS_FILE}")
        return

    with open(DANAWA_TARGETS_FILE, 'r', encoding='utf-8') as f:
        targets = json.load(f)

    catalog_db = load_or_create_danawa_catalog()
    session = get_danawa_session()
    
    current_delay = (1.5, 2.0)
    delay_name = "1.5~2.0s"
    logger.info(f"Starting Danawa Full Crawl: {len(targets)} total target models. Current catalog has {len(catalog_db)} models.")
    
    processed_count = 0
    saved_batch_count = 0
    error_streak = 0
    
    for mid, tinfo in targets.items():
        if target_mids and mid not in target_mids:
            continue
        if max_models and processed_count >= max_models:
            break
            
        mname_target = tinfo.get("name", "")
        # 이미 수집된 모델인지 확인 (이어받기)
        # 카탈로그의 키 중 하나에 매핑되거나 이미 연식 데이터가 있으면 건너뜀
        already_collected = False
        for k in catalog_db.keys():
            if k == mname_target:
                # 2026 또는 데이터가 1개 이상 있는지
                if len(catalog_db[k]) > 0:
                    already_collected = True
                    break
        
        if already_collected and mid != "4586": # 카니발은 파일럿으로 이미 수집됨
            continue

        try:
            logger.info(f"[{processed_count+1}] Crawling model {mid} ({tinfo.get('brand_name')} {mname_target}) with delay {delay_name}...")
            model_key, model_cat = crawl_model_catalog(mid, session=session, delay_range=current_delay)
            
            # 빈 껍데기가 아닌 경우만 저장
            if model_cat:
                if model_key not in catalog_db:
                    catalog_db[model_key] = {}
                # 연식별 병합
                for yr, yr_data in model_cat.items():
                    catalog_db[model_key][yr] = yr_data
                logger.info(f" -> Success: '{model_key}', years: {list(model_cat.keys())}")
            else:
                logger.info(f" -> No valid price/trim data found for model {mid}, skipping key creation.")

            processed_count += 1
            saved_batch_count += 1
            error_streak = 0

            # 5건마다 디스크에 저장
            if saved_batch_count >= 5:
                save_danawa_catalog(catalog_db)
                saved_batch_count = 0
                logger.info(f"*** Auto-saved to {DANAWA_CATALOG_FILE} (Total models in catalog: {len(catalog_db)}) ***")

        except (requests.exceptions.HTTPError, requests.exceptions.SSLError, ConnectionError) as e:
            logger.warning(f"Network / Block detected on model {mid}: {e}")
            error_streak += 1
            if current_delay == (1.5, 2.0):
                logger.warning(">>> Switching to 10s crawl-delay (robots.txt recommendation) and retrying...")
                current_delay = (10.0, 11.0)
                delay_name = "10.0~11.0s (Robots.txt)"
                time.sleep(10.0)
                continue
            else:
                if error_streak >= 2:
                    logger.error(">>> Block persisted even at 10s delay. Halting crawl safely to protect IP.")
                    break
        except Exception as e:
            logger.error(f"Unexpected error crawling model {mid}: {e}")
            continue

    # 최종 저장
    save_danawa_catalog(catalog_db)
    logger.info(f"Finished run. Total models in catalog: {len(catalog_db)}")

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    run_full_crawling()
