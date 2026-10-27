# api_server.py
import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
import re
import csv
import json
import time
import threading
import subprocess
import urllib.parse
from typing import List, Any, Optional, Union, Dict
from datetime import datetime
from pydantic import BaseModel
import requests
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uvicorn

from services.master_mapping import MasterMappingService
from services.sold_out_tracker import SoldOutTracker
from services.encar_service import Scraper
from services.chaolma_service import ChaolmaService
from services.git_sync_service import GitSyncService
from services.gdrive_backup_service import GDriveBackupService
from services.data_processor import DataProcessor
from services.autoplus_sync_service import AutoplusSyncService, start_autoplus_scheduler
from routers.ledger_router import router as ledger_router
from routers.settlement_router import router as settlement_router
from routers.ocr_router import router as ocr_router
from routers.tracking_router import router as tracking_router

app = FastAPI(title="J-Project Local API Server", version="1.0.0")

# 프로세스 기동 시점의 커밋 기록 (프로세스-커밋 일치 불변조건 보장용)
BOOT_TIME = datetime.now()
try:
    BOOT_COMMIT = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
    BOOT_COMMIT_MSG = subprocess.run(["git", "log", "-1", "--format=%s"], capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=5).stdout.strip()
    BOOT_COMMIT_DATE = subprocess.run(["git", "log", "-1", "--format=%cd", "--date=format:%m-%d %H:%M"], capture_output=True, text=True, timeout=5).stdout.strip()
except Exception:
    BOOT_COMMIT = "-"
    BOOT_COMMIT_MSG = "-"
    BOOT_COMMIT_DATE = "-"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def cors_and_pna_preflight_middleware(request: Request, call_next):
    origin = request.headers.get("origin") or "*"
    req_headers = request.headers.get("access-control-request-headers") or "Content-Type, X-JPRO-Token, Authorization"

    # 모든 OPTIONS 사전 요청을 라우터 도달 전에 200 OK로 즉시 처리 (405 원천 차단)
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": req_headers,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Private-Network": "true",
            },
        )

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

app.include_router(ledger_router)
app.include_router(settlement_router)
app.include_router(ocr_router)
app.include_router(tracking_router)

@app.on_event("startup")
def on_app_startup():
    try:
        start_autoplus_scheduler()
    except Exception as e:
        print(f"[api_server] Failed to start Autoplus sync scheduler: {e}", flush=True)
    try:
        SoldOutTracker.start_tracked_cars_scheduler(interval_hours=12.0)
    except Exception as e:
        print(f"[api_server] Failed to start Tracked cars scheduler: {e}", flush=True)
    try:
        GDriveBackupService.start_realtime_watcher()
    except Exception as e:
        print(f"[api_server] Failed to start GDrive realtime watcher: {e}", flush=True)
    try:
        from scraper import HeydealerScraper
        HeydealerScraper.start_keepalive_manager()
    except Exception as e:
        print(f"[api_server] Failed to start Heydealer keep-alive manager: {e}", flush=True)
    try:
        # 노트북 서버(C:\jpro) 환경인 경우에만 24시간 무인 Git auto-pull 파수꾼 가동
        is_server_env = os.path.abspath(__file__).lower().startswith("c:\\jpro")
        if is_server_env:
            GitSyncService.start_auto_pull_daemon(interval_sec=10, cooldown_sec=10)
    except Exception as e:
        print(f"[api_server] Failed to start Git auto pull daemon: {e}", flush=True)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LEDGER_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_car_ledger.csv")
SETTLEMENT_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_inventory_settlement.csv")


def _safe_int(val: Any, default: int = 0) -> int:
    if not val:
        return default
    clean = str(val).replace(",", "").strip()
    try:
        return int(float(clean))
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    if not val:
        return default
    clean = str(val).replace(",", "").strip()
    try:
        return float(clean)
    except (ValueError, TypeError):
        return default


@app.get("/api/health")
def health_check():
    return {"status": "ok", "mode": "local_only"}


# ----------------------------------------------------
# 0-0. 신차가격표 카탈로그 조회 API (옵션 및 패키지 정밀 매칭용)
# ----------------------------------------------------
_newcar_catalog_cache = None
_newcar_catalog_mtime = 0

def _get_newcar_catalog():
    global _newcar_catalog_cache, _newcar_catalog_mtime
    cat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "encar_newcar_catalog.json")
    if not os.path.exists(cat_path):
        return {}
    mtime = os.path.getmtime(cat_path)
    if _newcar_catalog_cache is None or mtime > _newcar_catalog_mtime:
        try:
            with open(cat_path, "r", encoding="utf-8") as f:
                _newcar_catalog_cache = json.load(f)
                _newcar_catalog_mtime = mtime
        except Exception as e:
            print(f"[api_server] 신차가격표 카탈로그 로드 실패: {e}")
            _newcar_catalog_cache = {}
    return _newcar_catalog_cache or {}


@app.get("/api/newcar_catalog")
def get_newcar_catalog_endpoint(car_name: str, year: Optional[str] = None):
    """
    차량명(예: 올 뉴 카니발)과 연식(예: 2017)으로 공식 신차 옵션 및 패키지 목록 조회
    """
    if not car_name:
        return {"success": False, "message": "차량명을 입력해주세요."}

    catalog = _get_newcar_catalog()
    clean_name = re.sub(r'^(현대|기아|제네시스|쉐보레|르노코리아|르노삼성|KG모빌리티|쌍용)\s*', '', car_name).strip()
    norm_input = re.sub(r'\s+', '', clean_name).lower()

    # 1. 모델명 매칭
    matched_key = None
    if clean_name in catalog:
        matched_key = clean_name
    else:
        for k in catalog.keys():
            if re.sub(r'\s+', '', k).lower() == norm_input:
                matched_key = k
                break
        if not matched_key:
            for k in catalog.keys():
                norm_k = re.sub(r'\s+', '', k).lower()
                if norm_input in norm_k or norm_k in norm_input:
                    matched_key = k
                    break

    if not matched_key:
        return {"success": False, "message": f"'{car_name}' 모델을 카탈로그에서 찾을 수 없습니다."}

    model_data = catalog[matched_key]

    # 2. 연식 매칭
    target_yr = None
    if year:
        m_yr = re.search(r'(20\d{2})', str(year))
        if m_yr:
            target_yr = m_yr.group(1)
        else:
            m_short = re.search(r'(\d{2})', str(year))
            if m_short:
                target_yr = f"20{m_short.group(1)}"
            else:
                target_yr = str(year).strip()

    if target_yr and target_yr in model_data:
        res = model_data[target_yr]
        return {
            "success": True,
            "model": matched_key,
            "year": target_yr,
            "grades": res.get("grades", []),
            "options": res.get("options", {}),
            "packages": res.get("packages", {})
        }

    # 해당 연식이 없으면 등록된 최신 연식 폴백
    all_yrs = sorted(list(model_data.keys()), reverse=True)
    if all_yrs:
        fallback_yr = all_yrs[0]
        res = model_data[fallback_yr]
        return {
            "success": True,
            "model": matched_key,
            "year": fallback_yr,
            "fallback": True,
            "requested_year": year,
            "grades": res.get("grades", []),
            "options": res.get("options", {}),
            "packages": res.get("packages", {})
        }

    return {"success": False, "message": f"'{matched_key}'의 연식 데이터를 찾을 수 없습니다."}


# ----------------------------------------------------
# 0-1. 오토플러스.Data 사내 데이터 자동 동기화 API
# ----------------------------------------------------
@app.get("/api/autoplus/sync_status")
def get_autoplus_sync_status():
    return AutoplusSyncService.get_status()


@app.post("/api/autoplus/sync_now")
def trigger_autoplus_sync():
    return AutoplusSyncService.execute_sync()


@app.get("/api/autoplus/company_carids")
def get_company_carids():
    return AutoplusSyncService.get_company_carid_map()


# ----------------------------------------------------
# 0. 차얼마 API (오토플러스 ERP 실시간 제원 및 옵션 조회)
# ----------------------------------------------------
@app.get("/api/chaolma/{car_no}")
def get_chaolma_car_info(car_no: str, mileage: Optional[int] = None):
    clean_no = car_no.replace(" ", "").strip()
    if not clean_no:
        return {"success": False, "message": "차량번호를 입력해주세요."}
    try:
        actual_mileage = mileage if (mileage is not None and mileage > 0) else 50000
        res = ChaolmaService.fetch_car_info(clean_no, mileage=actual_mileage)
        if not res or not res.get("success"):
            return {"success": False, "message": "차얼마 데이터 조회 실패 또는 미등록 차량", "car_no": clean_no}
        return res
    except Exception as e:
        return {"success": False, "message": f"차얼마 조회 오류: {str(e)}", "car_no": clean_no}


@app.get("/api/chaolma/history/{car_no}")
def get_chaolma_car_history_endpoint(car_no: str):
    clean_no = car_no.replace(" ", "").strip()
    if not clean_no:
        return {"success": False, "message": "차량번호를 입력해주세요."}
    try:
        return ChaolmaService.fetch_car_history(clean_no)
    except Exception as e:
        return {"success": False, "message": f"카히스토리 조회 오류: {str(e)}", "car_no": clean_no}


@app.get("/api/chaolma/origin/{car_no}")
def get_chaolma_car_origin_endpoint(car_no: str):
    clean_no = car_no.replace(" ", "").strip()
    if not clean_no:
        return {"success": False, "message": "차량번호를 입력해주세요."}
    try:
        return ChaolmaService.fetch_car_origin_doc(clean_no)
    except Exception as e:
        return {"success": False, "message": f"자동차등록원부 조회 오류: {str(e)}", "car_no": clean_no}


