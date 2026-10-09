# api_server.py
import os
import re
import csv
import json
import urllib.parse
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uvicorn

from services.master_mapping import MasterMappingService
from services.sold_out_tracker import SoldOutTracker
from services.encar_service import Scraper
from services.chaolma_service import ChaolmaService
from services.git_sync_service import GitSyncService
from services.data_processor import DataProcessor

app = FastAPI(title="J-Project Local API Server", version="1.0.0")

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
def save_cookie_api(payload: CookieSavePayload):
    from services.cookie_server import set_env_variable, save_cookie
    target = (payload.target or "heydealer").lower()
    raw_cookie = payload.cookie.strip()
    if not raw_cookie:
        return {"status": "error", "message": "Cookie is empty"}
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if target == "encar":
        save_cookie(raw_cookie)
        set_env_variable("ENCAR_COOKIE", raw_cookie)
        os.environ["ENCAR_COOKIE"] = raw_cookie
    elif target in ("autoplus", "chaolma"):
        with open(os.path.join(base_dir, "autoplus_cookie.txt"), "w", encoding="utf-8") as f:
            f.write(raw_cookie)
        set_env_variable("AUTOPLUS_COOKIE", raw_cookie)
        os.environ["AUTOPLUS_COOKIE"] = raw_cookie
    else:
        with open(os.path.join(base_dir, "heydealer_cookie.txt"), "w", encoding="utf-8") as f:
            f.write(raw_cookie)
        set_env_variable("HEYDEALER_COOKIE", raw_cookie)
        os.environ["HEYDEALER_COOKIE"] = raw_cookie

    return {"status": "ok", "message": f"{target} cookie saved successfully"}


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
        
        cleaned_stats = {k: v for k, v in stats.items() if k != "sample_df"}
        return {
            "success": True,
            "data": {
                **cleaned_stats,
                "sample_list": sample_list
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
# 1. 장부 API (my_car_ledger.csv 읽기)
# ----------------------------------------------------
@app.get("/api/ledger", response_model=List[Dict[str, Any]])
def get_car_ledger():
    if not os.path.exists(LEDGER_CSV_PATH):
        return []

    items = []
    seen_ids = set()

    try:
        with open(LEDGER_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return []

            h_map = {col.strip(): i for i, col in enumerate(header)}

            for idx, row in enumerate(reader, start=1):
                if not row or not any(field.strip() for field in row):
                    continue

                def get_val(col_name: str, default: str = "") -> str:
                    pos = h_map.get(col_name)
                    if pos is not None and pos < len(row):
                        return row[pos].strip()
                    return default

                reg_date = get_val("등록일")
                car_number = get_val("차량번호")
                manufacturer = get_val("제조사")
                car_name = get_val("차량명")
                detail_model = get_val("세부모델")
                year = get_val("연식")
                mileage = get_val("주행거리")
                options = get_val("옵션")
                buy_price_raw = get_val("매입가")
                sell_price_raw = get_val("판매가")
                outer_repairs_raw = get_val("외판수리")
                repair_cost_raw = get_val("외판수리비")
                heydealer_fee_raw = get_val("헤딜수수료")
                memo = get_val("특이사항")
                status = get_val("상태")

                base_id = f"{car_number}_{reg_date}".strip("_")
                if not base_id:
                    base_id = f"item_{idx}"

                unique_id = base_id
                seq = 1
                while unique_id in seen_ids:
                    unique_id = f"{base_id}_{seq}"
                    seq += 1
                seen_ids.add(unique_id)

                item = {
                    "id": unique_id,
                    "regDate": reg_date,
                    "carNumber": car_number,
                    "manufacturer": manufacturer,
                    "carName": car_name,
                    "detailModel": detail_model,
                    "year": year,
                    "mileage": mileage,
                    "options": options,
                    "buyPrice": _safe_int(buy_price_raw),
                    "sellPrice": _safe_int(sell_price_raw),
                    "outerRepairs": _safe_int(outer_repairs_raw),
                    "repairCost": _safe_int(repair_cost_raw),
                    "heydealerFee": _safe_float(heydealer_fee_raw),
                    "memo": memo,
                    "status": status,
                    "등록일": reg_date,
                    "차량번호": car_number,
                    "제조사": manufacturer,
                    "차량명": car_name,
                    "세부모델": detail_model,
                    "연식": year,
                    "주행거리": mileage,
                    "옵션": options,
                    "매입가": buy_price_raw,
                    "판매가": sell_price_raw,
                    "외판수리": outer_repairs_raw,
                    "외판수리비": repair_cost_raw,
                    "헤딜수수료": heydealer_fee_raw,
                    "특이사항": memo,
                    "상태": status,
                }
                items.append(item)

        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"장부 CSV 파싱 오류: {str(e)}")


class CarLedgerCreateRequest(BaseModel):
    regDate: Optional[str] = ""
    carNumber: str
    manufacturer: Optional[str] = ""
    carName: Optional[str] = ""
    detailModel: Optional[str] = ""
    year: Optional[Any] = ""
    mileage: Optional[Any] = ""
    options: Optional[str] = ""
    buyPrice: Optional[Any] = 0
    sellPrice: Optional[Any] = 0
    outerRepairs: Optional[Any] = 0
    repairCost: Optional[Any] = 0
    heydealerFee: Optional[Any] = 0.0
    memo: Optional[str] = ""
    status: Optional[str] = "장부저장"


@app.post("/api/ledger")
def save_car_to_ledger(req: CarLedgerCreateRequest):
    if not req.carNumber or not req.carNumber.strip():
        raise HTTPException(status_code=400, detail="차량번호는 필수 입력 항목입니다.")

    car_no = req.carNumber.strip()

    # 등록일 기본값 (YY-MM-DD 형식)
    reg_date = req.regDate.strip() if req.regDate else datetime.now().strftime("%y-%m-%d")

    # 1. 원본 훼손 방지: 작업 전 자동 백업 생성
    backup_path = LEDGER_CSV_PATH.replace(".csv", "_backup.csv")
    try:
        if os.path.exists(LEDGER_CSV_PATH):
            import shutil
            shutil.copy2(LEDGER_CSV_PATH, backup_path)
    except Exception as e:
        print(f"[api_server] 백업 생성 경고: {e}")

    # 2. 기존 원장 읽기
    header = ['등록일', '차량번호', '제조사', '차량명', '세부모델', '연식', '주행거리', '옵션', '매입가', '판매가', '외판수리', '외판수리비', '헤딜수수료', '특이사항', '상태']
    existing_rows = []

    if os.path.exists(LEDGER_CSV_PATH):
        try:
            with open(LEDGER_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                try:
                    file_header = next(reader)
                    if file_header and len(file_header) >= 10:
                        header = [c.strip() for c in file_header]
                except StopIteration:
                    pass
                for r in reader:
                    if r and any(field.strip() for field in r):
                        existing_rows.append(r)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"기존 장부 읽기 실패: {str(e)}")

    h_map = {col.strip(): i for i, col in enumerate(header)}

    # 새 행 데이터 생성 (15개 컬럼 순서 일치)
    new_row = [""] * len(header)

    def set_col(name: str, val: Any):
        pos = h_map.get(name)
        if pos is not None:
            new_row[pos] = str(val if val is not None else "").strip()

    set_col("등록일", reg_date)
    set_col("차량번호", car_no)
    set_col("제조사", req.manufacturer or "")
    set_col("차량명", req.carName or "")
    set_col("세부모델", req.detailModel or "")
    set_col("연식", str(req.year or ""))
    set_col("주행거리", str(req.mileage or ""))
    set_col("옵션", req.options or "")
    set_col("매입가", str(req.buyPrice if req.buyPrice is not None else "0"))
    set_col("판매가", str(req.sellPrice if req.sellPrice is not None else "0"))
    set_col("외판수리", str(req.outerRepairs if req.outerRepairs is not None else "0"))
    set_col("외판수리비", str(req.repairCost if req.repairCost is not None else "0"))
    set_col("헤딜수수료", str(req.heydealerFee if req.heydealerFee is not None else "0"))
    set_col("특이사항", req.memo or "")
    set_col("상태", req.status or "장부저장")

    # 동일 차량번호 중복 방지 (기존 동일 차량이 있으면 교체, 없으면 상단 추가)
    car_no_idx = h_map.get("차량번호", 1)
    filtered_rows = [r for r in existing_rows if len(r) > car_no_idx and r[car_no_idx].strip() != car_no]
    filtered_rows.insert(0, new_row)

    # 3. UTF-8-SIG 원자적(atomic) 파일 쓰기
    temp_path = f"{LEDGER_CSV_PATH}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(filtered_rows)
        os.replace(temp_path, LEDGER_CSV_PATH)
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"장부 CSV 저장 실패: {str(e)}")

    try:
        GitSyncService.sync_push_async(f"auto: save ledger for {car_no}")
    except Exception as e:
        print(f"[api_server] Git sync push warning: {e}")

    return {
        "success": True,
        "message": f"차량 [{car_no}] 장부 영구 저장 완료",
        "carNumber": car_no,
        "totalCount": len(filtered_rows),
        "regDate": reg_date
    }


# ----------------------------------------------------
# 1-1. 장부 차량 삭제 및 수정 API (my_car_ledger.csv 원자적 반영)
# ----------------------------------------------------
class CarLedgerUpdateRequest(BaseModel):
    carNumber: Optional[str] = None
    manufacturer: Optional[str] = None
    carName: Optional[str] = None
    detailModel: Optional[str] = None
    year: Optional[Any] = None
    mileage: Optional[Any] = None
    options: Optional[str] = None
    buyPrice: Optional[Any] = None
    sellPrice: Optional[Any] = None
    outerRepairs: Optional[Any] = None
    repairCost: Optional[Any] = None
    heydealerFee: Optional[Any] = None
    memo: Optional[str] = None
    status: Optional[str] = None


@app.delete("/api/ledger/{car_key}")
def delete_car_from_ledger(car_key: str):
    key = urllib.parse.unquote(car_key).strip()
    if not key:
        raise HTTPException(status_code=400, detail="삭제할 차량 식별자가 필요합니다.")

    if not os.path.exists(LEDGER_CSV_PATH):
        raise HTTPException(status_code=404, detail="장부 파일이 존재하지 않습니다.")

    # 1. 안전 백업 생성
    backup_path = LEDGER_CSV_PATH.replace(".csv", "_backup.csv")
    try:
        import shutil
        shutil.copy2(LEDGER_CSV_PATH, backup_path)
    except Exception as e:
        print(f"[api_server] 백업 생성 경고: {e}")

    # 2. 기존 원장 읽기
    header = []
    rows = []
    try:
        with open(LEDGER_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return {"success": False, "message": "장부가 비어 있습니다.", "deletedCount": 0}
            for r in reader:
                if r and any(field.strip() for field in r):
                    rows.append(r)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"장부 CSV 읽기 실패: {str(e)}")

    h_map = {col.strip(): i for i, col in enumerate(header)}
    car_no_idx = h_map.get("차량번호", 1)
    reg_date_idx = h_map.get("등록일", 0)

    # 3. 매칭 검사 (차량번호 또는 id 일치 행 제거)
    deleted_count = 0
    new_rows = []
    for r in rows:
        row_car_no = r[car_no_idx].strip() if len(r) > car_no_idx else ""
        row_reg_date = r[reg_date_idx].strip() if len(r) > reg_date_idx else ""
        row_id = f"{row_car_no}_{row_reg_date}".strip("_")

        if row_car_no == key or row_id == key:
            deleted_count += 1
        else:
            new_rows.append(r)

    if deleted_count == 0:
        return {"success": False, "message": f"차량 [{key}]을 장부에서 찾을 수 없습니다.", "deletedCount": 0}

    # 4. 원자적(atomic) 파일 쓰기
    temp_path = f"{LEDGER_CSV_PATH}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(new_rows)
        os.replace(temp_path, LEDGER_CSV_PATH)
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"장부 CSV 삭제 반영 실패: {str(e)}")

    try:
        GitSyncService.sync_push_async(f"auto: delete ledger for {key}")
    except Exception as e:
        print(f"[api_server] Git sync push warning: {e}")

    return {
        "success": True,
        "message": f"차량 [{key}] 장부에서 삭제 완료 ({deleted_count}건)",
        "deletedCount": deleted_count,
        "totalCount": len(new_rows)
    }


