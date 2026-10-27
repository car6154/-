"""
services/mobile_purchase_service.py
하이오플 모바일 API (https://high.autoplus.co.kr/admin/v1/purchases/estimates) 연동 서비스
- 백엔드에서 직접 모바일 REST API를 호출하여 매입 차량 목록 및 수수료(etcAmt) 추출
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIGH_COOKIE_FILE_PATH = os.path.join(BASE_DIR, "high_cookie.txt")
AUTOPLUS_COOKIE_FILE_PATH = os.path.join(BASE_DIR, "autoplus_cookie.txt")
API_URL = "https://high.autoplus.co.kr/admin/v1/purchases/estimates"
KNOWN_PCS_IDS = [4058, 4017, 4108, 4261, 4100, 4078]
# 4058: 155라7987, 4017: 37다1840, 4108: 01수9643, 4261: 224버2800, 4100: 43노5327, 4078: 337너5231


class MobilePurchaseService:
    @staticmethod
    def get_cookie() -> str:
        """high_cookie.txt (1순위) 또는 autoplus_cookie.txt / 환경변수에서 쿠키 로드"""
        # 1. high.autoplus.co.kr 전용 쿠키 파일 우선
        if os.path.exists(HIGH_COOKIE_FILE_PATH):
            try:
                with open(HIGH_COOKIE_FILE_PATH, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception as e:
                logger.warning(f"[MobilePurchaseService] high_cookie.txt 읽기 실패: {e}")

        # 2. HIGH_COOKIE 환경변수
        env_high = os.environ.get("HIGH_COOKIE", "").strip()
        if env_high:
            return env_high

        # 3. fallback: 기존 autoplus_cookie.txt
        if os.path.exists(AUTOPLUS_COOKIE_FILE_PATH):
            try:
                with open(AUTOPLUS_COOKIE_FILE_PATH, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception as e:
                logger.warning(f"[MobilePurchaseService] autoplus_cookie.txt 읽기 실패: {e}")

        return os.environ.get("AUTOPLUS_COOKIE", "").strip()

    @classmethod
    def get_purchase_list(
        cls,
        manager: str = "kimjh1202",
        start_date: Optional[str] = None,
        page: int = 1,
        size: int = 50
    ) -> Dict[str, Any]:
        """
        하이오플 매입 차량 목록 API 호출 및 정형화된 데이터 반환
        - 날짜 파라미터 없이 담당자(pcsManagerId)만으로 필터링
        - transferDate가 None이어도 carNumber와 etcAmt가 있으면 유효한 차량으로 처리
        반환:
        {
            "success": bool,
            "status_code": int,
            "raw_response": Any,
            "cars": List[Dict[str, Any]],
            "has_etc_amt": bool,
            "message": str
        }
        """
        cookie_str = cls.get_cookie()
        if not cookie_str:
            return {
                "success": False,
                "status_code": 0,
                "is_no_session": True,
                "is_403": False,
                "raw_response": None,
                "cars": [],
                "has_etc_amt": False,
                "message": "오토플러스 모바일 세션 없음: high_cookie.txt 파일이 비어있습니다. high.autoplus.co.kr 로그인이 필요합니다."
            }

        headers = {
            "Cookie": cookie_str,
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Referer": "https://high.autoplus.co.kr/",
            "Origin": "https://high.autoplus.co.kr",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        # 날짜 파라미터 없이 담당자만으로 필터링
        params = {
            "pcsManagerId": manager,
            "page": page,
            "size": size
        }

        try:
            resp = requests.get(API_URL, headers=headers, params=params, timeout=12)
            status_code = resp.status_code

            if status_code != 200:
                is_403 = (status_code == 403)
                err_msg = "high.autoplus.co.kr 모바일 세션 만료(HTTP 403): 모바일 사이트 재로그인이 필요합니다." if is_403 else f"모바일 API 호출 실패 (HTTP {status_code}): {resp.text[:200]}"
                logger.error(f"[MobilePurchaseService] API 응답 에러 HTTP {status_code}: {resp.text[:300]}")
                return {
                    "success": False,
                    "status_code": status_code,
                    "is_no_session": False,
                    "is_403": is_403,
                    "raw_response": resp.text[:1000],
                    "cars": [],
                    "has_etc_amt": False,
                    "message": err_msg
                }

            json_data = resp.json()

            # 응답 구조 분석 (data가 리스트이거나 페이징 객체이거나 루트 리스트인 경우 지원)
            raw_items = []
            if isinstance(json_data, list):
                raw_items = json_data
            elif isinstance(json_data, dict):
                if isinstance(json_data.get("data"), list):
                    raw_items = json_data.get("data")
                elif isinstance(json_data.get("data"), dict) and isinstance(json_data["data"].get("list"), list):
                    raw_items = json_data["data"]["list"]
                elif isinstance(json_data.get("content"), list):
                    raw_items = json_data.get("content")
                elif isinstance(json_data.get("items"), list):
                    raw_items = json_data.get("items")
                elif isinstance(json_data.get("list"), list):
                    raw_items = json_data.get("list")

            parsed_cars = []
            has_etc_amt = False

            for item in raw_items:
                if not isinstance(item, dict):
                    continue

                car_no = (
                    item.get("carNumber") or
                    item.get("carNo") or
                    item.get("vhclNo") or
                    item.get("car_number") or ""
                ).strip()

                car_name = (
                    item.get("carName") or
                    item.get("modelNm") or
                    item.get("vhclNm") or
                    item.get("car_name") or ""
                ).strip()

                buy_price = item.get("finalPcsAmt") or item.get("pcsAmt") or item.get("buyPrice") or 0
                try:
                    buy_price = int(str(buy_price).replace(",", ""))
                except (ValueError, TypeError):
                    buy_price = 0

                etc_amt = item.get("etcAmt")
                if etc_amt is not None:
                    has_etc_amt = True
                    try:
                        etc_amt = int(str(etc_amt).replace(",", ""))
                    except (ValueError, TypeError):
                        etc_amt = 0

                raw_td = (
                    item.get("pcsDt") or
                    item.get("returnDt") or
                    item.get("regDt") or
                    item.get("transferDate")
                )
                transfer_date = str(raw_td).strip() if raw_td else None

                # transferDate가 None이어도 carNumber가 있으면 유효한 차량으로 처리
                if not car_no:
                    continue

                # 판매 완료 여부 판정 (soldYn, status, saleStatus 등)
                sold_yn = (
                    item.get("soldYn") or
                    item.get("sold_yn") or
                    item.get("isSold") or
                    item.get("saleYn") or ""
                )
                sold_yn_str = str(sold_yn).strip().upper() if sold_yn is not None else ""

                status_val = str(
                    item.get("status") or
                    item.get("statusNm") or
                    item.get("saleStatus") or
                    item.get("pcsStatus") or
                    item.get("carStatus") or ""
                ).strip()

                is_sold = (sold_yn_str in ("Y", "YES", "TRUE", "1")) or ("완료" in status_val or status_val == "판매완료")

                list_mileage = None
                for mk in ["carMileage", "mileage", "vhclMileage", "accumMileage", "drivingDistance", "주행거리", "dvrDsc", "useKm", "runKm", "distance"]:
                    if mk in item and item[mk] is not None and str(item[mk]).strip() not in ("", "null", "none"):
                        digits = re.sub(r"[^0-9]", "", str(item[mk]))
                        if digits:
                            try:
                                lm_val = int(digits)
                                if lm_val > 0:
                                    list_mileage = lm_val
                                    break
                            except (ValueError, TypeError):
                                pass

                ap_car_id_list = item.get("apCarId") or item.get("carId") or None
                if ap_car_id_list is not None:
                    ap_car_id_list = str(ap_car_id_list).strip()
                    if ap_car_id_list.lower() in ("", "null", "none"):
                        ap_car_id_list = None

                parsed_cars.append({
                    "carNumber": car_no,
                    "carName": car_name,
                    "buyPrice": buy_price,
                    "targetSaleAmt": target_sale_amt,
                    "apCarId": ap_car_id_list,
                    "mileage": list_mileage,
                    "etcAmt": etc_amt,
                    "transferDate": transfer_date,
                    "manager": manager,
                    "soldYn": sold_yn_str,
                    "status": status_val,
                    "isSold": is_sold,
                    "raw": item
                })

            return {
                "success": True,
                "status_code": 200,
                "raw_response": json_data,
                "cars": parsed_cars,
                "has_etc_amt": has_etc_amt,
                "total_count": len(parsed_cars),
                "message": f"성공적으로 {len(parsed_cars)}대 매입 차량을 조회했습니다."
            }

        except Exception as e:
            logger.exception(f"[MobilePurchaseService] 요청 예외 발생: {e}")
            return {
                "success": False,
                "status_code": 500,
                "raw_response": None,
                "cars": [],
                "has_etc_amt": False,
                "message": f"요청 예외: {str(e)}"
            }

    @classmethod
    def get_purchase_details(cls, pcs_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        상세 API (GET /admin/v1/purchases/estimates/{id})를 직접 호출하여
        각 차량의 carNumber, etcAmt, finalPcsAmt, pcsManagerName 추출
        - pcsManagerId가 kimjh1202인지 확인
        """
        if pcs_ids is None:
            pcs_ids = KNOWN_PCS_IDS

        cookie_str = cls.get_cookie()
        if not cookie_str:
            return {
                "success": False,
                "status_code": 0,
                "is_no_session": True,
                "is_403": False,
                "cars": [],
                "message": "오토플러스 모바일 세션 없음: high_cookie.txt 파일이 비어있습니다. high.autoplus.co.kr 로그인이 필요합니다."
            }

        headers = {
            "Cookie": cookie_str,
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Referer": "https://high.autoplus.co.kr/",
            "Origin": "https://high.autoplus.co.kr",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        detailed_cars = []
        has_403 = False
        last_status = 200

        for pcs_id in pcs_ids:
            url = f"{API_URL}/{pcs_id}"
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                last_status = resp.status_code
                if resp.status_code != 200:
                    if resp.status_code == 403:
                        has_403 = True
                    logger.warning(f"[MobilePurchaseService] pcs_id {pcs_id} 상세 조회 실패 HTTP {resp.status_code}")
                    continue

                res_json = resp.json()
                data = res_json.get("data") if isinstance(res_json, dict) and "data" in res_json else res_json
                if not isinstance(data, dict):
                    continue

                # pcsManagerId 확인 (kimjh1202)
                manager_id = str(data.get("pcsManagerId") or data.get("managerId") or "").strip()
                manager_name = str(data.get("pcsManagerName") or data.get("managerNm") or data.get("managerName") or "").strip()
                if manager_id and "kimjh" not in manager_id.lower() and "김재현" not in manager_name:
                    logger.info(f"[MobilePurchaseService] pcs_id {pcs_id} 담당자 불일치 ({manager_id}, {manager_name}) -> 제외")
                    continue

                car_no = str(data.get("carNumber") or data.get("carNo") or "").replace(" ", "").strip()
                car_name = str(data.get("carName") or data.get("modelNm") or "").strip()

                buy_price = data.get("finalPcsAmt") or data.get("pcsAmt") or data.get("buyPrice") or 0
                try:
                    buy_price = int(str(buy_price).replace(",", ""))
                except (ValueError, TypeError):
                    buy_price = 0

                raw_etc = data.get("etcAmt")
                etc_amt = None
                if raw_etc is not None and str(raw_etc).strip() != "" and str(raw_etc).strip().lower() != "null":
                    try:
                        etc_amt = int(str(raw_etc).replace(",", ""))
                    except (ValueError, TypeError):
                        etc_amt = None

                transfer_date = str(data.get("pcsDt") or data.get("returnDt") or data.get("transferDate") or "").strip() or None

                raw_target_sale = data.get("targetSaleAmt") or data.get("saleAmt")
                target_sale_amt = None
                if raw_target_sale is not None and str(raw_target_sale).strip() != "" and str(raw_target_sale).strip().lower() != "null":
                    try:
                        target_sale_amt = int(str(raw_target_sale).replace(",", ""))
                    except (ValueError, TypeError):
                        target_sale_amt = None

                ap_car_id = data.get("apCarId") or data.get("carId") or None
                if ap_car_id is not None:
                    ap_car_id = str(ap_car_id).strip()
                    if ap_car_id.lower() in ("", "null", "none"):
                        ap_car_id = None

                # 주행거리 추출: 콤마·공백·단위 문자 제거 후 정규식 숫자만 추출 (0 초과)
                extracted_mileage = None
                matched_mileage_key = None
                mileage_candidates = ["carMileage", "mileage", "vhclMileage", "accumMileage", "drivingDistance", "주행거리", "dvrDsc", "useKm", "runKm", "distance"]
                for mk in mileage_candidates:
                    if mk in data and data[mk] is not None and str(data[mk]).strip() not in ("", "null", "none"):
                        digits = re.sub(r"[^0-9]", "", str(data[mk]))
                        if digits:
                            try:
                                m_val = int(digits)
                                if m_val > 0:
                                    extracted_mileage = m_val
                                    matched_mileage_key = mk
                                    break
                            except (ValueError, TypeError):
                                pass

                if matched_mileage_key:
                    logger.info(f"[MobilePurchaseService] pcs_id {pcs_id}: 주행거리 추출 성공 (키='{matched_mileage_key}', 값={extracted_mileage}km)")
                    print(f"[MobilePurchaseService] pcs_id {pcs_id}: 주행거리 추출 성공 (키='{matched_mileage_key}', 값={extracted_mileage}km)", flush=True)
                else:
                    raw_cm = data.get("carMileage")
                    logger.info(f"[MobilePurchaseService] pcs_id {pcs_id}: 주행거리 키 미발견 (carMileage 원본={repr(raw_cm)}, 타입={type(raw_cm).__name__}, 원본 data 키: {list(data.keys())})")
                    print(f"[MobilePurchaseService] pcs_id {pcs_id}: 주행거리 키 미발견 (carMileage 원본={repr(raw_cm)}, 타입={type(raw_cm).__name__}, 원본 data 키: {list(data.keys())})", flush=True)

                car_dict = {
                    "pcsId": pcs_id,
                    "carNumber": car_no,
                    "carName": car_name,
                    "buyPrice": buy_price,
                    "targetSaleAmt": target_sale_amt,
                    "apCarId": ap_car_id,
                    "mileage": extracted_mileage,
                    "etcAmt": etc_amt,
                    "transferDate": transfer_date,
                    "manager": manager_name or "김재현",
                    "managerId": manager_id,
                    "raw": data
                }
                detailed_cars.append(car_dict)
                print(f"[MobilePurchaseService] pcs_id {pcs_id}: 차량={car_no}, etcAmt={etc_amt}, buyPrice={buy_price}, targetSaleAmt={target_sale_amt}, apCarId={ap_car_id}, mileage={extracted_mileage}, 매니저={manager_name}({manager_id})", flush=True)
            except Exception as e:
                logger.error(f"[MobilePurchaseService] pcs_id {pcs_id} 상세 호출 예외: {e}")

        success = bool(detailed_cars)
        if success:
            msg = f"성공적으로 {len(detailed_cars)}대 차량 상세 정보를 조회했습니다."
        elif has_403:
            msg = "high.autoplus.co.kr 모바일 세션 만료(HTTP 403): 모바일 사이트 재로그인이 필요합니다."
        else:
            msg = f"차량 상세 정보를 조회하지 못했습니다. (HTTP {last_status})"

        return {
            "success": success,
            "status_code": 403 if (not success and has_403) else (200 if success else last_status),
            "is_no_session": False,
            "is_403": has_403,
            "cars": detailed_cars,
            "total_count": len(detailed_cars),
            "message": msg
        }