class CookieSavePayload(BaseModel):
    cookie: str
    target: Optional[str] = "heydealer"
    secretToken: Optional[str] = None

@app.post("/api/save_cookie")
@app.post("/api/session/cookie")
def save_cookie_api(payload: CookieSavePayload):
    from services.cookie_server import set_env_variable, save_cookie
    target = (payload.target or "").lower()
    raw_cookie = payload.cookie.strip()
    if not raw_cookie:
        return {"status": "error", "message": "Cookie is empty"}
    
    # 타겟 자동 추론 보강
    if not target or target == "unknown":
        if "JSESSIONID" in raw_cookie.upper() or "remember-me" in raw_cookie:
            target = "autoplus"
        elif "sessionid=" in raw_cookie:
            target = "heydealer"
        else:
            target = "autoplus" if "autoplus" in raw_cookie else "heydealer"

    base_dir = os.path.dirname(os.path.abspath(__file__))
    if target == "encar":
        save_cookie(raw_cookie)
        set_env_variable("ENCAR_COOKIE", raw_cookie)
        os.environ["ENCAR_COOKIE"] = raw_cookie
        print(f"[CookieReceive] 엔카 쿠키 {len(raw_cookie)}자 갱신 완료", flush=True)
    elif target in ("autoplus_data", "data", "ap_data"):
        with open(os.path.join(base_dir, "autoplus_data_cookie.txt"), "w", encoding="utf-8") as f:
            f.write(raw_cookie)
        set_env_variable("AUTOPLUS_DATA_COOKIE", raw_cookie)
        os.environ["AUTOPLUS_DATA_COOKIE"] = raw_cookie
        print(f"[CookieReceive] 오토플러스.Data 쿠키 {len(raw_cookie)}자 갱신 완료. 백그라운드 동기화(execute_sync) 즉시 트리거!", flush=True)
        import threading
        def _bg_sync():
            try:
                from services.autoplus_sync_service import AutoplusSyncService
                AutoplusSyncService.execute_sync()
            except Exception as se:
                print(f"[CookieReceive] 오플 데이터 자동 동기화 오류: {se}", flush=True)
        threading.Thread(target=_bg_sync, daemon=True).start()
    elif target in ("high", "autoplus_high", "high_cookie") or "high" in target:
        with open(os.path.join(base_dir, "high_cookie.txt"), "w", encoding="utf-8") as f:
            f.write(raw_cookie)
        set_env_variable("HIGH_COOKIE", raw_cookie)
        os.environ["HIGH_COOKIE"] = raw_cookie
        print(f"[CookieReceive] 하이오플(모바일) 쿠키 {len(raw_cookie)}자 갱신 완료 (high_cookie.txt)", flush=True)
    elif target in ("autoplus", "chaolma", "autoplus_admin") or "auto" in target:
        from services.cookie_server import get_current_autoplus_cookie
        curr_cookie = get_current_autoplus_cookie()
        curr_has_session = curr_cookie and (('JSESSIONID' in curr_cookie.upper()) or ('REMEMBER-ME' in curr_cookie.upper()))
        new_has_session = ('JSESSIONID' in raw_cookie.upper()) or ('REMEMBER-ME' in raw_cookie.upper())
        if curr_has_session and not new_has_session:
            print(f"[CookieReceive] 차얼마 세션 보호: 유효 JSESSIONID 보존 (새 쿠키 세션키 누락, {len(raw_cookie)}자)", flush=True)
            return {"status": "ok", "message": "Existing chaolma session preserved"}

        with open(os.path.join(base_dir, "autoplus_cookie.txt"), "w", encoding="utf-8") as f:
            f.write(raw_cookie)
        set_env_variable("AUTOPLUS_COOKIE", raw_cookie)
        os.environ["AUTOPLUS_COOKIE"] = raw_cookie
        try:
            from services.chaolma_service import ChaolmaService
            ChaolmaService.clear_cache()
        except Exception:
            pass
        print(f"[CookieReceive] 차얼마/오토플러스 쿠키 {len(raw_cookie)}자 갱신 완료 (autoplus_cookie.txt)", flush=True)
    else:
        from services.cookie_server import get_current_hd_cookie
        curr_hd = get_current_hd_cookie()
        if curr_hd and ('sessionid=' in curr_hd) and ('sessionid=' not in raw_cookie):
            print(f"[CookieReceive] 헤이딜러 세션 보호: 유효 sessionid 보존 (새 쿠키 sessionid 누락, {len(raw_cookie)}자)", flush=True)
            return {"status": "ok", "message": "Existing heydealer session preserved"}

        with open(os.path.join(base_dir, "heydealer_cookie.txt"), "w", encoding="utf-8") as f:
            f.write(raw_cookie)
        set_env_variable("HEYDEALER_COOKIE", raw_cookie)
        os.environ["HEYDEALER_COOKIE"] = raw_cookie
        try:
            from scraper import HeydealerScraper
            HeydealerScraper.reload_session_from_saved_cookie()
        except Exception:
            pass
        print(f"[CookieReceive] 헤이딜러 쿠키 {len(raw_cookie)}자 갱신 완료", flush=True)

    return {"status": "ok", "message": f"{target} cookie saved successfully"}


class QuickLoginPayload(BaseModel):
    target: str = "autoplus"


class PlatformCredentialsPayload(BaseModel):
    platform: str
    userId: str
    userPw: str


@app.post("/api/auth/quick_login")
def quick_login_api(payload: QuickLoginPayload):
    from services.auto_login_service import perform_auto_login
    return perform_auto_login(payload.target)


@app.post("/api/auth/credentials")
def save_credentials_api(payload: PlatformCredentialsPayload):
    from services.auto_login_service import save_platform_credentials
    return save_platform_credentials(payload.platform, payload.userId, payload.userPw)


@app.get("/api/auth/credentials/status")
def get_credentials_status_api():
    from services.auto_login_service import get_credential_status
    return get_credential_status()


@app.get("/api/cookie/status")
def get_all_cookies_status():
    from services.cookie_server import get_current_encar_cookie, get_current_hd_cookie, get_current_autoplus_cookie
    hd_c = get_current_hd_cookie()
    ap_c = get_current_autoplus_cookie()
    ec_c = get_current_encar_cookie()
    return {
        "heydealer": {
            "active": bool(hd_c and len(hd_c) > 20 and "sessionid=" in hd_c),
            "present": bool(hd_c and len(hd_c) > 10),
            "length": len(hd_c) if hd_c else 0
        },
        "autoplus": {
            "active": bool(ap_c and len(ap_c) > 20),
            "present": bool(ap_c and len(ap_c) > 10),
            "length": len(ap_c) if ap_c else 0
        },
        "encar": {
            "active": bool(ec_c and len(ec_c) > 20),
            "present": bool(ec_c and len(ec_c) > 10),
            "length": len(ec_c) if ec_c else 0
        }
    }


# ----------------------------------------------------
# 0-1. 헤이딜러 실시간 차량 및 동급 낙찰시세 API (Python Scraper & Session 연동)
# ----------------------------------------------------
@app.get("/api/heydealer/car/{car_id}")
def get_heydealer_car_data(car_id: str):
    clean_id = car_id.strip()
    match = re.search(r'/cars/([a-zA-Z0-9_-]+)', clean_id)
    if match:
        clean_id = match.group(1)
    
    from scraper import HeydealerScraper
    from services.cookie_server import get_current_hd_cookie
    
    cookie_str = get_current_hd_cookie()
    # 1. 라이브 헤이딜러 스크래퍼 호출 시도
    if cookie_str:
        try:
            s = HeydealerScraper.build_session(cookie_str)
            res = HeydealerScraper.fetch_car_detail(clean_id, session=s)
            if res and res.get('detail'):
                det_obj = json.loads(res['detail']) if isinstance(res['detail'], str) else res['detail']
                mp_obj = json.loads(res['market_prices']) if res.get('market_prices') and isinstance(res['market_prices'], str) else res.get('market_prices')
                rep_obj = json.loads(res['auction_repairs']) if res.get('auction_repairs') and isinstance(res['auction_repairs'], str) else res.get('auction_repairs')
                
                payload = {
                    **det_obj,
                    "market_prices": mp_obj,
                    "auction_repairs": rep_obj,
                    "encar_url": res.get("encar_url")
                }
                return {"success": True, "data": payload, "isLive": True}
        except Exception as e:
            print(f"[FastAPI] Heydealer live fetch failed ({clean_id}): {e}")
            if "인증 오류 (401)" in str(e) or "403" in str(e):
                pass  # 아래 캐시 파일 fallback 시도
    
    # 2. 로컬 캐시 last_heydealer_detail.json 백업 활용
    try:
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_heydealer_detail.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                if cached_data:
                    c_hid = cached_data.get('hash_id') or cached_data.get('detail', {}).get('detail_hash_id')
                    if not clean_id or clean_id in ('sample', 'QrqzKqKn') or c_hid == clean_id:
                        return {"success": True, "data": cached_data, "isFallback": True, "cached": True}
    except Exception as e_c:
        print(f"[FastAPI] Heydealer cache load error: {e_c}")

    return {
        "success": False,
        "errorType": "LOGIN_REQUIRED",
        "message": "헤이딜러 세션이 만료되었거나 쿠키가 없습니다. 딜러 로그인 후 상단 [세션 연동]에서 쿠키를 업데이트해주세요."
    }