@app.put("/api/ledger/{car_key}")
def update_car_in_ledger(car_key: str, req: CarLedgerUpdateRequest):
    key = urllib.parse.unquote(car_key).strip()
    if not key:
        raise HTTPException(status_code=400, detail="수정할 차량 식별자가 필요합니다.")

    if not os.path.exists(LEDGER_CSV_PATH):
        raise HTTPException(status_code=404, detail="장부 파일이 존재하지 않습니다.")

    backup_path = LEDGER_CSV_PATH.replace(".csv", "_backup.csv")
    try:
        import shutil
        shutil.copy2(LEDGER_CSV_PATH, backup_path)
    except Exception as e:
        print(f"[api_server] 백업 생성 경고: {e}")

    header = []
    rows = []
    try:
        with open(LEDGER_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return {"success": False, "message": "장부가 비어 있습니다.", "updatedCount": 0}
            for r in reader:
                if r and any(field.strip() for field in r):
                    rows.append(r)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"장부 CSV 읽기 실패: {str(e)}")

    h_map = {col.strip(): i for i, col in enumerate(header)}
    car_no_idx = h_map.get("차량번호", 1)
    reg_date_idx = h_map.get("등록일", 0)

    updated_count = 0
    new_rows = []
    for r in rows:
        row_car_no = r[car_no_idx].strip() if len(r) > car_no_idx else ""
        row_reg_date = r[reg_date_idx].strip() if len(r) > reg_date_idx else ""
        row_id = f"{row_car_no}_{row_reg_date}".strip("_")

        if row_car_no == key or row_id == key:
            updated_count += 1
            def update_col(col_name: str, new_val: Any):
                pos = h_map.get(col_name)
                if pos is not None and new_val is not None:
                    while len(r) <= pos:
                        r.append("")
                    r[pos] = str(new_val).strip()

            if req.carNumber is not None: update_col("차량번호", req.carNumber)
            if req.manufacturer is not None: update_col("제조사", req.manufacturer)
            if req.carName is not None: update_col("차량명", req.carName)
            if req.detailModel is not None: update_col("세부모델", req.detailModel)
            if req.year is not None: update_col("연식", req.year)
            if req.mileage is not None: update_col("주행거리", req.mileage)
            if req.options is not None: update_col("옵션", req.options)
            if req.buyPrice is not None: update_col("매입가", req.buyPrice)
            if req.sellPrice is not None: update_col("판매가", req.sellPrice)
            if req.outerRepairs is not None: update_col("외판수리", req.outerRepairs)
            if req.repairCost is not None: update_col("외판수리비", req.repairCost)
            if req.heydealerFee is not None: update_col("헤딜수수료", req.heydealerFee)
            if req.memo is not None: update_col("특이사항", req.memo)
            if req.status is not None: update_col("상태", req.status)

        new_rows.append(r)

    if updated_count == 0:
        return {"success": False, "message": f"차량 [{key}]을 장부에서 찾을 수 없습니다.", "updatedCount": 0}

    temp_path = f"{LEDGER_CSV_PATH}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(new_rows)
        os.replace(temp_path, LEDGER_CSV_PATH)
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"장부 CSV 수정 반영 실패: {str(e)}")

    try:
        GitSyncService.sync_push_async(f"auto: update ledger for {key}")
    except Exception as e:
        print(f"[api_server] Git sync push warning: {e}")

    return {
        "success": True,
        "message": f"차량 [{key}] 장부 수정 완료",
        "updatedCount": updated_count
    }

