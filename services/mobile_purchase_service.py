"""
services/mobile_purchase_service.py
하이오플 모바일 API (https://high.autoplus.co.kr/admin/v1/purchases/estimates) 연동 서비스
- 백엔드에서 직접 모바일 REST API를 호출하여 매입 차량 목록 및 수수료(etcAmt) 추출
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIGH_COOKIE_FILE_PATH = os.path.join(BASE_DIR, "high_cookie.txt")
AUTOPLUS_COOKIE_FILE_PATH = os.path.join(BASE_DIR, "autoplus_cookie.txt")
API_URL = "https://high.autoplus.co.kr/admin/v1/purchases/estimates"


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
                "raw_response": None,
                "cars": [],
                "has_etc_amt": False,
                "message": "오토플러스 쿠키가 설정되지 않았습니다. (autoplus_cookie.txt 없음)"
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
                logger.error(f"[MobilePurchaseService] API 응답 에러 HTTP {status_code}: {resp.text[:300]}")
                return {
                    "success": False,
                    "status_code": status_code,
                    "raw_response": resp.text[:1000],
                    "cars": [],
                    "has_etc_amt": False,
                    "message": f"API 호출 실패 (HTTP {status_code}): {resp.text[:200]}"
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

                parsed_cars.append({
                    "carNumber": car_no,
                    "carName": car_name,
                    "buyPrice": buy_price,
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
