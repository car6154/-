import json
import re
from typing import Dict, Any
import requests
from bs4 import BeautifulSoup

REBORN_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def build_reborn_url(pid: str) -> str:
    clean_pid = str(pid or "").strip()
    if not clean_pid or clean_pid in ("-", "None", "nan"):
        return ""
    return f"https://www.reborncar.co.kr/smartbuy/SB1002/{clean_pid}?bShow=false"


def fetch_reborn_detail(pid: str) -> Dict[str, Any]:
    """
    리본카 매물 상세 페이지(SB1002/{PID})에서 검증된 고유 필드만 수집한다.
    - 일반 HTTP GET (타임아웃 6초, 로그인/우회/스텔스 미사용)
    - 403/429 발생 시 재시도 없이 즉시 중단 및 링크만 반환
    - 반환 필드: pid, rebornUrl, price(만원), mileage(km), regYearMonth(최초등록 연월),
                color, fuel, seating, branch, imageUrl, isSoldOut
    """
    clean_pid = str(pid or "").strip()
    if not clean_pid or clean_pid in ("-", "None", "nan"):
        return {
            "success": False,
            "pid": "",
            "rebornUrl": "",
            "error": "유효한 PID가 없습니다."
        }

    reborn_url = build_reborn_url(clean_pid)

    try:
        resp = requests.get(
            reborn_url,
            headers={"User-Agent": REBORN_USER_AGENT},
            timeout=6
        )
    except Exception as e:
        return {
            "success": False,
            "pid": clean_pid,
            "rebornUrl": reborn_url,
            "error": f"네트워크 요청 실패: {e}"
        }

    if resp.status_code in (403, 429):
        return {
            "success": False,
            "pid": clean_pid,
            "rebornUrl": reborn_url,
            "statusCode": resp.status_code,
            "error": f"HTTP {resp.status_code} 요청 제한 (링크로 확인하세요)"
        }

    if resp.status_code != 200:
        return {
            "success": False,
            "pid": clean_pid,
            "rebornUrl": reborn_url,
            "statusCode": resp.status_code,
            "error": f"HTTP {resp.status_code}"
        }

    soup = BeautifulSoup(resp.text, "html.parser")
    ld_script = soup.find("script", type="application/ld+json")
    if not ld_script or not ld_script.string:
        return {
            "success": False,
            "pid": clean_pid,
            "rebornUrl": reborn_url,
            "error": "리본카 상세 정보를 찾을 수 없습니다."
        }

    try:
        ld_data = json.loads(ld_script.string)
    except Exception:
        return {
            "success": False,
            "pid": clean_pid,
            "rebornUrl": reborn_url,
            "error": "리본카 데이터 파싱 실패"
        }

    offers = ld_data.get("offers") if isinstance(ld_data.get("offers"), dict) else {}
    raw_price = offers.get("price", 0)
    try:
        price_num = float(raw_price)
        price_man = int(round(price_num / 10000.0)) if price_num >= 10000 else int(round(price_num))
    except (ValueError, TypeError):
        price_man = 0

    if price_man <= 0:
        return {
            "success": False,
            "pid": clean_pid,
            "rebornUrl": reborn_url,
            "error": "유효한 가격 정보가 없습니다."
        }

    # 주행거리 (JSON-LD 우선, 없으면 상단 .car-navi 폴백)
    mil_obj = ld_data.get("mileageFromOdometer")
    mileage_km = 0
    if isinstance(mil_obj, dict) and mil_obj.get("value") is not None:
        try:
            mileage_km = int(float(mil_obj.get("value")))
        except (ValueError, TypeError):
            mileage_km = 0

    info_box = soup.select_one(".car-infos")
    if mileage_km <= 0 and info_box:
        navi_el = info_box.select_one(".car-navi")
        if navi_el:
            m_digits = re.sub(r"[^\d]", "", navi_el.get_text(strip=True))
            if m_digits:
                mileage_km = int(m_digits)

    # 상단 연월 (최초등록: .release-dt)
    reg_ym = "-"
    if info_box:
        rel_el = info_box.select_one(".release-dt")
        if rel_el and rel_el.get_text(strip=True):
            reg_ym = rel_el.get_text(strip=True)

    # 색상
    color_str = str(ld_data.get("color") or "").strip()
    if not color_str and info_box:
        col_el = info_box.select_one(".car-color")
        if col_el:
            color_str = col_el.get_text(strip=True)
    color_str = color_str or "-"

    # 연료
    fuel_str = str(ld_data.get("fuelType") or "").strip()
    if not fuel_str and info_box:
        fuel_el = info_box.select_one(".car-fuel")
        if fuel_el:
            fuel_str = fuel_el.get_text(strip=True)
    fuel_str = fuel_str or "-"

    # 인승 (.car-seat)
    seating_str = "-"
    if info_box:
        seat_el = info_box.select_one(".car-seat")
        if seat_el and seat_el.get_text(strip=True):
            seating_str = seat_el.get_text(strip=True)

    # 지점
    place_obj = offers.get("availableAtOrFrom")
    branch_str = ""
    if isinstance(place_obj, dict):
        branch_str = str(place_obj.get("name") or "").strip()
    branch_str = branch_str or "-"

    # 대표 사진 URL 1장
    img_val = ld_data.get("image")
    image_url = ""
    if isinstance(img_val, list) and img_val:
        image_url = str(img_val[0] or "").strip()
    elif isinstance(img_val, str):
        image_url = img_val.strip()
    if not image_url:
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            image_url = str(og_img.get("content")).strip()

    # 판매완료 여부 (OutOfStock)
    avail_str = str(offers.get("availability") or "")
    is_sold_out = "OutOfStock" in avail_str

    return {
        "success": True,
        "pid": clean_pid,
        "rebornUrl": reborn_url,
        "price": price_man,
        "mileage": mileage_km,
        "regYearMonth": reg_ym,
        "color": color_str,
        "fuel": fuel_str,
        "seating": seating_str,
        "branch": branch_str,
        "imageUrl": image_url,
        "isSoldOut": is_sold_out
    }

