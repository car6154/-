# scripts/crawl_encar_catalog_v2.py
"""
[11-11-12] 엔카 신차가격표 전체 재크롤링 (v2)
- 제조사별 묶음 수집 지원
- 파서 보완 버전 (기본가, 등급명, 옵션가 72%+, condition/package_ref 구분)
- 안전 규칙:
  - 요청 간격 10~25초 불규칙 딜레이
  - 403, 429 감지 시 즉시 전면 중단 (Fail-Stop)
  - 원본 HTML data/raw_vault/encar_newprice_20261111/ 에 영구 캐시 보존
  - 결과 data/encar_newcar_catalog_v2.json 에 누적 저장
"""

import os
import sys
import re
import json
import time
import random
import html
import argparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# 콘솔 UTF-8 출력 보장
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
VAULT_DIR = os.path.join(DATA_DIR, "raw_vault", "encar_newprice_20261111")
TARGETS_INDEX_FILE = os.path.join(DATA_DIR, "encar_crawl_targets_index.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "encar_newcar_catalog_v2.json")

os.makedirs(VAULT_DIR, exist_ok=True)


def log(msg: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


def clean_text(txt: str) -> str:
    if not txt:
        return ""
    t = txt.replace('\xa0', ' ').replace('&nbsp;', ' ')
    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def parse_price(prc_str: str, unit_str: str = "") -> int:
    clean_digits = re.sub(r'[^\d]', '', prc_str)
    if not clean_digits:
        return None
    val = int(clean_digits)
    unit = (unit_str or "").strip()
    if unit in ('만', '만원'):
        return val * 10000
    elif unit == '원':
        return val
    else:
        if val < 10000:
            return val * 10000
        return val


def parse_option_item(raw_item: str, packages: dict) -> dict:
    item_clean = clean_text(html.unescape(re.sub(r'<[^>]+>', '', raw_item)))
    item_clean = re.sub(r'^[▶►▶︎●•*※\-–—]\s*', '', item_clean).strip()
    if not item_clean or any(k == item_clean for k in ['선택사양 품목', '선택사양', '기본사양', '기본사양 품목']):
        return None

    # 가격 패턴 매칭
    m_price = re.search(r'[:\s]+([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)\s*(만|만원|원)?\s*$', item_clean)
    if m_price:
        prc_digits = m_price.group(1)
        prc_unit = m_price.group(2)
        price_val = parse_price(prc_digits, prc_unit)
        opt_name = item_clean[:m_price.start()].strip()
        opt_name = re.sub(r'[:\-–—]\s*$', '', opt_name).strip()

        if len(opt_name) > 1 and price_val is not None:
            opt_data = {
                'name': opt_name,
                'price': price_val,
                'kind': 'optional'
            }
            for p_key, p_val in packages.items():
                clean_p = re.sub(r'[\s\-_]', '', p_key).lower()
                clean_o = re.sub(r'[\s\-_]', '', opt_name).lower()
                if clean_p == clean_o or clean_p in clean_o or clean_o in clean_p:
                    opt_data['desc'] = p_val
                    break
            return opt_data

    # 조건문 / 안내문 / 패키지참조 구분
    CONDITION_KEYWORDS = ['적용시', '적용 시', '선택 가능', '선택가능', '불가', '미적용', '전용', '동시 적용']
    if any(k in item_clean for k in CONDITION_KEYWORDS):
        return {
            'name': item_clean,
            'price': None,
            'kind': 'condition'
        }
    else:
        opt_data = {
            'name': item_clean,
            'price': None,
            'kind': 'package_ref'
        }
        for p_key, p_val in packages.items():
            clean_p = re.sub(r'[\s\-_]', '', p_key).lower()
            clean_o = re.sub(r'[\s\-_]', '', item_clean).lower()
            if clean_p == clean_o or clean_p in clean_o or clean_o in clean_p:
                opt_data['desc'] = p_val
                break
        return opt_data


def parse_encar_newprice_html(html_text: str) -> dict:
    if not html_text:
        return {"grades": [], "packages": {}}

    soup = BeautifulSoup(html_text, 'html.parser')

    # 1. 패키지 상세 설명 추출
    packages = {}
    EXCLUDE_PKG_NAMES = [
        '사양', '파워트레인', '외장컬러', '기본사양', '공통', '참고', '품목', '선택', '주의',
        '안전', '외관', '내장', '시트', '편의', '멀티미디어', '엔진', '변속기', '보증'
    ]
    for s in soup(['script', 'style', 'head', 'noscript']):
        s.decompose()

    cleaned_html = str(soup).replace('<br>', '\n').replace('<BR>', '\n').replace('<br/>', '\n')
    for line in cleaned_html.splitlines():
        clean = clean_text(html.unescape(re.sub(r'<[^>]+>', '', line)))
        if not clean or any(k in clean for k in ['차량DB', '신차가격표', '가격 및 사양', 'javascript', 'gtm']):
            continue

        m1 = re.match(r'^[■●•*※\-\—]?\s*([가-힣A-Za-z0-9\sⅠⅡⅢⅣIViv\+\(\)]{2,25}?)\s*[-—:]\s*(.+)$', clean)
        if m1:
            p_name = clean_text(m1.group(1))
            p_desc = clean_text(m1.group(2))
            if len(p_name) > 1 and len(p_desc) > 5 and not any(k in p_name for k in EXCLUDE_PKG_NAMES):
                packages[p_name] = p_desc
                continue

        m2 = re.match(r'^([가-힣A-Za-z0-9\sⅠⅡⅢⅣIViv\+\(\)]{2,25})\s*[-—:]\s*([가-힣A-Za-z0-9].{5,})$', clean)
        if m2:
            p_name = clean_text(m2.group(1))
            p_desc = clean_text(m2.group(2))
            if len(p_name) > 1 and len(p_desc) > 5 and not any(k in p_name for k in EXCLUDE_PKG_NAMES):
                if p_name not in packages or len(p_desc) > len(packages[p_name]):
                    packages[p_name] = p_desc

    # 2. 등급 및 가격, 등급별 옵션 파싱
    grades = []
    tables = soup.find_all('table')
    if not tables:
        return {"grades": [], "packages": packages}

    main_table = tables[-1]
    rows = main_table.find_all('tr')
    for tr in rows:
        grade_td = tr.find('td', class_='grade')
        price_td = tr.find('td', class_='price')
        mission_td = tr.find('td', class_='mission')
        option_td = tr.find('td', class_='option')

        if not grade_td or not price_td:
            continue

        g_name = clean_text(grade_td.get_text(' ', strip=True))
        g_mission = clean_text(mission_td.get_text(' ', strip=True)) if mission_td else ''

        # 기본가격 파싱
        prc_txt = clean_text(price_td.get_text(' ', strip=True))
        m_prc = re.search(r'([0-9,]+)\s*만원', prc_txt)
        base_price = None
        if m_prc:
            base_price = int(m_prc.group(1).replace(',', '')) * 10000
        elif re.search(r'([0-9,]+)', prc_txt):
            num = int(re.sub(r'[^\d]', '', prc_txt))
            if num < 100000:
                base_price = num * 10000
            else:
                base_price = num

        # 등급별 옵션 파싱
        options = {}
        if option_td:
            contents = option_td.decode_contents()
            raw_items = re.split(r'<br\s*/?>', contents, flags=re.I)
            for raw in raw_items:
                opt_info = parse_option_item(raw, packages)
                if opt_info:
                    oname = opt_info['name']
                    options[oname] = {
                        'price': opt_info['price'],
                        'kind': opt_info['kind']
                    }
                    if 'desc' in opt_info:
                        options[oname]['desc'] = opt_info['desc']

        grades.append({
            'name': g_name,
            'mission': g_mission,
            'base_price': base_price,
            'options': options
        })

    return {'grades': grades, 'packages': packages}


class EncarCatalogCrawlerV2:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": "https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2"
        })
        self.access_token = ""
        self.token_expiry = 0
        self.catalog = self._load_catalog()

    def _load_catalog(self) -> dict:
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log(f"기존 v2 카탈로그 로드 오류: {e}")
        return {}

    def _save_catalog(self):
        try:
            temp_file = OUTPUT_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, OUTPUT_FILE)
        except Exception as e:
            log(f"카탈로그 저장 실패: {e}")

    def get_token(self) -> str:
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token
        try:
            init_url = "https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2"
            r = self.session.get(init_url, timeout=7)
            match = re.search(r'name=["\']?pageAccessToken["\']?\s+value=["\']([^"\']+)["\']', r.text)
            if not match:
                match = re.search(r'id=["\']?pageAccessToken["\']?[^>]*?value=["\']([^"\']+)["\']', r.text)
            if match:
                self.access_token = match.group(1)
                self.token_expiry = time.time() + 600
                return self.access_token
        except Exception as e:
            log(f"토큰 갱신 오류: {e}")
        return ""

    def crawl_target(self, target: dict) -> tuple:
        """
        단일 타깃 수집 및 파싱
        반환값: (html_text, is_cached, parsed_result)
        """
        safe_model = re.sub(r'[\\/*?:"<>|]', '_', target['model_name']).strip()
        cache_filename = f"{safe_model}_{target['year']}.html"
        cache_filepath = os.path.join(VAULT_DIR, cache_filename)

        # 1. 캐시 확인
        if os.path.exists(cache_filepath) and os.path.getsize(cache_filepath) > 500:
            with open(cache_filepath, "r", encoding="utf-8") as f:
                html_text = f.read()
            parsed = parse_encar_newprice_html(html_text)
            return (html_text, True, parsed)

        # 2. 외부 요청 (안전 딜레이 필수)
        token = self.get_token()
        url = (
            f"https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2"
            f"&mnfccd={target['mfg_code']}&mdlgroupcd={target['group_id']}"
            f"&mdlcd={target['model_id']}&caryear={target['year']}"
        )
        if token:
            url += f"&pageAccessToken={requests.utils.quote(token)}"

        # 제이 지침: 5~10초 가속 딜레이 (이상 징후 감지 시 자동 15~25초 복구)
        delay = random.uniform(5.0, 10.0) if not getattr(self, 'slow_mode', False) else random.uniform(15.0, 25.0)
        time.sleep(delay)

        try:
            r = self.session.get(url, timeout=10)
            if r.status_code in (403, 429):
                log(f"🚨 [FAIL-STOP] HTTP {r.status_code} 감지! IP 차단 방지를 위해 즉시 전면 중단합니다.")
                sys.exit(1)
            elif r.status_code != 200:
                log(f"⚠️ [이상감지] HTTP {r.status_code} 발생! 즉시 원래 안전 시간(15~25초)으로 복구합니다.")
                self.slow_mode = True

            if "area_nodata" in r.text:
                time.sleep(2)
                self.access_token = ""
                token = self.get_token()
                retry_url = (
                    f"https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2"
                    f"&mnfccd={target['mfg_code']}&mdlgroupcd={target['group_id']}"
                    f"&mdlcd={target['model_id']}&caryear={target['year']}"
                    f"&pageAccessToken={requests.utils.quote(token)}"
                )
                r = self.session.get(retry_url, timeout=10)

            if r.status_code == 200:
                with open(cache_filepath, "w", encoding="utf-8") as f:
                    f.write(r.text)
                parsed = parse_encar_newprice_html(r.text)
                return (r.text, False, parsed)
            else:
                log(f"  [요청오류] {target['model_name']} ({target['year']}) -> HTTP {r.status_code}")
        except Exception as e:
            log(f"  [예외발생] {target['model_name']} ({target['year']}) -> {e}")

        return ("", False, {"grades": [], "packages": {}})

    def run_batch(self, mfg_filter: str):
        with open(TARGETS_INDEX_FILE, "r", encoding="utf-8") as f:
            all_targets = json.load(f)

        if mfg_filter != "all":
            targets = [t for t in all_targets if t['mfg_name'] == mfg_filter]
        else:
            targets = all_targets

        log("==================================================")
        log(f"🚀 [11-11-12] 엔카 신차가격표 묶음 수집 시작: [{mfg_filter}] (총 {len(targets)}개 타깃)")
        log("==================================================")

        cached_count = 0
        crawled_count = 0
        total_grades = 0
        total_base_price = 0
        total_options = 0
        total_has_price_options = 0
        total_packages = 0
        missing_base_grades = []

        for idx, t in enumerate(targets, 1):
            m_name = t['model_name']
            yr = t['year']

            html_text, is_cached, parsed = self.crawl_target(t)
            if is_cached:
                cached_count += 1
            else:
                crawled_count += 1

            # 카탈로그 메모리 갱신
            if m_name not in self.catalog:
                self.catalog[m_name] = {}
            self.catalog[m_name][yr] = parsed

            # 통계 집계
            grades = parsed.get('grades', [])
            g_cnt = len(grades)
            total_grades += g_cnt
            for g in grades:
                if g.get('base_price') is not None:
                    total_base_price += 1
                else:
                    missing_base_grades.append(f"{m_name} {yr}년형 - {g['name']}")
                
                for oname, oinfo in g.get('options', {}).items():
                    total_options += 1
                    if oinfo.get('price') is not None:
                        total_has_price_options += 1

            p_cnt = len(parsed.get('packages', {}))
            total_packages += p_cnt

            status_tag = "캐시" if is_cached else "신규"
            if idx % 10 == 0 or idx == len(targets) or not is_cached:
                log(f"[{idx:03d}/{len(targets)}] ({status_tag}) {m_name} ({yr}년형) -> 등급 {g_cnt}개, 옵션 {sum(len(g.get('options', {})) for g in grades)}개 | 누적 등급 {total_grades}개")

            # 10건마다 중간 파일 저장
            if idx % 10 == 0:
                self._save_catalog()

        # 최종 저장
        self._save_catalog()

        log("\n==================================================")
        log(f"📋 [{mfg_filter}] 묶음 수집 완료 보고서")
        log("==================================================")
        log(f"- 대상 타깃 총합: {len(targets)}개 (캐시 적중: {cached_count}개 / 신규 수집: {crawled_count}개)")
        log(f"- 수집 등급 총합: {total_grades}개")
        log(f"  * 기본가격 등록: {total_base_price}개 ({total_base_price/total_grades*100:.1f}%)" if total_grades else "  * 기본가격 등록: 0개")
        log(f"  * 기본가격 결측: {total_grades - total_base_price}개")
        log(f"- 등급별 옵션 총합: {total_options}개")
        log(f"  * 유료 옵션(가격보유): {total_has_price_options}개 ({total_has_price_options/total_options*100:.1f}%)" if total_options else "  * 유료 옵션: 0개")
        log(f"  * 조건/패키지참조: {total_options - total_has_price_options}개")
        log(f"- 패키지 세부설명 총합: {total_packages}개")
        if missing_base_grades:
            log(f"\n⚠️ 기본가격 결측 등급 목록 ({len(missing_base_grades)}건):")
            for mg in missing_base_grades[:20]:
                log(f"  - {mg}")
            if len(missing_base_grades) > 20:
                log(f"  ... 외 {len(missing_base_grades) - 20}건")
        else:
            log("🎉 기본가격 결측 등급 0건 (전 등급 기본가 100% 등록 완료!)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mfg", default="현대", help="제조사명 (현대, 기아, 제네시스, 르노코리아, KGM, 쉐보레, all)")
    args = parser.parse_args()

    crawler = EncarCatalogCrawlerV2()
    crawler.run_batch(args.mfg)


if __name__ == "__main__":
    main()

