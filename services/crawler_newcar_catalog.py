# services/crawler_newcar_catalog.py
"""
엔카 공식 신차가격표(차량정보 DB) 국산차 전 차종 연식별 일괄 수집기
- 대상 제조사: 현대, 기아, 제네시스, 쉐보레, 르노코리아, KGM(쌍용)
- 연식 범위: 2013년 ~ 2025년
- 데이터 구조: { "모델명": { "연식": { "패키지명": "세부 품목 설명 문자열", ... } } }
- 저장 위치: data/encar_newcar_catalog.json
- 중복 방지 및 이어받기(Resume) 지원
- 차단 방지용 안전 딜레이 및 세션 자동 유지
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

# 기본 인코딩 UTF-8 설정
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "encar_newcar_catalog.json")
LOG_FILE = os.path.join(DATA_DIR, "catalog_crawl.log")

TARGET_MFGS = [
    {"code": "001", "name": "현대"},
    {"code": "007", "name": "제네시스"},
    {"code": "002", "name": "기아"},
    {"code": "003", "name": "쉐보레(GM대우)"},
    {"code": "005", "name": "르노코리아(삼성)"},
    {"code": "004", "name": "KG모빌리티(쌍용)"}
]

class EncarNewCarCrawler:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": "https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2"
        })
        self.catalog_data = self._load_existing_catalog()
        self.access_token = ""
        self.token_expiry_time = 0

    def log(self, msg: str):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{now_str}] {msg}"
        print(log_line)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception:
            pass

    def _load_existing_catalog(self) -> dict:
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.log(f"기존 카탈로그 로드 완료: {len(data)}개 모델 등록됨")
                    return data
            except Exception as e:
                self.log(f"기존 카탈로그 로드 실패 (새로 생성): {e}")
        return {}

    def _save_catalog(self):
        try:
            temp_file = OUTPUT_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.catalog_data, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, OUTPUT_FILE)
        except Exception as e:
            self.log(f"카탈로그 저장 실패: {e}")

    def refresh_access_token(self) -> str:
        """신차가격표 팝업 초기 접속으로 pageAccessToken 갱신"""
        try:
            init_url = "https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2"
            r = self.session.get(init_url, timeout=7)
            match = re.search(r'name=["\']?pageAccessToken["\']?\s+value=["\']([^"\']+)["\']', r.text)
            if not match:
                match = re.search(r'id=["\']?pageAccessToken["\']?[^>]*?value=["\']([^"\']+)["\']', r.text)
            if match:
                self.access_token = match.group(1)
                self.token_expiry_time = time.time() + 600  # 10분 유효
                return self.access_token
        except Exception as e:
            self.log(f"토큰 갱신 오류: {e}")
        return self.access_token

    def get_model_groups(self, mfg_cd: str) -> list:
        """제조사별 모델그룹 목록 조회"""
        url = f"https://www.encar.com/common/combo/modelgroupfordb.json?method=carList&mnfccd={mfg_cd}"
        try:
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            self.log(f"모델그룹 조회 실패 ({mfg_cd}): {e}")
        return []

    def get_models(self, mfg_cd: str, mdlgroup_cd: str) -> list:
        """모델그룹별 세부모델 목록 조회"""
        url = f"https://www.encar.com/common/combo/cardbmodel.json?method=carList&mnfccd={mfg_cd}&mdlgroupcd={mdlgroup_cd}"
        try:
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            self.log(f"세부모델 조회 실패 ({mdlgroup_cd}): {e}")
        return []

    def get_years(self, mfg_cd: str, mdl_cd: str) -> list:
        """세부모델별 형식연도 목록 조회"""
        url = f"https://www.encar.com/common/combo/jatoYr.json?method=carList&mnfccd={mfg_cd}&mdlcd={mdl_cd}"
        try:
            r = self.session.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                # 2013년 이후 연식 필터링 (최신 중고차 중심)
                years = []
                for item in data:
                    yr = str(item.get("abbreviation") or item.get("label") or "").strip()
                    if yr.isdigit() and int(yr) >= 2013:
                        years.append(yr)
                return sorted(list(set(years)), reverse=True)
        except Exception as e:
            self.log(f"연식 조회 실패 ({mdl_cd}): {e}")
        return []

    def parse_newcar_details_from_html(self, html_text: str) -> dict:
        """
        신차가격표 HTML 본문에서 전 등급(트림), 선택 추가옵션(가격 포함), 패키지 세부 구성품목 전체 추출
        반환값: {
            "grades": ["트림1", "트림2", ...],
            "options": { "옵션명": { "price": 650000, "desc": "세부설명" }, ... },
            "packages": { "패키지명": "세부 품목 설명", ... }
        }
        """
        result = {
            "grades": [],
            "options": {},
            "packages": {}
        }
        if not html_text:
            return result

        soup = BeautifulSoup(html_text, 'html.parser')

        # 1. 등급 (Trims) 추출
        grades = set()
        TRIM_KEYWORDS = ['스마트', '모던', '프리미엄', '익스클루시브', '인스퍼레이션', '캘리그래피', '르블랑', '스타일', 
                         '트렌디', '프레스티지', '노블레스', '시그니처', '그래비티', '스페셜', '어드밴스드',
                         'lt', 'ltz', 'premier', 'redline', 'rs', 'activ', 'ls', 're', 'le', 'se', 'iconic', 'tce']
        for elem in soup.find_all(['th', 'td', 'p', 'strong']):
            cls = " ".join(elem.get('class', [])).lower()
            txt = elem.get_text(strip=True)
            if not txt or len(txt) > 30:
                continue
            txt_lower = txt.lower()
            if ('grade' in cls or 'tit' in cls) and not any(k in txt for k in ['가격', '사양', '품목', '선택', '외장', '내장', '보증']):
                grades.add(txt)
            elif any(k == txt_lower or f" {k}" in txt_lower or f"{k} " in txt_lower for k in TRIM_KEYWORDS):
                if not any(k in txt for k in ['가격', '사양', '품목', '선택', '패키지', '시스템']):
                    grades.add(txt)

        # 2. 추가옵션 리스트 (▶ 화살표 및 li.goods / p.option / choice) 추출
        for opt_elem in soup.find_all(['li', 'p', 'td']):
            cls = " ".join(opt_elem.get('class', [])).lower()
            if 'goods' in cls or 'option' in cls or 'choice' in cls:
                text_lines = opt_elem.decode_contents().replace('<br>', '\n').replace('<br/>', '\n').split('\n')
                for line in text_lines:
                    clean = html.unescape(re.sub(r'<[^>]+>', '', line)).strip()
                    if not clean:
                        continue
                    m_opt = re.search(r'^[▶►▶︎●•*※]?\s*([가-힣A-Za-z0-9\sⅠⅡⅢⅣIViv\+\&\(\)\/]+?)\s+([0-9,]+(?:\s*원)?)$', clean)
                    if m_opt:
                        opt_name = m_opt.group(1).strip()
                        price_str = m_opt.group(2).strip()
                        price = int(re.sub(r'[^\d]', '', price_str)) if re.sub(r'[^\d]', '', price_str) else None
                        if opt_name and len(opt_name) > 1 and price:
                            if not any(k in opt_name for k in ['컬러', '외장', '내장', '기본사양', '합계', '소계']):
                                result["options"][opt_name] = {"price": price}

        # 3. 패키지 세부 구성 품목 추출 (■, ●, •, - 연결형)
        lines = html_text.replace('<br>', '\n').replace('<BR>', '\n').replace('<br/>', '\n').splitlines()
        for line in lines:
            clean = html.unescape(re.sub(r'<[^>]+>', '', line)).strip()
            if not clean or '차량DB' in clean or '신차가격표' in clean or '가격 및 사양' in clean:
                continue

            # 3-1. "■ 패키지명 - 세부설명" 또는 "● 패키지명 - 세부설명"
            m1 = re.match(r'^[■●•*※]\s*([^\n\-—:]{2,30}?)\s*[-—:]\s*(.+)$', clean)
            if m1:
                p_name = m1.group(1).replace("&nbsp;", " ").strip()
                p_desc = m1.group(2).replace("&nbsp;", " ").strip()
                if len(p_name) > 1 and len(p_desc) > 3:
                    if not any(k in p_name for k in ['사양', '파워트레인', '외장컬러', '기본사양', '공통', '참고']):
                        result["packages"][p_name] = p_desc
                        if p_name not in result["options"]:
                            result["options"][p_name] = {"price": None}
                continue

            # 3-2. "패키지명 - 세부설명"
            m2 = re.match(r'^([가-힣A-Za-z0-9\sⅠⅡⅢⅣIViv\+\(\)]{2,25})\s*[-—]\s*([가-힣A-Za-z0-9].{5,})$', clean)
            if m2:
                p_name = m2.group(1).replace("&nbsp;", " ").strip()
                p_desc = m2.group(2).replace("&nbsp;", " ").strip()
                if len(p_name) > 1 and len(p_desc) > 5:
                    if not any(k in p_name for k in ['사양', '파워트레인', '외장컬러', '기본사양', '공통', '품목', '선택', '주의']):
                        if p_name not in result["packages"] or len(p_desc) > len(result["packages"][p_name]):
                            result["packages"][p_name] = p_desc
                            if p_name not in result["options"]:
                                result["options"][p_name] = {"price": None}

        # 옵션에 패키지 설명 매핑 연결
        for p_name, p_desc in result["packages"].items():
            for opt_key in list(result["options"].keys()):
                clean_p = re.sub(r'[\s\-_]', '', p_name).lower()
                clean_o = re.sub(r'[\s\-_]', '', opt_key).lower()
                if clean_p == clean_o or clean_p in clean_o or clean_o in clean_p:
                    result["options"][opt_key]["desc"] = p_desc

        result["grades"] = sorted(list(grades))
        return result

    def crawl_model_year(self, mfg_cd: str, mfg_name: str, model_name: str, mdlgroup_cd: str, mdl_cd: str, year: str) -> bool:
        """특정 모델의 단일 연식 신차가격표 수집"""
        clean_model_key = model_name.strip()
        # 이미 수집되어 있고 내용이 있으면 건너뛰기
        if clean_model_key in self.catalog_data and year in self.catalog_data[clean_model_key]:
            existing_val = self.catalog_data[clean_model_key][year]
            if isinstance(existing_val, dict) and ("options" in existing_val or "packages" in existing_val):
                if len(existing_val.get("options", {})) > 0 or len(existing_val.get("packages", {})) > 0:
                    return True

        if not self.access_token or time.time() > self.token_expiry_time:
            self.refresh_access_token()

        url = (
            f"https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2"
            f"&mnfccd={mfg_cd}&mdlgroupcd={mdlgroup_cd}&mdlcd={mdl_cd}&caryear={year}"
        )
        if self.access_token:
            url += f"&pageAccessToken={requests.utils.quote(self.access_token)}"

        try:
            r = self.session.get(url, timeout=7)
            # 토큰 만료로 인한 area_nodata인 경우 1회 갱신 후 재시도
            if "area_nodata" in r.text:
                self.refresh_access_token()
                retry_url = (
                    f"https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2"
                    f"&mnfccd={mfg_cd}&mdlgroupcd={mdlgroup_cd}&mdlcd={mdl_cd}&caryear={year}"
                    f"&pageAccessToken={requests.utils.quote(self.access_token)}"
                )
                r_retry = self.session.get(retry_url, timeout=7)
                if r_retry.status_code == 200 and "area_nodata" not in r_retry.text:
                    r = r_retry

            if r.status_code == 200:
                res_dict = self.parse_newcar_details_from_html(r.text)
                
                if clean_model_key not in self.catalog_data:
                    self.catalog_data[clean_model_key] = {}
                
                self.catalog_data[clean_model_key][year] = res_dict
                cnt_g = len(res_dict.get("grades", []))
                cnt_o = len(res_dict.get("options", {}))
                cnt_p = len(res_dict.get("packages", {}))
                if cnt_g > 0 or cnt_o > 0 or cnt_p > 0:
                    self.log(f"  [수집성공] {mfg_name} {clean_model_key} ({year}년형) -> 등급 {cnt_g}개 | 옵션 {cnt_o}개 | 패키지 {cnt_p}개")
                else:
                    self.log(f"  [확인완료] {mfg_name} {clean_model_key} ({year}년형) -> 신차가격표 준비중/미등록")
                return True
            else:
                self.log(f"  [응답오류] {clean_model_key} ({year}년형) -> HTTP {r.status_code}")
        except Exception as e:
            self.log(f"  [수집실패] {clean_model_key} ({year}년형) -> {e}")

        return False

    def run(self):
        self.log("🚀 국산차 전 차종 연식별 신차 옵션 패키지 일괄 수집을 시작합니다.")
        self.refresh_access_token()
        
        total_models = 0
        total_years = 0
        saved_count = 0

        for mfg in TARGET_MFGS:
            mfg_cd = mfg["code"]
            mfg_name = mfg["name"]
            self.log(f"\n==========================================")
            self.log(f"🏢 [{mfg_name}] 모델 목록 탐색 시작...")
            self.log(f"==========================================")

            mdlgroups = self.get_model_groups(mfg_cd)
            for mg in mdlgroups:
                mg_name = mg.get("name", "").strip()
                mg_cd = mg.get("abbreviation", "").strip()
                if not mg_name or not mg_cd:
                    continue

                models = self.get_models(mfg_cd, mg_cd)
                for mdl in models:
                    mdl_name = mdl.get("name", "").strip()
                    mdl_cd = mdl.get("abbreviation", "").strip()
                    if not mdl_name or not mdl_cd:
                        continue

                    # 대표 모델명 선정 (모델그룹 + 세부모델명 중복 방지)
                    if mg_name.lower() in mdl_name.lower():
                        full_car_name = mdl_name
                    else:
                        full_car_name = f"{mg_name} {mdl_name}".strip()
                    total_models += 1

                    years = self.get_years(mfg_cd, mdl_cd)
                    if not years:
                        continue

                    self.log(f"▶ [{mfg_name}] {full_car_name} (연식 {len(years)}개: {years[0]}~{years[-1]})")

                    for yr in years:
                        total_years += 1
                        success = self.crawl_model_year(mfg_cd, mfg_name, full_car_name, mg_cd, mdl_cd, yr)
                        
                        # 주기적 저장 (매 5건마다 디스크 동기화)
                        saved_count += 1
                        if saved_count % 5 == 0:
                            self._save_catalog()

                        # 안전 딜레이 (0.6초 ~ 1.2초)
                        time.sleep(random.uniform(0.6, 1.2))

            # 제조사 완료 시마다 저장
            self._save_catalog()

        # 최종 저장
        self._save_catalog()
        self.log(f"\n🎉 모든 수집이 완료되었습니다!")
        self.log(f"총 모델 수: {total_models}개 | 총 연식 페이지: {total_years}개")
        self.log(f"저장된 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    crawler = EncarNewCarCrawler()
    crawler.run()
