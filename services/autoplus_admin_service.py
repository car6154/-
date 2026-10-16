# services/autoplus_admin_service.py
"""
오토플러스 high A+ (admin.autoplus.co.kr) 매입 데이터 자동 연동 서비스
- 크롬 확장프로그램이 매입조회(SPPOL10001) 및 매입등록 화면에서 실시간 추출한 매입 데이터를 수신
- 1) 제이프로 매입 장부(my_car_ledger.csv)에서 상태를 [매입확정]으로 자동 승격
- 2) 실전 재고 정산표(my_inventory_settlement.csv)의 보유 재고로 자동 등록 (외판, 수수료, 매입가 반영)
- 안전 백업(backups/) 후 원자적 CSV 갱신 및 Git 자동 동기화
"""

import os
import csv
import json
import shutil
import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from services.git_sync_service import GitSyncService

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

LEDGER_CSV = os.path.join(BASE_DIR, "my_car_ledger.csv")
SETTLEMENT_CSV = os.path.join(BASE_DIR, "my_inventory_settlement.csv")
STATUS_FILE = os.path.join(DATA_DIR, "highplus_buy_status.json")

MANAGER = "김재현"


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    clean = re.sub(r"[^\d.-]", "", str(val)).strip()
    try:
        return int(float(clean))
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    clean = re.sub(r"[^\d.-]", "", str(val)).strip()
    try:
        return float(clean)
    except (ValueError, TypeError):
        return default


def calculate_heydealer_fee(buy_price_man: float, purchase_type: str = "셀프(기본)", is_light: bool = False) -> float:
    """
    헤이딜러 실측 수수료 구간표 자동 계산기
    - 셀프(기본): <=100만: 7.5만 / <=500만: 18.5만 / <=1000만: (경차 19.0만 / 일반 24.5만) / <=3000만: 25.0만 / >3000만: 36.0만
    - 제로: <=100만: 14만 / <=500만: 30만 / <=1000만: (경차 30.5만 / 일반 36.5만) / <=1500만: 36.5만 / <=3000만: 39.5만 / <=4000만: 47.5만 / >4000만: 50.5만
    """
    p = float(buy_price_man or 0)
    p_type = str(purchase_type or "")
    if "제로" in p_type:
        if p <= 100: return 14.0
        if p <= 500: return 30.0
        if p <= 1000: return 30.5 if is_light else 36.5
        if p <= 1500: return 36.5
        if p <= 3000: return 39.5
        if p <= 4000: return 47.5
        return 50.5
    elif "셀프" in p_type or "헤이딜러" in p_type or not p_type:
        if p <= 100: return 7.5
        if p <= 500: return 18.5
        if p <= 1000: return 19.0 if is_light else 24.5
        if p <= 3000: return 25.0
        return 36.0
    return 0.0