# ----------------------------------------------------
# 0-2. 자사(오토플러스) 실적 및 시장 수요도 통계 API (Streamlit 8501 100% 동일 로직)
# ----------------------------------------------------
@app.get("/api/market_statistics")
def get_market_statistics(car_name: str, sub_model: Optional[str] = "", year: Optional[str] = "", current_retail: Optional[int] = 0):
    try:
        from sales_analysis import get_car_market_stats
        stats = get_car_market_stats(car_name, sub_model or "", str(year or ""), current_retail or 0)
        sample_df = stats.get("sample_df")
        sample_list = []
        if sample_df is not None and isinstance(sample_df, pd.DataFrame) and not sample_df.empty:
            for _, r in sample_df.iterrows():
                sample_list.append({
                    "id": f"autoplus-{r.get('차량번호', _)}",
                    "soldDate": str(r.get("최종수정일", "") or r.get("최초등록일", "") or "-"),
                    "carNumber": str(r.get("차량번호", "")),
                    "carName": str(r.get("차량명", "")),
                    "subModel": str(r.get("세부모델", "")),
                    "year": str(r.get("등록연도_num", "") or r.get("연식", "")),
                    "mileage": int(r.get("주행거리_num", 0) or 0),
                    "buyPrice": int(r.get("매입가", 0) or 0),
                    "sellPrice": int(r.get("판매가_만원", 0) or 0),
                    "realizedProfit": int(r.get("이익_만원", 0) or 0),
                    "stockDays": int(r.get("경과일수_num", 0) or 0),
                    "branch": str(r.get("지점", "")),
                    "manager": str(r.get("담당자명", "")),
                    "regDate": str(r.get("최초등록일", "")),
                    "encarUrl": str(r.get("E URL", ""))
                })

        auction_df = stats.get("auction_sample_df")
        auction_sample_list = []
        if auction_df is not None and isinstance(auction_df, pd.DataFrame) and not auction_df.empty:
            for _, r in auction_df.iterrows():
                auction_sample_list.append({
                    "id": f"autoplus-auction-{r.get('차량번호', _)}",
                    "soldDate": str(r.get("최종수정일", "") or r.get("최초등록일", "") or "-"),
                    "carNumber": str(r.get("차량번호", "")),
                    "carName": str(r.get("차량명", "")),
                    "subModel": str(r.get("세부모델", "")),
                    "year": str(r.get("등록연도_num", "") or r.get("연식", "")),
                    "mileage": int(r.get("주행거리_num", 0) or 0),
                    "buyPrice": int(r.get("매입가", 0) or 0),
                    "sellPrice": int(r.get("판매가_만원", 0) or 0),
                    "realizedProfit": int(r.get("이익_만원", 0) or 0),
                    "stockDays": int(r.get("경과일수_num", 0) or 0),
                    "branch": str(r.get("지점", "")),
                    "manager": str(r.get("담당자명", "") or "도매출고"),
                    "regDate": str(r.get("최초등록일", ""))
                })
        
        cleaned_stats = {k: v for k, v in stats.items() if k not in ["sample_df", "auction_sample_df"]}
        return {
            "success": True,
            "data": {
                **cleaned_stats,
                "sample_list": sample_list,
                "auction_sample_list": auction_sample_list
            }
        }
    except Exception as e:
        print(f"[FastAPI] market_statistics error: {e}")
        return {"success": False, "error": str(e)}


# ----------------------------------------------------
# 0-3. 엔카 최근 완판(팔린매물) 실거래 스냅샷 통계 API (Streamlit 8501 100% 동일 로직)
# ----------------------------------------------------
@app.get("/api/sold_out_cars")
def get_sold_out_cars(car_name: str, year: Optional[str] = "", candidate_ids: Optional[str] = ""):
    try:
        from services.encar_service import Scraper
        from services.sold_out_tracker import SoldOutTracker
        
        ids_list = [i.strip() for i in candidate_ids.split(",") if i.strip()] if candidate_ids else []
        
        sold_res = Scraper.fetch_sold_out_cars(
            ids_list,
            target_year=year or "",
            expected_model=car_name or ""
        )
        
        enriched = {}
        if sold_res.get("has_data") and sold_res.get("cars_sample"):
            enriched = SoldOutTracker.enrich_sold_cars(
                sold_res["cars_sample"],
                target_year=sold_res.get("target_year"),
                expected_model=car_name or ""
            )
        
        return {
            "success": True,
            "sold_statistics": sold_res,
            "enriched_info": enriched
        }
    except Exception as e:
        print(f"[FastAPI] sold_out_cars error: {e}")
        return {"success": False, "error": str(e)}



# ----------------------------------------------------
# 1. 자사 장부 및 정산 관리 APIRouter (routers/ledger_router.py, routers/settlement_router.py로 분리 완료)
# ----------------------------------------------------

