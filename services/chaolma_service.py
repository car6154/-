# services/chaolma_service.py
"""
오토플러스 차얼마2(purchase.autoplus.co.kr) 신차 출고 정보 및 순정 옵션 크롤링/파싱 서비스
- 차량번호로 신차 출고가(기본가 + 순정 옵션가), 세부 옵션 목록, 잔가율, 출고일자 자동 수집
- 연식별 옵션 잔존가치(80% / 50% / 35% / 20%) 자동 계산
"""

import os
import re
import json
import time
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup

from services.cookie_server import get_current_autoplus_cookie

# 메모리 캐시 (차량번호 -> {timestamp, data}) : 30분간 유효
_CHAOLMA_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 1800  # 30분


class ChaolmaService:
    BASE_URL = "https://purchase.autoplus.co.kr/purchase/PCVP010001"

    @classmethod
    def get_cookie(cls) -> str:
        """현재 저장된 오토플러스 로그인 쿠키 반환"""
        return get_current_autoplus_cookie()

    @classmethod
    def is_authenticated(cls) -> bool:
        """오토플러스 쿠키가 존재하는지 확인"""
        cookie = cls.get_cookie()
        return bool(cookie and len(cookie.strip()) > 10)

    @classmethod
    def fetch_car_info(cls, car_no: str, mileage: int = 50000, branch_code: str = "00244") -> Dict[str, Any]:
        """
        차량번호로 차얼마2에서 신차 기본가, 옵션 정보, 잔가율 등을 조회
        """
        car_no = str(car_no).replace(" ", "").strip()
        if not car_no:
            return {"success": False, "message": "차량번호가 입력되지 않았습니다."}

        # 1. 캐시 확인
        now = time.time()
        if car_no in _CHAOLMA_CACHE:
            entry = _CHAOLMA_CACHE[car_no]
            if now - entry["timestamp"] < CACHE_TTL:
                return entry["data"]

        # 2. 쿠키 확인
        cookie = cls.get_cookie()
        if not cookie:
            return {
                "success": False,
                "message": "오토플러스(차얼마2) 로그인 쿠키가 없습니다. 크롬 확장프로그램에서 차얼마2 쿠키를 전송해주세요.",
                "need_login": True
            }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Cookie": cookie,
            "Referer": "https://purchase.autoplus.co.kr/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        params = {
            "brCd": branch_code,
            "tsKey": "",
            "seriesNo": "",
            "carNumber": car_no,
            "carNavi": str(mileage)
        }

        try:
            resp = requests.get(cls.BASE_URL, params=params, headers=headers, timeout=8)
            if resp.status_code == 200:
                html_text = resp.text
                
                # 로그인 만료 체크 (로그인 페이지로 리다이렉트되거나 로그인 폼이 나타난 경우)
                if "/login/login.do" in html_text or "로그인이 필요합니다" in html_text or "frm-login" in html_text:
                    return {
                        "success": False,
                        "message": "오토플러스 로그인 세션이 만료되었습니다. 차얼마2에 다시 로그인 후 쿠키를 전송해주세요.",
                        "need_login": True
                    }

                # HTML 파싱
                parsed_data = cls.parse_car_html(html_text, car_no)
                if parsed_data.get("success"):
                    # 캐시에 저장
                    _CHAOLMA_CACHE[car_no] = {
                        "timestamp": now,
                        "data": parsed_data
                    }
                return parsed_data
            elif resp.status_code == 500:
                return {
                    "success": False,
                    "message": "오토플러스(차얼마2) 로그인 세션이 만료되었습니다. 크롬에서 차얼마2(purchase.autoplus.co.kr)에 로그인 후 쿠키를 다시 전송해주세요.",
                    "need_login": True
                }
            else:
                return {
                    "success": False,
                    "message": f"차얼마2 서버 응답 오류 (상태코드: {resp.status_code})"
                }
        except requests.exceptions.Timeout:
            return {"success": False, "message": "차얼마2 서버 응답 시간이 초과되었습니다 (8초 초과)."}
        except Exception as e:
            return {"success": False, "message": f"차얼마2 조회 중 오류 발생: {str(e)}"}

    @classmethod
    def parse_car_html(cls, html: str, target_car_no: str = "") -> Dict[str, Any]:
        """
        차얼마2 PCVP010001 HTML을 파싱하여 정형화된 데이터 반환
        """
        soup = BeautifulSoup(html, "html.parser")
        result: Dict[str, Any] = {
            "success": True,
            "car_no": target_car_no,
            "vin": "",
            "maker": "",
            "model_name": "",
            "grade_name": "",
            "trim_name": "",
            "model_year": "",
            "release_date": "",
            "mileage": "",
            "color": "",
            "transmission": "",
            "fuel": "",
            "new_car_price": 0,           # 총 신차가 (기본가 + 옵션가)
            "base_car_price": 0,          # 기본 출고가
            "remain_rate": 0.0,           # 잔가율 (%)
            "options": [],                # [{"name": "현대스마트센스", "price": 400000, "depreciated_price": ...}]
            "total_option_price": 0,      # 순정옵션 합계 원가
            "total_depreciated_opt_price": 0, # 감가 반영된 옵션 현재가
            "depreciation_rate": 0.0,     # 적용된 감가율
            "wholesale_price": 0,         # 기준도매가
            "retail_price": 0,            # 기준소매가
            "raw_inputs": {}
        }

        # 1. 히든 및 일반 인풋 태그 수집
        hidden_inputs = {}
        for inp in soup.find_all("input"):
            name = inp.get("name") or inp.get("id")
            if name:
                hidden_inputs[name] = inp.get("value", "")
        result["raw_inputs"] = hidden_inputs

        # 2. 순정 옵션 표준 신차가 사전 (차얼마2에서 price가 null로 올 때 지능적 매칭)
        DEFAULT_OPTION_PRICES = {
            "7인치내비": 800000,
            "8인치내비": 950000,
            "내비": 850000,
            "내비게이션": 850000,
            "ecm&etcs": 250000,
            "ecm": 250000,
            "하이패스": 250000,
            "etcs": 200000,
            "컴포트": 600000,
            "컴포트시트": 600000,
            "기본형-컴포트시트": 600000,
            "시트": 500000,
            "통풍시트": 400000,
            "스타일": 850000,
            "스타일1": 850000,
            "스타일2": 950000,
            "스타일3": 1050000,
            "선루프": 1150000,
            "파노라마선루프": 1150000,
            "드라이브와이즈": 1100000,
            "드라이브와이즈1": 1000000,
            "드라이브와이즈2": 1150000,
            "스마트센스": 1050000,
            "현대스마트센스": 1050000,
            "후측방경보": 450000,
            "후측방": 450000,
            "hud": 1200000,
            "헤드업디스플레이": 1200000,
            "서라운드뷰": 800000,
            "어라운드뷰": 800000,
            "모니터링팩": 700000,
            "스마트키": 350000,
            "버튼시동": 350000,
            "사운드": 600000,
            "크렐": 600000,
            "jbl": 600000,
            "보스": 600000,
            "프리미엄사운드": 600000,
            "led헤드램프": 650000,
            "휠": 500000,
            "18인치휠": 500000,
            "19인치휠": 650000,
        }

        # 순정 옵션 리스트 파싱 (input#optionSelectList)
        opt_json_str = hidden_inputs.get("optionSelectList", "")
        if not opt_json_str:
            opt_tag = soup.find("input", {"id": "optionSelectList"}) or soup.find("input", {"name": "optionSelectList"})
            if opt_tag:
                opt_json_str = opt_tag.get("value", "")

        raw_options = []
        if opt_json_str:
            try:
                raw_options = json.loads(opt_json_str)
            except Exception:
                matches = re.findall(r'\{"price":([^,]+),"name":"([^"]+)"\}', opt_json_str)
                for price_val, name in matches:
                    raw_options.append({"name": name, "price": price_val if price_val != "null" else None})

        total_opt_price = 0
        cleaned_options = []
        for opt in raw_options:
            name = str(opt.get("name", "")).strip()
            price_raw = opt.get("price")
            price = 0
            if price_raw is not None:
                try:
                    price = int(str(price_raw).replace(",", "").strip())
                except ValueError:
                    price = 0
            
            # 사내 시스템에서 price가 null/0으로 오는 경우 지능형 표준 가격 매핑
            if price == 0 and name:
                n_clean = name.lower().replace(" ", "").replace("_", "")
                if n_clean in DEFAULT_OPTION_PRICES:
                    price = DEFAULT_OPTION_PRICES[n_clean]
                else:
                    for k, v in DEFAULT_OPTION_PRICES.items():
                        if k in n_clean:
                            price = v
                            break
                if price == 0:
                    price = 500000  # 기본 추정치

            if name:
                cleaned_options.append({
                    "name": name,
                    "price": price
                })
                total_opt_price += price

        result["options"] = cleaned_options
        result["total_option_price"] = total_opt_price

        # 3. 신차 출고가 / 연식 / 최초등록일 / 차대번호 / 색상 / 변속기 / 연료
        vin = hidden_inputs.get("ideNumber", "")
        if not vin:
            m_vin = re.search(r'ideNumber["\']?\s*[:=]\s*["\']?([A-Za-z0-9]{17})["\']?', html)
            if m_vin: vin = m_vin.group(1)
        result["vin"] = vin

        result["model_year"] = hidden_inputs.get("carYear", "").replace("년", "").strip()
        result["release_date"] = hidden_inputs.get("releaseDate", "").strip()
        result["color"] = hidden_inputs.get("carColor", "").strip()

        raw_new_price = hidden_inputs.get("newPrice", "")
        if not raw_new_price:
            m_np = re.search(r'newPrice["\']?\s*[:=]\s*["\']?([0-9,]+)["\']?', html)
            if m_np: raw_new_price = m_np.group(1)
        clean_new_price = re.sub(r'[^\d]', '', raw_new_price) if raw_new_price else ""
        result["new_car_price"] = int(clean_new_price) if clean_new_price else 0

        # 기본 출고가 = 총 출고가 - 옵션 총액
        result["base_car_price"] = max(0, result["new_car_price"] - result["total_option_price"])

        # 제조사
        maker_sel = soup.find("select", {"id": "menufacturer"})
        maker = ""
        if maker_sel:
            opt = maker_sel.find("option", selected=True)
            if opt: maker = opt.get_text(strip=True)
        result["maker"] = maker or "현대/기아"

        # 변속기 / 연료
        trans_sel = soup.find("select", {"id": "gearbox"})
        result["transmission"] = trans_sel.find("option", selected=True).get_text(strip=True) if trans_sel and trans_sel.find("option", selected=True) else "오토"

        fuel_sel = soup.find("select", {"id": "carFuel"})
        result["fuel"] = fuel_sel.find("option", selected=True).get_text(strip=True) if fuel_sel and fuel_sel.find("option", selected=True) else "가솔린"

        # 4. 차종 / 모델 / 등급 / 세부등급 (JSP 스크립트 val 주입문 분석)
        container_vals = re.findall(r"\$container\.val\(['\"]([^'\"]+)['\"]\)", html)
        model_name = hidden_inputs.get("justModel", "")
        grade_name = ""
        trim_name = ""

        if len(container_vals) >= 1:
            model_name = container_vals[0]
        if len(container_vals) >= 2:
            grade_name = container_vals[1]
        if len(container_vals) >= 3:
            trim_name = container_vals[2]

        result["model_name"] = model_name
        result["grade_name"] = grade_name
        result["trim_name"] = trim_name

        # 잔가율 (사내 잔가율)
        raw_remain = hidden_inputs.get("remainRate", "")
        if not raw_remain:
            m_rr = re.search(r'remainRate["\']?\s*[:=]\s*["\']?([0-9.]+)["\']?', html)
            if m_rr: raw_remain = m_rr.group(1)
        try:
            result["remain_rate"] = float(raw_remain) if raw_remain else 0.0
        except ValueError:
            result["remain_rate"] = 0.0

        # 5. 연식별 옵션 감가 계산 적용
        deprec_result = cls.calculate_option_depreciation(
            cleaned_options,
            release_date=result["release_date"],
            year=result["model_year"]
        )
        result["options"] = deprec_result["options"]
        result["total_depreciated_opt_price"] = deprec_result["total_depreciated_opt_price"]
        result["depreciation_rate"] = deprec_result["depreciation_rate"]
        return result

    @classmethod
    def calculate_option_depreciation(
        cls,
        options: List[Dict[str, Any]],
        release_date: Optional[str] = None,
        year: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        차량 출고일 또는 연식에 따라 순정 옵션 잔존가치(감가율) 계산
        - 1년 미만: 80% (0.80)
        - 1~2년차: 50% (0.50)
        - 3~4년차: 35% (0.35)
        - 5년차 이상: 20% (0.20)
        """
        age_years = 3.0  # 기본값 3년

        # 1. 최초등록일 기준 경과 연수 계산
        if release_date:
            try:
                date_clean = re.sub(r'[^\d-]', '', release_date.strip())
                if len(date_clean) >= 10:
                    dt = datetime.strptime(date_clean[:10], "%Y-%m-%d")
                    age_years = (datetime.now() - dt).days / 365.25
            except Exception:
                pass
        elif year:
            try:
                yr = int(re.sub(r'[^\d]', '', str(year)))
                age_years = max(0.0, datetime.now().year - yr + 0.5)
            except Exception:
                pass

        # 2. 감가율(잔존율) 결정
        if age_years < 1.0:
            rate = 0.80
        elif age_years < 3.0:
            rate = 0.50
        elif age_years < 5.0:
            rate = 0.35
        else:
            rate = 0.20

        # 3. 각 옵션별 잔존가 계산
        total_deprec = 0
        computed_options = []
        for opt in options:
            p = opt.get("price", 0)
            deprec_p = int(round(p * rate))
            total_deprec += deprec_p
            computed_options.append({
                **opt,
                "depreciated_price": deprec_p,
                "rate": rate
            })

        return {
            "options": computed_options,
            "total_depreciated_opt_price": total_deprec,
            "depreciation_rate": rate,
            "age_years": round(age_years, 1)
        }
