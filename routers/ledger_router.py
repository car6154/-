import os
import csv
import shutil
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.git_sync_service import GitSyncService

router = APIRouter(prefix="/api/ledger", tags=["ledger"])

BASE_DIR = Path(__file__).resolve().parent.parent
LEDGER_CSV_PATH = str(BASE_DIR / "my_car_ledger.csv")


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
# 1. 장부 API (my_car_ledger.csv 읽기)
# ----------------------------------------------------
@router.get("", response_model=List[Dict[str, Any]])
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


@router.post("")
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


@router.delete("/{car_key}")
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


@router.put("/{car_key}")
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

