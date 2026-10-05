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

    return {
        "success": True,
        "message": f"차량 [{key}] 정산 데이터 삭제 완료",
        "deletedCount": deleted_count,
        "totalCount": len(new_rows)
    }




# 2. 엔카 실시간 시세 검색 API (스냅샷 자동 누적)
# ----------------------------------------------------
class EncarSearchRequest(BaseModel):
    url: Optional[str] = ""
    carName: Optional[str] = ""
    detailModel: Optional[str] = ""
    manufacturer: Optional[str] = ""
    year: Optional[int] = 0
    mileage: Optional[int] = 0


@app.post("/api/encar/search")
def search_encar_market(req: EncarSearchRequest):
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://fem.encar.com",
            "Referer": "http://www.encar.com/"
        })

        car_name = req.carName or "올 뉴 K7"
        detail_model = req.detailModel or "2.4 GDI 프레스티지"
        manufacturer = req.manufacturer or "기아"
        year_num = req.year or 17
        mileage_num = req.mileage or 149461

        # 1. MasterMappingService를 통해 정확한 엔카 검색 액션 URL 생성
        encar_action_url = MasterMappingService.generate_smart_encar_url(
            car_name=car_name,
            sub_model=detail_model,
            year=year_num,
            mileage=mileage_num
        )

        condition = ""
        if encar_action_url and "#!" in encar_action_url:
            try:
                payload_str = urllib.parse.unquote(encar_action_url.split("#!")[1])
                payload_obj = json.loads(payload_str)
                condition = payload_obj.get("action", "")
            except Exception:
                condition = ""

        if not condition:
            # Fallback condition
            condition = f"(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.{manufacturer}._.ModelGroup.{car_name}.)))"

        safe_condition = urllib.parse.quote(condition)
        api_url = f"https://api.encar.com/search/car/list/general?count=true&q={safe_condition}&sr=%7CModifiedDate%7C0%7C100"

        raw_cars = []
        try:
            res = session.get(api_url, timeout=7)
            if res.status_code == 200:
                raw_cars = res.json().get("SearchResults", [])
        except Exception:
            raw_cars = []

        # 1차 실패 시 연식/주행거리 제약을 완화한 모델 그룹 전체 검색 시도
        if not raw_cars:
            master_match = MasterMappingService.resolve_encar_model("", car_name, detail_model, year=year_num)
            if master_match and master_match.get("model_group"):
                f_brand = master_match.get("brand", manufacturer)
                f_mg = master_match.get("model_group", "")
                f_model = master_match.get("encar_model", "")
                
                alt_cond = f"(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.{f_brand}._.(C.ModelGroup.{f_mg}._.Model.{f_model}.))))"
                try:
                    alt_res = session.get(f"https://api.encar.com/search/car/list/general?count=true&q={urllib.parse.quote(alt_cond)}&sr=%7CModifiedDate%7C0%7C100", timeout=7)
                    if alt_res.status_code == 200:
                        raw_cars = alt_res.json().get("SearchResults", [])
                except Exception:
                    pass

        # 100대 도달 시 2페이지 추가 수집
        if len(raw_cars) == 100:
            try:
                p2_url = f"https://api.encar.com/search/car/list/general?count=false&q={safe_condition}&sr=%7CModifiedDate%7C100%7C100"
                p2_res = session.get(p2_url, timeout=5)
                if p2_res.status_code == 200:
                    p2_cars = p2_res.json().get("SearchResults", [])
                    if p2_cars:
                        raw_cars.extend(p2_cars)
            except Exception:
                pass

        items = []
        prices = []
        df_rows = []

        for c in raw_cars:
            cid = str(c.get("Id", "")).strip()
            if not cid:
                continue

            name = f"{c.get('Manufacturer', '')} {c.get('Model', '')} {c.get('Badge', '')}".strip()
            year_str = str(c.get("Year", ""))
            mil_val = _safe_int(c.get("Mileage", 0))
            price_val = _safe_int(c.get("Price", 0))
            photo = f"https://ci.encar.com/carpicture{c['Photos'][0]['location']}" if c.get("Photos") and len(c["Photos"]) > 0 else ""

            detail_url = f"https://fem.encar.com/cars/detail/{cid}"

            if price_val > 0:
                prices.append(price_val)

            item = {
                "id": cid,
                "checkDate": datetime.now().strftime("%y-%m-%d"),
                "holdingDays": 1,
                "carName": name,
                "modelName": c.get("Model", ""),
                "subModel": c.get("Badge", ""),
                "year": year_str,
                "mileage": mil_val,
                "price": price_val,
                "accidentType": "확인대기",
                "color": "-",
                "optionsText": "-",
                "replaces": [],
                "repairs": [],
                "encarUrl": detail_url,
                "photo": photo,
                "isLive": True,
                "_carid": cid,
                "차량명": name,
                "연식": year_str,
                "주행거리": str(mil_val),
                "판매가": str(price_val),
                "링크": detail_url
            }
            items.append(item)
            df_rows.append(item)

        # 로컬 스냅샷 DB(data/encar_snapshots.json)에 자동 누적
        if df_rows:
            df = pd.DataFrame(df_rows)
            try:
                SoldOutTracker.record_active_listings(df)
            except Exception as e:
                print(f"[api_server] SoldOutTracker error: {e}")

        avg_price = int(sum(prices) / len(prices)) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0

        return {
            "success": True,
            "items": items,
            "totalModelCount": len(items),
            "filteredCount": len(items),
            "directSearchUrl": encar_action_url or (f"https://fem.encar.com/cars/detail/{items[0]['id']}" if items else ""),
            "stats": {
                "avg": avg_price,
                "min": min_price,
                "max": max_price,
                "count": len(items)
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
}


def _resolve_part_code(title: str) -> Optional[str]:
    if not title:
        return None
    for k, v in PART_CODE_MAP.items():
        if k in title:
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

        # 1. 차량 기본 제원 및 옵션 조회
        vehicle_id = car_id
        color = "미확인"
        vehicle_no = ""
        options_text = "기본사양"

        try:
            v_res = session.get(f"https://api.encar.com/v1/readside/vehicle/{car_id}", timeout=5)
            if v_res.status_code == 200:
                v_data = v_res.json()
                if v_data.get("vehicleId"):
                    vehicle_id = str(v_data["vehicleId"])
                color = v_data.get("spec", {}).get("colorName") or "미확인"
                vehicle_no = v_data.get("vehicleNo") or ""
        except Exception:
            pass

        # 2. 성능점검 상세 조회
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
        inspection_date = "-"

        if res.status_code == 200:
            ij = res.json()
            master = ij.get("master", {}) or {}
            raw_date = master.get("detail", {}).get("issueDate") or (master.get("registrationDate") or "")[:10].replace("-", "")
            if raw_date and len(raw_date) >= 8:
                inspection_date = f"{raw_date[2:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

            if master.get("accident"):
                accident_type = "유사고"
            elif master.get("simpleRepair"):
                accident_type = "단순교환"
            else:
                accident_type = "완전무사고"

            all_parts = (ij.get("outers", []) or []) + (ij.get("inners", []) or [])
            if not all_parts and "master" in ij:
                all_parts = (ij["master"].get("outers", []) or []) + (ij["master"].get("inners", []) or [])

            for part in all_parts:
                p_title = ""
                if isinstance(part.get("type"), dict):
                    p_title = part["type"].get("title", "")
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
                accident_type = f"단순교환({len(replace_names)}부위)"
            elif repairs and not replaces:
                accident_type = f"단순판금({len(repair_names)}부위)"
            elif replaces and repairs:
                accident_type = f"단순(교환{len(replace_names)}/판금{len(repair_names)})"

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