# ----------------------------------------------------
# 1-3. 깃허브 실시간 동기화 (Git Cloud Sync) API
# ----------------------------------------------------
@app.get("/api/git/status")
def get_git_sync_status():
    current_head = "-"
    current_head_msg = "-"
    current_head_date = "-"
    try:
        current_head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
        current_head_msg = subprocess.run(["git", "log", "-1", "--format=%s"], capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=5).stdout.strip()
        current_head_date = subprocess.run(["git", "log", "-1", "--format=%cd", "--date=format:%m-%d %H:%M"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        pass

    is_up_to_date = True
    if BOOT_COMMIT and current_head and BOOT_COMMIT != "-" and current_head != "-":
        is_up_to_date = (BOOT_COMMIT == current_head)

    return {
        "statusBadge": GitSyncService.get_status_badge(),
        "isSyncing": GitSyncService._is_syncing,
        "lastSyncTime": GitSyncService._last_sync_time.isoformat() if GitSyncService._last_sync_time else None,
        "lastSyncStatus": GitSyncService._last_sync_status,
        "appliedCommit": BOOT_COMMIT,
        "appliedCommitMsg": BOOT_COMMIT_MSG,
        "appliedCommitDate": BOOT_COMMIT_DATE,
        "bootTime": BOOT_TIME.strftime("%m-%d %H:%M:%S") if BOOT_TIME else "-",
        "currentHead": current_head,
        "currentHeadMsg": current_head_msg,
        "currentHeadDate": current_head_date,
        "isProcessUpToDate": is_up_to_date
    }


@app.post("/api/git/sync")
def trigger_git_sync(action: str = "pull"):
    if action == "pull":
        ok, msg = GitSyncService.sync_pull()
        return {"success": ok, "action": "pull", "message": msg}
    elif action == "force_pull":
        ok, msg = GitSyncService.sync_force_pull()
        return {"success": ok, "action": "force_pull", "message": msg}
    elif action == "push":
        GitSyncService.sync_push_async("manual: trigger push from web UI")
        return {"success": True, "action": "push", "message": "백그라운드 동기화 푸시 요청됨"}
    else:
        raise HTTPException(status_code=400, detail=f"알 수 없는 동기화 액션: {action}")


@app.post("/api/server/restart_all")
def restart_all_servers_endpoint():
    """
    GitHub 최신 코드 업데이트(git pull) + 3대 서버 및 쇼핑봇 일괄 재가동 (update_and_run.bat)
    """
    def _do_restart():
        time.sleep(1.0)
        bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_and_run.bat")
        if not os.path.exists(bat_path):
            bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_all.bat")
        if os.path.exists(bat_path):
            CREATE_NEW_CONSOLE = 0x00000010
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            subprocess.Popen(
                f'cmd.exe /c start "JPRO_Updater" "{bat_path}"',
                cwd=os.path.dirname(os.path.abspath(__file__)),
                creationflags=CREATE_NEW_CONSOLE | CREATE_NEW_PROCESS_GROUP,
                shell=True
            )

    threading.Thread(target=_do_restart, daemon=True).start()
    return {
        "success": True,
        "message": "⚡ 최신 업데이트 & 쇼핑봇 포함 서버 일괄 재가동이 시작되었습니다. 약 8~10초 후 페이지를 새로고침하세요."
    }


@app.post("/api/server/kill_all")
def kill_all_servers_endpoint():
    """
    전체 서버 및 프로세스 완전 종료 (kill_servers.bat)
    """
    def _do_kill():
        time.sleep(0.5)
        subprocess.run('taskkill /f /im node.exe', shell=True, capture_output=True)
        subprocess.run('taskkill /f /fi "WINDOWTITLE eq JPRO_FastAPI_*"', shell=True, capture_output=True)
        subprocess.run('taskkill /f /fi "WINDOWTITLE eq JPRO_Frontend_*"', shell=True, capture_output=True)
        subprocess.run('taskkill /f /fi "WINDOWTITLE eq JPRO_Streamlit_*"', shell=True, capture_output=True)
        subprocess.run('taskkill /f /fi "WINDOWTITLE eq Shopping_Web_6154*"', shell=True, capture_output=True)
        subprocess.run('taskkill /f /fi "WINDOWTITLE eq AI_Shopping_Bot*"', shell=True, capture_output=True)
        bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kill_servers.bat")
        if os.path.exists(bat_path):
            subprocess.run(f'cmd.exe /c "{bat_path}"', shell=True, capture_output=True)
        subprocess.run('taskkill /f /im python.exe', shell=True, capture_output=True)

    threading.Thread(target=_do_kill, daemon=True).start()
    return {
        "success": True,
        "message": "🛑 J-PRO 및 쇼핑봇 모든 서버가 완전히 종료됩니다."
    }





# 2. 엔카 실시간 시세 검색 API (스냅샷 자동 누적)
# ----------------------------------------------------
class EncarSearchRequest(BaseModel):
    url: Optional[str] = ""
    carName: Optional[str] = ""
    detailModel: Optional[str] = ""
    gradeName: Optional[str] = ""
    gradeDetailName: Optional[str] = ""
    manufacturer: Optional[str] = ""
    year: Optional[int] = 0
    mileage: Optional[int] = 0
    targetOptions: Optional[str] = ""
    targetAccident: Optional[str] = ""
    carNumber: Optional[str] = ""
    skipDetail: Optional[bool] = False


@app.post("/api/encar/search")
def search_encar_market(req: EncarSearchRequest):
    try:
        car_name = req.carName or ""
        raw_g = (req.gradeName or "").strip()
        raw_gd = (req.gradeDetailName or "").strip()

        # 등급 결합 (단일 진실 공급원: 백엔드가 조립, dedup 필수, 누락 시 기존 detailModel 폴백)
        if raw_g:
            if raw_gd and raw_gd not in raw_g:
                detail_model = f"{raw_g} {raw_gd}".strip()
            else:
                detail_model = raw_g
        else:
            detail_model = req.detailModel or ""

        try:
            os.makedirs("data", exist_ok=True)
            with open("data/encar_debug.log", "a", encoding="utf-8") as f_dbg:
                f_dbg.write(f"[{datetime.now().strftime('%H:%M:%S')}] carName='{car_name}' | gradeName='{raw_g}' | gradeDetailName='{raw_gd}' | detailModel='{req.detailModel}' => 결합='{detail_model}'\n")
        except Exception:
            pass

        print(f"\n==================================================", flush=True)
        print(f"[엔카검색 요청 수신]", flush=True)
        print(f"   carName = '{car_name}'", flush=True)
        print(f"   gradeName = '{raw_g}'", flush=True)
        print(f"   gradeDetailName = '{raw_gd}'", flush=True)
        print(f"   req.detailModel = '{req.detailModel}'", flush=True)
        print(f"   => 최종 결합 detail_model = '{detail_model}'", flush=True)
        print(f"==================================================\n", flush=True)

        manufacturer = req.manufacturer or ""
        year_num = req.year or 0
        mileage_num = req.mileage if req.mileage is not None else 0
        car_no = req.carNumber or ""

        encar_url = req.url
        if not encar_url or not str(encar_url).strip():
            encar_url = MasterMappingService.generate_smart_encar_url(
                car_name=car_name,
                sub_model=detail_model,
                year=year_num,
                mileage=mileage_num,
                car_number=car_no
            )

        # 유효한 상세 조건(action)이 없는 단순 전체 목록 URL일 경우 전수 국산차 덤프 차단 (빈 상태 반환)
        if not encar_url or ("action" not in encar_url and "q=" not in encar_url):
            return {
                "success": False,
                "message": "엔카 실시간 매물을 불러오지 못했습니다.",
                "items": [],
                "totalModelCount": 0,
                "filteredCount": 0,
                "directSearchUrl": encar_url or "",
                "stats": {
                    "avg": 0, "min": 0, "max": 0, "median": 0, "count": 0,
                    "benchmarkPrice": 0, "minBand": 0, "maxBand": 0,
                    "noAccAvg": 0, "accAvg": 0, "accGap": 0
                }
            }

        skip_detail = req.skipDetail if req.skipDetail is not None else False
        df, msg = Scraper.run(encar_url, "", fetch_details=not skip_detail)
        print(f"[엔카검색 결과] rows={len(df)} msg={msg} (skip_detail={skip_detail})", flush=True)
        if df.empty and req.url:
            alt_url = MasterMappingService.generate_smart_encar_url(
                car_name=car_name,
                sub_model=detail_model,
                year=year_num,
                mileage=mileage_num,
                car_number=car_no
            )
            if alt_url and alt_url != encar_url and ("action" in alt_url or "q=" in alt_url):
                df, msg = Scraper.run(alt_url, "", fetch_details=not skip_detail)
                print(f"[엔카검색 결과] rows={len(df)} msg={msg} (skip_detail={skip_detail})", flush=True)
                if not df.empty:
                    encar_url = alt_url

        if df.empty:
            return {
                "success": False,
                "message": "엔카 실시간 매물을 불러오지 못했습니다.",
                "items": [],
                "totalModelCount": 0,
                "filteredCount": 0,
                "directSearchUrl": encar_url or "",
                "stats": {
                    "avg": 0, "min": 0, "max": 0, "median": 0, "count": 0,
                    "benchmarkPrice": 0, "minBand": 0, "maxBand": 0,
                    "noAccAvg": 0, "accAvg": 0, "accGap": 0
                }
            }

        # 1. 표준화 및 중복 제거
        df = DataProcessor.standardize(df)
        df = Scraper.dedupe_after_scan(df)

        # 2. 세부모델/파생트림 엄격 정밀 필터링 (Badge 파라미터 확정 차종은 스킵)
        should_skip_filter = False
        try:
            import urllib.parse
            resolve_res = MasterMappingService.resolve_encar_model(
                brand=manufacturer or "",
                car_name=car_name or "",
                sub_model=detail_model or "",
                year=year_num
            )
            if resolve_res and resolve_res.get("encar_model"):
                trims_dict = resolve_res.get("trims", {})
                matched_trim = None
                if detail_model and trims_dict:
                    _, matched_trim = MasterMappingService.match_structured_trim(detail_model, trims_dict)
                has_badge = bool(matched_trim and matched_trim.get("badge") and str(matched_trim.get("badge")).strip())
                decoded_url = urllib.parse.unquote(encar_url or "")
                has_badge_param = "Badge." in (encar_url or "") or "Badge." in decoded_url
                if has_badge and has_badge_param:
                    should_skip_filter = True
        except Exception as e_gate:
            print(f"[게이트 판정 오류] {e_gate}")

        if should_skip_filter:
            print(f"   => [필터 스킵] 파라미터 조회로 등급 확정 — 텍스트 후처리 생략", flush=True)
        else:
            df = DataProcessor.filter_strictly_by_submodel(df, target_car_name=car_name, target_sub_model=detail_model)

        # 💡 [제이 7번 규칙] 엄격(동일 연식·등급) 비교대상이 7대 미만이면 주행 범위를 ±5만km로 확장 재수집
        if len(df) < 7 and mileage_num and mileage_num > 0:
            print(f"   => [표본 부족] 엄격 매물 {len(df)}대 < 7대: 주행거리 범위를 ±50,000km로 확장 재수집", flush=True)
            wider_url = MasterMappingService.generate_smart_encar_url(
                car_name=car_name,
                sub_model=detail_model,
                year=year_num,
                mileage=mileage_num,
                car_number=car_no,
                mileage_range=50000
            )
            if wider_url and wider_url != encar_url:
                df_wider, msg_wider = Scraper.run(wider_url, "", fetch_details=not skip_detail)
                if not df_wider.empty:
                    df_wider = DataProcessor.standardize(df_wider)
                    df_wider = Scraper.dedupe_after_scan(df_wider)
                    if not should_skip_filter:
                        df_wider = DataProcessor.filter_strictly_by_submodel(df_wider, target_car_name=car_name, target_sub_model=detail_model)
                    if len(df_wider) >= len(df):
                        df = df_wider
                        encar_url = wider_url
                        print(f"   => [확장 수집 성공] 최종 반환 매물: {len(df)}대 (±5만km)", flush=True)

        print(f"   => [필터링 결과] 최종 반환 매물: {len(df)}대 (target_sub_model='{detail_model}')\n", flush=True)
        try:
            with open("data/encar_debug.log", "a", encoding="utf-8") as f_dbg:
                if should_skip_filter:
                    f_dbg.write(f"   => [필터 스킵] 파라미터 조회로 등급 확정 — 텍스트 후처리 생략\n")
                f_dbg.write(f"   => 최종 필터링 결과: {len(df)}대 (target_sub_model='{detail_model}')\n\n")
        except Exception:
            pass

        # 3. 스트림릿 확정 복합 정렬 기준 (성능점검일 최신순 -> 가격 낮은순 -> 연식 최신순)
        df = DataProcessor.sort_by_perf_and_year(df)

        # 스냅샷 자동 누적
        try:
            SoldOutTracker.record_active_listings(df)
        except Exception as e:
            print(f"[api_server] SoldOutTracker error: {e}")

        # --- 옵션 감가(opt_adj) 로직 이관 ---
        import numpy as np
        from datetime import datetime
        
        def extract_option_val(opt_str):
            if not opt_str or str(opt_str) in ("없음", "-", "없음(구버전점검)", "⚠️조회실패", "코드매칭실패"):
                return 0
            prices = re.findall(r'\((\d+)\s*만(?:원)?\)', str(opt_str))
            return sum(int(p) for p in prices) if prices else 0

        KEY_OPT_WEIGHTS = {
            '파노라마선루프': 90, '선루프': 70, 'HUD': 60, '헤드업': 60,
            '어라운드뷰': 70, '서라운드뷰': 70, '모니터링': 60,
            '드라이브와이즈': 80, '스마트센스': 80, '반자율': 70, 'ASCC': 70,
            '통풍시트': 50, '전동트렁크': 40, '스마트테일게이트': 40,
            '사운드': 40, '크렐': 40, '보스': 40, 'JBL': 40, '렉시콘': 40,
            '컴포트': 70, '멀티미디어내비': 70, '내비게이션': 60, '내비': 60,
            '익스테리어': 50, '스타일': 50, '플래티넘': 70, '빌트인캠': 40,
            '시트패키지': 50, '파킹어시스트': 60
        }

        def score_key_options(opt_list_or_str):
            text = " ".join(opt_list_or_str) if isinstance(opt_list_or_str, list) else str(opt_list_or_str)
            matched_opts = []
            score = 0
            for k, w in KEY_OPT_WEIGHTS.items():
                if k in text:
                    norm_k = '선루프' if '선루프' in k else ('HUD' if k in ('HUD', '헤드업') else ('어라운드뷰' if '라운드뷰' in k or '모니터링' in k else ('주행보조' if k in ('드라이브와이즈', '스마트센스', '반자율', 'ASCC') else ('내비' if '내비' in k or '멀티미디어' in k else k))))
                    if norm_k not in matched_opts:
                        matched_opts.append(norm_k)
                        score += w
            return score, matched_opts

        target_year_val = year_num if year_num > 0 else 2021
        if target_year_val < 100:
            target_year_val += 2000
        curr_year = datetime.now().year
        car_age = max(0, curr_year - target_year_val)

        if car_age <= 1:
            opt_ratio = 0.80
        elif car_age <= 3:
            opt_ratio = 0.50
        elif car_age <= 5:
            opt_ratio = 0.35
        else:
            opt_ratio = 0.20

        from services.option_package_service import calculate_catalog_option_value

        no_acc_df = df[~df['사고유무'].astype(str).str.contains('사고|교환|판금', regex=True)]
        avg_opt_new = 0
        avg_opt_score = 0
        if not no_acc_df.empty and '추가옵션' in no_acc_df.columns:
            def _get_opt_val(x):
                val = calculate_catalog_option_value(str(x), car_name=car_name, year=str(target_year_val))
                return val if val > 0 else extract_option_val(x)
            opt_vals = no_acc_df['추가옵션'].apply(_get_opt_val)
            avg_opt_new = int(opt_vals.mean()) if not opt_vals.empty else 0
            scores = [score_key_options(str(x))[0] for x in no_acc_df['추가옵션'].dropna()]
            avg_opt_score = int(np.mean(scores)) if scores else 0

        target_opts = req.targetOptions or ""
        target_score, target_opt_names = score_key_options(target_opts)
        
        # 🌟 1순위: 공식 신차가격표 카탈로그 기반 옵션 출고가 산출 (37다1840 등 지원)
        target_opt_new = calculate_catalog_option_value(target_opts, car_name=car_name, year=str(target_year_val))
        if target_opt_new == 0 and target_opts:
            target_opt_new = extract_option_val(target_opts)
            if target_opt_new == 0:
                target_opt_new = int(target_score * 1.5) if target_score > 0 else (len(target_opts.split()) * 80)

        opt_adj = 0
        if target_opt_new > 0:
            if avg_opt_new > 0 and avg_opt_new != target_opt_new:
                opt_adj = int(round((target_opt_new - avg_opt_new) * opt_ratio))
            else:
                opt_adj = int(round(target_opt_new * opt_ratio * 0.7))
        elif target_score != avg_opt_score and target_score > 0:
            opt_adj = int(round((target_score - avg_opt_score) * opt_ratio))
        elif target_opts:
            opt_adj = int(round(len(target_opt_names) * 70 * opt_ratio))

        # 4. [계산 직전 엄격 필터] 동일 연식 AND 동일 등급 매물 격리 (통계 왜곡 원천 차단)
        strict_df = DataProcessor.filter_strictly_same_year_and_grade(
            df,
            target_year=year_num,
            target_detail_model=detail_model
        )
        strict_has_data = not strict_df.empty

        # 4-1. [엄격 매물 한정 상세 보강] skipDetail=True 시 엄격 subset만 상세(성능일·재고·사고유무·외장컬러·추가옵션) 병렬 조회
        if skip_detail and strict_has_data:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from services.cookie_server import get_current_encar_cookie

            strict_carids = [
                str(cid).strip() for cid in strict_df['_carid'].dropna().unique()
                if str(cid).strip() and str(cid).strip() not in ('-', 'None', '')
            ]
            if strict_carids:
                detail_session = requests.Session()
                detail_session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Origin": "https://fem.encar.com",
                })
                cur_cookie = get_current_encar_cookie()
                if cur_cookie:
                    detail_session.headers["Cookie"] = cur_cookie

                max_workers = min(5, len(strict_carids))
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_cid = {
                        executor.submit(Scraper.fetch_car_detail, detail_session, cid): cid
                        for cid in strict_carids
                    }
                    for future in as_completed(future_to_cid):
                        cid = future_to_cid[future]
                        try:
                            detail_res = future.result()
                            mask = df['_carid'].astype(str) == str(cid)
                            df.loc[mask, '성능일'] = detail_res.get('성능일', '-')
                            df.loc[mask, '재고'] = detail_res.get('재고', '-')
                            df.loc[mask, '사고유무'] = detail_res.get('사고유무', '-')
                            df.loc[mask, '외장컬러'] = detail_res.get('외장컬러', '-')
                            df.loc[mask, '추가옵션'] = detail_res.get('추가옵션', '-')
                        except Exception as e_dt:
                            print(f"[엄격 상세조회 예외] cid={cid}: {e_dt}", flush=True)

                # 채운 df로 strict_df 재동기화
                strict_df = DataProcessor.filter_strictly_same_year_and_grade(
                    df,
                    target_year=year_num,
                    target_detail_model=detail_model
                )
                strict_has_data = not strict_df.empty

                # 채워진 성능일 기반으로 복합 정렬 재적용 (점검 완료 -> 점검일 최신 -> 가격 낮은 -> 연식 최신)
                df = DataProcessor.sort_by_perf_and_year(df)

                # 엄격 매물의 채워진 사고유무/옵션을 바탕으로 avg_opt_new, opt_adj 재계산
                no_acc_strict = strict_df[~strict_df['사고유무'].astype(str).str.contains('사고|교환|판금', regex=True)]
                if not no_acc_strict.empty and '추가옵션' in no_acc_strict.columns:
                    def _get_opt_val(x):
                        val = calculate_catalog_option_value(str(x), car_name=car_name, year=str(target_year_val))
                        return val if val > 0 else extract_option_val(x)
                    opt_vals = no_acc_strict['추가옵션'].apply(_get_opt_val)
                    avg_opt_new = int(opt_vals.mean()) if not opt_vals.empty else 0
                    scores = [score_key_options(str(x))[0] for x in no_acc_strict['추가옵션'].dropna()]
                    avg_opt_score = int(np.mean(scores)) if scores else 0

                    if target_opt_new > 0:
                        if avg_opt_new > 0 and avg_opt_new != target_opt_new:
                            opt_adj = int(round((target_opt_new - avg_opt_new) * opt_ratio))
                        else:
                            opt_adj = int(round(target_opt_new * opt_ratio * 0.7))
                    elif target_score != avg_opt_score and target_score > 0:
                        opt_adj = int(round((target_score - avg_opt_score) * opt_ratio))
                    elif target_opts:
                        opt_adj = int(round(len(target_opt_names) * 70 * opt_ratio))

        # 통계 및 AI 정밀 밸류에이션 (동일 연식·동일 등급 엄격 매물 기준)
        bench_val = Scraper.get_benchmarked_valuation(
            df,
            target_mil=mileage_num,
            target_accident=req.targetAccident or "",
            target_year=year_num,
            target_options=req.targetOptions or "",
            target_opt_adj=opt_adj,
            target_sub_model=detail_model
        ) if not df.empty else {"has_data": False}

        # 엄격 매물 기준 통계 산출 (엄격 subset이 비면 엄격 추정가는 0/해당없음 처리, 넓은 범위로 슬쩍 대체 금지)
        calc_df = strict_df if strict_has_data else pd.DataFrame()
        valid_prices = pd.to_numeric(calc_df['판매가'], errors='coerce').dropna() if not calc_df.empty else pd.Series(dtype=float)
        avg_price = int(valid_prices.mean()) if not valid_prices.empty else 0
        min_price = int(valid_prices.min()) if not valid_prices.empty else 0
        max_price = int(valid_prices.max()) if not valid_prices.empty else 0
        median_price = int(valid_prices.median()) if not valid_prices.empty else 0

        # 넓은 범위 참고용 통계 (별도 필드 보존)
        wide_prices = pd.to_numeric(df['판매가'], errors='coerce').dropna() if not df.empty else pd.Series(dtype=float)
        wide_avg_price = int(wide_prices.mean()) if not wide_prices.empty else 0
        wide_median_price = int(wide_prices.median()) if not wide_prices.empty else 0

        benchmark_price = bench_val.get("calc_individual_price", avg_price) if bench_val.get("has_data") else 0
        min_band = bench_val.get("calc_min_price", int(benchmark_price * 0.94)) if bench_val.get("has_data") else 0
        max_band = bench_val.get("calc_max_price", int(benchmark_price * 1.08)) if bench_val.get("has_data") else 0

        # 사고/무사고 격차 (엄격 매물 우선, 없으면 전체 매물)
        gap_base_df = strict_df if len(strict_df) >= 3 else df
        is_no = gap_base_df['사고유무'].astype(str).str.contains('무사고') if '사고유무' in gap_base_df.columns else pd.Series(False, index=gap_base_df.index)
        p_num = pd.to_numeric(gap_base_df['판매가'], errors='coerce')

        no_acc_avg = int(p_num[is_no].mean()) if is_no.any() else 0
        acc_avg = int(p_num[~is_no].mean()) if (~is_no).any() else 0
        acc_gap = no_acc_avg - acc_avg if no_acc_avg > 0 and acc_avg > 0 else 0

        # 사고 감가(acc_adj) 로직 이관
        market_gap = acc_gap if acc_gap > 0 else 80
        market_gap = max(40, min(market_gap, 180))
        acc_adj = 0
        target_acc_status = req.targetAccident or ""
        if "사고" in target_acc_status and "무사고" not in target_acc_status:
            acc_adj = -int(round(market_gap))
        elif "단순" in target_acc_status or "교환" in target_acc_status or "판금" in target_acc_status:
            acc_adj = -int(round(market_gap * 0.4))

        from services.autoplus_sync_service import AutoplusSyncService
        try:
            company_car_map = AutoplusSyncService.get_company_carid_map()
        except Exception:
            company_car_map = {}

        items = []
        seen_ids = set()
        seen_specs = set()
        for _, row in df.iterrows():
            cid = str(row.get('_carid', '')).strip()
            if cid and cid in seen_ids:
                continue
            if cid:
                seen_ids.add(cid)

            price_val = _safe_int(row.get('판매가', 0))
            mil_val = _safe_int(row.get('주행거리', 0))
            c_name = str(row.get('차량명', ''))
            yr_str = str(row.get('연식', ''))

            spec_key = f"{c_name}_{yr_str}_{mil_val}_{price_val}"
            if mil_val > 0 and price_val > 0:
                if spec_key in seen_specs:
                    continue
                seen_specs.add(spec_key)
            
            raw_hold = row.get('재고')
            hold_days = None
            if raw_hold is not None and str(raw_hold).strip() not in ('-', '', 'None', 'nan'):
                try:
                    hold_days = int(str(raw_hold).replace('일', '').strip())
                except (ValueError, TypeError):
                    hold_days = None

            c_name = str(row.get('차량명', ''))
            s_model = str(row.get('세부모델', ''))
            yr_str = str(row.get('연식', ''))
            perf_d = str(row.get('성능일', '-'))
            acc_str = str(row.get('사고유무', '-'))
            col_str = str(row.get('외장컬러', '-'))
            opt_s = str(row.get('추가옵션', '-'))
            link_s = str(row.get('링크', f"https://fem.encar.com/cars/detail/{cid}"))
            clean_cid = re.sub(r'\D', '', cid)
            is_company = bool(clean_cid and clean_cid in company_car_map)

            items.append({
                "id": cid,
                "checkDate": perf_d,
                "holdingDays": hold_days,
                "carName": c_name,
                "modelName": c_name,
                "subModel": s_model,
                "year": yr_str,
                "mileage": mil_val,
                "price": price_val,
                "accidentType": acc_str,
                "color": col_str,
                "optionsText": opt_s,
                "replaces": [],
                "repairs": [],
                "encarUrl": link_s,
                "photo": "",
                "isLive": True,
                "isCompanyCar": is_company,
                "_carid": cid,
                "차량명": c_name,
                "세부모델": s_model,
                "연식": yr_str,
                "주행거리": str(mil_val),
                "판매가": str(price_val),
                "링크": link_s,
                "성능일": perf_d,
                "재고": f"{hold_days}일" if hold_days is not None else "-",
                "사고유무": acc_str,
                "외장컬러": col_str,
                "추가옵션": opt_s
            })

        return {
            "success": True,
            "items": items,
            "totalModelCount": len(items),
            "filteredCount": len(items),
            "directSearchUrl": encar_url or (items[0]['encarUrl'] if items else ""),
            "stats": {
                "avg": avg_price,
                "min": min_price,
                "max": max_price,
                "median": median_price,
                "count": len(strict_df) if strict_has_data else 0,
                "strictCount": len(strict_df),
                "strictHasData": strict_has_data,
                "wideCount": len(items),
                "wideAvg": wide_avg_price if not strict_has_data else None,
                "wideMedian": wide_median_price if not strict_has_data else None,
                "benchmarkPrice": benchmark_price,
                "minBand": min_band,
                "maxBand": max_band,
                "noAccAvg": no_acc_avg,
                "accAvg": acc_avg,
                "accGap": acc_gap,
                "optAdj": opt_adj,
                "accAdj": acc_adj
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e), "items": []}