# ----------------------------------------------------
# 1-2. 재고 및 정산 관리 API (my_inventory_settlement.csv 원자적 연동)
# ----------------------------------------------------
SETTLEMENT_HEADER = [
    '순차', '매입일', '상태', '차량번호', '차종', '판매가', '재고일', '매입가',
    '외판수리', '상품화', '헤딜수수료', '기본제경비', '공헌이익', '실수익',
    '수수료율', '판매수수료', '수수료율_수동', '최종매출이익', '내꺼', '엔카URL'
]


@app.get("/api/settlement", response_model=List[Dict[str, Any]])
def get_inventory_settlement():
    if not os.path.exists(SETTLEMENT_CSV_PATH):
        return []

    items = []
    try:
        with open(SETTLEMENT_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return []

            h_map = {col.strip(): i for i, col in enumerate(header)}

            for idx, row in enumerate(reader, start=1):
                if not row or not any(field.strip() for field in row):
                    continue

                def get_val(col_name: str, default: str = "") -> str:
                    pos = h_map.get(col_name)
                    if pos is not None and pos < len(row):
                        return row[pos].strip()
                    return default

                order_val = _safe_int(get_val("순차"), idx)
                car_no = get_val("차량번호")
                item = {
                    "id": f"settle_{car_no or idx}",
                    "order": order_val,
                    "buyDate": get_val("매입일"),
                    "status": get_val("상태", "보유/상품화중"),
                    "carNumber": car_no,
                    "carName": get_val("차종"),
                    "sellPrice": _safe_int(get_val("판매가")),
                    "stockDays": _safe_int(get_val("재고일")),
                    "buyPrice": _safe_int(get_val("매입가")),
                    "outerRepairs": _safe_int(get_val("외판수리")),
                    "repairCost": _safe_int(get_val("상품화")),
                    "heydealerFee": _safe_int(get_val("헤딜수수료")),
                    "baseExpenses": _safe_int(get_val("기본제경비"), 15),
                    "contributionMargin": _safe_float(get_val("공헌이익")),
                    "netProfit": _safe_float(get_val("실수익")),
                    "feeRate": _safe_float(get_val("수수료율"), 0.1),
                    "salesCommission": _safe_int(get_val("판매수수료")),
                    "feeRateManual": _safe_float(get_val("수수료율_수동")),
                    "finalProfit": _safe_float(get_val("최종매출이익")),
                    "isMine": get_val("내꺼") not in ("false", "False", "0", "N"),
                    "encarUrl": get_val("엔카URL"),
                }
                items.append(item)

        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정산 CSV 파싱 오류: {str(e)}")


class InventorySettlementCreateRequest(BaseModel):
    buyDate: Optional[str] = ""
    status: Optional[str] = "보유/상품화중"
    carNumber: str
    carName: Optional[str] = ""
    sellPrice: Optional[Any] = 0
    stockDays: Optional[Any] = 0
    buyPrice: Optional[Any] = 0
    outerRepairs: Optional[Any] = 0
    repairCost: Optional[Any] = 0
    heydealerFee: Optional[Any] = 0
    baseExpenses: Optional[Any] = 15
    contributionMargin: Optional[Any] = 0
    netProfit: Optional[Any] = 0
    feeRate: Optional[Any] = 0.1
    salesCommission: Optional[Any] = 0
    finalProfit: Optional[Any] = 0
    isMine: Optional[bool] = True
    encarUrl: Optional[str] = ""


@app.post("/api/settlement")
def create_settlement_item(req: InventorySettlementCreateRequest):
    if not req.carNumber or not req.carNumber.strip():
        raise HTTPException(status_code=400, detail="차량번호는 필수 항목입니다.")

    car_no = req.carNumber.strip()

    # 1. 안전 백업 생성
    backup_path = SETTLEMENT_CSV_PATH.replace(".csv", "_backup.csv")
    try:
        if os.path.exists(SETTLEMENT_CSV_PATH):
            import shutil
            shutil.copy2(SETTLEMENT_CSV_PATH, backup_path)
    except Exception as e:
        print(f"[api_server] 정산 백업 생성 경고: {e}")

    # 2. 기존 파일 읽기
    header = list(SETTLEMENT_HEADER)
    existing_rows = []
    if os.path.exists(SETTLEMENT_CSV_PATH):
        try:
            with open(SETTLEMENT_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                try:
                    file_header = next(reader)
                    if file_header and len(file_header) >= 10:
                        header = [c.strip() for c in file_header]
                except StopIteration:
                    pass
                for r in reader:
                    if r and any(field.strip() for field in r):
                        existing_rows.append(r)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"기존 정산 파일 읽기 실패: {str(e)}")

    h_map = {col.strip(): i for i, col in enumerate(header)}
    car_no_idx = h_map.get("차량번호", 3)

    # 순차 번호 결정 (최대 순차 + 1)
    max_order = 0
    for r in existing_rows:
        if len(r) > 0:
            max_order = max(max_order, _safe_int(r[0]))
    new_order = max_order + 1

    buy_date = req.buyDate.strip() if req.buyDate else datetime.now().strftime("%m. %d")

    new_row = [""] * len(header)
    def set_col(name: str, val: Any):
        pos = h_map.get(name)
        if pos is not None:
            new_row[pos] = str(val if val is not None else "").strip()

    set_col("순차", str(new_order))
    set_col("매입일", buy_date)
    set_col("상태", req.status or "보유/상품화중")
    set_col("차량번호", car_no)
    set_col("차종", req.carName or "")
    set_col("판매가", str(req.sellPrice or 0))
    set_col("재고일", str(req.stockDays or 0))
    set_col("매입가", str(req.buyPrice or 0))
    set_col("외판수리", str(req.outerRepairs or 0))
    set_col("상품화", str(req.repairCost or 0))
    set_col("헤딜수수료", str(req.heydealerFee or 0))
    set_col("기본제경비", str(req.baseExpenses or 15))
    set_col("공헌이익", str(req.contributionMargin or 0))
    set_col("실수익", str(req.netProfit or 0))
    set_col("수수료율", str(req.feeRate or 0.1))
    set_col("판매수수료", str(req.salesCommission or 0))
    set_col("수수료율_수동", "0.0")
    set_col("최종매출이익", str(req.finalProfit or ""))
    set_col("내꺼", "true" if req.isMine else "false")
    set_col("엔카URL", req.encarUrl or "")

    # 중복 제거 후 최상단 삽입
    filtered_rows = [r for r in existing_rows if len(r) > car_no_idx and r[car_no_idx].strip() != car_no]
    filtered_rows.insert(0, new_row)

    temp_path = f"{SETTLEMENT_CSV_PATH}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(filtered_rows)
        os.replace(temp_path, SETTLEMENT_CSV_PATH)
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"정산 CSV 저장 실패: {str(e)}")

    try:
        GitSyncService.sync_push_async(f"auto: add settlement for {car_no}")
    except Exception as e:
        print(f"[api_server] Git sync push warning: {e}")

    return {
        "success": True,
        "message": f"차량 [{car_no}] 재고 정산 등록 완료",
        "carNumber": car_no,
        "totalCount": len(filtered_rows)
    }


