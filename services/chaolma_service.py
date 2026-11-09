# services/chaolma_service.py
"""
오토플러스 차얼마(purchase.autoplus.co.kr) 신차 출고 정보 및 순정 옵션 연동 서비스
- 차량번호로 신차 출고가(기본가 + 순정 옵션가), 장착된 세부 옵션 목록, 잔가율, 출고일자 자동 수집
- 연식별 옵션 잔존가치(80% / 50% / 35% / 20%) 자동 계산
"""

import re
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import urllib.parse
import xml.etree.ElementTree as ET
import requests

import os
from services.cookie_server import get_current_autoplus_cookie
from services.local_cache import LocalFileCache
from services.option_package_service import (
    normalize_opt_name,
    resolve_option_item,
    get_catalog_for_car,
    compute_bigram_jaccard
)

# 메모리 캐시 (차량번호 -> {timestamp, data}) : 30분간 유효 (로컬 파일 캐시 연동)
_CHAOLMA_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 1800  # 30분
_CHAOLMA_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "cache", "chaolma_cache.json"
)
_chaolma_file_cache = LocalFileCache(_CHAOLMA_CACHE_FILE, CACHE_TTL, _CHAOLMA_CACHE)

# 하위 호환 별칭 (단일 진실 공급원 normalize_opt_name 사용)
norm_opt_name = normalize_opt_name
compute_opt_jaccard = compute_bigram_jaccard