class AutoplusAdminService:
    @classmethod
    def get_last_sync_status(cls) -> Dict[str, Any]:
        """최근 매입연동 상태 조회"""
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "status": "NONE",
            "last_sync_time": None,
            "total_synced_cars": 0,
            "new_inventory_added": 0,
            "ledger_updated": 0,
            "message": "매입연동 이력이 없습니다."
        }

    @classmethod
    def _save_status(cls, data: Dict[str, Any]):
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AutoplusAdminService] 상태 저장 오류: {e}", flush=True)

    @classmethod
    def backup_file(cls, filepath: str) -> Optional[str]:
        """기존 CSV 파일을 backups/ 폴더에 타임스탬프와 함께 백업"""
        if not os.path.exists(filepath):
            return None
        os.makedirs(BACKUP_DIR, exist_ok=True)
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"{name}_{now_str}{ext}")
        try:
            shutil.copy2(filepath, backup_path)
            return backup_path
        except Exception as e:
            print(f"[AutoplusAdminService] 백업 실패 ({filepath}): {e}", flush=True)
            return None

    @classmethod
    def process_highplus_buy_data(cls, buy_cars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        high A+ 매입 데이터 수신 및 장부/재고 정산표 연동
        buy_cars: [
            {
                "carNumber": "37다1840",
                "carName": "기아 올 뉴카니발 9인승 디젤 프레스티지",
                "modelYear": "2018",
                "buyPrice": 6540000,          # 원 단위 또는 만원 단위
                "transferDate": "2026-10-02",  # 이전일자
                "billDate": "2026-10-01",      # 계산서일자
                "purchaseType": "헤이딜러(셀프)",
                "pid": "C26100100177",
                "outerRepairs": 3,             # 외판 판수 (옵션)
                "etcFee": 545000,              # 기타비용 (헤딜+영업사원 수수료, 옵션)
                "repairCost": 260000,          # 상품화비용 (옵션)
                "scrapDeduction": 594545       # 폐자원공제액 (옵션)
            },
            ...
        ]
        """
        if not buy_cars or not isinstance(buy_cars, list):
            return {"success": False, "message": "전송된 매입 데이터가 없습니다.", "syncedCount": 0}

        ledger_cars = cls._load_valid_ledger_cars()

        cleaned_cars = []
        for c in buy_cars:
            car_no = str(c.get("carNumber", "")).replace(" ", "").strip()
            if not car_no or len(car_no) < 6:
                continue

            mgr = str(c.get("manager", "")).strip()
            if mgr and mgr != MANAGER:
                continue
            if car_no not in ledger_cars:
                continue

            # 금액 만원 단위 정규화
            raw_p = _safe_float(c.get("buyPrice", 0))
            buy_price_man = round(raw_p / 10000) if raw_p > 50000 else round(raw_p)

            raw_fee = _safe_float(c.get("etcFee", c.get("heydealerFee", 0)))
            fee_man = round(raw_fee / 10000, 1) if raw_fee > 5000 else round(raw_fee, 1)

            raw_rep = _safe_float(c.get("repairCost", 0))
            rep_man = round(raw_rep / 10000) if raw_rep > 5000 else round(raw_rep)

            raw_date = str(c.get("transferDate") or c.get("billDate") or "").strip()
            buy_date_disp = ""
            stock_days = 0
            if raw_date:
                m = re.search(r"(\d{4})[^\d]?(\d{1,2})[^\d]?(\d{1,2})", raw_date)
                if m:
                    y, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    # 2026년 9월 1일 이전 매입건은 동기화에서 제외
                    if y < 2026 or (y == 2026 and mm < 9):
                        continue
                    buy_date_disp = f"{mm:02d}. {dd:02d}"
                    try:
                        d_obj = date(y, mm, dd)
                        stock_days = max(0, (date.today() - d_obj).days)
                    except:
                        pass
                else:
                    # '09. 07', '10. 15' 형태일 경우
                    m_short = re.search(r"^0?(\d{1,2})[^\d]?(\d{1,2})", raw_date)
                    if m_short:
                        s_mm = int(m_short.group(1))
                        if s_mm < 9:
                            continue
                        buy_date_disp = raw_date
            else:
                continue # 날짜가 아예 없으면 스킵

            if not buy_date_disp:
                continue

            cleaned_cars.append({
                "carNumber": car_no,
                "carName": str(c.get("carName", "")).strip(),
                "modelYear": str(c.get("modelYear", "")).strip(),
                "buyPrice": buy_price_man,
                "buyDate": buy_date_disp,
                "stockDays": stock_days,
                "outerRepairs": _safe_int(c.get("outerRepairs", 0)),
                "repairCost": rep_man,
                "heydealerFee": fee_man,
                "purchaseType": str(c.get("purchaseType", "")).strip(),
                "pid": str(c.get("pid", "")).strip(),
                "scrapDeduction": _safe_int(c.get("scrapDeduction", 0))
            })

        if not cleaned_cars:
            return {"success": False, "message": "유효한 차량번호를 가진 매입 데이터가 없습니다.", "syncedCount": 0}

        # ── 1. 제이프로 매입장부 (my_car_ledger.csv) 상태 [매입확정] 승격 ──
        ledger_updated = cls._sync_ledger_cars(cleaned_cars)

        # ── 2. 실전 재고 정산표 (my_inventory_settlement.csv) 보유 재고 연동 ──
        inventory_res = cls._sync_settlement_inventory(cleaned_cars)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_info = {
            "status": "SUCCESS",
            "last_sync_time": now_str,
            "total_synced_cars": len(cleaned_cars),
            "new_inventory_added": inventory_res["added"],
            "inventory_updated": inventory_res["updated"],
            "ledger_updated": ledger_updated,
            "message": f"매입연동 완료: {len(cleaned_cars)}대 감지 (신규 {inventory_res['added']}대, 갱신 {inventory_res['updated']}대, 장부승격 {ledger_updated}대)"
        }
        cls._save_status(status_info)

        # Git 비동기 푸시
        try:
            GitSyncService.sync_push_async(f"auto: sync highplus buy {len(cleaned_cars)} cars")
        except Exception:
            pass

        return {
            "success": True,
            "message": status_info["message"],
            "data": status_info
        }

    @classmethod
    def _sync_ledger_cars(cls, cleaned_cars: List[Dict[str, Any]]) -> int:
        """my_car_ledger.csv의 동일 차량 상태를 [매입확정]으로 갱신"""
        if not os.path.exists(LEDGER_CSV):
            return 0

        cls.backup_file(LEDGER_CSV)
        cars_by_no = {c["carNumber"]: c for c in cleaned_cars}
        updated_count = 0

        encodings = ['utf-8-sig', 'utf-8', 'cp949']
        header = []
        rows = []

        for enc in encodings:
            try:
                with open(LEDGER_CSV, "r", encoding=enc, newline="") as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    for r in reader:
                        if r:
                            rows.append(r)
                break
            except Exception:
                continue

        if not header:
            return 0

        h_map = {col.strip(): i for i, col in enumerate(header)}
        car_no_idx = h_map.get("차량번호")
        status_idx = h_map.get("상태")
        buy_p_idx = h_map.get("실매입가") or h_map.get("매입가")

        if car_no_idx is None or status_idx is None:
            return 0

        new_rows = []
        for r in rows:
            if len(r) > car_no_idx:
                c_no = r[car_no_idx].strip()
                if c_no in cars_by_no:
                    c_info = cars_by_no[c_no]
                    # 상태 매입확정으로 전환
                    r[status_idx] = "매입확정"
                    if buy_p_idx is not None and len(r) > buy_p_idx and c_info["buyPrice"] > 0:
                        r[buy_p_idx] = str(c_info["buyPrice"])
                    updated_count += 1
            new_rows.append(r)

        if updated_count > 0:
            temp_path = f"{LEDGER_CSV}.tmp"
            try:
                with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(new_rows)
                os.replace(temp_path, LEDGER_CSV)
            except Exception as e:
                if os.path.exists(temp_path): os.remove(temp_path)
                print(f"[AutoplusAdminService] 장부 저장 오류: {e}")

        return updated_count

    @classmethod
    def _sync_settlement_inventory(cls, cleaned_cars: List[Dict[str, Any]]) -> Dict[str, int]:
        """my_inventory_settlement.csv에 보유 재고로 안전하게 Upsert"""
        if not os.path.exists(SETTLEMENT_CSV):
            return {"added": 0, "updated": 0}
        return cls._sync_inventory_settlement_csv(cleaned_cars)

    @classmethod
    def _load_valid_ledger_cars(cls) -> set:
        """my_car_ledger.csv에서 2026-09-01 이후 매입/등록된 차량번호 집합 로드"""
        ledger_cars = set()
        if not os.path.exists(LEDGER_CSV):
            return ledger_cars
        for enc in ['utf-8-sig', 'utf-8', 'cp949']:
            try:
                with open(LEDGER_CSV, "r", encoding=enc) as f:
                    reader = csv.reader(f)
                    header = next(reader, [])
                    h_map = {col.strip(): i for i, col in enumerate(header)}
                    c_idx = h_map.get("차량번호")
                    d_idx = h_map.get("매입일") if h_map.get("매입일") is not None else h_map.get("등록일")
                    if c_idx is None:
                        continue
                    for r in reader:
                        if not r or len(r) <= c_idx:
                            continue
                        c_no = str(r[c_idx]).replace(" ", "").strip()
                        if not c_no:
                            continue
                        if d_idx is not None and len(r) > d_idx:
                            raw_date = str(r[d_idx]).strip()
                            m_d = re.search(r"(\d{2,4})[-/.]0?(\d{1,2})", raw_date)
                            if m_d:
                                y = int(m_d.group(1))
                                if y < 100:
                                    y += 2000
                                mm = int(m_d.group(2))
                                if y < 2026 or (y == 2026 and mm < 9):
                                    continue
                        ledger_cars.add(c_no)
                break
            except Exception:
                continue
        return ledger_cars

    @classmethod
    def _load_ledger_info_map(cls) -> Dict[str, Dict[str, Any]]:
        """my_car_ledger.csv에서 차량번호별 외판수리, 상품화, 차종, 헤딜수수료 로드"""
        res = {}
        if not os.path.exists(LEDGER_CSV):
            return res
        for enc in ['utf-8-sig', 'utf-8', 'cp949']:
            try:
                with open(LEDGER_CSV, "r", encoding=enc) as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        cno = str(r.get("차량번호", "")).replace(" ", "").strip()
                        if not cno or cno in res: continue
                        outer = _safe_int(r.get("외판수리", 0))
                        rep = _safe_int(r.get("외판수리비", 0))
                        fee = _safe_float(r.get("헤딜수수료", 0))
                        m_name = f"{r.get('제조사', '')} {r.get('차량명', '')} {r.get('세부모델', '')}".strip()
                        res[cno] = {
                            "outer": outer,
                            "repairCost": rep,
                            "fee": fee,
                            "carName": m_name
                        }
                break
            except Exception:
                continue
        return res

    @classmethod
    def _sync_inventory_settlement_csv(cls, cleaned_cars: List[Dict[str, Any]]) -> Dict[str, int]:
        """실전 재고 정산표(my_inventory_settlement.csv) 동기화 (외판은 장부 기준 보존, 매입가/수수료만 반영)"""
        if not os.path.exists(SETTLEMENT_CSV):
            return {"added": 0, "updated": 0}

        cls.backup_file(SETTLEMENT_CSV)
        cars_by_no = {c["carNumber"]: c for c in cleaned_cars}
        ledger_map = cls._load_ledger_info_map()
        ledger_cars = cls._load_valid_ledger_cars()

        header = [
            '순차', '매입일', '상태', '차량번호', '차종', '판매가', '재고일', '매입가',
            '외판수리', '상품화', '헤딜수수료', '기본제경비', '공헌이익', '실수익',
            '수수료율', '판매수수료', '수수료율_수동', '최종매출이익', '내꺼', '엔카URL'
        ]
        rows = []

        encodings = ['utf-8-sig', 'utf-8', 'cp949']
        for enc in encodings:
            try:
                with open(SETTLEMENT_CSV, "r", encoding=enc, newline="") as f:
                    reader = csv.reader(f)
                    file_header = next(reader)
                    if file_header and len(file_header) >= 10:
                        header = [c.strip() for c in file_header]
                    for r in reader:
                        if r and any(field.strip() for field in r):
                            rows.append(r)
                break
            except Exception:
                continue

        h_map = {col.strip(): i for i, col in enumerate(header)}
        car_no_idx = h_map.get("차량번호", 3)
        date_idx = h_map.get("매입일", 1)

        existing_cars = set()
        updated_count = 0
        new_rows = []

        # 1) 기존 행 갱신 (없는 차량 0453, 9940 및 9월 이전 과거 건 제거, 외판은 장부에서 복구)
        for r in rows:
            if len(r) > car_no_idx:
                c_no = r[car_no_idx].strip()
                b_date = r[date_idx].strip() if len(r) > date_idx else ""

                # 없는 차량 및 타인 차량 제거 (매입장부 기준)
                if c_no and c_no not in ledger_cars:
                    continue

                # 2026년 9월 이전 매입건(04., 05., 06., 07., 08. 등) 필터링 제거
                m_d = re.search(r"(?:20\d{2}[-/.])?0?(\d{1,2})[-/.]", b_date)
                if m_d:
                    m_val = int(m_d.group(1))
                    if m_val < 9:
                        continue

                existing_cars.add(c_no)

                def update_val(col_name: str, new_val: Any):
                    pos = h_map.get(col_name)
                    if pos is not None and new_val is not None:
                        while len(r) <= pos: r.append("")
                        r[pos] = str(new_val).strip()

                # 외판 및 상품화: 사용자가 수정한 실제 외판값을 100% 영구 보존! (최초 1회만 장부값 가져옴)
                if c_no in ledger_map:
                    l_info = ledger_map[c_no]
                    cur_outer_str = r[h_map.get("외판수리", 8)].strip() if len(r) > h_map.get("외판수리", 8) else ""
                    cur_rep_str = r[h_map.get("상품화", 9)].strip() if len(r) > h_map.get("상품화", 9) else ""
                    if cur_outer_str == "" and l_info["outer"] > 0:
                        update_val("외판수리", l_info["outer"])
                    if cur_rep_str == "" and (l_info["repairCost"] > 0 or l_info["outer"] > 0):
                        rep = l_info["repairCost"] if l_info["repairCost"] > 0 else (l_info["outer"] * 13)
                        update_val("상품화", rep)
                    # 수수료: 44.0 등 장부 오류값 배제 및 자동 계산기 적용
                    raw_l_fee = l_info["fee"]
                    b_p = _safe_float(r[h_map.get("매입가", 7)])
                    c_fee = calculate_heydealer_fee(b_p, "셀프(기본)")
                    fee_to_set = raw_l_fee if raw_l_fee in [55.0, 54.5] else (c_fee if c_fee > 0 else raw_l_fee)
                    cur_fee = _safe_float(r[h_map.get("헤딜수수료", 10)]) if len(r) > 10 else 0
                    if fee_to_set > 0 and (cur_fee == 0 or cur_fee == 44.0):
                        update_val("헤딜수수료", fee_to_set)
                    if l_info["carName"] and not r[h_map.get("차종", 4)]:
                        update_val("차종", l_info["carName"])

                # high A+에서는 매입가와 기타비용(수수료)만 반영 (외판은 건드리지 않음!)
                if c_no in cars_by_no:
                    c_info = cars_by_no[c_no]
                    if c_info["buyPrice"] > 0:
                        update_val("매입가", c_info["buyPrice"])
                    if c_info["buyDate"]:
                        update_val("매입일", c_info["buyDate"])
                    if c_info["heydealerFee"] > 0:
                        update_val("헤딜수수료", c_info["heydealerFee"])
                    updated_count += 1

                new_rows.append(r)

        # 2) 신규 차량 추가 (Upsert)
        added_count = 0
        for c_no, c_info in cars_by_no.items():
            if c_no not in existing_cars:
                row_new = [""] * len(header)
                def set_new(col_name: str, val: Any):
                    pos = h_map.get(col_name)
                    if pos is not None:
                        row_new[pos] = str(val if val is not None else "").strip()

                l_info = ledger_map.get(c_no, {})
                outer = l_info.get("outer", 0)
                rep_cost = l_info.get("repairCost", 0) or (outer * 13 if outer > 0 else 0)
                
                # 수수료 결정 (high A+ 기타비용 우선 -> 특수대행료 55만 -> 헤이딜러 표준구간표 계산기)
                raw_l_fee = l_info.get("fee", 0)
                calc_fee = calculate_heydealer_fee(c_info["buyPrice"], c_info.get("purchaseType", "셀프(기본)"))
                if c_info["heydealerFee"] > 0:
                    fee = c_info["heydealerFee"]
                elif raw_l_fee in [55.0, 54.5]:
                    fee = raw_l_fee
                elif calc_fee > 0:
                    fee = calc_fee
                else:
                    fee = raw_l_fee
                car_name = c_info["carName"] or l_info.get("carName", "")

                set_new("순차", "0")
                set_new("매입일", c_info["buyDate"])
                set_new("상태", "보유/상품화중")
                set_new("차량번호", c_no)
                set_new("차종", car_name)
                set_new("판매가", "0")
                set_new("재고일", str(c_info["stockDays"]))
                set_new("매입가", str(c_info["buyPrice"]))
                set_new("외판수리", str(outer))
                set_new("상품화", str(rep_cost))
                set_new("헤딜수수료", str(fee))
                set_new("기본제경비", "15")
                set_new("공헌이익", "0")
                set_new("실수익", "0")
                set_new("수수료율", "0.1")
                set_new("판매수수료", "0")
                set_new("수수료율_수동", "0.0")
                set_new("최종매출이익", "")
                set_new("내꺼", "true")
                set_new("엔카URL", "")

                new_rows.insert(0, row_new)
                added_count += 1

        # 3) 순차를 1부터 위에서부터 깔끔하게 재부여 (1, 2, 3, 4, 5...)
        for idx, row in enumerate(new_rows):
            if len(row) > 0:
                row[0] = str(idx + 1)

        # 원자적 파일 교체
        temp_path = f"{SETTLEMENT_CSV}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(new_rows)
            os.replace(temp_path, SETTLEMENT_CSV)
            # [자동화 파이프라인] 매입 연동 완료 즉시 오플 전사 재고의 판매가, 재고일, 엔카URL을 100% 자동 매칭
            try:
                from services.autoplus_sync_service import AutoplusSyncService
                AutoplusSyncService._sync_settlement_ledger()
            except Exception as se:
                print(f"[AutoplusAdminService] 오플 재고 자동 매칭 연동 경고: {se}", flush=True)
        except Exception as e:
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
            print(f"[AutoplusAdminService] 정산표 저장 오류: {e}")
        return {"added": added_count, "updated": updated_count}

    @classmethod
    def parse_sppol10001_html(cls, html_content: str) -> List[Dict[str, Any]]:
        """admin.autoplus.co.kr/spot/syspo/SPPOL10001 HTML 파싱"""
        cars = []
        if not html_content:
            return cars

        tr_matches = re.findall(r"<tr[^>]*>(.*?)</tr>", html_content, re.DOTALL | re.IGNORECASE)
        for tr in tr_matches:
            m_car = re.search(r"\b(\d{2,3}[가-힣]\s*\d{4})\b", tr)
            if not m_car:
                continue
            car_no = m_car.group(1).replace(" ", "")

            m_pid = re.search(r"\b(C\d{11})\b", tr)
            pid = m_pid.group(1) if m_pid else ""

            m_po = re.search(r"poId=(\d+)", tr, re.IGNORECASE) or re.search(r"poIdList['\"\s:=]+(\d+)", tr, re.IGNORECASE)
            po_id = m_po.group(1) if m_po else ""

            dates = re.findall(r"\b(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2})\b", tr)
            transfer_date = dates[-1] if dates else ""
            bill_date = dates[0] if len(dates) > 1 else transfer_date

            # 2026년 9월 이전 매입건 제외
            target_date = transfer_date or bill_date
            if target_date:
                m_ym = re.search(r"(\d{4})[-/.](\d{1,2})", target_date)
                if m_ym:
                    y, mm = int(m_ym.group(1)), int(m_ym.group(2))
                    if y < 2026 or (y == 2026 and mm < 9):
                        continue

            raw_nums = re.findall(r"\b\d{1,3}(?:,\d{3}){2,}\b", tr)
            buy_price = 0
            for rn in raw_nums:
                val = int(rn.replace(",", ""))
                if val >= 1000000:
                    buy_price = val
                    break

            m_year = re.search(r"\b(201\d|202\d)\b", tr)
            model_year = m_year.group(1) if m_year else ""

            tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.DOTALL | re.IGNORECASE)
            car_name = ""
            for td in tds:
                clean_td = re.sub(r"<[^>]+>", "", td).strip()
                if re.search(r"(현대|기아|제네시스|쉐보레|르노|쌍용|KGM|BMW|벤츠|아우디|볼보|폭스바겐|포르쉐|렉서스|카니발|아반떼|투싼|캐스퍼|쏘렌토|그랜저|스포티지)", clean_td):
                    car_name = clean_td
                    break

            # 담당자 매칭 (김재현 등)
            manager = ""
            if "김재현" in tr:
                manager = "김재현"

            scrap_deduction = 0
            m_scrap = re.findall(r"\b(\d{1,3}(?:,\d{3})+)\b", tr)
            for ms in m_scrap:
                val = int(ms.replace(",", ""))
                if 100000 <= val < 10000000 and val != buy_price:
                    scrap_deduction = val

            cars.append({
                "carNumber": car_no,
                "carName": car_name,
                "modelYear": model_year,
                "buyPrice": buy_price,
                "transferDate": transfer_date,
                "billDate": bill_date,
                "pid": pid,
                "poId": po_id,
                "manager": manager,
                "scrapDeduction": scrap_deduction
            })

        return cars

    @classmethod
    def clean_pre_september_inventory(cls) -> int:
        """2026년 9월 1일 이전 과거 데이터 및 없는 차량 정리, 외판 복구, 순차 1부터 재부여"""
        if not os.path.exists(SETTLEMENT_CSV):
            return 0
        cls.backup_file(SETTLEMENT_CSV)
        header = []
        clean_rows = []
        removed_count = 0
        ledger_map = cls._load_ledger_info_map()
        ledger_cars = cls._load_valid_ledger_cars()

        for enc in ['utf-8-sig', 'utf-8', 'cp949']:
            try:
                with open(SETTLEMENT_CSV, 'r', encoding=enc) as f:
                    reader = csv.reader(f)
                    header = next(reader, [])
                    h_map = {col.strip(): i for i, col in enumerate(header)}
                    date_idx = h_map.get("매입일", 1)
                    car_no_idx = h_map.get("차량번호", 3)
                    for r in reader:
                        if not r or not any(field.strip() for field in r): continue
                        c_no = r[car_no_idx].strip() if len(r) > car_no_idx else ""

                        # 1. 없는 차량 및 전사 타인 차량 제거 (매입장부 기준)
                        if c_no and c_no not in ledger_cars:
                            removed_count += 1
                            continue

                        # 2. 9월 이전 매입건 제거
                        b_date = r[date_idx].strip() if len(r) > date_idx else ""
                        m_d = re.search(r"(?:20\d{2}[-/.])?0?(\d{1,2})[-/.]", b_date)
                        if m_d:
                            m_val = int(m_d.group(1))
                            if m_val < 9:
                                removed_count += 1
                                continue

                        # 3. 외판/상품화 복구 (장부 기준)
                        if c_no in ledger_map:
                            l_info = ledger_map[c_no]
                            p_out = h_map.get("외판수리")
                            p_rep = h_map.get("상품화")
                            p_fee = h_map.get("헤딜수수료")
                            p_name = h_map.get("차종")

                            # 외판/상품화: 사용자가 정산표에서 수정한 실측값을 100% 보존 (비어있을 때만 최초 1회 세팅)
                            cur_out_s = r[p_out].strip() if p_out is not None and len(r) > p_out else ""
                            cur_rep_s = r[p_rep].strip() if p_rep is not None and len(r) > p_rep else ""

                            if p_out is not None and cur_out_s == "" and l_info["outer"] > 0:
                                while len(r) <= p_out: r.append("")
                                r[p_out] = str(l_info["outer"])

                            if p_rep is not None and cur_rep_s == "":
                                rep = l_info["repairCost"] if l_info["repairCost"] > 0 else (l_info["outer"] * 13)
                                if rep > 0:
                                    while len(r) <= p_rep: r.append("")
                                    r[p_rep] = str(rep)

                            if p_fee is not None:
                                cur_f = _safe_float(r[p_fee]) if len(r) > p_fee else 0
                                raw_l_fee = l_info["fee"]
                                b_p = _safe_float(r[h_map.get("매입가", 7)]) if h_map.get("매입가") is not None and len(r) > h_map.get("매입가", 7) else 0
                                calc_fee = calculate_heydealer_fee(b_p, "셀프(기본)")
                                f_val = raw_l_fee if raw_l_fee in [55.0, 54.5] else (calc_fee if calc_fee > 0 else raw_l_fee)
                                if f_val > 0 and (cur_f == 0 or cur_f == 44.0):
                                    while len(r) <= p_fee: r.append("")
                                    r[p_fee] = str(f_val)

                            if p_name is not None and l_info["carName"] and (not r[p_name] if len(r) > p_name else True):
                                while len(r) <= p_name: r.append("")
                                r[p_name] = l_info["carName"]

                        clean_rows.append(r)
                break
            except Exception:
                continue

        # 4. 순차를 1부터 위에서부터 차례대로 재부여 (1, 2, 3, 4, 5...)
        for idx, row in enumerate(clean_rows):
            if len(row) > 0:
                row[0] = str(idx + 1)

        temp_path = f"{SETTLEMENT_CSV}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(clean_rows)
            os.replace(temp_path, SETTLEMENT_CSV)
            print(f"[AutoplusAdminService] 정산표 정리 완료 (제외: {removed_count}건, 남은 대수: {len(clean_rows)}대, 외판 복구 완료)", flush=True)
        except Exception as e:
            if os.path.exists(temp_path): os.remove(temp_path)
            print(f"[AutoplusAdminService] 9월 이전 정리 저장 오류: {e}")
        return removed_count

    @classmethod
    def fetch_and_sync_backend(cls) -> Dict[str, Any]:
        """백엔드에 저장된 쿠키로 admin.autoplus.co.kr 매입 데이터 직접 호출 및 동기화"""
        cls.clean_pre_september_inventory()
        cookie_file = os.path.join(BASE_DIR, "autoplus_cookie.txt")
        if not os.path.exists(cookie_file):
            return {"success": False, "message": "오토플러스 쿠키 파일이 없습니다.", "syncedCount": 0}

        try:
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookie = f.read().strip()
        except Exception as e:
            return {"success": False, "message": f"쿠키 읽기 오류: {e}", "syncedCount": 0}

        if not cookie:
            return {"success": False, "message": "오토플러스 쿠키가 비어 있습니다.", "syncedCount": 0}

        url = "https://admin.autoplus.co.kr/spot/syspo/SPPOL10001"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://admin.autoplus.co.kr/spot/syspo/SPPOL10001",
            "Cookie": cookie
        }

        try:
            import requests
            resp = requests.get(url, headers=headers, timeout=15, allow_redirects=False)
            if resp.status_code == 302 or "login" in resp.headers.get("Location", "").lower():
                return {
                    "success": False,
                    "message": "high A+ 로그인 세션이 만료되었습니다. 크롬 브라우저에서 재로그인이 필요합니다.",
                    "syncedCount": 0
                }

            if resp.status_code != 200:
                return {"success": False, "message": f"high A+ 응답 오류: HTTP {resp.status_code}", "syncedCount": 0}

            cars = cls.parse_sppol10001_html(resp.text)
            if not cars:
                return {"success": True, "message": "조회된 매입 차량이 없거나 파싱되지 않았습니다.", "syncedCount": 0}

            # 상세 화면(SPPOR20001)에서 기타비용(낙찰/소개수수료 545,000원 등) 백엔드 직접 크롤링
            for c in cars:
                p_id = c.get("poId")
                if p_id:
                    try:
                        d_url = f"https://admin.autoplus.co.kr/spot/syspo/SPPOR20001?poId={p_id}&vw=1&showGbn=H"
                        d_resp = requests.get(d_url, headers=headers, timeout=10, allow_redirects=False)
                        if d_resp.status_code == 200:
                            m_etc = re.search(r"기타비용[^\d]*([\d,]{4,})", d_resp.text)
                            if m_etc:
                                fee_clean = int(m_etc.group(1).replace(",", ""))
                                if fee_clean > 0:
                                    c["etcFee"] = fee_clean
                    except Exception as de:
                        print(f"[AutoplusAdminService] 상세 크롤링 오류 ({p_id}): {de}")

            return cls.process_highplus_buy_data(cars)
        except Exception as e:
            return {"success": False, "message": f"백엔드 매입연동 호출 실패: {str(e)}", "syncedCount": 0}