class InventorySettlementUpdateRequest(BaseModel):
    buyDate: Optional[str] = None
    status: Optional[str] = None
    carNumber: Optional[str] = None
    carName: Optional[str] = None
    sellPrice: Optional[Any] = None
    stockDays: Optional[Any] = None
    buyPrice: Optional[Any] = None
    outerRepairs: Optional[Any] = None
    repairCost: Optional[Any] = None
    heydealerFee: Optional[Any] = None
    baseExpenses: Optional[Any] = None
    contributionMargin: Optional[Any] = None
    netProfit: Optional[Any] = None
    feeRate: Optional[Any] = None
    salesCommission: Optional[Any] = None
    finalProfit: Optional[Any] = None
    isMine: Optional[bool] = None
    encarUrl: Optional[str] = None


@app.put("/api/settlement/{car_no}")
def update_settlement_item(car_no: str, req: InventorySettlementUpdateRequest):
    key = urllib.parse.unquote(car_no).strip()
    if not key:
        raise HTTPException(status_code=400, detail="차량 식별자가 필요합니다.")

    if not os.path.exists(SETTLEMENT_CSV_PATH):
        raise HTTPException(status_code=404, detail="정산 파일이 존재하지 않습니다.")

    backup_path = SETTLEMENT_CSV_PATH.replace(".csv", "_backup.csv")
    try:
        import shutil
        shutil.copy2(SETTLEMENT_CSV_PATH, backup_path)
    except Exception as e:
        print(f"[api_server] 백업 생성 경고: {e}")

    header = []
    rows = []
    try:
        with open(SETTLEMENT_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return {"success": False, "message": "정산 파일이 비어 있습니다.", "updatedCount": 0}
            for r in reader:
                if r and any(field.strip() for field in r):
                    rows.append(r)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정산 CSV 읽기 실패: {str(e)}")

    h_map = {col.strip(): i for i, col in enumerate(header)}
    car_no_idx = h_map.get("차량번호", 3)

    updated_count = 0
    new_rows = []
    for r in rows:
        row_car_no = r[car_no_idx].strip() if len(r) > car_no_idx else ""
        if row_car_no == key or f"settle_{row_car_no}" == key:
            updated_count += 1
            def update_col(col_name: str, new_val: Any):
                pos = h_map.get(col_name)
                if pos is not None and new_val is not None:
                    while len(r) <= pos:
                        r.append("")
                    r[pos] = str(new_val).strip()

            if req.buyDate is not None: update_col("매입일", req.buyDate)
            if req.status is not None: update_col("상태", req.status)
            if req.carNumber is not None: update_col("차량번호", req.carNumber)
            if req.carName is not None: update_col("차종", req.carName)
            if req.sellPrice is not None: update_col("판매가", req.sellPrice)
            if req.stockDays is not None: update_col("재고일", req.stockDays)
            if req.buyPrice is not None: update_col("매입가", req.buyPrice)
            if req.outerRepairs is not None: update_col("외판수리", req.outerRepairs)
            if req.repairCost is not None: update_col("상품화", req.repairCost)
            if req.heydealerFee is not None: update_col("헤딜수수료", req.heydealerFee)
            if req.baseExpenses is not None: update_col("기본제경비", req.baseExpenses)
            if req.contributionMargin is not None: update_col("공헌이익", req.contributionMargin)
            if req.netProfit is not None: update_col("실수익", req.netProfit)
            if req.feeRate is not None: update_col("수수료율", req.feeRate)
            if req.salesCommission is not None: update_col("판매수수료", req.salesCommission)
            if req.finalProfit is not None: update_col("최종매출이익", req.finalProfit)
            if req.isMine is not None: update_col("내꺼", "true" if req.isMine else "false")
            if req.encarUrl is not None: update_col("엔카URL", req.encarUrl)

        new_rows.append(r)

    if updated_count == 0:
        return {"success": False, "message": f"차량 [{key}] 정산 데이터를 찾을 수 없습니다.", "updatedCount": 0}

    temp_path = f"{SETTLEMENT_CSV_PATH}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(new_rows)
        os.replace(temp_path, SETTLEMENT_CSV_PATH)
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"정산 CSV 수정 반영 실패: {str(e)}")

    try:
        GitSyncService.sync_push_async(f"auto: update settlement for {key}")
    except Exception as e:
        print(f"[api_server] Git sync push warning: {e}")

    return {
        "success": True,
        "message": f"차량 [{key}] 정산 데이터 수정 완료",
        "updatedCount": updated_count
    }