@app.get("/api/encar/verify/{car_id}")
def verify_encar_car_status(car_id: str):
    """
    엔카 공식 API를 호출하여 해당 차량의 실제 판매완료/판매중 상태를 실측 확정 (AGENTS.md 3-3)
    """
    return SoldOutTracker.verify_car_status(car_id)


# ----------------------------------------------------
# 2-2. K-Car 직영 매물 검색 및 실시간 소매 시세 API
# ----------------------------------------------------
class KcarMarketRequest(BaseModel):
    carName: Optional[str] = ""
    detailModel: Optional[str] = ""
    gradeName: Optional[str] = ""
    gradeDetailName: Optional[str] = ""
    manufacturer: Optional[str] = ""
    year: Optional[int] = 0
    mileage: Optional[int] = 0
    accident: Optional[str] = "PERFECT"
    targetOptions: Optional[Union[str, List[Dict[str, Any]]]] = ""


@app.post("/api/kcar/market")
def get_kcar_market_stats_post(req: KcarMarketRequest):
    try:
        from services.kcar_service import fetch_kcar_market_stats
        raw_g = (req.gradeName or "").strip()
        raw_gd = (req.gradeDetailName or "").strip()
        if raw_g:
            detail_model = f"{raw_g} {raw_gd}".strip() if (raw_gd and raw_gd not in raw_g) else raw_g
        else:
            detail_model = req.detailModel or ""

        return fetch_kcar_market_stats(
            car_name=req.carName or "",
            year=req.year or 0,
            detail_model=detail_model,
            mileage=req.mileage or 0,
            manufacturer=req.manufacturer or "",
            accident=req.accident or "PERFECT",
            target_options=req.targetOptions or ""
        )
    except Exception as e:
        return {"success": False, "error": str(e), "count": 0, "cars": [], "yearStats": [], "priceBins": []}


