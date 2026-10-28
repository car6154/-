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

from services.cookie_server import get_current_autoplus_cookie

# 메모리 캐시 (차량번호 -> {timestamp, data}) : 30분간 유효
_CHAOLMA_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 1800  # 30분


def norm_opt_name(s: str) -> str:
    """옵션명 정규화 (유니코드 특수 로마자, 띄어쓰기, 특수문자, 패키지 제거)"""
    if not s:
        return ""
    # 유니코드 로마자 기호 (Ⅰ, Ⅱ, Ⅲ, Ⅳ, ⅰ, ⅱ, ⅲ, ⅳ) 변환
    ROMAN_MAP = {
        'Ⅰ': '1', 'Ⅱ': '2', 'Ⅲ': '3', 'Ⅳ': '4', 'Ⅴ': '5',
        'ⅰ': '1', 'ⅱ': '2', 'ⅲ': '3', 'ⅳ': '4', 'ⅴ': '5',
    }
    for r, d in ROMAN_MAP.items():
        s = s.replace(r, d)
    s = s.lower()
    for ch in [" ", "-", "_", "+", "&", "/", "\"", "'", "(", ")", "[", "]", "·", ","]:
        s = s.replace(ch, "")
    s = s.replace("iii", "3").replace("ii", "2").replace("iv", "4")
    s = s.replace("패키지", "").replace("팩", "")
    return s


def compute_opt_jaccard(s1: str, s2: str) -> float:
    """두 옵션명 간의 바이그램(2글자) 자카드 유사도 계산"""
    n1 = norm_opt_name(s1)
    n2 = norm_opt_name(s2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    # 버전 식별자 불일치 방지 (1 vs 2, 1 vs 3 등)
    digits1 = [c for c in n1 if c.isdigit()]
    digits2 = [c for c in n2 if c.isdigit()]
    if digits1 and digits2 and "".join(digits1) != "".join(digits2):
        return 0.0
    b1 = set(n1[i:i+2] for i in range(len(n1)-1))
    b2 = set(n2[i:i+2] for i in range(len(n2)-1))
    if not b1 or not b2:
        return 0.0
    return len(b1 & b2) / len(b1 | b2)


class ChaolmaService:
    API_URL = "https://purchase.autoplus.co.kr/ajax/getCarMartData"
    HISTORY_URL = "https://purchase.autoplus.co.kr/ajax/getPurchaseInfoList"
    CAR_HISTORY_URL = "https://purchase.autoplus.co.kr/ajax/getCarHistory"
    ORIGIN_DOC_URL = "https://purchase.autoplus.co.kr/ajax/getCarOriginDocData"

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
                    # 1. 카히스토리(보험이력) 자동 결합 조회
                    try:
                        ch_res = cls.fetch_car_history(car_no)
                        if ch_res and ch_res.get("success"):
                            parsed["car_history"] = ch_res
                    except Exception:
                        pass

                    # 2. 국토부 자동차등록원부(압류·저당·구조변경·검사유효기간) 자동 결합 조회
                    try:
                        doc_res = cls.fetch_car_origin_doc(car_no)
                        if doc_res and doc_res.get("success"):
                            parsed["origin_doc"] = doc_res
                    except Exception:
                        pass

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
                # 1) 카탈로그에서 완전/포함 일치 우선 매칭
                for cname, cprice in price_by_name.items():
                    cn_norm = norm_opt_name(cname)
                    if n_norm == cn_norm or (n_norm in cn_norm) or (cn_norm in n_norm):
                        p_val = cprice
                        break

                # 2) 미매칭 시 바이그램 자카드 유사도 매칭 (오타/기호/부가단어 차이 극복)
                if p_val == 0:
                    best_score = 0.0
                    best_price = 0
                    for cname, cprice in price_by_name.items():
                        score = compute_opt_jaccard(name, cname)
                        if score > best_score and score >= 0.45:
                            best_score = score
                            best_price = cprice
                    if best_price > 0:
                        p_val = best_price

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
                "market_price_range": get_text("r701", ""),
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

