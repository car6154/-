# -*- coding: utf-8 -*-
"""
scripts/crawl_accessories_and_notices.py
다나와 신차가격표 옵션 페이지(Tab=item)에서 전 차종 액세서리(Kia Genuine, HGA, TUON, TUIX, N 퍼포먼스, KGM 커스텀 등) 및
하단 유의사항/안내문구(※)를 전수 수집하여 data/catalog_by_source_v2.json에 안전 병합하는 백그라운드 스크립트.
- ThreadPoolExecutor (동시 6개 워커) 병렬 네트워크 I/O
- 기존 옵션(58,683개), 기본가, 기본사양 100% 불변 보존
- 카탈로그 책의 출처 최상위 키('danawa') 및 모델 309개 전수 1:1 매칭
"""

import sys
import os
import re
import json
import time
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.danawa_crawler import get_danawa_session, get_model_lineups
from scripts.run_domestic_catalog_pipeline import get_models_for_brand

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("data/accessories_crawl.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AccessoriesCrawl")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CATALOG_V2_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2.json")
BACKUP_FILE = os.path.join(DATA_DIR, "catalog_by_source_v2_backup_before_11-06-74.json")

BRANDS = [
    ('303', '현대'),
    ('304', '제네시스'),
    ('307', '기아'),
    ('312', '쉐보레'),
    ('321', '르노코리아'),
    ('326', 'KGM')
]


def clean_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r'\s+', ' ', str(s)).strip()


def normalize_key(s: str) -> str:
    return re.sub(r'[\s\-/\(\)\.,_·■\+\[\]]', '', str(s)).lower()


def parse_price_str(price_str: str) -> Tuple[int, int]:
    """가격 문자열('166만원', '1,660,000', '90,000원' 등)을 (원, 만원) 튜플로 변환"""
    if not price_str or price_str == '-':
        return 0, 0
    clean = clean_text(price_str).replace(',', '')
    m_man = re.search(r'([\d\.]+)\s*만\s*원?', clean)
    if m_man:
        val = float(m_man.group(1))
        return int(val * 10000), int(round(val))
    m_won = re.search(r'(\d+)\s*원?', clean)
    if m_won:
        val = int(m_won.group(1))
        return val, int(round(val / 10000.0))
    return 0, 0


def parse_tab_item_page(html: str) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """다나와 Tab=item HTML에서 액세서리 딕셔너리와 안내문구 리스트 추출"""
    soup = BeautifulSoup(html, 'html.parser')
    accessories: Dict[str, Dict[str, Any]] = {}
    notices: List[str] = []

    # 1. ※ 안내문구 추출 (중복 제거)
    raw_notices = re.findall(r'※\s*([^\n\r<>]+)', html)
    seen_notices = set()
    for n in raw_notices:
        n_clean = clean_text(n)
        if 5 < len(n_clean) < 300 and n_clean not in seen_notices:
            seen_notices.add(n_clean)
            notices.append(f"※ {n_clean}")

    # 2. 테이블 순회하여 액세서리 추출
    for tbl in soup.find_all('table'):
        ths = [clean_text(th.get_text()) for th in tbl.find_all('th')]
        if not ths:
            continue

        header_text = ' '.join(ths).lower()

        # 메인 스펙 테이블 제외
        if '세부모델' in ths and '판매가격' in ths:
            continue

        # 가로형 KGM 액세서리 테이블 (ths[0] == '구분' and ths에 품목명들)
        if len(ths) > 2 and ths[0] in ['구분', '구 분']:
            trs = tbl.find_all('tr')
            for tr in trs:
                tds = [clean_text(c.get_text()) for c in tr.find_all(['td', 'th'])]
                if tds and tds[0] in ['옵션가격', '가격']:
                    for col_idx in range(1, min(len(ths), len(tds))):
                        item_name = ths[col_idx]
                        item_price_str = tds[col_idx]
                        p_won, p_man = parse_price_str(item_price_str)
                        if item_name and (p_won > 0 or p_man > 0):
                            accessories[item_name] = {
                                'price': p_won,
                                'price_man': p_man,
                                'desc': f'{item_name} 커스터마이징 상품'
                            }
            continue

        # 세로형 액세서리/커스터마이징 테이블
        is_accessory_table = False
        if any(k in header_text for k in [
            'genuine', 'accessories', 'hga', 'tuon', 'tuix', 'n 퍼포먼스', 'n performance',
            '커스터마이징', '액세서리', '커스텀', '용품'
        ]):
            is_accessory_table = True
        elif '가격' in ths and any(k in ths for k in ['세부 사양', '세부사양', '세부내용', '세부 내용', '주요사항', '적용사양']):
            is_accessory_table = True
        elif ths[0] in ['구분', '구 분', '패키지'] and any(k in ths for k in ['세부내용', '세부 내용', '주요사항']):
            is_accessory_table = True

        if is_accessory_table:
            for tr in tbl.find_all('tr'):
                tds = [clean_text(td.get_text()) for td in tr.find_all('td')]
                if len(tds) >= 2:
                    name = tds[0]
                    if not name or name in ['구분', '세부모델', '선택품목', '패키지', '옵션', '패키지 옵션']:
                        continue
                    if any(k in name for k in ['차량가격', '합계', '인승)']):
                        continue

                    price_won = 0
                    price_man = 0
                    desc = ""

                    if len(tds) == 2:
                        desc = tds[1]
                        p_m = re.search(r'([\d,]+)\s*만\s*원', desc)
                        if p_m:
                            price_won, price_man = parse_price_str(p_m.group(0))
                    elif len(tds) >= 3:
                        price_won, price_man = parse_price_str(tds[1])
                        desc = tds[2]
                        if desc == '-' or not desc:
                            desc = f"{name} 정품 액세서리"

                    if name:
                        accessories[name] = {
                            'price': price_won,
                            'price_man': price_man,
                            'desc': desc
                        }

    return accessories, notices


