import os
import csv
import shutil
import re
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.git_sync_service import GitSyncService

router = APIRouter(prefix="/api/settlement", tags=["settlement"])

BASE_DIR = Path(__file__).resolve().parent.parent
SETTLEMENT_CSV_PATH = str(BASE_DIR / "my_inventory_settlement.csv")


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

# ----------------------------------------------------
# 1-2. 재고 및 정산 관리 API (my_inventory_settlement.csv 원자적 연동)
# ----------------------------------------------------
SETTLEMENT_HEADER = [
    '순차', '매입일', '상태', '차량번호', '차종', '판매가', '재고일', '매입가',
    '외판수리', '상품화', '헤딜수수료', '기본제경비', '공헌이익', '실수익',
    '수수료율', '판매수수료', '수수료율_수동', '최종매출이익', '내꺼', '엔카URL'
]


@router.get("", response_model=List[Dict[str, Any]])
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


@router.post("")
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


@router.put("/{car_no}")
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


@router.delete("/{car_no}")
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
# 3. high A+ 매입연동 API (admin.autoplus.co.kr 실시간 땡겨오기)
# ----------------------------------------------------
class HighplusBuySyncRequest(BaseModel):
    cars: List[Dict[str, Any]]


@router.post("/sync_highplus_buy")
def sync_highplus_buy(req: HighplusBuySyncRequest):
    try:
        from services.autoplus_admin_service import AutoplusAdminService
        res = AutoplusAdminService.process_highplus_buy_data(req.cars)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"매입연동 처리 오류: {str(e)}")


@router.get("/highplus_status")
def get_highplus_status():
    from services.autoplus_admin_service import AutoplusAdminService
    return AutoplusAdminService.get_last_sync_status()


@router.post("/trigger_highplus_sync")
def trigger_highplus_sync():
    """사용자가 '매입연동' 버튼을 누르면 백엔드 쿠키로 즉시 동기화 시도 및 9월 이전 데이터 정리"""
    from services.autoplus_admin_service import AutoplusAdminService
    cleaned = AutoplusAdminService.clean_pre_september_inventory()
    res = AutoplusAdminService.fetch_and_sync_backend()
    status = AutoplusAdminService.get_last_sync_status()
    return {
        "syncResult": res,
        "status": status,
        "cleanedCount": cleaned
    }