@app.get("/api/kcar/market")
def get_kcar_market_stats_get(
    carName: str = "",
    detailModel: str = "",
    gradeName: str = "",
    gradeDetailName: str = "",
    manufacturer: str = "",
    year: int = 0,
    mileage: int = 0,
    accident: str = "PERFECT",
    targetOptions: str = ""
):
    try:
        from services.kcar_service import fetch_kcar_market_stats
        raw_g = (gradeName or "").strip()
        raw_gd = (gradeDetailName or "").strip()
        if raw_g:
            d_model = f"{raw_g} {raw_gd}".strip() if (raw_gd and raw_gd not in raw_g) else raw_g
        else:
            d_model = detailModel or ""

        return fetch_kcar_market_stats(
            car_name=carName,
            year=year,
            detail_model=d_model,
            mileage=mileage,
            manufacturer=manufacturer,
            accident=accident,
            target_options=targetOptions or ""
        )
    except Exception as e:
        return {"success": False, "error": str(e), "count": 0, "cars": [], "yearStats": [], "priceBins": []}


# ----------------------------------------------------
# 3. 엔카 성능점검 / 2D 사고도면 조회 API
# ----------------------------------------------------
# 3. 엔카 성능점검 / 2D 사고도면 조회 API
# ----------------------------------------------------
PART_CODE_MAP = {
    '후드': 'HOOD', '본넷': 'HOOD',
    '앞휀더(좌)': 'F_FENDER_L', '프론트 휀더(좌)': 'F_FENDER_L', '프론트휀더(좌)': 'F_FENDER_L',
    '앞휀더(우)': 'F_FENDER_R', '프론트 휀더(우)': 'F_FENDER_R', '프론트휀더(우)': 'F_FENDER_R',
    '앞도어(좌)': 'FRONT_DOOR_L', '프론트 도어(좌)': 'FRONT_DOOR_L', '프론트도어(좌)': 'FRONT_DOOR_L',
    '앞도어(우)': 'FRONT_DOOR_R', '프론트 도어(우)': 'FRONT_DOOR_R', '프론트도어(우)': 'FRONT_DOOR_R',
    '뒤도어(좌)': 'REAR_DOOR_L', '리어 도어(좌)': 'REAR_DOOR_L', '리어도어(좌)': 'REAR_DOOR_L',
    '뒤도어(우)': 'REAR_DOOR_R', '리어 도어(우)': 'REAR_DOOR_R', '리어도어(우)': 'REAR_DOOR_R',
    '트렁크': 'TRUNK', '트렁크 리드': 'TRUNK', '트렁크리드': 'TRUNK',
    '쿼터(우)': 'QUARTER_R', '쿼터패널(우)': 'QUARTER_R', '쿼터 패널(우)': 'QUARTER_R', '뒤휀더(우)': 'QUARTER_R',
    '쿼터(좌)': 'QUARTER_L', '쿼터패널(좌)': 'QUARTER_L', '쿼터 패널(좌)': 'QUARTER_L', '뒤휀더(좌)': 'QUARTER_L',
    '루프': 'ROOF', '루프 패널': 'ROOF', '루프패널': 'ROOF',
    '사이드실(좌)': 'SIDE_SILL_L', '사이드실 패널(좌)': 'SIDE_SILL_L', '사이드실(스텝)(좌)': 'SIDE_SILL_L',
    '사이드실(우)': 'SIDE_SILL_R', '사이드실 패널(우)': 'SIDE_SILL_R', '사이드실(스텝)(우)': 'SIDE_SILL_R',
    '라디에이터': 'RADIATOR_SUPPORT', '라디에이터 서포트': 'RADIATOR_SUPPORT', '라디에이터서포트': 'RADIATOR_SUPPORT',
    '인사이드(좌)': 'INSIDE_PANEL_L', '인사이드 패널(좌)': 'INSIDE_PANEL_L', '인사이드패널(좌)': 'INSIDE_PANEL_L',
    '인사이드(우)': 'INSIDE_PANEL_R', '인사이드 패널(우)': 'INSIDE_PANEL_R', '인사이드패널(우)': 'INSIDE_PANEL_R',
    '크로스': 'CROSS_MEMBER', '크로스멤버': 'CROSS_MEMBER',
    '프론트 패널': 'FRONT_PANEL', '프론트패널': 'FRONT_PANEL',
    '사이드 멤버(좌)': 'FRONT_SIDE_MEMBER_L', '프론트 사이드 멤버(좌)': 'FRONT_SIDE_MEMBER_L',
    '사이드 멤버(우)': 'FRONT_SIDE_MEMBER_R', '프론트 사이드 멤버(우)': 'FRONT_SIDE_MEMBER_R',
    '휠하우스(좌)': 'FRONT_WHEEL_HOUSE_L', '휠 하우스(좌)': 'FRONT_WHEEL_HOUSE_L',
    '휠하우스(우)': 'FRONT_WHEEL_HOUSE_R', '휠 하우스(우)': 'FRONT_WHEEL_HOUSE_R',
    '리어 패널': 'REAR_PANEL', '리어패널': 'REAR_PANEL',
    '트렁크 플로어': 'TRUNK_FLOOR', '트렁크플로어': 'TRUNK_FLOOR',
    '필러(A)(좌)': 'PILLAR_A_L', 'A필러(좌)': 'PILLAR_A_L',
    '필러(A)(우)': 'PILLAR_A_R', 'A필러(우)': 'PILLAR_A_R',
    '필러(B)(좌)': 'PILLAR_B_L', 'B필러(좌)': 'PILLAR_B_L',
    '필러(B)(우)': 'PILLAR_B_R', 'B필러(우)': 'PILLAR_B_R',
    '필러(C)(좌)': 'PILLAR_C_L', 'C필러(좌)': 'PILLAR_C_L',
    '필러(C)(우)': 'PILLAR_C_R', 'C필러(우)': 'PILLAR_C_R',
    # 엔카 영문 부위 코드 직접 매핑
    'HOOD': 'HOOD', 'BONNET': 'HOOD',
    'FRONT_FENDER_LEFT': 'F_FENDER_L', 'FRONT_FENDER_L': 'F_FENDER_L', 'FENDER_FL': 'F_FENDER_L',
    'FRONT_FENDER_RIGHT': 'F_FENDER_R', 'FRONT_FENDER_R': 'F_FENDER_R', 'FENDER_FR': 'F_FENDER_R',
    'FRONT_DOOR_LEFT': 'FRONT_DOOR_L', 'FRONT_DOOR_L': 'FRONT_DOOR_L', 'DOOR_FL': 'FRONT_DOOR_L',
    'FRONT_DOOR_RIGHT': 'FRONT_DOOR_R', 'FRONT_DOOR_R': 'FRONT_DOOR_R', 'DOOR_FR': 'FRONT_DOOR_R',
    'REAR_DOOR_LEFT': 'REAR_DOOR_L', 'REAR_DOOR_L': 'REAR_DOOR_L', 'DOOR_RL': 'REAR_DOOR_L',
    'REAR_DOOR_RIGHT': 'REAR_DOOR_R', 'REAR_DOOR_R': 'REAR_DOOR_R', 'DOOR_RR': 'REAR_DOOR_R',
    'TRUNK': 'TRUNK', 'TRUNK_LID': 'TRUNK',
    'TRUNK_FLOOR': 'TRUNK_FLOOR',
    'REAR_PANEL': 'REAR_PANEL',
    'QUARTER_LEFT': 'QUARTER_L', 'QUARTER_L': 'QUARTER_L',
    'QUARTER_RIGHT': 'QUARTER_R', 'QUARTER_R': 'QUARTER_R',
    'ROOF': 'ROOF',
    'RADIATOR': 'RADIATOR_SUPPORT', 'RADIATOR_SUPPORT': 'RADIATOR_SUPPORT',
    # 엔카 국토부 표준 부위 코드 (P-Code)
    'P010': 'HOOD', 'P021': 'F_FENDER_L', 'P022': 'F_FENDER_R',
    'P031': 'FRONT_DOOR_L', 'P032': 'FRONT_DOOR_R',
    'P033': 'REAR_DOOR_L', 'P034': 'REAR_DOOR_R',
    'P040': 'TRUNK', 'P041': 'TRUNK',
    'P061': 'QUARTER_L', 'P062': 'QUARTER_R',
    'P070': 'ROOF', 'P081': 'SIDE_SILL_L', 'P082': 'SIDE_SILL_R',
    'P101': 'FRONT_SIDE_MEMBER_L', 'P102': 'FRONT_SIDE_MEMBER_R',
    'P111': 'FRONT_WHEEL_HOUSE_L', 'P112': 'FRONT_WHEEL_HOUSE_R',
    'P120': 'CROSS_MEMBER', 'P131': 'INSIDE_PANEL_L', 'P132': 'INSIDE_PANEL_R',
    'P141': 'SIDE_MEMBER_REAR_L', 'P142': 'SIDE_MEMBER_REAR_R',
    'P150': 'TRUNK_FLOOR', 'P160': 'REAR_PANEL', 'P181': 'REAR_PANEL',
}