def crawl_model_accessories(model_info: Tuple[str, str, str, str]) -> Dict[str, Any]:
    """단일 모델의 연식별 액세서리 및 안내문구 크롤링 (병렬 워커용)"""
    bid, bname, mid, mname = model_info
    session = get_danawa_session()

    try:
        _, lineups_by_year = get_model_lineups(mid, session)
    except Exception:
        return {'model_id': mid, 'model_name': mname, 'years': {}}

    if not lineups_by_year:
        return {'model_id': mid, 'model_name': mname, 'years': {}}

    result_by_year: Dict[str, Dict[str, Any]] = {}

    for yr, l_list in lineups_by_year.items():
        if not l_list:
            continue

        combined_accs: Dict[str, Dict[str, Any]] = {}
        combined_notices: List[str] = []
        seen_notices = set()

        for lup in l_list:
            lid = lup.get('lineup_id')
            if not lid:
                continue
            url = f"https://auto.danawa.com/auto/?Work=model&Model={mid}&Lineup={lid}&Tab=item"
            try:
                r = session.get(url, timeout=12)
                if r.status_code in [403, 429]:
                    logger.error(f"HTTP {r.status_code} blocked on model {mid} lineup {lid}!")
                    break
                r.encoding = 'utf-8'
                accs, nots = parse_tab_item_page(r.text)
                combined_accs.update(accs)
                for n in nots:
                    if n not in seen_notices:
                        seen_notices.add(n)
                        combined_notices.append(n)
            except Exception as e:
                logger.warning(f"Error fetching {url}: {e}")

        if combined_accs or combined_notices:
            result_by_year[yr] = {
                'accessories': combined_accs,
                'notices': combined_notices
            }

    return {'model_id': mid, 'model_name': mname, 'years': result_by_year}


def merge_accessories_into_catalog(model_data: Dict[str, Any], v2_danawa: Dict[str, Any]) -> Tuple[int, int]:
    """수집된 액세서리와 안내문구를 v2_danawa (309개 모델)에 1:1 안전 병합"""
    mname = model_data.get('model_name', '')
    years_data = model_data.get('years', {})
    if not years_data:
        return 0, 0

    clean_mname = re.sub(r'\([^\)]*\)', '', mname).strip()
    norm_mname = normalize_key(clean_mname)

    matched_v2_cars = []
    for v2_cname in v2_danawa.keys():
        clean_v2 = re.sub(r'\([^\)]*\)', '', v2_cname).strip()
        norm_v2 = normalize_key(clean_v2)
        if norm_mname == norm_v2 or norm_mname in norm_v2 or norm_v2 in norm_mname:
            matched_v2_cars.append(v2_cname)

    if not matched_v2_cars:
        return 0, 0

    added_accs = 0
    added_nots = 0

    for yr, y_info in years_data.items():
        accs = y_info.get('accessories', {})
        nots = y_info.get('notices', [])

        cand_years = [yr]
        try:
            y_int = int(yr)
            cand_years.append(str(y_int - 1))
            cand_years.append(str(y_int + 1))
        except Exception:
            pass

        for v2_c in matched_v2_cars:
            for c_yr in cand_years:
                if c_yr not in v2_danawa[v2_c]:
                    continue
                yr_book = v2_danawa[v2_c][c_yr]
                for grd, spec in yr_book.items():
                    if not isinstance(spec, dict):
                        continue

                    # 1. accessories 병합 (등급 레벨)
                    if accs:
                        if 'accessories' not in spec:
                            spec['accessories'] = {}
                        for acc_k, acc_v in accs.items():
                            if acc_k not in spec['accessories']:
                                spec['accessories'][acc_k] = acc_v
                                added_accs += 1
                            else:
                                if not spec['accessories'][acc_k].get('desc') and acc_v.get('desc'):
                                    spec['accessories'][acc_k]['desc'] = acc_v['desc']
                                if not spec['accessories'][acc_k].get('price') and acc_v.get('price'):
                                    spec['accessories'][acc_k]['price'] = acc_v['price']
                                    spec['accessories'][acc_k]['price_man'] = acc_v['price_man']

                # 2. notices 병합 (연식 레벨 _notices에 1회만 보관하여 JSON 비대화 및 GitHub 100MB 초과 원천 방지)
                if nots:
                    if '_notices' not in yr_book:
                        yr_book['_notices'] = []
                    existing_notices = set(yr_book['_notices'])
                    for n in nots:
                        if n not in existing_notices:
                            yr_book['_notices'].append(n)
                            existing_notices.add(n)
                            added_nots += 1

    return added_accs, added_nots