@app.delete("/api/settlement/{car_no}")
def delete_settlement_item(car_no: str):
    key = urllib.parse.unquote(car_no).strip()
    if not key:
        raise HTTPException(status_code=400, detail="차량 식별자가 필요합니다.")

    if not os.path.exists(SETTLEMENT_CSV_PATH):
        raise HTTPException(status_code=404, detail="정산 파일이 존재하지 않습니다.")

    backup_path = SETTLEMENT_CSV_PATH.replace(".csv", "_backup.csv")
    try:
        import shutil
        shutil.copy2(SETTLEMENT_CSV_PATH, backup_path)
    except Exception as e:
        print(f"[api_server] 백업 생성 경고: {e}")

    header = []
    rows = []
    try:
        with open(SETTLEMENT_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return {"success": False, "message": "정산 파일이 비어 있습니다.", "deletedCount": 0}
            for r in reader:
                if r and any(field.strip() for field in r):
                    rows.append(r)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정산 CSV 읽기 실패: {str(e)}")

    h_map = {col.strip(): i for i, col in enumerate(header)}
    car_no_idx = h_map.get("차량번호", 3)

    deleted_count = 0
    new_rows = []
    for r in rows:
        row_car_no = r[car_no_idx].strip() if len(r) > car_no_idx else ""
        if row_car_no == key or f"settle_{row_car_no}" == key:
            deleted_count += 1
        else:
            new_rows.append(r)

    if deleted_count == 0:
        return {"success": False, "message": f"차량 [{key}] 정산 데이터를 찾을 수 없습니다.", "deletedCount": 0}

    temp_path = f"{SETTLEMENT_CSV_PATH}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(new_rows)
        os.replace(temp_path, SETTLEMENT_CSV_PATH)
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"정산 CSV 삭제 반영 실패: {str(e)}")

    try:
        GitSyncService.sync_push_async(f"auto: delete settlement for {key}")
    except Exception as e:
        print(f"[api_server] Git sync push warning: {e}")

    return {
        "success": True,
        "message": f"차량 [{key}] 정산 데이터 삭제 완료",
        "deletedCount": deleted_count,
        "totalCount": len(new_rows)
    }


