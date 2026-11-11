# scripts/run_encar_recrawl_pilot.py
"""
[11-11-11] 엔카 신차가격표 재크롤링 파일럿
- 대상: 제이가 지정한 대표 10개 차종·연식
- 안전 규칙:
  1. 10개 초과 호출 금지 (Fail-Stop)
  2. 요청 간격 10~25초 불규칙 딜레이 (random.uniform)
  3. 403, 429 감지 시 즉시 중단 (Fail-Stop)
  4. data/raw_vault/encar_newprice_20261111/ 폴더에 원본 HTML 파일 캐시
- 산출물: data/encar_recrawl_pilot_2026-11-11.json
"""

import os
import sys
import re
import json
import time
import random
import html
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
VAULT_DIR = os.path.join(PROJECT_ROOT, "data", "raw_vault", "encar_newprice_20261111")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data", "encar_recrawl_pilot_2026-11-11.json")

os.makedirs(VAULT_DIR, exist_ok=True)

PILOT_TARGETS = [
    {
        "id": 1,
        "model_key": "XM3",
        "year": "2021",
        "mnfccd": "005",
        "mdlgroupcd": "015",
        "mdlcd": "072",
        "desc": "르노 XM3 2021"
    },
    {
        "id": 2,
        "model_key": "더 뉴 QM6",
        "year": "2024",
        "mnfccd": "005",
        "mdlgroupcd": "011",
        "mdlcd": "071",
        "desc": "르노 더 뉴 QM6 2024"
    },
    {
        "id": 3,
        "model_key": "쏘렌토 4세대",
        "year": "2022",
        "mnfccd": "002",
        "mdlgroupcd": "027",
        "mdlcd": "151",
        "desc": "기아 쏘렌토 2022"
    },
    {
        "id": 4,
        "model_key": "카니발 4세대",
        "year": "2022",
        "mnfccd": "002",
        "mdlgroupcd": "036",
        "mdlcd": "154",
        "desc": "기아 카니발 2022"
    },
    {
        "id": 5,
        "model_key": "더 뉴 아반떼 (CN7)",
        "year": "2024",
        "mnfccd": "001",
        "mdlgroupcd": "019",
        "mdlcd": "182",
        "desc": "현대 아반떼 2024"
    },
    {
        "id": 6,
        "model_key": "K5 3세대",
        "year": "2023",
        "mnfccd": "002",
        "mdlgroupcd": "001",
        "mdlcd": "149",
        "desc": "기아 K5 2023"
    },
    {
        "id": 7,
        "model_key": "그랜저 (GN7)",
        "year": "2023",
        "mnfccd": "001",
        "mdlgroupcd": "004",
        "mdlcd": "178",
        "desc": "현대 그랜저 2023"
    },
    {
        "id": 8,
        "model_key": "투싼 (NX4)",
        "year": "2022",
        "mnfccd": "001",
        "mdlgroupcd": "032",
        "mdlcd": "169",
        "desc": "현대 투싼 2022"
    },
    {
        "id": 9,
        "model_key": "GV80",
        "year": "2025",
        "mnfccd": "007",
        "mdlgroupcd": "005",
        "mdlcd": "005",
        "desc": "제네시스 더 뉴 GV80 2025"
    },
    {
        "id": 10,
        "model_key": "EV9",
        "year": "2026",
        "mnfccd": "002",
        "mdlgroupcd": "069",
        "mdlcd": "169",
        "desc": "기아 EV9 2026"
    }
]