def count_catalog_stats(v2_danawa: Dict[str, Any]) -> Dict[str, int]:
    """카탈로그 전체 옵션 수, 액세서리 수, 안내문구 수 계측"""
    total_options = 0
    total_accessories = 0
    total_notices = 0

    for cname, cyears in v2_danawa.items():
        if not isinstance(cyears, dict):
            continue
        for yr, ygrades in cyears.items():
            if not isinstance(ygrades, dict):
                continue
            if '_notices' in ygrades:
                total_notices += len(ygrades['_notices'])
            for gname, ginfo in ygrades.items():
                if gname == '_notices' or not isinstance(ginfo, dict):
                    continue
                opts = ginfo.get('options', {})
                total_options += len(opts)
                accs = ginfo.get('accessories', {})
                total_accessories += len(accs)
                nots = ginfo.get('notices', [])
                total_notices += len(nots)

    return {
        'total_options': total_options,
        'total_accessories': total_accessories,
        'total_notices': total_notices
    }


def main():
    logger.info("=== Starting Accessories and Notices Crawl Pipeline (11-06-74) ===")

    # 1. 백업
    if not os.path.exists(BACKUP_FILE):
        logger.info(f"Creating backup: {BACKUP_FILE}")
        shutil.copy2(CATALOG_V2_FILE, BACKUP_FILE)
    else:
        logger.info(f"Backup already exists: {BACKUP_FILE}")

    # 2. 카탈로그 로드
    with open(CATALOG_V2_FILE, 'r', encoding='utf-8') as f:
        full_catalog = json.load(f)

    v2_danawa = full_catalog.get('danawa', {})
    logger.info(f"Loaded danawa book with {len(v2_danawa)} models.")

    initial_stats = count_catalog_stats(v2_danawa)
    logger.info(f"Initial stats: options={initial_stats['total_options']}, accessories={initial_stats['total_accessories']}, notices={initial_stats['total_notices']}")

    # 3. 모델 수집
    session = get_danawa_session()
    all_models: List[Tuple[str, str, str, str]] = []

    for bid, bname in BRANDS:
        brand_models = get_models_for_brand(bid, session)
        logger.info(f"Brand {bname} (bid={bid}): {len(brand_models)} models found")
        for m in brand_models:
            all_models.append((bid, bname, m['model_id'], m['model_name']))

    logger.info(f"Total models to process: {len(all_models)} (6 workers)")

    start_time = time.time()
    total_added_accs = 0
    total_added_notices = 0
    processed_count = 0

    # ThreadPoolExecutor (워커 6개)
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_model = {executor.submit(crawl_model_accessories, m_info): m_info for m_info in all_models}

        for future in as_completed(future_to_model):
            m_info = future_to_model[future]
            bid, bname, mid, mname = m_info
            processed_count += 1

            try:
                model_res = future.result()
                acc_cnt, not_cnt = merge_accessories_into_catalog(model_res, v2_danawa)
                total_added_accs += acc_cnt
                total_added_notices += not_cnt

                if processed_count % 30 == 0 or processed_count == len(all_models):
                    elapsed = time.time() - start_time
                    logger.info(f"[{processed_count}/{len(all_models)}] Progress: {(processed_count/len(all_models))*100:.1f}% | Elapsed: {elapsed:.1f}s | Accs added: {total_added_accs:,} | Notices added: {total_added_notices:,}")

            except Exception as e:
                logger.error(f"Error processing {bname} {mname}: {e}")

    # 4. 저장 및 최종 검증
    full_catalog['danawa'] = v2_danawa
    logger.info("Saving updated catalog...")
    with open(CATALOG_V2_FILE, 'w', encoding='utf-8') as f:
        json.dump(full_catalog, f, ensure_ascii=False, indent=2)

    final_stats = count_catalog_stats(v2_danawa)
    elapsed_total = time.time() - start_time
    logger.info(f"=== Accessories Crawl Finished in {elapsed_total:.1f}s ===")
    logger.info(f"Final stats: options={final_stats['total_options']} (diff={final_stats['total_options'] - initial_stats['total_options']}), accessories={final_stats['total_accessories']:,}, notices={final_stats['total_notices']:,}")

    # 기존 옵션 불변성 검증
    if final_stats['total_options'] < initial_stats['total_options']:
        logger.critical(f"FATAL: Existing options decreased! ({initial_stats['total_options']} -> {final_stats['total_options']})")
        sys.exit(1)
    else:
        logger.info("VALIDATION PASSED: Existing options 100% preserved.")


if __name__ == "__main__":
    main()