# ----------------------------------------------------
# 1-3. 깃허브 실시간 동기화 (Git Cloud Sync) API
# ----------------------------------------------------
@app.get("/api/git/status")
def get_git_sync_status():
    return {
        "statusBadge": GitSyncService.get_status_badge(),
        "isSyncing": GitSyncService._is_syncing,
        "lastSyncTime": GitSyncService._last_sync_time.isoformat() if GitSyncService._last_sync_time else None,
        "lastSyncStatus": GitSyncService._last_sync_status
    }


@app.post("/api/git/sync")
def trigger_git_sync(action: str = "pull"):
    if action == "pull":
        ok, msg = GitSyncService.sync_pull()
        return {"success": ok, "action": "pull", "message": msg}
    elif action == "push":
        GitSyncService.sync_push_async("manual: trigger push from web UI")
        return {"success": True, "action": "push", "message": "백그라운드 동기화 푸시 요청됨"}
    else:
        raise HTTPException(status_code=400, detail=f"알 수 없는 동기화 액션: {action}")





# 2. 엔카 실시간 시세 검색 API (스냅샷 자동 누적)
# ----------------------------------------------------
class EncarSearchRequest(BaseModel):
    url: Optional[str] = ""
    carName: Optional[str] = ""
    detailModel: Optional[str] = ""
    manufacturer: Optional[str] = ""
    year: Optional[int] = 0
    mileage: Optional[int] = 0
    targetOptions: Optional[str] = ""
    targetAccident: Optional[str] = ""