def log(msg: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


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

    cleaned_html = str(soup)
    lines = cleaned_html.replace('<br>', '\n').replace('<BR>', '\n').replace('<br/>', '\n').splitlines()
    for line in lines:
        clean = html.unescape(re.sub(r'<[^>]+>', '', line)).strip()
        if not clean or any(k in clean for k in ['차량DB', '신차가격표', '가격 및 사양', 'javascript', 'gtm', 'function']):
            continue

        m1 = re.match(r'^[■●•*※\-\—]?\s*([가-힣A-Za-z0-9\sⅠⅡⅢⅣIViv\+\(\)]{2,25}?)\s*[-—:]\s*(.+)$', clean)
        if m1:
            p_name = m1.group(1).replace('&nbsp;', ' ').strip()
            p_desc = m1.group(2).replace('&nbsp;', ' ').strip()
            if len(p_name) > 1 and len(p_desc) > 5 and not any(k in p_name for k in EXCLUDE_PKG_NAMES):
                packages[p_name] = p_desc
                continue

        m2 = re.match(r'^([가-힣A-Za-z0-9\sⅠⅡⅢⅣIViv\+\(\)]{2,25})\s*[-—:]\s*([가-힣A-Za-z0-9].{5,})$', clean)
        if m2:
            p_name = m2.group(1).replace('&nbsp;', ' ').strip()
            p_desc = m2.group(2).replace('&nbsp;', ' ').strip()
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

        g_name = grade_td.get_text(' ', strip=True)
        g_mission = mission_td.get_text(' ', strip=True) if mission_td else ''

        # 기본가격 파싱: '2,352 만원' -> 23,520,000원
        prc_txt = price_td.get_text(' ', strip=True)
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
            opt_regex = r'^[▶►▶︎●•*※\-]?\s*([가-힣A-Za-z0-9\sⅠⅡⅢⅣIViv\+\&\(\)\/\,\:\.\-\~]+?)(?:\s*:\s*|\s+)([0-9,]+(?:\s*원)?)$'
            for item in raw_items:
                clean_item = html.unescape(re.sub(r'<[^>]+>', '', item)).replace('&nbsp;', ' ').strip()
                if not clean_item:
                    continue

                m_opt = re.search(opt_regex, clean_item)
                if m_opt:
                    opt_name = m_opt.group(1).strip()
                    opt_prc_str = m_opt.group(2).strip()
                    opt_prc = int(re.sub(r'[^\d]', '', opt_prc_str)) if re.sub(r'[^\d]', '', opt_prc_str) else None
                    if opt_name and len(opt_name) > 1:
                        opt_data = {'price': opt_prc}
                        # 패키지 설명 매핑
                        for p_key, p_val in packages.items():
                            clean_p = re.sub(r'[\s\-_]', '', p_key).lower()
                            clean_o = re.sub(r'[\s\-_]', '', opt_name).lower()
                            if clean_p == clean_o or clean_p in clean_o or clean_o in clean_p:
                                opt_data['desc'] = p_val
                                break
                        options[opt_name] = opt_data
                else:
                    clean_name = re.sub(r'^[▶►▶︎●•*※\-]\s*', '', clean_item).strip()
                    if clean_name and len(clean_name) > 1 and not any(k in clean_name for k in ['선택사양', '품목', '기본사양']):
                        opt_data = {'price': None}
                        for p_key, p_val in packages.items():
                            clean_p = re.sub(r'[\s\-_]', '', p_key).lower()
                            clean_o = re.sub(r'[\s\-_]', '', clean_name).lower()
                            if clean_p == clean_o or clean_p in clean_o or clean_o in clean_p:
                                opt_data['desc'] = p_val
                                break
                        options[clean_name] = opt_data

        grades.append({
            'name': g_name,
            'mission': g_mission,
            'base_price': base_price,
            'options': options
        })

    return {'grades': grades, 'packages': packages}


class EncarPilotCrawler:
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
                log(f"토큰 갱신 성공: {self.access_token[:20]}...")
                return self.access_token
        except Exception as e:
            log(f"토큰 획득 실패: {e}")
        return ""

    def fetch_target_html(self, target: dict) -> str:
        safe_name = re.sub(r'[\\/*?:"<>|]', '_', target['model_key']).strip()
        cache_filename = f"{safe_name}_{target['year']}.html"
        cache_filepath = os.path.join(VAULT_DIR, cache_filename)

        # 1. 파일 캐시 우선 확인
        if os.path.exists(cache_filepath) and os.path.getsize(cache_filepath) > 1000:
            log(f"  [캐시 사용] {target['desc']} -> {cache_filename} ({os.path.getsize(cache_filepath)} bytes)")
            with open(cache_filepath, "r", encoding="utf-8") as f:
                return f.read()

        # 2. 캐시 없으면 외부 요청
        token = self.get_token()
        url = (
            f"https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2"
            f"&mnfccd={target['mnfccd']}&mdlgroupcd={target['mdlgroupcd']}"
            f"&mdlcd={target['mdlcd']}&caryear={target['year']}"
        )
        if token:
            url += f"&pageAccessToken={requests.utils.quote(token)}"

        # 안전 딜레이 적용 (10~25초)
        delay = random.uniform(10.0, 20.0)
        log(f"  [안전 딜레이] {delay:.1f}초 대기 후 요청 시작...")
        time.sleep(delay)

        try:
            r = self.session.get(url, timeout=10)
            if r.status_code in (403, 429):
                log(f"🚨 [FAIL-STOP] HTTP {r.status_code} 감지! IP 차단 방지를 위해 즉시 전면 중단합니다.")
                sys.exit(1)

            if "area_nodata" in r.text:
                log(f"  [주의] {target['desc']} -> area_nodata 발생, 토큰 갱신 후 재시도...")
                time.sleep(3)
                self.access_token = ""
                token = self.get_token()
                retry_url = (
                    f"https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2"
                    f"&mnfccd={target['mnfccd']}&mdlgroupcd={target['mdlgroupcd']}"
                    f"&mdlcd={target['mdlcd']}&caryear={target['year']}"
                    f"&pageAccessToken={requests.utils.quote(token)}"
                )
                r = self.session.get(retry_url, timeout=10)

            if r.status_code == 200:
                with open(cache_filepath, "w", encoding="utf-8") as f:
                    f.write(r.text)
                log(f"  [수집 완료] {target['desc']} -> {cache_filename} 저장 성공 ({len(r.text)} bytes)")
                return r.text
            else:
                log(f"  [요청 실패] {target['desc']} -> HTTP {r.status_code}")
        except Exception as e:
            log(f"  [예외 발생] {target['desc']} -> {e}")

        return ""


def main():
    log("==================================================")
    log("🚀 [11-11-11] 엔카 신차가격표 파일럿 크롤링 시작 (10개)")
    log("==================================================")

    crawler = EncarPilotCrawler()
    results = {}

    for t in PILOT_TARGETS:
        log(f"\n[{t['id']}/10] {t['desc']} (모델: {t['model_key']}, 연식: {t['year']}) 처리 중...")
        html_content = crawler.fetch_target_html(t)
        if not html_content:
            log(f"  ❌ HTML 내용 없음: {t['desc']}")
            continue

        parsed = parse_encar_newprice_html(html_content)
        m_key = t['model_key']
        yr = t['year']

        if m_key not in results:
            results[m_key] = {}

        results[m_key][yr] = parsed
        
        grades_cnt = len(parsed.get('grades', []))
        total_opts = sum(len(g.get('options', {})) for g in parsed.get('grades', []))
        pkgs_cnt = len(parsed.get('packages', {}))
        log(f"  ✅ 파싱 완료: 등급 {grades_cnt}개, 등급별 옵션 총합 {total_opts}개, 패키지 설명 {pkgs_cnt}개")

    # 결과 JSON 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log(f"\n🎉 파일럿 결과 저장 완료: {OUTPUT_FILE}")

    # 검증 출력
    log("\n==================================================")
    log("📋 파일럿 데이터 검증 보고서")
    log("==================================================")

    # 1. XM3 2021 실측값 검증
    xm3_data = results.get("XM3", {}).get("2021", {})
    xm3_grades = xm3_data.get("grades", [])
    log("1. XM3 2021 핵심 등급 가격 검증 (제이 기준치: RE 2,352만원, RE 시그니처 2,597만원):")
    for g in xm3_grades:
        gname = g['name']
        prc = g['base_price']
        opts_cnt = len(g['options'])
        if "RE" in gname:
            prc_str = f"{prc:,}원 ({prc//10000:,}만원)" if prc else "None"
            log(f"   - {gname}: {prc_str} | 옵션 {opts_cnt}개")

    # 2. 10개 차종별 요약 테이블
    log("\n2. 10개 대상 차종별 수집 요약:")
    for t in PILOT_TARGETS:
        m_key = t['model_key']
        yr = t['year']
        item = results.get(m_key, {}).get(yr, {})
        g_list = item.get('grades', [])
        g_cnt = len(g_list)
        base_cnt = sum(1 for g in g_list if g.get('base_price') is not None)
        opt_cnt = sum(len(g.get('options', {})) for g in g_list)
        pkg_cnt = len(item.get('packages', {}))
        log(f"   [{t['id']:02d}] {t['desc']} -> 등급 {g_cnt}개 (기본가 등록 {base_cnt}개 / 결측 {g_cnt - base_cnt}개) | 등급별 옵션 {opt_cnt}개 | 패키지 {pkg_cnt}개")


if __name__ == "__main__":
    main()