class ChaolmaService:
    API_URL = "https://purchase.autoplus.co.kr/ajax/getCarMartData"
    HISTORY_URL = "https://purchase.autoplus.co.kr/ajax/getPurchaseInfoList"
    CAR_HISTORY_URL = "https://purchase.autoplus.co.kr/ajax/getCarHistory"
    ORIGIN_DOC_URL = "https://purchase.autoplus.co.kr/ajax/getCarOriginDocData"
    MARKET_PRICE_URL = "https://purchase.autoplus.co.kr/ajax/getDaaMarketPriceModel"

    @classmethod
    def clear_cache(cls):
        """메모리 및 로컬 파일 캐시 전체 초기화"""
        global _CHAOLMA_CACHE
        _chaolma_file_cache.clear()

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
    def fetch_carmart_raw(cls, car_no: str, mileage: int = 50000) -> Dict[str, Any]:
        """
        차얼마 1차 API(getCarMartData)만 빠르게 호출하여 원시 car_data 반환 (약 0.1초 소요).
        - 캐시 히트 시: {"success": True, "is_cached": True, "cached_result": cached_data}
        - 캐시 미스 시: {"success": True, "is_cached": False, "car_data": car_data, "cookie": cookie}
        - 실패 시: {"success": False, "message": ..., "need_login": ...}
        """
        car_no = str(car_no).replace(" ", "").strip()
        if not car_no:
            return {"success": False, "message": "차량번호가 입력되지 않았습니다."}

        # 1. 캐시 확인
        now = time.time()
        cached_entry = _chaolma_file_cache.get(car_no)
        if cached_entry and (now - cached_entry.get("timestamp", 0) < CACHE_TTL):
            cached_data = cached_entry.get("data")
            if isinstance(cached_data, dict):
                return {"success": True, "is_cached": True, "cached_result": cached_data}

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
            resp_text = resp.content.decode("utf-8", errors="ignore")

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
                    return {"success": False, "message": "차얼마 서버 응답 형식이 올바르지 않습니다."}

                header = res_json.get("header", {})
                if not header.get("isSuccessful"):
                    msg = res_json.get("msg") or header.get("resultMessage") or "차량 정보를 찾을 수 없습니다."
                    return {"success": False, "message": f"차얼마 조회 실패: {msg}"}

                car_data = res_json.get("data")
                if not car_data:
                    return {"success": False, "message": f"차얼마에 해당 차량 데이터가 존재하지 않습니다 ({car_no})."}

                return {"success": True, "is_cached": False, "car_data": car_data, "cookie": cookie}

            elif resp.status_code == 500:
                try:
                    err_json = json.loads(resp_text)
                    err_msg = err_json.get("msg") or err_json.get("header", {}).get("resultMessage")
                    if err_msg:
                        return {"success": False, "message": f"차얼마 안내: {err_msg} ({car_no})"}
                except Exception:
                    pass
                return {"success": False, "message": f"차얼마에 등록되지 않은 차량번호이거나 조회할 수 없습니다 ({car_no})."}
            else:
                return {"success": False, "message": f"차얼마 서버 오류 (상태코드: {resp.status_code})"}
        except requests.exceptions.Timeout:
            return {"success": False, "message": "차얼마 서버 응답 시간 초과 (10초). 잠시 후 다시 시도해주세요."}
        except Exception as e:
            return {"success": False, "message": f"차얼마 조회 중 오류 발생: {str(e)}"}

    @classmethod
    def extract_quick_spec(cls, car_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        1차 car_data에서 model_name, model_detail_name, maker, year, reg_year, grade_name, grade_detail_name 즉시 추출
        """
        if not car_data:
            return {}
        jf = {}
        raw_jf = car_data.get("jsonFullText")
        if raw_jf:
            if isinstance(raw_jf, dict):
                jf = raw_jf
            elif isinstance(raw_jf, str):
                try:
                    jf = json.loads(raw_jf)
                except Exception:
                    pass

        maker = car_data.get("makerName") or jf.get("makername") or ""
        model_name = car_data.get("modelName") or jf.get("modelname") or ""
        model_detail = car_data.get("modelDetailName") or ""
        grade_name = car_data.get("gradeName") or jf.get("seriesname1") or ""
        grade_detail = car_data.get("gradeDetailName") or jf.get("seriesname") or ""

        rel_date = car_data.get("firstDate") or jf.get("firstdate") or ""
        m_year = str(car_data.get("year") or jf.get("year") or "").replace("년", "").strip()

        reg_year = ""
        if rel_date:
            m_ry = re.search(r"(\d{4})", str(rel_date))
            if m_ry:
                reg_year = m_ry.group(1)
        if not reg_year and m_year:
            m_my = re.search(r"(\d{4})", str(m_year))
            if m_my:
                reg_year = m_my.group(1)

        year_num = 0
        if m_year and m_year.isdigit():
            y_val = int(m_year)
            year_num = (y_val - 2000) if y_val > 2000 else y_val
        elif reg_year and reg_year.isdigit():
            y_val = int(reg_year)
            year_num = (y_val - 2000) if y_val > 2000 else y_val

        return {
            "car_name": model_detail or model_name or "",
            "model_name": model_name,
            "model_detail_name": model_detail,
            "maker": maker,
            "year": year_num,
            "model_year": m_year,
            "reg_year": reg_year,
            "grade_name": grade_name,
            "grade_detail_name": grade_detail
        }

    @classmethod
    def complete_car_info_enrichment(
        cls,
        car_data: Dict[str, Any],
        car_no: str,
        mileage: int = 50000
    ) -> Dict[str, Any]:
        """
        1차 car_data를 바탕으로 등록원부, 카히스토리, 공식시세, 옵션을 보강하여 최종 chaolma_res 완성 및 캐시 저장
        """
        now = time.time()
        # 1. 국토부 자동차등록원부 선행 조회
        doc_res = None
        try:
            doc_res = cls.fetch_car_origin_doc(car_no)
        except Exception:
            doc_res = None

        # 정상 데이터 파싱
        parsed = cls.parse_carmart_json(car_data, car_no, origin_doc=doc_res)
        if parsed.get("success"):
            # 카히스토리(보험이력) 자동 결합 조회
            try:
                ch_res = cls.fetch_car_history(car_no)
                if ch_res and ch_res.get("success"):
                    parsed["car_history"] = ch_res
                    parsed["market_price_range"] = ch_res.get("market_price_range", "")
                    parsed["market_price_min"] = ch_res.get("market_price_min", 0)
                    parsed["market_price_max"] = ch_res.get("market_price_max", 0)
                    parsed["market_price_avg"] = ch_res.get("market_price_avg", 0)
            except Exception:
                pass

            # 국토부 자동차등록원부 결과 결합
            if doc_res and doc_res.get("success"):
                parsed["origin_doc"] = doc_res

            # 차얼마 공식 시세(기준소매가) 자동 결합 조회
            parsed["chaolma_retail_price"] = 0
            try:
                raw_jf = car_data.get("jsonFullText")
                jf_obj = {}
                if isinstance(raw_jf, dict):
                    jf_obj = raw_jf
                elif isinstance(raw_jf, str):
                    try:
                        jf_obj = json.loads(raw_jf)
                    except Exception:
                        jf_obj = {}

                ap_id = (
                    car_data.get("apModelId")
                    or parsed.get("ap_model_id")
                    or (jf_obj.get("apmodelid") if isinstance(jf_obj, dict) else "")
                    or (jf_obj.get("apModelId") if isinstance(jf_obj, dict) else "")
                    or ""
                )
                rel_d = car_data.get("firstDate") or parsed.get("release_date") or (jf_obj.get("firstdate") if isinstance(jf_obj, dict) else "") or ""
                n_p = (
                    parsed.get("new_car_price")
                    or car_data.get("carMakePrice")
                    or (jf_obj.get("carmakeprice") if isinstance(jf_obj, dict) else 0)
                    or 0
                )
                has_ap = bool(str(ap_id).strip())
                has_rel = bool(str(rel_d).strip())
                has_np = bool(n_p and n_p > 0)

                if has_ap and has_np:
                    try:
                        mp_res = cls.fetch_daa_market_price(
                            ap_model_id=ap_id,
                            release_date=rel_d,
                            mileage=mileage,
                            new_price=n_p,
                            car_no=car_no
                        )
                        if mp_res and mp_res.get("success"):
                            r_man = mp_res.get("retail_price_man", 0)
                            parsed["chaolma_retail_price"] = r_man
                            t_ret_done = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                            print(f"[{t_ret_done}] 💰 [차얼마 기준소매가 획득] {r_man}만", flush=True)
                            res_type = "success" if r_man > 0 else "retail_zero"
                            cls._log_retail_debug("신규", has_ap, has_rel, has_np, res_type, r_man)
                        else:
                            msg = (mp_res or {}).get("message", "")
                            res_type = "unsuccessful" if "응답 오류" in msg or "상태코드" in msg else "api_error"
                            cls._log_retail_debug("신규", has_ap, has_rel, has_np, res_type, 0)
                    except Exception:
                        cls._log_retail_debug("신규", has_ap, has_rel, has_np, "api_error", 0)
                else:
                    cls._log_retail_debug("신규", has_ap, has_rel, has_np, "ap_missing" if not has_ap else "new_price_missing", 0)
            except Exception:
                pass

            _chaolma_file_cache.set(car_no, {
                "timestamp": now,
                "data": parsed
            })
        return parsed

    @classmethod
    def fetch_car_info(cls, car_no: str, mileage: int = 50000, branch_code: str = "00244") -> Dict[str, Any]:
        """
        차량번호로 차얼마에서 신차 기본가, 옵션 정보, 잔가율 등을 실시간 조회
        """
        car_no = str(car_no).replace(" ", "").strip()
        if not car_no:
            return {"success": False, "message": "차량번호가 입력되지 않았습니다."}

        # 1. 1차 raw API 호출 (캐시 확인 포함)
        raw_res = cls.fetch_carmart_raw(car_no, mileage=mileage)
        if not raw_res.get("success"):
            return raw_res
        if raw_res.get("is_cached"):
            cached_data = raw_res.get("cached_result")
            # 기준소매가 보충 로직
            cur_retail = cached_data.get("chaolma_retail_price") or 0
            if cur_retail <= 0:
                ap_id = cached_data.get("ap_model_id") or cached_data.get("apModelId") or ""
                rel_d = cached_data.get("release_date") or ""
                n_p = cached_data.get("new_car_price") or 0
                if ap_id and n_p > 0:
                    try:
                        mp_res = cls.fetch_daa_market_price(
                            ap_model_id=ap_id,
                            release_date=rel_d,
                            mileage=mileage,
                            new_price=n_p,
                            car_no=car_no
                        )
                        if mp_res and mp_res.get("success"):
                            cached_data["chaolma_retail_price"] = mp_res.get("retail_price_man", 0)
                    except Exception:
                        pass
            return cached_data

        # 2. 2차 후속 정보 결합
        car_data = raw_res.get("car_data")
        return cls.complete_car_info_enrichment(car_data, car_no, mileage=mileage)

    @classmethod
    def parse_carmart_json(
        cls,
        c_data: Dict[str, Any],
        car_no: str,
        origin_doc: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        getCarMartData JSON 응답을 정형화된 시세 분석 데이터로 변환
        """
        # 1. 원시 JSON 텍스트 파싱
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

        # 2. 기본 출고가 및 총 신차가
        new_car_price = int(c_data.get("carMakePrice") or jf.get("carmakeprice") or 0)
        base_car_price = int(jf.get("newprice") or 0)

        # 3. 연식 및 최초등록일 추출
        rel_date = c_data.get("firstDate") or jf.get("firstdate") or ""
        m_year = str(c_data.get("year") or jf.get("year") or "").replace("년", "").strip()

        reg_ym = None
        if rel_date:
            m_ym = re.search(r"(\d{4})[^\d]?(\d{1,2})", str(rel_date).strip())
            if m_ym:
                y_str = m_ym.group(1)[-2:]
                m_int = int(m_ym.group(2))
                if 1 <= m_int <= 12:
                    reg_ym = f"{y_str}-{m_int:02d}"

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

        # 4. 모델 및 등급 정보
        maker = c_data.get("makerName") or jf.get("makername") or ""
        model_name = c_data.get("modelName") or jf.get("modelname") or ""
        model_detail = c_data.get("modelDetailName") or ""
        grade_name = c_data.get("gradeName") or jf.get("seriesname1") or ""
        grade_detail = c_data.get("gradeDetailName") or jf.get("seriesname") or ""

        # 승차정원(seating_capacity) 확인: origin_doc 전달값 우선, 없을 시 c_data 내 origin_doc 확인
        seating_cap = 0
        if origin_doc and isinstance(origin_doc, dict):
            seating_cap = origin_doc.get("seating_capacity") or 0
        if not seating_cap and isinstance(c_data.get("origin_doc"), dict):
            seating_cap = c_data["origin_doc"].get("seating_capacity") or 0

        # [인승 공통 보정]: 등급 문자열에 인승(\d+인승)이 없고 origin_doc.seating_capacity > 0이면 등급 끝에 "{N}인승" 추가
        if seating_cap > 0 and not re.search(r'\d+인승', f"{grade_name} {grade_detail}"):
            if grade_detail:
                grade_detail = f"{grade_detail} {seating_cap}인승".strip()
            elif grade_name:
                grade_name = f"{grade_name} {seating_cap}인승".strip()

        trim_name = grade_detail or model_detail or ""

        # 5. 카탈로그 데이터 로드 (V2 새 책 조회 1순위)
        catalog_data = None
        target_car = model_detail or model_name
        target_year = m_year or reg_year or str(car_yr)
        full_grade = f"{grade_name} {grade_detail}".strip()
        if target_car and full_grade:
            try:
                from services.catalog_by_source_service import get_pilot_catalog_spec
                v2_spec = get_pilot_catalog_spec(source="danawa", car_name=target_car, year=target_year, grade=full_grade)
                if v2_spec and v2_spec.get("found"):
                    catalog_data = v2_spec.get("options") or {}
            except Exception:
                catalog_data = None

        # 6. 차얼마 API 제공 선택 옵션 사전 (원가 매핑용)
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

        # 7. 실제 장착된 옵션 목록 파싱 (단일 가격 규칙 적용)
        installed_opts_raw = jf.get("optlist") or c_data.get("optList") or []

        resolved_opts = []
        total_opt_price = 0

        for io in installed_opts_raw:
            name = str(io.get("name", "")).strip()
            if not name:
                continue

            raw_p = io.get("price")
            raw_p_val = 0
            if raw_p is not None:
                try:
                    raw_p_val = int(str(raw_p).replace(",", "").strip() or 0)
                except ValueError:
                    raw_p_val = 0

            # 4단계 단일 가격 규칙 (OptionItem 생성)
            opt_item = resolve_option_item(
                raw_name=name,
                raw_price=raw_p_val,
                catalog_data=catalog_data,
                price_by_name=price_by_name
            )
            resolved_opts.append(opt_item)
            total_opt_price += opt_item["price"]

        # 8. 출고가 - 기본가 차액 및 미분류 잔액 계산 (차액 덤터기 완전 제거)
        diff_price = max(0, new_car_price - base_car_price)
        unclassified_balance = max(0, diff_price - total_opt_price)

        # 신차가 / 기본가 상호 보완
        if base_car_price == 0 and new_car_price > 0:
            base_car_price = max(0, new_car_price - total_opt_price)
        if new_car_price == 0 and base_car_price > 0:
            new_car_price = base_car_price + total_opt_price

        # 9. 연식별 옵션 감가율 적용
        deprec_result = cls.calculate_option_depreciation(
            resolved_opts,
            release_date=rel_date,
            year=str(car_yr)
        )

        return {
            "success": True,
            "car_no": car_no,
            "ap_model_id": (
                c_data.get("apModelId")
                or (jf.get("apmodelid") if isinstance(jf, dict) else "")
                or (jf.get("apModelId") if isinstance(jf, dict) else "")
                or ""
            ),
            "chaolma_retail_price": 0,
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
            **( {"reg_ym": reg_ym} if reg_ym else {} ),
            "color": c_data.get("color") or jf.get("color") or "",
            "fuel": c_data.get("fuel") or jf.get("fuel") or "",
            "transmission": c_data.get("gearBox") or jf.get("gearbox") or "오토",
            "new_car_price": new_car_price,
            "base_car_price": base_car_price,
            "options": deprec_result["options"],
            "total_option_price": total_opt_price,
            "total_option_price_man": round(total_opt_price / 10000),
            "unclassified_balance": unclassified_balance,
            "unclassified_balance_man": round(unclassified_balance / 10000),
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
        parsed = False

        if release_date:
            try:
                raw_d = str(release_date).strip()
                raw_d = raw_d.replace(".", "-").replace("/", "-")
                date_clean = re.sub(r"[^\d-]", "", raw_d)

                dt = None
                m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", date_clean)
                if m:
                    dt = datetime.strptime(f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}", "%Y-%m-%d")
                else:
                    digits = re.sub(r"[^\d]", "", raw_d)
                    if len(digits) == 8:
                        dt = datetime.strptime(f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}", "%Y-%m-%d")

                if dt:
                    age_years = (datetime.now() - dt).days / 365.25
                    parsed = True
            except Exception:
                parsed = False

        if not parsed and year:
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

    @classmethod
    def parse_carhistory_xml(cls, xml_str: str, car_no: str) -> Dict[str, Any]:
        """
        오토플러스 getCarHistory 응답의 보험개발원 XML을 정형화된 JSON 딕셔너리로 변환
        """
        if not xml_str:
            return {"success": False, "message": "카히스토리 XML 데이터가 없습니다."}

        try:
            # XML 파싱
            root = ET.fromstring(xml_str.strip())

            def get_text(tag: str, default: str = "") -> str:
                el = root.find(tag)
                return el.text.strip() if (el is not None and el.text) else default

            def get_int(tag: str, default: int = 0) -> int:
                val = get_text(tag)
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return default

            # 1. 소유자 변경 및 번호 변경
            plate_change_count = get_int("r201", 0)
            owner_changed_count = get_int("r204", 0)
            is_single_owner = (owner_changed_count == 0)

            # 2. 특수 용도 이력 (영업용, 관용, 대여/렌트)
            is_business = (get_text("r301", "N") == "Y")
            is_government = (get_text("r302", "N") == "Y")
            has_rent_history = (get_text("r303", "N") == "Y")

            # 3. 사고 건수 및 금액
            # r401: 카히스토리 내차 피해 건수 공식 요약 (r501은 r502 상세목록 크기이므로 중복 합산 금지)
            r401_count = get_int("r401", 0)
            r501_count = get_int("r501", 0)
            my_acc_count = r401_count if r401_count > 0 else r501_count

            # r402: 카히스토리 내차 피해 공식 보험금 지급총액 요약
            # (주의: r502-03 총 수리비 견적을 여기에 또 합산하면 보험금+수리비 2배 중복 왜곡 발생)
            r402_cost = get_int("r402", 0)
            my_acc_cost = r402_cost
            my_acc_cost_man = round(my_acc_cost / 10000)

            # r403: 타차가해 건수, r404: 타차가해 총액
            other_acc_count = get_int("r403", 0)
            other_acc_cost = get_int("r404", 0)
            other_acc_cost_man = round(other_acc_cost / 10000)

            # r405: 전손, r407: 침수, r409: 도난
            total_loss_count = get_int("r405", 0)
            flooded_count = get_int("r407", 0)
            stolen_count = get_int("r409", 0)

            # 4. 보험 미가입 기간
            uninsured_period = get_text("r511-01", "")

            # 5. 주행거리 기록 (보험사/검사소)
            mileage_records = []
            r602 = root.find("r602")
            if r602 is not None:
                for e in r602.findall("e"):
                    d = e.find("r602-01")
                    src = e.find("r602-02")
                    m = e.find("r602-03")
                    if m is not None and m.text:
                        try:
                            mileage_records.append({
                                "date": d.text.strip() if (d is not None and d.text) else "",
                                "source": src.text.strip() if (src is not None and src.text) else "",
                                "mileage": int(float(m.text.strip()))
                            })
                        except Exception:
                            pass

            # 6. 내차피해/타차가해 상세 수리비 이력 분해 및 탈착(r502-20)/도장(r502-21) 부위 매핑
            CARMAP_PARTS_DICT = {
                "01": "앞범퍼", "02": "뒤범퍼", "03": "보닛", "04": "트렁크리드",
                "05": "백도어", "06": "앞도어(좌)", "07": "앞도어(우)", "08": "뒷도어(좌)",
                "09": "뒷도어(우)", "10": "앞펜더(좌)", "11": "앞펜더(우)", "12": "뒤펜더(좌)",
                "13": "뒤펜더(우)", "14": "앞유리", "15": "선루프", "16": "루프",
                "17": "슬라이딩도어(좌)", "18": "슬라이딩도어(우)", "19": "뒷유리",
                "20": "라디에이터 그릴", "21": "헤드램프(좌)", "22": "헤드램프(우)",
                "23": "리어컴비네이션램프(좌)", "24": "리어컴비네이션램프(우)",
                "25": "사이드스텝(좌)", "26": "사이드스텝(우)", "27": "센터필러(좌)",
                "28": "센터필러(우)"
            }

            accident_histories = []
            r502 = root.find("r502")
            if r502 is not None:
                for e in r502.findall("e"):
                    acc_date = e.find("r502-02")
                    tot = e.find("r502-03")
                    parts = e.find("r502-06")
                    labor = e.find("r502-07")
                    paint = e.find("r502-08")
                    payout = e.find("r502-15")
                    cat_code = e.find("r502-01")
                    my_ins = e.find("r502-09")
                    oth_ins = e.find("r502-10")
                    oth_payout = e.find("r502-14")
                    part_desc = e.find("r502-16")
                    dismantle_tag = e.find("r502-20")
                    paint_tag = e.find("r502-21")

                    cat_val = cat_code.text.strip() if (cat_code is not None and cat_code.text) else ""
                    my_ins_val = int(float(my_ins.text.strip())) if (my_ins is not None and my_ins.text) else 0
                    oth_ins_val = int(float(oth_ins.text.strip())) if (oth_ins is not None and oth_ins.text) else 0
                    oth_payout_val = int(float(oth_payout.text.strip())) if (oth_payout is not None and oth_payout.text) else 0
                    repair_details = part_desc.text.strip() if (part_desc is not None and part_desc.text) else ""
                    dismantle_codes = dismantle_tag.text.strip() if (dismantle_tag is not None and dismantle_tag.text) else ""
                    paint_codes = paint_tag.text.strip() if (paint_tag is not None and paint_tag.text) else ""

                    dismantle_parts = [CARMAP_PARTS_DICT.get(c.strip(), c.strip()) for c in dismantle_codes.split(",") if c.strip()]
                    paint_parts = [CARMAP_PARTS_DICT.get(c.strip(), c.strip()) for c in paint_codes.split(",") if c.strip()]

                    # 판정: r502-01이 '3'이거나, 상대보험 지급액이 있고 내차보험 지급액이 0인 경우 '타차가해'
                    is_other = (cat_val == "3") or (oth_ins_val > 0 and my_ins_val == 0) or (oth_payout_val > 0 and my_ins_val == 0)
                    acc_type = "other" if is_other else "my"
                    acc_type_label = "타차가해" if is_other else "내차피해"

                    accident_histories.append({
                        "date": acc_date.text.strip() if (acc_date is not None and acc_date.text) else "",
                        "repair_cost": int(float(tot.text.strip())) if (tot is not None and tot.text) else 0,
                        "parts_cost": int(float(parts.text.strip())) if (parts is not None and parts.text) else 0,
                        "labor_cost": int(float(labor.text.strip())) if (labor is not None and labor.text) else 0,
                        "paint_cost": int(float(paint.text.strip())) if (paint is not None and paint.text) else 0,
                        "insurance_paid": int(float(payout.text.strip())) if (payout is not None and payout.text) else 0,
                        "acc_type": acc_type,
                        "acc_type_label": acc_type_label,
                        "repair_details": repair_details,
                        "dismantle_codes": dismantle_codes,
                        "paint_codes": paint_codes,
                        "dismantle_parts": dismantle_parts,
                        "paint_parts": paint_parts,
                    })

            # 상세 이력 기반 fallback 보정 및 수리비 총액 산출
            if my_acc_count == 0 and len(accident_histories) > 0:
                my_acc_count = len(accident_histories)
            if my_acc_cost == 0 and len(accident_histories) > 0:
                calc_paid = sum(item.get("insurance_paid", 0) for item in accident_histories)
                my_acc_cost = calc_paid if calc_paid > 0 else sum(item.get("repair_cost", 0) for item in accident_histories)
                my_acc_cost_man = round(my_acc_cost / 10000)

            total_repair_cost = sum(item.get("repair_cost", 0) for item in accident_histories)
            total_dismantle_count = sum(len(item.get("dismantle_parts", [])) for item in accident_histories)
            total_paint_count = sum(len(item.get("paint_parts", [])) for item in accident_histories)

            # 최초등록일 포맷 (20110930 -> 2011-09-30)
            raw_reg_date = get_text("r105", "")
            formatted_reg_date = ""
            if len(raw_reg_date) == 8:
                formatted_reg_date = f"{raw_reg_date[:4]}-{raw_reg_date[4:6]}-{raw_reg_date[6:]}"

            # 카히스토리 시세 범위 파싱 (만원 단위, r701 텍스트: 예 "713~953")
            raw_mpr = get_text("r701", "")
            m_min, m_max, m_avg = 0, 0, 0
            if raw_mpr:
                nums = re.findall(r'\d+', str(raw_mpr).replace(',', ''))
                if len(nums) >= 2:
                    try:
                        m_min = int(nums[0])
                        m_max = int(nums[1])
                        m_avg = int(round((m_min + m_max) / 2.0))
                    except (ValueError, TypeError):
                        m_min, m_max, m_avg = 0, 0, 0

            return {
                "success": True,
                "car_no": car_no or get_text("r002", ""),
                "owner_changed_count": owner_changed_count,
                "is_single_owner": is_single_owner,
                "plate_change_count": plate_change_count,
                "has_rent_history": has_rent_history,
                "is_business": is_business,
                "is_government": is_government,
                "my_car_accident_count": my_acc_count,
                "my_car_accident_cost": my_acc_cost,
                "my_car_accident_cost_man": my_acc_cost_man,
                "total_repair_cost": total_repair_cost,
                "total_dismantle_count": total_dismantle_count,
                "total_paint_count": total_paint_count,
                "other_car_accident_count": other_acc_count,
                "other_car_accident_cost": other_acc_cost,
                "other_car_accident_cost_man": other_acc_cost_man,
                "total_loss_count": total_loss_count,
                "flooded_count": flooded_count,
                "stolen_count": stolen_count,
                "uninsured_period": uninsured_period,
                "mileage_records": mileage_records,
                "accident_histories": accident_histories,
                "market_price_range": raw_mpr,
                "market_price_min": m_min,
                "market_price_max": m_max,
                "market_price_avg": m_avg,
                "first_reg_date": formatted_reg_date or raw_reg_date
            }
        except Exception as e:
            return {"success": False, "message": f"카히스토리 XML 파싱 오류: {str(e)}"}

    @classmethod
    def fetch_car_history(cls, car_no: str) -> Dict[str, Any]:
        """
        차얼마(오토플러스) getCarHistory API를 호출하여 보험개발원 카히스토리 원본을 실시간 조회
        """
        clean_no = str(car_no).replace(" ", "").strip()
        if not clean_no:
            return {"success": False, "message": "차량번호가 입력되지 않았습니다."}

        cookie = cls.get_cookie()
        if not cookie:
            return {"success": False, "message": "차얼마 로그인 쿠키가 없습니다."}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
            "Cookie": cookie,
            "X-Requested-With": "XMLHttpRequest",
            "X-Ajax-call": "true",
            "Referer": f"https://purchase.autoplus.co.kr/purchase/PCVP010001?brCd=00244&tsKey=&seriesNo=&carNumber={urllib.parse.quote(clean_no)}&carNavi=50000",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        data_payload = {
            "carNumber": clean_no
        }

        try:
            resp = requests.post(cls.CAR_HISTORY_URL, data=data_payload, headers=headers, timeout=10)
            resp_text = resp.content.decode("utf-8", errors="ignore")

            # 로그인 만료 체크
            if "/login/login.do" in resp_text or "frm-login" in resp_text or ("<title>차얼마" in resp_text and not resp_text.strip().startswith("{")):
                return {
                    "success": False,
                    "message": "차얼마 로그인 세션이 만료되었습니다.",
                    "need_login": True
                }

            if resp.status_code == 200:
                try:
                    res_json = json.loads(resp_text)
                except Exception:
                    return {"success": False, "message": "카히스토리 서버 응답 JSON 파싱 실패"}

                header = res_json.get("header", {})
                if not header.get("isSuccessful"):
                    msg = res_json.get("msg") or header.get("resultMessage") or "카히스토리 조회 실패"
                    return {"success": False, "message": f"카히스토리 조회 안내: {msg}"}

                xml_data = res_json.get("data")
                if not xml_data:
                    return {"success": False, "message": "카히스토리 원본 데이터가 존재하지 않습니다."}

                return cls.parse_carhistory_xml(xml_data, clean_no)
            else:
                return {"success": False, "message": f"카히스토리 서버 오류 (상태코드: {resp.status_code})"}
        except requests.exceptions.Timeout:
            return {"success": False, "message": "카히스토리 서버 응답 시간 초과 (10초)"}
        except Exception as e:
            return {"success": False, "message": f"카히스토리 조회 중 오류: {str(e)}"}

    @classmethod
    def fetch_car_origin_doc(cls, car_no: str) -> Dict[str, Any]:
        """
        차얼마(오토플러스) getCarOriginDocData API를 호출하여 국토교통부 자동차등록원부 원본 조회
        - 압류 건수(SEIZR_CO), 저당 건수(MRTG_CO), 구조변경(STMD_CO), 정기검사 유효기간(INSPT_VALID_PD_ENDDE),
          최종명의이전일(LAST_REGIST_DE), 검사소 주행거리(TRVL_DSTNC), 부활차 여부(RESRECT_AT) 등
        """
        clean_no = str(car_no).replace(" ", "").strip()
        if not clean_no:
            return {"success": False, "message": "차량번호가 입력되지 않았습니다."}

        cookie = cls.get_cookie()
        if not cookie:
            return {"success": False, "message": "차얼마 로그인 쿠키가 없습니다."}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
            "Cookie": cookie,
            "X-Requested-With": "XMLHttpRequest",
            "X-Ajax-call": "true",
            "Referer": f"https://purchase.autoplus.co.kr/purchase/PCVP010001?brCd=00244&tsKey=&seriesNo=&carNumber={urllib.parse.quote(clean_no)}&carNavi=50000",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        data_payload = {
            "carNumber": clean_no
        }

        try:
            resp = requests.post(cls.ORIGIN_DOC_URL, data=data_payload, headers=headers, timeout=10)
            resp_text = resp.content.decode("utf-8", errors="ignore")

            if "/login/login.do" in resp_text or "frm-login" in resp_text:
                return {"success": False, "message": "차얼마 세션 만료", "need_login": True}

            if resp.status_code == 200:
                res_json = json.loads(resp_text)
                header = res_json.get("header", {})
                if not header.get("isSuccessful"):
                    msg = res_json.get("msg") or header.get("resultMessage") or "등록원부 조회 실패"
                    return {"success": False, "message": f"등록원부 조회 안내: {msg}"}

                d = res_json.get("data")
                if not d:
                    return {"success": False, "message": "등록원부 데이터가 존재하지 않습니다."}

                def to_int(v, default=0):
                    try:
                        return int(v) if v is not None else default
                    except (ValueError, TypeError):
                        return default

                # 날짜 포맷팅 (20260923 -> 2026-09-23)
                last_reg = str(d.get("LAST_REGIST_DE") or "").strip()
                if len(last_reg) == 8 and last_reg.isdigit():
                    last_reg = f"{last_reg[:4]}-{last_reg[4:6]}-{last_reg[6:]}"

                return {
                    "success": True,
                    "car_no": clean_no,
                    "seizure_count": to_int(d.get("SEIZR_CO"), 0),            # 압류 건수
                    "mortgage_count": to_int(d.get("MRTG_CO"), 0),           # 저당 건수
                    "tuning_count": to_int(d.get("STMD_CO"), 0),             # 구조변경 건수
                    "inspection_valid_end": str(d.get("INSPT_VALID_PD_ENDDE") or "").strip(), # 정기검사 만료일
                    "inspection_valid_start": str(d.get("INSPT_VALID_PD_BGNDE") or "").strip(),
                    "last_regist_date": last_reg,                            # 최종 명의이전일
                    "first_regist_date": str(d.get("FRST_REGIST_DE") or "").strip(), # 최초 등록일
                    "inspection_mileage": to_int(d.get("TRVL_DSTNC"), 0),    # 검사소 실측 주행거리
                    "is_resurrected": to_int(d.get("RESRECT_AT"), 0) > 0,    # 부활차 여부
                    "is_cbu": to_int(d.get("CBU_AT"), 0) > 0,                # 수입완성차 여부
                    "engine_type": str(d.get("MTRS_FOM_NM") or "").strip(),  # 엔진 형식 (예: D4HB)
                    "car_form": str(d.get("FOM_NM") or "").strip(),          # 차량 형식 (예: YP9ABE-S-9)
                    "seating_capacity": to_int(d.get("TKCAR_PSCAP_CO"), 0),  # 승차정원 (예: 7)
                    "plate_issue_ext": str(d.get("EXTRL_NMPL_ISSU_YN") or "").strip(),
                    "raw_doc": d
                }
            else:
                return {"success": False, "message": f"등록원부 서버 오류 (상태코드: {resp.status_code})"}
        except requests.exceptions.Timeout:
            return {"success": False, "message": "등록원부 서버 응답 시간 초과 (10초)"}
        except Exception as e:
            return {"success": False, "message": f"등록원부 조회 중 오류: {str(e)}"}

    @classmethod
    def _log_retail_debug(
        cls,
        path_type: str,
        has_ap_id: bool,
        has_release_date: bool,
        has_new_price: bool,
        result: str,
        retail_man: int = 0
    ):
        """
        차얼마 기준소매가 분기 진단 로깅 (data/chaolma_retail_debug.log)
        - 보안 준수: 쿠키, 차량번호, 차대번호, apModelId 값 자체, API 응답 원문 절대 기록 금지
        - 최근 200줄 유지 (회전 로그)
        - 실패해도 조회는 정상 진행 (fail-safe)
        """
        try:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "chaolma_retail_debug.log")

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = (
                f"[{now_str}] path={path_type} "
                f"ap_id_exists={str(has_ap_id).lower()} "
                f"release_date_exists={str(has_release_date).lower()} "
                f"new_price_exists={str(has_new_price).lower()} "
                f"result={result} "
                f"retail_man={retail_man}\n"
            )

            lines = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except Exception:
                    lines = []

            lines.append(line)
            if len(lines) > 200:
                lines = lines[-200:]

            with open(log_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception:
            pass

    @classmethod
    def fetch_daa_market_price(
        cls,
        ap_model_id: Any,
        release_date: str,
        mileage: int,
        new_price: Any,
        car_no: str = ""
    ) -> Dict[str, Any]:
        """
        차얼마(오토플러스) getDaaMarketPriceModel API를 호출하여 공식 기준소매가 조회 (참고 지표 전용)
        - 실패하거나 데이터가 없어도 전체 조회를 막지 않고 안전하게 기본값 반환
        """
        if not ap_model_id:
            return {"success": False, "message": "apModelId 누락"}

        cookie = cls.get_cookie()
        if not cookie:
            return {"success": False, "message": "차얼마 로그인 쿠키 없음"}

        clean_no = str(car_no).replace(" ", "").strip()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
            "Cookie": cookie,
            "X-Requested-With": "XMLHttpRequest",
            "X-Ajax-call": "true",
            "Referer": f"https://purchase.autoplus.co.kr/purchase/PCVP010001?brCd=00244&tsKey=&seriesNo=&carNumber={urllib.parse.quote(clean_no)}&carNavi={mileage}",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        data_payload = {
            "apModelId": str(ap_model_id).strip(),
            "releaseDate": str(release_date or "").strip(),
            "carNavi": str(mileage) if mileage > 0 else "50000",
            "newPrice": str(new_price or 0).strip()
        }

        try:
            resp = requests.post(cls.MARKET_PRICE_URL, data=data_payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                res_json = resp.json()
                header = res_json.get("header", {})
                if header.get("isSuccessful"):
                    d = res_json.get("data") or {}
                    raw_retail = d.get("retailPrice")
                    retail_man = 0
                    if raw_retail is not None:
                        try:
                            val_float = float(str(raw_retail).strip())
                            retail_man = int(round(val_float / 10000.0))
                        except (ValueError, TypeError):
                            retail_man = 0

                    return {
                        "success": True,
                        "retail_price_man": retail_man,
                        "raw_retail_price": raw_retail
                    }
            return {"success": False, "message": f"시세 응답 오류 (상태코드: {resp.status_code})"}
        except Exception as e:
            return {"success": False, "message": f"시세 조회 예외 발생: {str(e)}"}