@app.post("/api/encar/search")
def search_encar_market(req: EncarSearchRequest):
    try:
        car_name = req.carName or "올 뉴 K7"
        detail_model = req.detailModel or "2.4 GDI 프레스티지"
        manufacturer = req.manufacturer or "기아"
        year_num = req.year or 17
        mileage_num = req.mileage or 149461

        encar_url = req.url
        if not encar_url or not str(encar_url).strip():
            encar_url = MasterMappingService.generate_smart_encar_url(
                car_name=car_name,
                sub_model=detail_model,
                year=year_num,
                mileage=mileage_num
            )

        df, msg = Scraper.run(encar_url, "")
        if df.empty and req.url:
            alt_url = MasterMappingService.generate_smart_encar_url(
                car_name=car_name,
                sub_model=detail_model,
                year=year_num,
                mileage=mileage_num
            )
            if alt_url and alt_url != encar_url:
                df, msg = Scraper.run(alt_url, "")
                if not df.empty:
                    encar_url = alt_url

        if df.empty:
            return {
                "success": True,
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

        # 2. 세부모델/파생트림 엄격 정밀 필터링 (스페셜, 에디션, N Line 배제)
        df = DataProcessor.filter_strictly_by_submodel(df, target_car_name=car_name, target_sub_model=detail_model)

        # 3. 2번 정렬 기준 (가격 낮은순 -> 연식 최신순 -> 성능점검순)
        df = DataProcessor.sort_by_price_year_perf(df)

        # 스냅샷 자동 누적
        try:
            SoldOutTracker.record_active_listings(df)
        except Exception as e:
            print(f"[api_server] SoldOutTracker error: {e}")

        # --- 옵션 감가(opt_adj) 로직 이관 ---
        import re
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

        no_acc_df = df[~df['무사고여부'].astype(str).str.contains('사고|교환|판금', regex=True)]
        avg_opt_new = 0
        avg_opt_score = 0
        if not no_acc_df.empty and '추가옵션' in no_acc_df.columns:
            opt_vals = no_acc_df['추가옵션'].apply(extract_option_val)
            avg_opt_new = int(opt_vals.mean()) if not opt_vals.empty else 0
            scores = [score_key_options(str(x))[0] for x in no_acc_df['추가옵션'].dropna()]
            avg_opt_score = int(np.mean(scores)) if scores else 0

        target_opts = req.targetOptions or ""
        target_score, target_opt_names = score_key_options(target_opts)
        
        target_opt_new = extract_option_val(target_opts)
        if target_opt_new == 0 and target_opts:
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

        # 통계 및 AI 정밀 밸류에이션
        bench_val = Scraper.get_benchmarked_valuation(
            df,
            target_mil=mileage_num,
            target_accident=req.targetAccident or "",
            target_year=year_num,
            target_opt_adj=opt_adj
        ) if not df.empty else {"has_data": False}

        valid_prices = pd.to_numeric(df['판매가'], errors='coerce').dropna()
        avg_price = int(valid_prices.mean()) if not valid_prices.empty else 0
        min_price = int(valid_prices.min()) if not valid_prices.empty else 0
        max_price = int(valid_prices.max()) if not valid_prices.empty else 0
        median_price = int(valid_prices.median()) if not valid_prices.empty else 0

        benchmark_price = bench_val.get("calc_individual_price", avg_price) if bench_val.get("has_data") else avg_price
        min_band = bench_val.get("calc_min_price", int(benchmark_price * 0.94)) if bench_val.get("has_data") else min_price
        max_band = bench_val.get("calc_max_price", int(benchmark_price * 1.08)) if bench_val.get("has_data") else max_price

        # 사고/무사고 격차
        is_no = df['사고유무'].astype(str).str.contains('무사고') if '사고유무' in df.columns else pd.Series(False, index=df.index)
        p_num = pd.to_numeric(df['판매가'], errors='coerce')
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
            
            raw_hold = row.get('재고', 15)
            hold_days = _safe_int(str(raw_hold).replace('일', '').strip(), 15)

            c_name = str(row.get('차량명', ''))
            s_model = str(row.get('세부모델', ''))
            yr_str = str(row.get('연식', ''))
            perf_d = str(row.get('성능일', '-'))
            acc_str = str(row.get('사고유무', '-'))
            col_str = str(row.get('외장컬러', '-'))
            opt_s = str(row.get('추가옵션', '-'))
            link_s = str(row.get('링크', f"https://fem.encar.com/cars/detail/{cid}"))

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
                "_carid": cid,
                "차량명": c_name,
                "세부모델": s_model,
                "연식": yr_str,
                "주행거리": str(mil_val),
                "판매가": str(price_val),
                "링크": link_s,
                "성능일": perf_d,
                "재고": f"{hold_days}일",
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
                "count": len(items),
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
    'QUARTER_LEFT': 'QUARTER_L', 'QUARTER_L': 'QUARTER_L',
    'QUARTER_RIGHT': 'QUARTER_R', 'QUARTER_R': 'QUARTER_R',
    'ROOF': 'ROOF',
    'RADIATOR': 'RADIATOR_SUPPORT', 'RADIATOR_SUPPORT': 'RADIATOR_SUPPORT',
}