def _resolve_part_code(title: str) -> Optional[str]:
    if not title:
        return None
    raw_upper = title.strip().upper()
    if raw_upper in PART_CODE_MAP:
        return PART_CODE_MAP[raw_upper]
    # 긴 키워드(더 구체적인 명칭, 예: '트렁크 플로어' > '트렁크') 우선 순회로 부분일치 가로채기 방지
    for k in sorted(PART_CODE_MAP.keys(), key=len, reverse=True):
        if k in title or k.upper() in raw_upper:
            return PART_CODE_MAP[k]
    return None


@app.get("/api/encar/inspection/{car_id}")
def get_encar_inspection(car_id: str):
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": f"https://fem.encar.com/cars/detail/{car_id}"
        })

        # 1. 차량 기본 제원 및 옵션/관리 정보 조회
        vehicle_id = car_id
        color = "미확인"
        vehicle_no = ""
        options_text = "기본 출고 사양 (추가옵션 없음)"
        reg_date_str = ""
        holding_days = None
        origin_price = 0
        new_car_price = 0
        total_option_price = 0

        try:
            v_res = session.get(f"https://api.encar.com/v1/readside/vehicle/{car_id}?include=CATEGORY,MANAGE,OPTIONS,SPEC", timeout=5)
            if v_res.status_code == 200:
                v_data = v_res.json()
                cat = v_data.get("category") or {}
                if cat.get("originPrice"):
                    origin_price = _safe_int(cat.get("originPrice", 0))
                manage = v_data.get("manage") or {}
                spec = v_data.get("spec") or {}
                if manage.get("dummyVehicleId"):
                    vehicle_id = str(manage.get("dummyVehicleId"))
                elif v_data.get("vehicleId"):
                    vehicle_id = str(v_data["vehicleId"])
                color = spec.get("colorName") or "미확인"
                vehicle_no = v_data.get("vehicleNo") or ""

                # 등록일시 파싱 (표시용 - 재고일수 산정에는 사용하지 않음)
                dt_raw = manage.get("firstAdvertisedDateTime") or manage.get("registDateTime") or ""
                if dt_raw and len(dt_raw) >= 10:
                    try:
                        v_dt = datetime.strptime(dt_raw[:10], "%Y-%m-%d")
                        reg_date_str = v_dt.strftime("%y-%m-%d")
                    except Exception:
                        pass
        except Exception as e:
            print(f"[api_server] vehicle spec fetch error: {e}")

        # 2. 추가 옵션 카탈로그 정밀 조회 (Streamlit tab_cockpit.py 146~160행과 100% 동일: choice_codes와 일치하는 실 장착 유료옵션만 필터링)
        try:
            choice_codes = [str(c) for c in (v_data.get("options", {}).get("choice", []) or [])]
            opt_names = []
            if choice_codes:
                o_res = session.get(f"https://api.encar.com/v1/readside/vehicles/car/{car_id}/options/choice", timeout=5)
                if o_res.status_code != 200 and vehicle_id != car_id:
                    o_res = session.get(f"https://api.encar.com/v1/readside/vehicles/car/{vehicle_id}/options/choice", timeout=5)

                if o_res.status_code == 200 and o_res.json():
                    catalog = o_res.json()
                    if isinstance(catalog, list):
                        for opt in catalog:
                            if isinstance(opt, dict) and str(opt.get("optionCd", "")) in choice_codes:
                                o_name = opt.get("optionName", "").strip()
                                o_price = _safe_int(opt.get("price", 0))
                                if o_price > 0:
                                    total_option_price += o_price
                                if o_name and "외장컬러" not in o_name:
                                    if o_price > 0:
                                        opt_names.append(f"{o_name}({o_price}만)")
                                    else:
                                        opt_names.append(o_name)
            if opt_names:
                options_text = " · ".join(opt_names)
            else:
                options_text = "추가 옵션 없음"
        except Exception as e:
            print(f"[api_server] options fetch error: {e}")

        # 신차가 산출 (엔카 공식 '신차대비' 화면과 100% 동일 기준: 출고 등급가 originPrice + 유료 장착옵션(외장컬러 포함) 총액)
        if origin_price > 0:
            new_car_price = origin_price + total_option_price
        elif vehicle_no:
            # 엔카 카탈로그에 originPrice가 없는 특수 매물만 차얼마 공식 원장으로 안전하게 폴백
            try:
                from services.chaolma_service import ChaolmaService
                ch_res = ChaolmaService.fetch_car_info(vehicle_no)
                if ch_res and ch_res.get("base_car_price"):
                    b = ch_res.get("base_car_price", 0)
                    o = ch_res.get("total_option_price", 0)
                    b_man = round(b / 10000) if b > 10000 else b
                    o_man = round(o / 10000) if o > 10000 else o
                    new_car_price = b_man + o_man
                    if not origin_price:
                        origin_price = b_man
            except Exception as e:
                print(f"[api_server] chaolma fallback error: {e}")

        # 3. 성능점검 상세 조회
        insp_url = f"https://api.encar.com/v1/readside/inspection/vehicle/{vehicle_id}"
        res = session.get(insp_url, timeout=5)
        if res.status_code != 200 and vehicle_id != car_id:
            insp_url = f"https://api.encar.com/v1/readside/inspection/vehicle/{car_id}"
            res = session.get(insp_url, timeout=5)

        replaces = []
        repairs = []
        replace_names = []
        repair_names = []
        inspection_date = "-"

        if res.status_code == 200:
            ij = res.json() or {}
            master = ij.get("master") or {}
            detail = master.get("detail") or {}
            raw_date = detail.get("issueDate") or (master.get("registrationDate") or "")[:10].replace("-", "")
            if raw_date and len(raw_date) >= 8:
                inspection_date = f"{raw_date[2:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

        if inspection_date and inspection_date not in ["-", "⚠️미등록", "미검사/사진", "⚠️조회실패"]:
            try:
                full_date_str = f"20{inspection_date}" if len(inspection_date) == 8 else inspection_date
                holding_days = (datetime.now() - datetime.strptime(full_date_str, "%Y-%m-%d")).days
            except Exception:
                holding_days = None
        else:
            holding_days = None

        accident_type = "미확인"
        if res.status_code == 200:
            if master.get("accident"):
                accident_type = "유사고"
            elif master.get("simpleRepair"):
                accident_type = "단순교환"
            else:
                accident_type = "완전무사고"

            all_parts = (ij.get("outers", []) or []) + (ij.get("inners", []) or [])
            if not all_parts and isinstance(master, dict):
                all_parts = (master.get("outers", []) or []) + (master.get("inners", []) or [])

            for part in (all_parts or []):
                if not isinstance(part, dict):
                    continue
                p_title = ""
                p_type = part.get("type") or {}
                if isinstance(p_type, dict):
                    p_title = p_type.get("title", "")
                if not p_title:
                    p_title = part.get("name", "") or part.get("partName", "")

                status_types = part.get("statusTypes", []) or []
                codes = [str(s.get("code", "")).upper() for s in status_types if isinstance(s, dict)]

                svg_part = _resolve_part_code(p_title)

                if "X" in codes:
                    if svg_part:
                        replaces.append(svg_part)
                    replace_names.append(p_title or "외판교환")
                elif any(c in codes for c in ["W", "C", "A", "U", "T"]):
                    if svg_part:
                        repairs.append(svg_part)
                    repair_names.append(p_title or "판금/도색")

            if replaces and not repairs:
                accident_type = f"단순교환 [교환:{len(replaces)} / 판금:0]"
            elif repairs and not replaces:
                accident_type = f"단순판금 [교환:0 / 판금:{len(repairs)}]"
            elif replaces and repairs:
                accident_type = f"단순(교환/판금) [교환:{len(replaces)} / 판금:{len(repairs)}]"

        # 3-2. 성능점검에 결과가 없으면 엔카 진단(diagnosis) API 조회 (진단차량 완벽 지원)
        if not replaces and not repairs:
            try:
                d_url = f"https://api.encar.com/v1/readside/diagnosis/vehicle/{vehicle_id}"
                d_res = session.get(d_url, timeout=5)
                if d_res.status_code != 200 and vehicle_id != car_id:
                    d_url = f"https://api.encar.com/v1/readside/diagnosis/vehicle/{car_id}"
                    d_res = session.get(d_url, timeout=5)

                if d_res.status_code == 200:
                    dj = d_res.json()
                    items_list = dj.get("items", []) or []
                    for it in items_list:
                        raw_name = it.get("name", "")
                        if raw_name in ["CHECKER_COMMENT", "OUTER_PANEL_COMMENT"]:
                            continue
                        rc = str(it.get("resultCode", "") or "").upper()
                        rt = str(it.get("result", "") or "")
                        part_name = it.get("partName") or raw_name
                        svg_part = _resolve_part_code(part_name)

                        if rc in ["REPLACEMENT", "EXCHANGE", "X"] or rt == "교환":
                            if svg_part:
                                replaces.append(svg_part)
                            replace_names.append(part_name)
                        elif rc in ["SHEET_METAL", "WELD", "W", "C", "A", "U", "T"] or any(k in rt for k in ["판금", "용접", "도색", "수리"]):
                            if svg_part and svg_part not in replaces:
                                repairs.append(svg_part)
                            repair_names.append(part_name)

                    if replaces or repairs:
                        if replaces and not repairs:
                            accident_type = f"단순교환 [교환:{len(replaces)} / 판금:0]"
                        elif repairs and not replaces:
                            accident_type = f"단순판금 [교환:0 / 판금:{len(repairs)}]"
                        else:
                            accident_type = f"단순(교환/판금) [교환:{len(replaces)} / 판금:{len(repairs)}]"
            except Exception as e:
                print(f"[api_server] diagnosis fallback error: {e}")

        # 중복 제거
        replaces = list(dict.fromkeys(replaces))
        repairs = list(dict.fromkeys(repairs))

        return {
            "success": True,
            "carId": car_id,
            "data": {
                "color": color,
                "vehicleNo": vehicle_no,
                "inspectionDate": inspection_date,
                "checkDate": inspection_date,
                "holdingDays": holding_days,
                "accidentType": accident_type,
                "replaces": replaces,
                "repairs": repairs,
                "replaceNames": replace_names,
                "repairNames": repair_names,
                "optionsText": options_text,
                "originPrice": origin_price,
                "optionPrice": total_option_price,
                "newCarPrice": new_car_price
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e), "data": None}


