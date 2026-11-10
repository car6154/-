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
        manager: str = "김재현",
        start_date: Optional[str] = None,
        page: int = 1,
        size: int = 50,
        max_pages: int = 20
    ) -> Dict[str, Any]:
        """
        [11-06-79] 하이오플 실측 API 규격(searchManagerName·searchPurchaseType=A) 적용
        - 1. 실제 모바일 URL 규격: searchManagerName="김재현", searchPurchaseType="A"(매입완료), start=0, length=50
        - 2. 실측 응답 필드 1:1 완벽 일치:
             * 차종명: boname + gradename
             * 매입일자: purchaseDate
             * 주행거리: carNavi
             * 고유키: pcsNo
             * 매입가: finalPcsAmt / desiredPcsAmt
        - 3. 타인 차(문준영, 김준만 등) 및 가견적 완전 차단
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
                "total_pages_read": 0,
                "message": "오토플러스 모바일 세션 없음: high_cookie.txt 파일이 비어있습니다. high.autoplus.co.kr 로그인이 필요합니다."
            }

        headers = {
            "Cookie": cookie_str,
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Referer": "https://high.autoplus.co.kr/m/purchases/estimates",
            "Origin": "https://high.autoplus.co.kr",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        all_raw_items = []
        cur_page = 1
        total_pages_detected = 1
        last_status = 200

        try:
            while cur_page <= max_pages:
                # [실측 규격] DataTables 규격 start=0, length=50, searchManagerName=김재현, searchPurchaseType=A
                start_offset = (cur_page - 1) * size
                params = {
                    "carNumber": "",
                    "searchStartDate": "",
                    "searchEndDate": "",
                    "modelName": "",
                    "searchManagerName": "김재현",
                    "searchPurchaseType": "A",
                    "start": start_offset,
                    "length": size
                }
                resp = requests.get(API_URL, headers=headers, params=params, timeout=12)
                last_status = resp.status_code

                if resp.status_code != 200:
                    is_403 = (resp.status_code == 403)
                    err_msg = "high.autoplus.co.kr 모바일 세션 만료(HTTP 403): 모바일 사이트 재로그인이 필요합니다." if is_403 else f"모바일 API 호출 실패 (HTTP {resp.status_code}): {resp.text[:200]}"
                    logger.error(f"[MobilePurchaseService] API 응답 에러 HTTP {resp.status_code}: {resp.text[:300]}")
                    if cur_page == 1:
                        return {
                            "success": False,
                            "status_code": resp.status_code,
                            "is_no_session": False,
                            "is_403": is_403,
                            "raw_response": resp.text[:1000],
                            "cars": [],
                            "has_etc_amt": False,
                            "total_pages_read": 0,
                            "message": err_msg
                        }
                    break

                json_data = resp.json()

                # listCount로 전체 페이지 수 산출 (DataTables 규격)
                list_count = json_data.get("listCount")
                if list_count is not None:
                    try:
                        tot = int(list_count)
                        total_pages_detected = max(1, (tot + size - 1) // size)
                    except (ValueError, TypeError):
                        pass

                page_items = []
                if isinstance(json_data, list):
                    page_items = json_data
                elif isinstance(json_data, dict):
                    if isinstance(json_data.get("data"), list):
                        page_items = json_data.get("data")
                    elif isinstance(json_data.get("data"), dict) and isinstance(json_data["data"].get("list"), list):
                        page_items = json_data["data"]["list"]
                    elif isinstance(json_data.get("content"), list):
                        page_items = json_data.get("content")
                    elif isinstance(json_data.get("items"), list):
                        page_items = json_data.get("items")
                    elif isinstance(json_data.get("list"), list):
                        page_items = json_data.get("list")

                if not page_items:
                    break

                all_raw_items.extend(page_items)
                print(f"[MobilePurchaseService] 페이지 {cur_page} 수집 완료: {len(page_items)}건 (누적 {len(all_raw_items)}건, 전체 {list_count or len(all_raw_items)}건)", flush=True)

                if cur_page >= total_pages_detected or len(page_items) < size:
                    break
                cur_page += 1

            parsed_cars = []
            has_etc_amt = False
            filtered_out_other_manager = 0
            filtered_out_estimate_only = 0

            for item in all_raw_items:
                if not isinstance(item, dict):
                    continue

                # ── 1. 담당자 필터 (김재현 / kimjh1202 전담, 타인 차 완전 차단) ──
                mgr_names = [
                    item.get("pcsManagerName"), item.get("managerName"), item.get("managerNm"),
                    item.get("pcsManagerNm"), item.get("userNm"), item.get("empNm"),
                    item.get("addName"), item.get("regUserNm"), item.get("regEmpNm")
                ]
                mgr_ids = [
                    item.get("pcsManagerId"), item.get("managerId"), item.get("userId"),
                    item.get("addId"), item.get("empId"), item.get("regUserId"), item.get("regEmpId")
                ]

                has_mgr_info = any(bool(v and str(v).strip()) for v in mgr_names + mgr_ids)
                if has_mgr_info:
                    is_kim = any("김재현" in str(v) for v in mgr_names if v) or \
                             any("kimjh" in str(v).lower() for v in mgr_ids if v)
                    if not is_kim:
                        filtered_out_other_manager += 1
                        continue

                # ── 2. 차량번호 및 차종명 검증 (boname + gradename 실측 일치) ──
                car_no = (
                    item.get("carNumber") or
                    item.get("carNo") or
                    item.get("vhclNo") or
                    item.get("car_number") or ""
                ).replace(" ", "").strip()

                if not car_no or len(car_no) < 6:
                    continue

                boname = str(item.get("boname") or "").strip()
                gradename = str(item.get("gradename") or "").strip()
                car_name = f"{boname} {gradename}".strip() if boname else (
                    item.get("carName") or
                    item.get("modelNm") or
                    item.get("vhclNm") or
                    item.get("car_name") or ""
                ).strip()

                # 차종명이 없거나 무효한 가견적 제외
                if not car_name or car_name in ("-", "미확인", "null", "None"):
                    filtered_out_estimate_only += 1
                    continue

                # ── 3. 고유 식별키 (pcsNo 실측 일치) ──
                raw_pcs_id = (
                    item.get("pcsNo") or
                    item.get("id") or
                    item.get("pcsId") or
                    item.get("pcsEstimateId") or
                    item.get("estimateId")
                )
                pcs_id = None
                if raw_pcs_id is not None and str(raw_pcs_id).strip() not in ("", "null", "none"):
                    try:
                        pcs_id = int(str(raw_pcs_id).replace(",", ""))
                    except (ValueError, TypeError):
                        pcs_id = None

                # ── 4. 매입일자 검증 (purchaseDate 실측 일치) ──
                raw_td = (
                    item.get("purchaseDate") or
                    item.get("pcsDt") or
                    item.get("transferDate") or
                    item.get("returnDt") or
                    item.get("billDate")
                )
                transfer_date = str(raw_td).strip() if raw_td else None

                # ── 5. 매입가 (finalPcsAmt 우선, 없으면 desiredPcsAmt, 없으면 buyPrice) ──
                raw_buy = item.get("finalPcsAmt")
                if raw_buy is None or str(raw_buy).strip() in ("", "null", "none", "0"):
                    raw_buy = item.get("desiredPcsAmt")
                if raw_buy is None or str(raw_buy).strip() in ("", "null", "none", "0"):
                    raw_buy = item.get("buyPrice") or item.get("pcsAmt") or item.get("carPurchasePrice") or 0

                buy_price = 0
                try:
                    buy_price = int(float(str(raw_buy).replace(",", "").strip()))
                except (ValueError, TypeError):
                    buy_price = 0

                # 매입완료(searchPurchaseType=A) 데이터이므로 매입일자나 pcsNo가 있으면 유효 매입건으로 인정.
                # 단, 매입일자도 없고 pcsNo도 없는데 금액마저 0원이면 가견적으로 제외
                if buy_price <= 0 and not transfer_date and not pcs_id:
                    filtered_out_estimate_only += 1
                    continue

                # ── 6. 상태 검증 (단순 접수/취소/반려 제외) ──
                status_val = str(
                    item.get("strStatus") or
                    item.get("status") or
                    item.get("statusNm") or
                    item.get("saleStatus") or
                    item.get("pcsStatus") or
                    item.get("carStatus") or ""
                ).strip()

                if any(bad in status_val for bad in ["견적접수", "신청", "반려", "취소"]):
                    filtered_out_estimate_only += 1
                    continue

                # ── 7. 주행거리 (carNavi 실측 일치) ──
                list_mileage = None
                for mk in ["carNavi", "carMileage", "mileage", "vhclMileage", "accumMileage", "drivingDistance", "주행거리", "dvrDsc", "useKm", "runKm", "distance"]:
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

                # ── 8. 연식 (carYear 실측 일치) ──
                model_year = str(item.get("carYear") or item.get("modelYear") or "").strip()

                # ── 9. 기타수수료 etcAmt ──
                etc_amt = item.get("etcAmt")
                if etc_amt is not None and str(etc_amt).strip() not in ("", "null", "none"):
                    has_etc_amt = True
                    try:
                        etc_amt = int(str(etc_amt).replace(",", ""))
                    except (ValueError, TypeError):
                        etc_amt = None
                else:
                    etc_amt = None

                # ── 10. 목표판매가 ──
                raw_target_sale = item.get("targetSaleAmt") or item.get("saleAmt") or item.get("salePrice")
                target_sale_amt = None
                if raw_target_sale is not None and str(raw_target_sale).strip() not in ("", "null", "none"):
                    try:
                        target_sale_amt = int(str(raw_target_sale).replace(",", ""))
                    except (ValueError, TypeError):
                        target_sale_amt = None

                # 판매 완료 여부 판정
                sold_yn = (
                    item.get("soldYn") or
                    item.get("sold_yn") or
                    item.get("isSold") or
                    item.get("saleYn") or ""
                )
                sold_yn_str = str(sold_yn).strip().upper() if sold_yn is not None else ""
                is_sold = (sold_yn_str in ("Y", "YES", "TRUE", "1")) or ("완료" in status_val or status_val == "판매완료")

                ap_car_id_list = item.get("apCarId") or item.get("carId") or None
                if ap_car_id_list is not None:
                    ap_car_id_list = str(ap_car_id_list).strip()
                    if ap_car_id_list.lower() in ("", "null", "none"):
                        ap_car_id_list = None

                parsed_cars.append({
                    "pcsId": pcs_id,
                    "carNumber": car_no,
                    "carName": car_name,
                    "modelYear": model_year,
                    "buyPrice": buy_price,
                    "targetSaleAmt": target_sale_amt,
                    "apCarId": ap_car_id_list,
                    "mileage": list_mileage,
                    "etcAmt": etc_amt,
                    "transferDate": transfer_date,
                    "manager": "김재현",
                    "soldYn": sold_yn_str,
                    "status": status_val,
                    "isSold": is_sold,
                    "raw": item
                })

            print(f"[MobilePurchaseService] 필터링 완료: 전체 수집 {len(all_raw_items)}건 -> 타인차 제외 {filtered_out_other_manager}건, 가견적 제외 {filtered_out_estimate_only}건 -> 제이 실매입차 {len(parsed_cars)}건", flush=True)

            return {
                "success": True,
                "status_code": 200,
                "raw_response": None,
                "cars": parsed_cars,
                "has_etc_amt": has_etc_amt,
                "total_count": len(parsed_cars),
                "total_pages_read": cur_page,
                "message": f"성공적으로 {cur_page}페이지 탐색하여 김재현 실매입 차량 {len(parsed_cars)}대를 수집했습니다. (타인차 {filtered_out_other_manager}건·가견적 {filtered_out_estimate_only}건 차단)"
            }

        except Exception as e:
            logger.exception(f"[MobilePurchaseService] 요청 예외 발생: {e}")
            return {
                "success": False,
                "status_code": 500,
                "raw_response": None,
                "cars": [],
                "has_etc_amt": False,
                "total_pages_read": 0,
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

                # pcsManagerId / pcsManagerName 확인 (김재현/kimjh1202)
                manager_id = str(data.get("pcsManagerId") or data.get("managerId") or data.get("addId") or "").strip()
                manager_name = str(data.get("pcsManagerName") or data.get("managerNm") or data.get("managerName") or data.get("addName") or "").strip()
                if (manager_id or manager_name) and "kimjh" not in manager_id.lower() and "김재현" not in manager_name:
                    logger.info(f"[MobilePurchaseService] pcs_id {pcs_id} 담당자 불일치 ({manager_id}, {manager_name}) -> 제외")
                    continue

                car_no = str(data.get("carNumber") or data.get("carNo") or "").replace(" ", "").strip()
                boname = str(data.get("boname") or "").strip()
                gradename = str(data.get("gradename") or "").strip()
                car_name = f"{boname} {gradename}".strip() if boname else str(data.get("carName") or data.get("modelNm") or "").strip()

                raw_buy = data.get("finalPcsAmt")
                if raw_buy is None or str(raw_buy).strip() in ("", "null", "none", "0"):
                    raw_buy = data.get("desiredPcsAmt")
                if raw_buy is None or str(raw_buy).strip() in ("", "null", "none", "0"):
                    raw_buy = data.get("buyPrice") or data.get("pcsAmt") or data.get("carPurchasePrice") or 0

                buy_price = 0
                try:
                    buy_price = int(float(str(raw_buy).replace(",", "").strip()))
                except (ValueError, TypeError):
                    buy_price = 0

                raw_etc = data.get("etcAmt")
                etc_amt = None
                if raw_etc is not None and str(raw_etc).strip() != "" and str(raw_etc).strip().lower() != "null":
                    try:
                        etc_amt = int(str(raw_etc).replace(",", ""))
                    except (ValueError, TypeError):
                        etc_amt = None

                transfer_date = str(data.get("purchaseDate") or data.get("pcsDt") or data.get("returnDt") or data.get("transferDate") or data.get("billDate") or "").strip() or None

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

                model_year = str(data.get("carYear") or data.get("modelYear") or "").strip()

                # 주행거리 추출: carNavi 1순위 실측
                extracted_mileage = None
                matched_mileage_key = None
                mileage_candidates = ["carNavi", "carMileage", "mileage", "vhclMileage", "accumMileage", "drivingDistance", "주행거리", "dvrDsc", "useKm", "runKm", "distance"]
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
                    "modelYear": model_year,
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