def _resolve_part_code(title: str) -> Optional[str]:
    if not title:
        return None
    raw_upper = title.strip().upper()
    if raw_upper in PART_CODE_MAP:
        return PART_CODE_MAP[raw_upper]
    for k, v in PART_CODE_MAP.items():
        if k in title or k.upper() in raw_upper:
            return v
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
        holding_days = 15

        try:
            v_res = session.get(f"https://api.encar.com/v1/readside/vehicle/{car_id}?include=MANAGE,OPTIONS,SPEC", timeout=5)
            if v_res.status_code == 200:
                v_data = v_res.json()
                manage = v_data.get("manage") or {}
                spec = v_data.get("spec") or {}
                if manage.get("dummyVehicleId"):
                    vehicle_id = str(manage.get("dummyVehicleId"))
                elif v_data.get("vehicleId"):
                    vehicle_id = str(v_data["vehicleId"])
                color = spec.get("colorName") or "미확인"
                vehicle_no = v_data.get("vehicleNo") or ""

                # 등록일시 및 재고일수
                dt_raw = manage.get("firstAdvertisedDateTime") or manage.get("registDateTime") or ""
                if dt_raw and len(dt_raw) >= 10:
                    try:
                        v_dt = datetime.strptime(dt_raw[:10], "%Y-%m-%d")
                        diff = (datetime.now() - v_dt).days
                        if diff >= 0:
                            holding_days = max(1, diff)
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
        accident_type = "완전무사고"
        inspection_date = reg_date_str or "-"

        if res.status_code == 200:
            ij = res.json() or {}
            master = ij.get("master") or {}
            detail = master.get("detail") or {}
            raw_date = detail.get("issueDate") or (master.get("registrationDate") or "")[:10].replace("-", "")
            if raw_date and len(raw_date) >= 8:
                inspection_date = f"{raw_date[2:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

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
                "optionsText": options_text
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e), "data": None}


class EncarSoldOutRequest(BaseModel):
    carIds: Optional[List[str]] = []
    targetYear: Optional[str] = None
    expectedModel: Optional[str] = None


@app.post("/api/encar/soldout")
def get_encar_soldout_stats(req: EncarSoldOutRequest):
    try:
        car_ids = [str(cid).strip() for cid in (req.carIds or []) if str(cid).strip()]
        target_year = str(req.targetYear).strip() if req.targetYear else None
        expected_model = str(req.expectedModel).strip() if req.expectedModel else None

        # carIds가 없으면 로컬 스냅샷에서 최근 ID 추출 시도
        if not car_ids:
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

        if not car_ids:
            return {"success": False, "message": "후보 차량 ID가 없습니다.", "data": {"has_data": False}}

        sold_out_res = Scraper.fetch_sold_out_cars(
            car_ids,
            target_year=target_year,
            expected_model=expected_model
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


if __name__ == "__main__":
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=True)