class EncarSoldOutRequest(BaseModel):
    carIds: Optional[List[str]] = []
    targetYear: Optional[str] = None
    expectedModel: Optional[str] = None
    detailModel: Optional[str] = None


@app.post("/api/encar/soldout")
def get_encar_soldout_stats(req: EncarSoldOutRequest):
    try:
        car_ids = [str(cid).strip() for cid in (req.carIds or []) if str(cid).strip()]
        target_year = str(req.targetYear).strip() if req.targetYear else None
        expected_model = str(req.expectedModel).strip() if req.expectedModel else None
        detail_model = str(req.detailModel).strip() if req.detailModel else None

        direct_codes = None
        if detail_model:
            resolved = MasterMappingService.resolve_encar_model(
                brand="",
                car_name=expected_model or detail_model,
                sub_model=detail_model,
                year=target_year
            )
            if not resolved and expected_model:
                resolved = MasterMappingService.resolve_encar_model(
                    brand="",
                    car_name=detail_model,
                    sub_model=detail_model,
                    year=target_year
                )

            if resolved and resolved.get("soldout_codes"):
                base_codes = resolved.get("soldout_codes", {})
                trims_dict = resolved.get("trims", {})
                matched_trim = None
                if detail_model and trims_dict:
                    _, matched_trim = MasterMappingService.match_structured_trim(detail_model, trims_dict)

                if matched_trim and matched_trim.get("soldout_clsheadcd"):
                    direct_codes = {
                        "mnfccd": base_codes.get("mnfccd", ""),
                        "mdlgroupcd": base_codes.get("mdlgroupcd", ""),
                        "mdlcd": base_codes.get("mdlcd", ""),
                        "clsheadcd": matched_trim.get("soldout_clsheadcd", ""),
                        "clsdetailcd": matched_trim.get("soldout_clsdetailcd", "")
                    }

        # carIds가 없으면 로컬 스냅샷에서 최근 ID 추출 시도
        if not car_ids and not direct_codes:
            try:
                snap_path = os.path.join(os.path.dirname(__file__), "data", "encar_snapshots.json")
                if os.path.exists(snap_path):
                    with open(snap_path, "r", encoding="utf-8") as f:
                        snaps = json.load(f)
                    if isinstance(snaps, dict):
                        if expected_model:
                            car_ids = [cid for cid, v in snaps.items() if expected_model in str(v.get("name", ""))][:10]
                        if not car_ids:
                            car_ids = list(snaps.keys())[:10]
            except Exception as e:
                print("Snapshot fallback error:", e)

        if not car_ids and not direct_codes:
            return {"success": False, "message": "후보 차량 ID가 없습니다.", "data": {"has_data": False}}

        sold_out_res = Scraper.fetch_sold_out_cars(
            car_ids,
            target_year=target_year,
            expected_model=expected_model,
            direct_codes=direct_codes
        )

        enriched_info = {}
        if sold_out_res.get("has_data") and sold_out_res.get("cars_sample"):
            enriched_info = SoldOutTracker.enrich_sold_cars(
                sold_out_res["cars_sample"],
                target_year=sold_out_res.get("target_year"),
                expected_model=expected_model
            )

        return {
            "success": True,
            "data": {
                "has_data": sold_out_res.get("has_data", False),
                "total_sold_count": sold_out_res.get("total_sold_count", 0),
                "count_30d": sold_out_res.get("count_30d", 0),
                "daily_rate": sold_out_res.get("daily_rate", 0.0),
                "velocity_badge": sold_out_res.get("velocity_badge", "보통 출고"),
                "velocity_color": sold_out_res.get("velocity_color", "#38bdf8"),
                "avg_mileage": sold_out_res.get("avg_mileage", 0),
                "latest_sold_date": sold_out_res.get("latest_sold_date", "-"),
                "target_year": sold_out_res.get("target_year"),
                "is_year_filtered": sold_out_res.get("is_year_filtered", False),
                "matched_hits": enriched_info.get("matched_hits", 0),
                "sold_avg_price": enriched_info.get("sold_avg_price", 0),
                "sold_avg_days": enriched_info.get("sold_avg_days", 0),
                "enriched_cars": enriched_info.get("enriched_cars", sold_out_res.get("cars_sample", []))
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e), "data": {"has_data": False}}


@app.get("/api/gdrive/status")
def get_gdrive_backup_status():
    return {"success": True, **GDriveBackupService.get_status()}


@app.post("/api/gdrive/sync")
def trigger_gdrive_backup_sync(includeSnapshots: bool = True):
    ok, msg = GDriveBackupService.sync_now(reason="api_manual", include_snapshots=includeSnapshots)
    return {"success": ok, "message": msg, **GDriveBackupService.get_status()}


if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True, timeout_graceful_shutdown=1)


