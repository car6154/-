# services/chaolma_service.py
"""
오토플러스 차얼마(purchase.autoplus.co.kr) 신차 출고 정보 및 순정 옵션 연동 서비스
- 차량번호로 신차 출고가(기본가 + 순정 옵션가), 장착된 세부 옵션 목록, 잔가율, 출고일자 자동 수집
- 연식별 옵션 잔존가치(80% / 50% / 35% / 20%) 자동 계산
"""

import os
import re
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests

from services.cookie_server import get_current_autoplus_cookie

# 메모리 캐시 (차량번호 -> {timestamp, data}) : 30분간 유효
_CHAOLMA_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 1800  # 30분


def norm_opt_name(s: str) -> str:
    """옵션명 정규화 (로마자, 띄어쓰기, 특수문자, 패키지 제거)"""
    if not s:
        return ""
    s = s.lower().replace(" ", "").replace("-", "").replace("_", "").replace("+", "")
    s = s.replace("iii", "3").replace("ii", "2").replace("iv", "4").replace("i", "1")
    s = s.replace("패키지", "").replace("팩", "")
    return s


class ChaolmaService:
    API_URL = "https://purchase.autoplus.co.kr/ajax/getCarMartData"
    HISTORY_URL = "https://purchase.autoplus.co.kr/ajax/getPurchaseInfoList"

    @classmethod
    def clear_cache(cls):
        """메모리 캐시 전체 초기화"""
        global _CHAOLMA_CACHE
        _CHAOLMA_CACHE.clear()

    @classmethod
    def get_cookie(cls) -> str:
        """현재 저장된 차얼마(오토플러스) 로그인 쿠키 반환"""
        return get_current_autoplus_cookie()

    @classmethod
    def is_authenticated(cls) -> bool:
        """차얼마 로그인 쿠키가 유효한지 확인"""
        cookie = cls.get_cookie()
        if not cookie or len(cookie.strip()) < 15:
            return False
        c_upper = cookie.upper()
        has_session = ("JSESSIONID" in c_upper) or ("REMEMBER-ME" in c_upper)
        return has_session or len(cookie.strip()) > 30

    @classmethod
    def fetch_car_info(cls, car_no: str, mileage: int = 50000, branch_code: str = "00244") -> Dict[str, Any]:
        """
        차량번호로 차얼마에서 신차 기본가, 옵션 정보, 잔가율 등을 실시간 조회
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
                "message": "차얼마 로그인 쿠키가 없습니다. 크롬 확장프로그램에서 [차얼마 쿠키 전송]을 실행해주세요.",
                "need_login": True
            }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Cookie": cookie,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://purchase.autoplus.co.kr/purchase/PCLP010001",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        data_payload = {
            "carNumber": car_no,
            "carNavi": str(mileage) if mileage > 0 else "50000",
            "seriesNo": "",
            "tsKey": ""
        }

        try:
            resp = requests.post(cls.API_URL, data=data_payload, headers=headers, timeout=10)
            
            # 응답 인코딩 UTF-8 강제
            resp_text = resp.content.decode("utf-8", errors="ignore")

            # 로그인 만료 체크 (로그인 폼 HTML이 반환된 경우)
            if "/login/login.do" in resp_text or "frm-login" in resp_text or ("<title>차얼마" in resp_text and not resp_text.strip().startswith("{")):
                return {
                    "success": False,
                    "message": "차얼마 로그인 세션이 만료되었습니다. 크롬에서 차얼마(purchase.autoplus.co.kr) 로그인 후 쿠키를 다시 전송해주세요.",
                    "need_login": True
                }

            if resp.status_code == 200:
                try:
                    res_json = json.loads(resp_text)
                except Exception:
                    return {
                        "success": False,
                        "message": "차얼마 서버 응답 형식이 올바르지 않습니다."
                    }

                header = res_json.get("header", {})
                if not header.get("isSuccessful"):
                    msg = res_json.get("msg") or header.get("resultMessage") or "차량 정보를 찾을 수 없습니다."
                    return {
                        "success": False,
                        "message": f"차얼마 조회 실패: {msg}"
                    }

                car_data = res_json.get("data")
                if not car_data:
                    return {
                        "success": False,
                        "message": f"차얼마에 해당 차량 데이터가 존재하지 않습니다 ({car_no})."
                    }

                # 정상 데이터 파싱
                parsed = cls.parse_carmart_json(car_data, car_no)
                if parsed.get("success"):
                    _CHAOLMA_CACHE[car_no] = {
                        "timestamp": now,
                        "data": parsed
                    }
                return parsed

            elif resp.status_code == 500:
                # 500인 경우 JSON 에러 메시지 확인 ("차량번호가 없습니다." 등)
                try:
                    err_json = json.loads(resp_text)
                    err_msg = err_json.get("msg") or err_json.get("header", {}).get("resultMessage")
                    if err_msg:
                        return {
                            "success": False,
                            "message": f"차얼마 안내: {err_msg} ({car_no})"
                        }
                except Exception:
                    pass
                return {
                    "success": False,
                    "message": f"차얼마에 등록되지 않은 차량번호이거나 조회할 수 없습니다 ({car_no})."
                }
            else:
                return {
                    "success": False,
                    "message": f"차얼마 서버 오류 (상태코드: {resp.status_code})"
                }

        except requests.exceptions.Timeout:
            return {"success": False, "message": "차얼마 서버 응답 시간 초과 (10초). 잠시 후 다시 시도해주세요."}
        except Exception as e:
            return {"success": False, "message": f"차얼마 조회 중 오류 발생: {str(e)}"}

    @classmethod
    def parse_carmart_json(cls, c_data: Dict[str, Any], car_no: str) -> Dict[str, Any]:
        """
        getCarMartData JSON 응답을 정형화된 시세 분석 데이터로 변환
        """
        # 1. 카탈로그 전체 옵션 목록 (원가 매핑용)
        catalog_opts = c_data.get("optionSelectList", []) or []
        price_by_name = {}
        for o in catalog_opts:
            name = str(o.get("name", "")).strip()
            p_val = 0
            try:
                p_val = int(str(o.get("price", 0)).replace(",", "").strip() or 0)
            except ValueError:
                p_val = 0
            if name:
                price_by_name[name] = p_val

        # 2. 실제 장착된 옵션 목록 (jsonFullText.optlist)
        jf = {}
        raw_jf = c_data.get("jsonFullText")
        if raw_jf:
            if isinstance(raw_jf, dict):
                jf = raw_jf
            elif isinstance(raw_jf, str):
                try:
                    jf = json.loads(raw_jf)
                except Exception:
                    pass

        # 기본 출고가 및 총 신차가
        new_car_price = int(c_data.get("carMakePrice") or jf.get("carmakeprice") or 0)
        base_car_price = int(jf.get("newprice") or 0)

        # 3. 옵션 가격 사전 (카탈로그에 없거나 0일 때 보완)
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
            "기본형-컨비니언스": 1000000,
            "컨비니언스": 1000000,
            "시트": 500000,
            "통풍시트": 400000,
            "스타일": 850000,
            "스타일1": 850000,
            "스타일2": 950000,
            "선루프": 800000,
            "와이드선루프": 790000,
            "듀얼선루프": 800000,
            "파노라마선루프": 1150000,
            "드라이브와이즈": 1100000,
            "드라이브와이즈1": 1000000,
            "드라이브와이즈2": 1690000,
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
            "렉시콘": 1200000,
            "프리미엄사운드": 600000,
            "led헤드램프": 650000,
        }

        installed_opts_raw = jf.get("optlist", [])
        if not installed_opts_raw and c_data.get("optList"):
            installed_opts_raw = c_data.get("optList", [])

        resolved_opts = []
        total_opt_price = 0

        for io in installed_opts_raw:
            name = str(io.get("name", "")).strip()
            if not name:
                continue

            p = io.get("price")
            p_val = 0
            if p is not None:
                try:
                    p_val = int(str(p).replace(",", "").strip() or 0)
                except ValueError:
                    p_val = 0

            # 가격이 0이면 카탈로그 목록과 정규화 비교
            if p_val == 0:
                n_norm = norm_opt_name(name)
                # 1) 카탈로그에서 매칭
                for cname, cprice in price_by_name.items():
                    cn_norm = norm_opt_name(cname)
                    if n_norm == cn_norm or (n_norm in cn_norm) or (cn_norm in n_norm):
                        p_val = cprice
                        break

            # 2) 여전히 0이면 기본 추정치 사전 매칭
            if p_val == 0:
                n_clean = name.lower().replace(" ", "").replace("_", "")
                if n_clean in DEFAULT_OPTION_PRICES:
                    p_val = DEFAULT_OPTION_PRICES[n_clean]
                else:
                    for k, v in DEFAULT_OPTION_PRICES.items():
                        if k in n_clean:
                            p_val = v
                            break

            resolved_opts.append({
                "name": name,
                "price": p_val
            })
            total_opt_price += p_val

        # 출고가 - 기본가 차액이 있고 옵션 총액과 차이가 날 때 정밀 보정
        diff_price = max(0, new_car_price - base_car_price)
        if diff_price > 0:
            if total_opt_price == 0 and len(resolved_opts) > 0:
                # 옵션이 1개면 바로 전액 배정
                if len(resolved_opts) == 1:
                    resolved_opts[0]["price"] = diff_price
                    total_opt_price = diff_price
            elif abs(diff_price - total_opt_price) > 0:
                # 가격이 0인 옵션이 있으면 차액을 배정
                unpriced = [o for o in resolved_opts if o["price"] == 0]
                if len(unpriced) == 1 and diff_price > total_opt_price:
                    unpriced[0]["price"] = diff_price - total_opt_price
                    total_opt_price = diff_price

        # 신차가 / 기본가 상호 보완
        if base_car_price == 0 and new_car_price > 0:
            base_car_price = max(0, new_car_price - total_opt_price)
        if new_car_price == 0 and base_car_price > 0:
            new_car_price = base_car_price + total_opt_price

        # 4. 연식 및 최초등록일
        rel_date = c_data.get("firstDate") or jf.get("firstdate") or ""
        m_year = str(c_data.get("year") or jf.get("year") or "").replace("년", "").strip()

        reg_year = ""
        if rel_date:
            m_ry = re.search(r"(\d{4})", rel_date)
            if m_ry:
                reg_year = m_ry.group(1)
        if not reg_year and m_year:
            m_my = re.search(r"(\d{4})", m_year)
            if m_my:
                reg_year = m_my.group(1)

        cur_year = datetime.now().year
        car_yr = int(reg_year) if reg_year and reg_year.isdigit() else (int(m_year) if m_year and m_year.isdigit() else cur_year)

        if reg_year and m_year and reg_year != m_year:
            year_display = f"{reg_year[-2:]}년식 ({m_year[-2:]}년형)"
        elif reg_year:
            year_display = f"{reg_year[-2:]}년식"
        elif m_year:
            year_display = f"{m_year[-2:]}년식"
        else:
            year_display = f"{str(car_yr)[-2:]}년식"

        # 5. 연식별 옵션 감가율 적용
        deprec_result = cls.calculate_option_depreciation(
            resolved_opts,
            release_date=rel_date,
            year=str(car_yr)
        )

        maker = c_data.get("makerName") or jf.get("makername") or ""
        model_name = c_data.get("modelName") or jf.get("modelname") or ""
        model_detail = c_data.get("modelDetailName") or ""
        grade_name = c_data.get("gradeName") or jf.get("seriesname1") or ""
        grade_detail = c_data.get("gradeDetailName") or jf.get("seriesname") or ""
        trim_name = grade_detail or model_detail or ""

        return {
            "success": True,
            "car_no": car_no,
            "vin": c_data.get("vin") or jf.get("vin") or "",
            "maker": maker,
            "model_name": model_name,
            "model_detail_name": model_detail,
            "grade_name": grade_name,
            "grade_detail_name": grade_detail,
            "trim_name": trim_name,
            "model_year": m_year or str(car_yr),
            "reg_year": reg_year or str(car_yr),
            "release_date": rel_date,
            "year_display": year_display,
            "color": c_data.get("color") or jf.get("color") or "",
            "fuel": c_data.get("fuel") or jf.get("fuel") or "",
            "transmission": c_data.get("gearBox") or jf.get("gearbox") or "오토",
            "new_car_price": new_car_price,
            "base_car_price": base_car_price,
            "options": deprec_result["options"],
            "total_option_price": total_opt_price,
            "total_depreciated_opt_price": deprec_result["total_depreciated_opt_price"],
            "depreciation_rate": deprec_result["depreciation_rate"],
            "remain_rate": 0.0,
            "option_memo": jf.get("option_memo", "")
        }

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
        - 1~3년차: 50% (0.50)
        - 3~5년차: 35% (0.35)
        - 5년차 이상: 20% (0.20)
        """
        age_years = 3.0

        if release_date:
            try:
                date_clean = re.sub(r"[^\d-]", "", release_date.strip())
                if len(date_clean) >= 10:
                    dt = datetime.strptime(date_clean[:10], "%Y-%m-%d")
                    age_years = (datetime.now() - dt).days / 365.25
            except Exception:
                pass
        elif year:
            try:
                yr = int(re.sub(r"[^\d]", "", str(year)))
                age_years = max(0.0, datetime.now().year - yr + 0.5)
            except Exception:
                pass

        if age_years < 1.0:
            rate = 0.80
        elif age_years < 3.0:
            rate = 0.50
        elif age_years < 5.0:
            rate = 0.35
        else:
            rate = 0.20

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
