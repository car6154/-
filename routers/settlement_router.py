import os
import csv
import json
import shutil
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from services.git_sync_service import GitSyncService

router = APIRouter(prefix="/api/settlement", tags=["settlement"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTLEMENT_CSV_PATH = os.path.join(BASE_DIR, "my_inventory_settlement.csv")
LEDGER_CSV_PATH = os.path.join(BASE_DIR, "my_car_ledger.csv")
STATUS_FILE_PATH = os.path.join(BASE_DIR, "data", "highplus_buy_status.json")


def sync_ledger_with_settlement(car_no: str, outer: Optional[Any] = None, repair: Optional[Any] = None, fee: Optional[Any] = None, buy_p: Optional[Any] = None, sell_p: Optional[Any] = None):
    """정산표에서 수정한 외판/상품화/수수료/가격을 장부(my_car_ledger.csv)에도 1:1 동기화하여 재연동 시 덮어쓰기 영구 방지"""
    if not os.path.exists(LEDGER_CSV_PATH) or not car_no:
        return
    try:
        l_rows = []
        l_header = []
        with open(LEDGER_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            l_header = next(reader, [])
            l_rows = list(reader)
        if not l_header:
            return

        l_h_map = {col.strip(): i for i, col in enumerate(l_header)}
        c_idx = l_h_map.get("차량번호", 1)
        updated = False

        for r in l_rows:
            if len(r) > c_idx and r[c_idx].strip() == car_no:
                def set_l_col(c_name: str, val: Any):
                    pos = l_h_map.get(c_name)
                    if pos is not None and val is not None:
                        while len(r) <= pos: r.append("")
                        r[pos] = str(val).strip()

                if outer is not None: set_l_col("외판수리", outer)
                if repair is not None: set_l_col("외판수리비", repair)
                if fee is not None: set_l_col("헤딜수수료", fee)
                if buy_p is not None: set_l_col("매입가", buy_p)
                if sell_p is not None: set_l_col("판매가", sell_p)
                updated = True

        if updated:
            tmp_l = f"{LEDGER_CSV_PATH}.tmp"
            with open(tmp_l, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(l_header)
                writer.writerows(l_rows)
            os.replace(tmp_l, LEDGER_CSV_PATH)
    except Exception as e:
        print(f"[settlement_router] 장부 동기화 경고: {e}")


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
    '수수료율', '판매수수료', '수수료율_수동', '최종매출이익', '내꺼', '엔카URL',
    '주행거리', 'apCarId'
]


@router.get("", response_model=List[Dict[str, Any]])
def get_inventory_settlement(response: Response):
    # 브라우저/프록시 캐시 방지 헤더 설정 (최신 데이터 즉시 반영 보장)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    abs_path = os.path.abspath(SETTLEMENT_CSV_PATH)
    exists = os.path.exists(abs_path)
    file_size = os.path.getsize(abs_path) if exists else 0
    mtime_str = datetime.fromtimestamp(os.path.getmtime(abs_path)).strftime('%Y-%m-%d %H:%M:%S') if exists else "N/A"

    print(f"[SettlementRouter][DEBUG] GET /api/settlement 호출 | 대상 파일: {abs_path} | 존재: {exists} | 크기: {file_size}B | 수정시각: {mtime_str}", flush=True)

    if not exists or file_size == 0:
        try:
            from services.autoplus_sync_service import AutoplusSyncService
            if AutoplusSyncService.ensure_settlement_file():
                exists = os.path.exists(abs_path)
                file_size = os.path.getsize(abs_path) if exists else 0
                mtime_str = datetime.fromtimestamp(os.path.getmtime(abs_path)).strftime('%Y-%m-%d %H:%M:%S') if exists else "N/A"
                print(f"[SettlementRouter][RECOVERY] ensure_settlement_file 성공! 크기: {file_size}B", flush=True)
        except Exception as e:
            print(f"[SettlementRouter] ensure_settlement_file 예외: {e}", flush=True)

    if not exists or file_size == 0:
        print(f"[SettlementRouter][WARN] {abs_path} 파일이 존재하지 않아 빈 배열 반환", flush=True)
        return []

    items = []
    try:
        with open(abs_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                print(f"[SettlementRouter][WARN] {abs_path} 파일이 비어있음", flush=True)
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
                    "heydealerFee": _safe_float(get_val("헤딜수수료")),
                    "baseExpenses": _safe_int(get_val("기본제경비"), 15),
                    "contributionMargin": _safe_float(get_val("공헌이익")),
                    "netProfit": _safe_float(get_val("실수익")),
                    "feeRate": _safe_float(get_val("수수료율"), 0.1),
                    "salesCommission": _safe_int(get_val("판매수수료")),
                    "feeRateManual": _safe_float(get_val("수수료율_수동")),
                    "finalProfit": _safe_float(get_val("최종매출이익")),
                    "isMine": get_val("내꺼") not in ("false", "False", "0", "N"),
                    "encarUrl": get_val("엔카URL"),
                    "mileage": _safe_int(get_val("주행거리")) if get_val("주행거리") else None,
                    "apCarId": get_val("apCarId") or None,
                }
                items.append(item)

        print(f"[SettlementRouter][DEBUG] GET /api/settlement 완료 | 총 {len(items)}건 반환", flush=True)

        return items
    except Exception as e:
        print(f"[SettlementRouter][ERROR] 정산 CSV 파싱 오류: {str(e)}", flush=True)
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
        from services.gdrive_backup_service import GDriveBackupService
        GDriveBackupService.on_file_changed("settlement", source=f"add_{car_no}")
    except Exception as e:
        print(f"[settlement_router] GDrive backup trigger warning: {e}")

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

    # 2. 장부(my_car_ledger.csv)에도 동일하게 외판/수리비/수수료/매입가/판매가 동기화
    sync_ledger_with_settlement(
        key,
        outer=req.outerRepairs,
        repair=req.repairCost,
        fee=req.heydealerFee,
        buy_p=req.buyPrice,
        sell_p=req.sellPrice
    )

    try:
        from services.gdrive_backup_service import GDriveBackupService
        GDriveBackupService.on_file_changed("settlement", source=f"update_{key}")
    except Exception as e:
        print(f"[settlement_router] GDrive backup trigger warning: {e}")

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
        from services.gdrive_backup_service import GDriveBackupService
        GDriveBackupService.on_file_changed("settlement", source=f"delete_{key}")
    except Exception as e:
        print(f"[settlement_router] GDrive backup trigger warning: {e}")

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
    cars: Optional[List[Dict[str, Any]]] = None


@router.post("/sync_highplus_buy")
def sync_highplus_buy(req: Optional[HighplusBuySyncRequest] = None):
    try:
        from services.autoplus_admin_service import AutoplusAdminService
        from services.mobile_purchase_service import MobilePurchaseService

        # 1. 6대 pcsNo로 상세 API 직접 호출하여 etcAmt 및 매입 정보 조회 (목록 API 필터 우회)
        from services.mobile_purchase_service import KNOWN_PCS_IDS
        detail_res = MobilePurchaseService.get_purchase_details(KNOWN_PCS_IDS)
        cars_to_process = []

        if detail_res.get("success") and detail_res.get("cars"):
            for c in detail_res["cars"]:
                c_no = c.get("carNumber")
                etc_amt = c.get("etcAmt")
                buy_price = c.get("buyPrice")
                t_date = c.get("transferDate")

                cars_to_process.append({
                    "carNumber": c_no,
                    "carName": c.get("carName"),
                    "buyPrice": buy_price,
                    "salePrice": c.get("targetSaleAmt"),
                    "apCarId": c.get("apCarId"),
                    "mileage": c.get("mileage"),
                    "etcFee": etc_amt,
                    "transferDate": t_date,
                    "manager": "김재현",
                    "api_success": True
                })
                print(f"[SettlementRouter] 6대 상세 매입 조회: 차량={c_no}, etcAmt={etc_amt}, buyPrice={buy_price}, targetSaleAmt={c.get('targetSaleAmt')}, apCarId={c.get('apCarId')}, mileage={c.get('mileage')}", flush=True)

            print(f"[SettlementRouter] 6대 상세 API 조회 완료: 총 {len(cars_to_process)}대 수집", flush=True)

        # 2. 상세 API 실패 시 목록 API 또는 확장프로그램 fallback
        fallback_res = {}
        if not cars_to_process:
            fallback_res = MobilePurchaseService.get_purchase_list(manager="kimjh1202")
            if fallback_res.get("success") and fallback_res.get("cars"):
                for c in fallback_res["cars"]:
                    if not c.get("isSold"):
                        cars_to_process.append({
                            "carNumber": c.get("carNumber"),
                            "carName": c.get("carName"),
                            "buyPrice": c.get("buyPrice"),
                            "salePrice": c.get("targetSaleAmt"),
                            "apCarId": c.get("apCarId"),
                            "mileage": c.get("mileage"),
                            "etcFee": c.get("etcAmt"),
                            "transferDate": c.get("transferDate"),
                            "manager": "김재현",
                            "api_success": True
                        })
            elif req and req.cars:
                cars_to_process = req.cars
                print(f"[SettlementRouter] 모바일 API 미응답 -> 확장프로그램 {len(cars_to_process)}대 fallback 사용", flush=True)

        # 3. 데이터가 없고 세션 이슈(403 또는 쿠키 부재)인 경우 명확한 에러 반환
        is_session_issue = (
            not cars_to_process and (
                detail_res.get("is_no_session") or detail_res.get("is_403") or
                fallback_res.get("is_no_session") or fallback_res.get("is_403")
            )
        )

        if is_session_issue:
            is_no_sess = detail_res.get("is_no_session") or fallback_res.get("is_no_session")
            status_code_str = "NO_SESSION" if is_no_sess else "EXPIRED"
            err_message = detail_res.get("message") or fallback_res.get("message") or "high.autoplus.co.kr 모바일 세션이 만료되었습니다 (HTTP 403). high.autoplus.co.kr 로그인 후 세션을 갱신해 주세요."
            
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_record = {
                "status": status_code_str,
                "last_sync_time": now_str,
                "total_synced_cars": 0,
                "cars_in_api": [],
                "has_155_in_api": False,
                "new_inventory_added": 0,
                "inventory_updated": 0,
                "ledger_updated": 0,
                "message": err_message
            }
            try:
                os.makedirs(os.path.dirname(STATUS_FILE_PATH), exist_ok=True)
                with open(STATUS_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(status_record, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[SettlementRouter] highplus_buy_status.json 저장 실패: {e}", flush=True)

            return {
                "success": False,
                "status": status_code_str,
                "message": err_message,
                "syncedCount": 0,
                "data": status_record
            }

        res = AutoplusAdminService.process_highplus_buy_data(cars_to_process)
        if isinstance(res, dict):
            if "data" not in res:
                res["data"] = {}
            res["data"]["cars_in_api"] = [c.get("carNumber") for c in cars_to_process]
            res["data"]["has_155_in_api"] = any(c.get("carNumber") == "155라7987" for c in cars_to_process)

        # ── 상태 파일 (data/highplus_buy_status.json)에 실시간 연동 시간 및 결과 기록 ──
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st_data = res.get("data", {}) if isinstance(res, dict) else {}
        total_cars = st_data.get("total_synced_cars", len(cars_to_process))
        new_added = st_data.get("new_inventory_added", 0)
        updated_inv = st_data.get("inventory_updated", 0)
        updated_led = st_data.get("ledger_updated", 0)
        msg_str = st_data.get("message") or f"매입연동 완료: {total_cars}대 감지 (신규 {new_added}대, 갱신 {updated_inv}대, 장부승격 {updated_led}대)"

        status_record = {
            "status": "SUCCESS" if res.get("success", True) else "FAIL",
            "last_sync_time": now_str,
            "total_synced_cars": total_cars,
            "cars_in_api": [c.get("carNumber") for c in cars_to_process],
            "has_155_in_api": any(c.get("carNumber") == "155라7987" for c in cars_to_process),
            "new_inventory_added": new_added,
            "inventory_updated": updated_inv,
            "ledger_updated": updated_led,
            "message": msg_str
        }

        try:
            os.makedirs(os.path.dirname(STATUS_FILE_PATH), exist_ok=True)
            with open(STATUS_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(status_record, f, ensure_ascii=False, indent=2)
            print(f"[SettlementRouter][DEBUG] highplus_buy_status.json 갱신 완료: {now_str} | 감지 {total_cars}대, 갱신 {updated_inv}대", flush=True)
        except Exception as se:
            print(f"[SettlementRouter][WARN] highplus_buy_status.json 저장 실패: {se}", flush=True)

        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"매입연동 처리 오류: {str(e)}")


@router.get("/highplus_status")
def get_highplus_status(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    if os.path.exists(STATUS_FILE_PATH):
        try:
            with open(STATUS_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    from services.autoplus_admin_service import AutoplusAdminService
    return AutoplusAdminService.get_last_sync_status()






