# services/autoplus_sync_service.py
"""
오토플러스.Data (data.autoplus.co.kr) 자사 재고 및 판매완료 데이터 자동 동기화 서비스
- 판매중 차량(ap_all_car) -> autoplus_inventory.csv (및 my_inventory_settlement.csv 최신화)
- 판매완료 차량(ap_all_car_out) -> 20260813_sales_car_datalist.csv
- 기존 파일 자동 백업(backups/) 후 안전한 upsert 병합
- 서버 시작 시 1회 + 24시간 주기 자동 실행 및 수동 즉시 실행 지원
"""

import os
import re
import csv
import json
import shutil
import datetime
import threading
import requests
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
STATUS_FILE = os.path.join(DATA_DIR, "autoplus_sync_status.json")

INVENTORY_CSV = os.path.join(BASE_DIR, "autoplus_inventory.csv")
SOLD_CSV = os.path.join(BASE_DIR, "sales_car_datalist.csv")
SETTLEMENT_CSV = os.path.join(BASE_DIR, "my_inventory_settlement.csv")
LEDGER_CSV = os.path.join(BASE_DIR, "my_car_ledger.csv")
ALIAS_JSON = os.path.join(BASE_DIR, "company_carid_alias.json")

# 1. 판매중 헤더 (33개)
SELLING_HEADERS = [
    'PID', '차량번호', '이전차량번호', '차량명', '세부 모델', '색상',
    '주행거리', '최초등록일', '홈페이지상태', '자사몰광고', 'E광고',
    '경과일수(매입일기준)', '매입유형1', '매입유형2', '매입유형3', '매입담당자',
    '최종수정일', '신차가', '매입가', '지점판매가', '할인',
    '할인적용가', '예상매출이익', '신차가대비', '지점', '담당자명', 'RB상담수',
    'E상담수', 'E URL', 'RB조회수', 'RB찜수', 'E조회수', 'E찜수'
]

# 2. 판매완료 헤더 (30개)
SOLD_HEADERS = [
    'PID', '차량번호', '이전차량번호', '차량명', '세부 모델', '색상',
    '주행거리', '최초등록일', '홈페이지상태', '경과일수(매입일기준)', '매입유형1',
    '매입유형2', '매입유형3', '매입담당자', '최종수정일', '신차가', '매입가',
    '지점판매가', '할인', '할인적용가', '예상매출이익', '신차가대비', '담당자명',
    'RB상담수', 'E상담수', 'E URL', 'RB조회수', 'RB찜수', 'E조회수', 'E찜수'
]


class AutoplusSyncService:
    _lock = threading.Lock()
    _is_running = False

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """최근 동기화 상태 반환"""
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "status": "NONE",
            "last_sync_time": None,
            "inventory_count": 0,
            "sold_count": 0,
            "settlement_updated_count": 0,
            "message": "동기화 이력이 없습니다."
        }

    @classmethod
    def _save_status(cls, status_data: Dict[str, Any]):
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AutoplusSync] 상태 저장 실패: {e}", flush=True)

    @classmethod
    def backup_file(cls, filepath: str) -> Optional[str]:
        """기존 CSV 파일을 backups/ 폴더에 타임스탬프와 함께 백업"""
        if not os.path.exists(filepath):
            return None
        os.makedirs(BACKUP_DIR, exist_ok=True)
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"{name}_{now_str}{ext}")
        try:
            shutil.copy2(filepath, backup_path)
            print(f"[AutoplusSync] 백업 완료: {backup_path}", flush=True)
            return backup_path
        except Exception as e:
            print(f"[AutoplusSync] 백업 실패 ({filepath}): {e}", flush=True)
            return None

    @classmethod
    def ensure_settlement_file(cls) -> bool:
        """SETTLEMENT_CSV 파일 부재 시 .tmp 또는 backups 폴더의 최신 백업에서 안전하게 복구"""
        if os.path.exists(SETTLEMENT_CSV) and os.path.getsize(SETTLEMENT_CSV) > 0:
            return True

        # 1. .tmp 파일 복구 시도
        tmp_path = SETTLEMENT_CSV + ".tmp"
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            try:
                os.replace(tmp_path, SETTLEMENT_CSV)
                print(f"[AutoplusSync] .tmp 파일에서 {SETTLEMENT_CSV} 복구 완료", flush=True)
                return True
            except Exception as e:
                print(f"[AutoplusSync] .tmp 파일 복구 실패: {e}", flush=True)

        # 2. backups 폴더의 최신 백업 파일 복구 시도
        if os.path.exists(BACKUP_DIR):
            candidates = []
            for fn in os.listdir(BACKUP_DIR):
                if fn.startswith("my_inventory_settlement_") and fn.endswith(".csv"):
                    fp = os.path.join(BACKUP_DIR, fn)
                    try:
                        if os.path.getsize(fp) > 0:
                            candidates.append((os.path.getmtime(fp), fp))
                    except Exception:
                        pass
            if candidates:
                candidates.sort(reverse=True)
                latest_backup = candidates[0][1]
                try:
                    shutil.copy2(latest_backup, SETTLEMENT_CSV)
                    print(f"[AutoplusSync] 최신 백업({latest_backup})에서 {SETTLEMENT_CSV} 복구 완료", flush=True)
                    return True
                except Exception as e:
                    print(f"[AutoplusSync] 백업 복구 실패: {e}", flush=True)

        return False

    @classmethod
    def fetch_selling_cars(cls, cookie: str) -> List[List[Any]]:
        """판매중 차량 데이터(ap_all_car) 실시간 수신"""
        url = "https://data.autoplus.co.kr/on_sale_car_list"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Referer": "https://data.autoplus.co.kr/data/ap_all_car",
            "Origin": "https://data.autoplus.co.kr",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": cookie
        }
        param = {
            "now": 0,
            "add": 20,
            "sortDataType": "data-type01",
            "sortServiceType": "service-type01",
            "listType": "all",
            "loadType": "excel-download",
            "location": "",
            "manager": "",
            "brand": "",
            "model": "",
            "dtModel": "",
            "grade": "",
            "keyword": "",
            "leadtime": "all",
            "purchaseType1": "",
            "purchaseType2": "",
            "purchaseType3": "",
            "carType": "",
            "platform": "all"
        }
        try:
            resp = requests.post(url, headers=headers, json=param, timeout=30)
            data = resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f"오토플러스 재고 서버 통신 오류: {e}")
        except Exception:
            raise RuntimeError("오토플러스 로그인 세션이 만료되었습니다. 쿠키를 갱신해 주세요.")
        excel_data = data.get("excel_data", [])
        rows = []
        for d in excel_data:
            if not isinstance(d, list) or len(d) < 34:
                continue
            is_encar = 'O' if str(d[24]).strip() not in ('javascript:;', '') else 'X'
            is_hp = 'O' if str(d[31]).strip().upper() == 'Y' else 'X'
            row = [
                d[33], d[0], d[1], d[2], d[3], d[4],
                d[5], d[6], d[7], is_hp, is_encar,
                d[8], d[9], d[10], d[11], d[12],
                d[13], d[14], d[15], d[16], d[17],
                d[18], d[19], d[20], d[32], d[21], d[22],
                d[23], d[24], d[25], d[26], d[27], d[28]
            ]
            rows.append(row)
        return rows

    @classmethod
    def fetch_sold_cars(cls, cookie: str, days: int = 95) -> List[List[Any]]:
        """최근 3개월 판매완료 차량 데이터(ap_all_car_out) 실시간 수신"""
        url = "https://data.autoplus.co.kr/on_sale_car_list"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Referer": "https://data.autoplus.co.kr/data/ap_all_car_out",
            "Origin": "https://data.autoplus.co.kr",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": cookie
        }
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=days)
        param = {
            "now": 0,
            "add": 20,
            "sortDataType": "data-type01",
            "sortServiceType": "service-type01",
            "listType": "all",
            "loadType": "excel-download",
            "location": "",
            "manager": "",
            "brand": "",
            "model": "",
            "dtModel": "",
            "grade": "",
            "keyword": "",
            "leadtime": "all",
            "purchaseType1": "",
            "purchaseType2": "",
            "purchaseType3": "",
            "carType": "",
            "HA05": "out",
            "date01": start_date.strftime("%Y-%m-%d"),
            "date02": today.strftime("%Y-%m-%d")
        }
        try:
            resp = requests.post(url, headers=headers, json=param, timeout=40)
            data = resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f"오토플러스 판매완료 서버 통신 오류: {e}")
        except Exception:
            raise RuntimeError("오토플러스 로그인 세션이 만료되었습니다. 쿠키를 갱신해 주세요.")
        excel_data = data.get("excel_data", [])
        rows = []
        for d in excel_data:
            if not isinstance(d, list) or len(d) < 34:
                continue
            row = [
                d[33], d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8],
                d[9], d[10], d[11], d[12], d[13], d[14], d[15], d[16], d[17],
                d[18], d[19], d[20], d[21], d[22], d[23], d[24], d[25], d[26],
                d[27], d[28]
            ]
            rows.append(row)
        return rows

    @classmethod
    def _upsert_csv(cls, target_path: str, headers: List[str], new_rows: List[List[Any]], key_idx: int = 1) -> int:
        """
        차량번호(또는 PID) 기준 안전 upsert 병합
        - 기존 파일이 있으면 읽어서 맵 구성
        - 최신 데이터로 기존 데이터 갱신 및 신규 건 추가
        - UTF-8 with BOM 인코딩으로 저장
        """
        existing_data: Dict[str, List[Any]] = {}
        row_order: List[str] = []

        if os.path.exists(target_path):
            cls.backup_file(target_path)
            try:
                for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
                    try:
                        with open(target_path, 'r', encoding=enc) as f:
                            reader = csv.reader(f)
                            orig_headers = next(reader, None)
                            for r in reader:
                                if r and len(r) > key_idx:
                                    k = str(r[key_idx]).strip()
                                    if k:
                                        if k not in existing_data:
                                            row_order.append(k)
                                        existing_data[k] = r
                        break
                    except (UnicodeDecodeError, Exception):
                        continue
            except Exception as e:
                print(f"[AutoplusSync] 기존 파일 읽기 경고 ({target_path}): {e}", flush=True)

        # Upsert
        for nr in new_rows:
            if len(nr) > key_idx:
                k = str(nr[key_idx]).strip()
                if k:
                    if k not in existing_data:
                        row_order.append(k)
                    existing_data[k] = nr

        # 안전하게 임시 파일에 먼저 기록 후 교체
        temp_path = target_path + ".tmp"
        with open(temp_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for k in row_order:
                writer.writerow(existing_data[k])

        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(temp_path, target_path)
        return len(existing_data)

    @classmethod
    def _sync_settlement_ledger(cls, selling_rows: Optional[List[List[Any]]] = None) -> int:
        """
        제이님의 개인 정산 파일(my_inventory_settlement.csv) 동기화
        - 외판수리, 상품화, 헤딜수수료, 공헌이익, 실수익, 내꺼 등 커스텀 정산 필드는 100% 보존
        - 차량번호가 일치하는 건의 상태, 판매가, 재고일, 엔카URL을 최신값으로 업데이트
        - selling_rows가 주어지지 않으면 디스크의 autoplus_inventory.csv에서 자동 로드
        """
        if not os.path.exists(SETTLEMENT_CSV):
            return 0

        # selling_rows가 없으면 디스크의 autoplus_inventory.csv에서 로드
        if selling_rows is None:
            selling_rows = []
            if os.path.exists(INVENTORY_CSV):
                for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
                    try:
                        with open(INVENTORY_CSV, 'r', encoding=enc) as f:
                            reader = csv.reader(f)
                            next(reader, None)
                            selling_rows = [r for r in reader if r]
                        break
                    except Exception:
                        continue

        # 판매중 차량 맵: plate -> dict
        selling_map = {}
        for r in selling_rows:
            if len(r) >= 30:
                plate = str(r[1]).strip()
                if plate:
                    # 광고가 (할인적용가 우선, 없으면 지점판매가)
                    adv_price = str(r[21]).strip() if len(r) > 21 and str(r[21]).strip() and str(r[21]).strip() != '0' else str(r[19]).strip()
                    
                    # 주행거리 (r[6])
                    mileage_val = None
                    if len(r) > 6 and r[6] is not None:
                        digits = re.sub(r"[^0-9]", "", str(r[6]))
                        if digits:
                            try:
                                mv = int(digits)
                                if mv > 0:
                                    mileage_val = mv
                            except (ValueError, TypeError):
                                pass

                    selling_map[plate] = {
                        "status": str(r[8]).strip() or "판매중",
                        "price": adv_price,
                        "stock_days": str(r[11]).strip(),     # 경과일수
                        "encar_url": str(r[28]).strip(),      # E URL
                        "mileage": mileage_val
                    }

        cls.ensure_settlement_file()
        cls.backup_file(SETTLEMENT_CSV)
        updated_count = 0
        lines = []

        enc_found = 'utf-8-sig'
        headers = None
        for enc in ['utf-8-sig', 'utf-8', 'cp949']:
            try:
                with open(SETTLEMENT_CSV, 'r', encoding=enc) as f:
                    reader = csv.reader(f)
                    file_headers = next(reader, None)
                    if not file_headers:
                        return 0
                    headers = list(file_headers)

                    h_map = {col.strip(): i for i, col in enumerate(headers)}
                    # 주행거리 및 apCarId 컬럼이 헤더에 없으면 스키마 확장
                    if "주행거리" not in h_map:
                        headers.append("주행거리")
                        h_map["주행거리"] = len(headers) - 1
                    if "apCarId" not in h_map:
                        headers.append("apCarId")
                        h_map["apCarId"] = len(headers) - 1

                    mileage_idx = h_map["주행거리"]
                    plate_idx = h_map.get("차량번호", 3)
                    sell_price_idx = h_map.get("판매가", 5)
                    stock_days_idx = h_map.get("재고일", 6)
                    encar_url_idx = h_map.get("엔카URL", 19)

                    for row in reader:
                        if not row or not any(field.strip() for field in row):
                            continue
                        # 행 길이를 headers 길이에 맞춤
                        while len(row) < len(headers):
                            row.append("")

                        if len(row) > plate_idx:
                            plate = str(row[plate_idx]).replace(' ', '').strip()
                            if plate in selling_map:
                                s_info = selling_map[plate]
                                # 판매가(만원 단위)
                                try:
                                    raw_p = float(s_info["price"].replace(',', ''))
                                    row[sell_price_idx] = str(int(raw_p // 10000)) if raw_p > 10000 else str(int(raw_p))
                                except:
                                    pass
                                # 재고일
                                try:
                                    row[stock_days_idx] = str(int(float(s_info["stock_days"])))
                                except:
                                    pass
                                # 엔카URL
                                if len(row) > encar_url_idx and s_info["encar_url"] and s_info["encar_url"] != 'javascript:;':
                                    row[encar_url_idx] = s_info["encar_url"]

                                # 주행거리: 비어 있는 행만 채우고, 이미 값이 있는 행은 절대 덮지 않는다
                                cur_mileage_str = str(row[mileage_idx]).strip()
                                cur_mileage_num = 0
                                if cur_mileage_str and cur_mileage_str.lower() not in ("none", "null", ""):
                                    try:
                                        cur_mileage_num = int(re.sub(r"[^0-9]", "", cur_mileage_str) or 0)
                                    except:
                                        cur_mileage_num = 0

                                if cur_mileage_num <= 0 and s_info.get("mileage"):
                                    row[mileage_idx] = str(s_info["mileage"])
                                    print(f"[AutoplusSync] 정산 행 주행거리 전사 데이터 매핑 성공: {plate[-4:]} -> {s_info['mileage']}km", flush=True)

                                updated_count += 1
                        lines.append(row)
                enc_found = enc
                break
            except (UnicodeDecodeError, Exception) as e:
                continue

        if headers and lines:
            import time
            try:
                from services.autoplus_admin_service import _parse_date_sort_key
                h_map_sort = {col.strip(): i for i, col in enumerate(headers)}
                date_idx_sort = h_map_sort.get("매입일", 1)
                status_idx_sort = h_map_sort.get("상태", 2)
                active_lines = [r for r in lines if "판매완료" not in (r[status_idx_sort] if len(r) > status_idx_sort else "")]
                sold_lines = [r for r in lines if "판매완료" in (r[status_idx_sort] if len(r) > status_idx_sort else "")]
                active_lines.sort(key=lambda r: _parse_date_sort_key(r[date_idx_sort] if len(r) > date_idx_sort else ""), reverse=True)
                sold_lines.sort(key=lambda r: _parse_date_sort_key(r[date_idx_sort] if len(r) > date_idx_sort else ""), reverse=True)
                lines = active_lines + sold_lines
                for idx, r in enumerate(lines):
                    if len(r) > 0:
                        r[0] = str(idx + 1)
            except Exception as se:
                print(f"[AutoplusSync] 최신순 정렬 보정 중 경고: {se}", flush=True)

            temp_path = f"{SETTLEMENT_CSV}.tmp"
            with open(temp_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(lines)
            for attempt in range(3):
                try:
                    os.replace(temp_path, SETTLEMENT_CSV)
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(0.1 * (attempt + 1))
                    else:
                        print(f"[AutoplusSync] SETTLEMENT_CSV os.replace 실패, shutil fallback: {e}", flush=True)
                        try:
                            shutil.copy2(temp_path, SETTLEMENT_CSV)
                            os.remove(temp_path)
                        except Exception:
                            pass

        return updated_count

    @classmethod
    def execute_sync(cls) -> Dict[str, Any]:
        """
        오토플러스.Data(data.autoplus.co.kr) 전사 실시간 동기화 메인 함수
        - 판매중 차량(on_sale_car_list) -> autoplus_inventory.csv 및 real_autoplus_inventory.json 갱신
        - 판매완료 차량(ap_all_car_out) -> sales_car_datalist.csv 갱신
        - 제이님 정산 장부 매칭 최신화
        """
        if cls._is_running:
            return {"status": "IN_PROGRESS", "message": "이미 동기화가 진행 중입니다."}

        with cls._lock:
            cls._is_running = True
            try:
                cookie_file = os.path.join(BASE_DIR, "autoplus_data_cookie.txt")
                cookie = ""
                if os.path.exists(cookie_file):
                    try:
                        with open(cookie_file, "r", encoding="utf-8") as f:
                            cookie = f.read().strip()
                    except Exception:
                        pass
                if not cookie:
                    from services.cookie_server import get_current_autoplus_data_cookie
                    cookie = get_current_autoplus_data_cookie()

                if not cookie:
                    res = {
                        "status": "COOKIE_EXPIRED",
                        "last_sync_time": datetime.datetime.now().isoformat(),
                        "inventory_count": 0,
                        "sold_count": 0,
                        "settlement_updated_count": 0,
                        "message": "오토플러스.Data 세션 쿠키가 없습니다. 브라우저에서 data.autoplus.co.kr에 로그인해 주세요."
                    }
                    cls._save_status(res)
                    return res

                print("[AutoplusSync] 전사 데이터 동기화 시작...", flush=True)

                # 1. 판매중 차량 수신 및 upsert
                selling_rows = cls.fetch_selling_cars(cookie)
                inv_total = cls._upsert_csv(INVENTORY_CSV, SELLING_HEADERS, selling_rows, key_idx=1)
                print(f"[AutoplusSync] 판매중 차량 {len(selling_rows)}대 수신 완료 (누적 {inv_total}대)", flush=True)

                # 2. 판매완료 차량 수신 및 upsert (days=95)
                sold_rows = cls.fetch_sold_cars(cookie, days=95)
                sold_total = cls._upsert_csv(SOLD_CSV, SOLD_HEADERS, sold_rows, key_idx=1)
                print(f"[AutoplusSync] 판매완료 차량 {len(sold_rows)}대 수신 완료 (누적 {sold_total}대)", flush=True)

                # 3. 제이님 개인 정산 장부 최신화 (스키마 및 수기 항목 100% 보존)
                settlement_upd = cls._sync_settlement_ledger(selling_rows)
                print(f"[AutoplusSync] 개인 정산 장부 매칭 갱신: {settlement_upd}건", flush=True)

                # 4. 프론트엔드 캐시 JSON(real_autoplus_inventory.json) 갱신
                cls._update_frontend_json(selling_rows)

                res = {
                    "status": "SUCCESS",
                    "last_sync_time": datetime.datetime.now().isoformat(),
                    "inventory_count": len(selling_rows),
                    "total_inventory": inv_total,
                    "sold_count": len(sold_rows),
                    "total_sold": sold_total,
                    "settlement_updated_count": settlement_upd,
                    "message": f"전사 동기화 완료: 판매중 {len(selling_rows):,}대 / 판매완료 {len(sold_rows):,}대"
                }
                cls._save_status(res)
                print(f"[AutoplusSync] {res['message']}", flush=True)

                # 5. [11-06-87]: 엔카 API 과부하/Rate Limit(429) 및 콕핏 무한로딩 방지를 위해 
                # 백그라운드 자동 해석 스레드 비활성화 (기존 ALIAS_JSON 파일 로드는 get_company_carid_map에서 정상 유지)
                # try:
                #     threading.Thread(
                #         target=cls._bg_resolve_aliases,
                #         daemon=True,
                #         name="AutoplusDummyVehicleResolver"
                #     ).start()
                # except Exception as e:
                #     print(f"[AutoplusSync] dummyVehicleId 해석 스레드 시작 실패: {e}", flush=True)

                return res

            except Exception as ex:
                err_msg = str(ex)
                print(f"[AutoplusSync] 동기화 실패: {err_msg}", flush=True)
                res = {
                    "status": "FAILED",
                    "last_sync_time": datetime.datetime.now().isoformat(),
                    "inventory_count": 0,
                    "sold_count": 0,
                    "settlement_updated_count": 0,
                    "message": f"동기화 오류: {err_msg}"
                }
                cls._save_status(res)
                return res
            finally:
                cls._is_running = False

    @classmethod
    def _update_frontend_json(cls, selling_rows: List[List[Any]]):
        """CompanyInventoryTab.tsx에서 즉시 렌더링할 수 있도록 real_autoplus_inventory.json 갱신"""
        json_path = os.path.join(BASE_DIR, "frontend", "src", "data", "real_autoplus_inventory.json")
        if not os.path.exists(os.path.dirname(json_path)):
            return

        cars = []
        for r in selling_rows:
            try:
                # row: [PID, 차량번호, 이전차량번호, 차량명, 세부 모델, 색상, 주행거리, 최초등록일, 홈페이지상태, ...]
                pid = str(r[0]).strip()
                plate = str(r[1]).strip()
                car_name = str(r[3]).strip()
                sub_model = str(r[4]).strip()
                color = str(r[5]).strip()
                mileage = int(float(str(r[6]).replace(',', '') or 0))
                reg_date = str(r[7]).strip()
                stock_days = int(float(str(r[11]).replace(',', '') or 0))
                buy_price = int(float(str(r[18]).replace(',', '') or 0))
                sell_price = int(float(str(r[19]).replace(',', '') or 0))
                new_car_price = int(float(str(r[17]).replace(',', '') or 0))
                expected_profit = int(float(str(r[22]).replace(',', '') or 0))
                status = str(r[8]).strip() or "판매중"
                branch = str(r[24]).strip()
                manager = str(r[25]).strip()
                encar_url = str(r[28]).strip()

                cars.append({
                    "id": pid,
                    "plate": plate,
                    "carName": car_name,
                    "subModel": sub_model,
                    "color": color,
                    "mileage": mileage,
                    "regDate": reg_date,
                    "stockDays": stock_days,
                    "buyPrice": buy_price,
                    "sellPrice": sell_price,
                    "newCarPrice": new_car_price,
                    "expectedProfit": expected_profit,
                    "status": status,
                    "branch": branch,
                    "manager": manager,
                    "encarUrl": encar_url if encar_url != 'javascript:;' else ""
                })
            except Exception:
                continue

        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(cars, f, ensure_ascii=False, indent=2)
            print(f"[AutoplusSync] 프론트엔드 실시간 JSON {len(cars)}건 갱신 완료", flush=True)
        except Exception as e:
            print(f"[AutoplusSync] JSON 갱신 실패: {e}", flush=True)

    _carid_cache: Dict[str, str] = {}
    _carid_cache_time: float = 0.0

    @classmethod
    def resolve_dummy_vehicle_ids(cls, target_carids: Optional[List[str]] = None) -> Dict[str, str]:
        """
        [11-06-86] 엔카 리드사이드 API(manage.dummyVehicleId)를 호출하여
        환불 후 재등록된 차량의 {옛 carid: 새 carid} 별칭을 증분 해석 및 저장.
        - CSV 원본은 전혀 건드리지 않고 company_carid_alias.json에 저장
        - 이미 검사 완료된 carid는 스킵 (증분 처리, 1,799건 매번 전수 호출 금지)
        - 429 수신 시 재시도하지 않고 안전 즉시 중단
        - 호출 간격(0.15초)을 두어 엔카 API 부하 방지
        """
        import time

        # 1. 기존 alias 파일 로드 (증분 처리를 위한 checked_ids 복원)
        aliases: Dict[str, str] = {}
        checked_ids: set = set()
        if os.path.exists(ALIAS_JSON):
            try:
                with open(ALIAS_JSON, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                if isinstance(saved_data, dict):
                    aliases = saved_data.get("aliases", {})
                    checked_ids = set(saved_data.get("checked_ids", []))
                    if not aliases and saved_data:
                        aliases = {str(k): str(v) for k, v in saved_data.items() if not str(k).startswith("_")}
                        checked_ids = set(aliases.keys())
            except Exception as e:
                print(f"[AutoplusSync] ALIAS_JSON 로드 중 예외(신규 생성): {e}", flush=True)

        # 2. 검사 대상 carid 목록 취합 (엔카 과부하 방지: target_carids 미지정 시 개인 정산표 매물에 한해 상한 30건으로 안전 제한)
        if target_carids is None:
            cids_to_check = set()
            target_csvs = [SETTLEMENT_CSV]  # 대량 전수 순회 차단, 개인 정산표 중심으로 제한
            for p in target_csvs:
                if not os.path.exists(p):
                    continue
                for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
                    try:
                        with open(p, 'r', encoding=enc) as f:
                            reader = csv.DictReader(f)
                            for r in reader:
                                url = str(r.get('엔카URL', '') or r.get('E URL', '') or r.get('특이사항', '')).strip()
                                if url:
                                    m = re.search(r'carid=(\d+)', url) or re.search(r'/cars/detail/(\d+)', url)
                                    if m:
                                        cids_to_check.add(m.group(1))
                        break
                    except Exception:
                        continue
        else:
            cids_to_check = set(str(c).strip() for c in target_carids if str(c).strip().isdigit())

        # 3. 이미 확인한 carid 제외 (증분 필터링)
        pending_ids = [cid for cid in cids_to_check if cid not in checked_ids]
        if not pending_ids:
            return aliases

        print(f"[AutoplusSync] dummyVehicleId 해석 시작: 전체 {len(cids_to_check)}건 중 신규 {len(pending_ids)}건 검사", flush=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        new_aliases_count = 0

        for idx, cid in enumerate(pending_ids):
            time.sleep(0.15)  # 과도한 엔카 API 호출 방지
            url = f"https://api.encar.com/v1/readside/vehicle/{cid}"
            try:
                resp = requests.get(url, headers=headers, timeout=4)
                if resp.status_code == 429:
                    print(f"[AutoplusSync] 엔카 API 429 (Too Many Requests) 감지 - 안전을 위해 해석을 즉시 중단합니다.", flush=True)
                    break
                if resp.status_code == 200:
                    data = resp.json()
                    manage = data.get("manage", {})
                    dummy_id = str(manage.get("dummyVehicleId", "") or "").strip()
                    if dummy_id and dummy_id.isdigit() and dummy_id != cid:
                        aliases[cid] = dummy_id
                        new_aliases_count += 1
                        print(f"[AutoplusSync] 재등록 매물 발견: {cid} -> {dummy_id}", flush=True)
                    checked_ids.add(cid)
                elif resp.status_code in (404, 400):
                    # 판매종료/존재하지 않는 매물은 다시 조회하지 않도록 완료 처리
                    checked_ids.add(cid)
            except Exception:
                continue

        # 4. JSON 파일 저장
        try:
            save_payload = {
                "aliases": aliases,
                "checked_ids": list(checked_ids),
                "updated_at": datetime.datetime.now().isoformat()
            }
            with open(ALIAS_JSON, "w", encoding="utf-8") as f:
                json.dump(save_payload, f, ensure_ascii=False, indent=2)
            print(f"[AutoplusSync] dummyVehicleId 해석 완료 (신규 alias {new_aliases_count}건, 총 alias {len(aliases)}건, 누적 검사 {len(checked_ids)}건)", flush=True)
            # 캐시 무효화하여 get_company_carid_map이 새 별칭을 즉시 읽도록 처리
            cls._carid_cache_time = 0.0
        except Exception as e:
            print(f"[AutoplusSync] ALIAS_JSON 저장 실패: {e}", flush=True)

        return aliases

    @classmethod
    def _bg_resolve_aliases(cls):
        """백그라운드 스레드에서 안전하게 dummyVehicleId 해석 수행"""
        try:
            cls.resolve_dummy_vehicle_ids()
        except Exception as e:
            print(f"[AutoplusSync] 백그라운드 dummyVehicleId 해석 예외: {e}", flush=True)

    @classmethod
    def get_company_carid_map(cls) -> Dict[str, str]:
        """자사 보유 차량의 차량번호 -> carid 및 전체 carid 맵 로드 (5분 메모리 캐시)"""
        import time, re
        now = time.time()
        if cls._carid_cache and (now - cls._carid_cache_time < 300):
            return cls._carid_cache

        mapping: Dict[str, str] = {}
        target_csvs = [SETTLEMENT_CSV, INVENTORY_CSV, LEDGER_CSV]

        for p in target_csvs:
            if not os.path.exists(p):
                continue
            for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
                try:
                    with open(p, 'r', encoding=enc) as f:
                        reader = csv.DictReader(f)
                        for r in reader:
                            plate = str(r.get('차량번호', '')).replace(' ', '').strip()
                            url = str(r.get('엔카URL', '') or r.get('E URL', '') or r.get('특이사항', '')).strip()
                            if url:
                                m = re.search(r'carid=(\d+)', url) or re.search(r'/cars/detail/(\d+)', url)
                                if m:
                                    cid = m.group(1)
                                    if plate:
                                        mapping[plate] = cid
                                    mapping[cid] = cid
                    break
                except Exception:
                    continue

        # 4. 재등록 매물(dummyVehicleId) 별칭 맵 적용
        if os.path.exists(ALIAS_JSON):
            try:
                with open(ALIAS_JSON, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                aliases = saved_data.get("aliases", saved_data) if isinstance(saved_data, dict) else {}
                for old_id, new_id in aliases.items():
                    old_s = str(old_id).strip()
                    new_s = str(new_id).strip()
                    if new_s and new_s.isdigit():
                        mapping[new_s] = new_s
                        # old_id에 연결되어 있던 차량번호가 있다면 그 차량번호도 새 carid 매핑 지원
                        for plate, cid in list(mapping.items()):
                            if cid == old_s and not plate.isdigit():
                                mapping[plate] = new_s
            except Exception as e:
                print(f"[AutoplusSync] ALIAS_JSON 로드 실패: {e}", flush=True)

        cls._carid_cache = mapping
        cls._carid_cache_time = now
        return mapping


def start_autoplus_scheduler():
    """서버 구동 시 1회 즉시 실행 + 하루 1회(24시간) 주기 백그라운드 스레드 가동"""
    def _run_loop():
        try:
            print("[AutoplusSync] 서버 기동 초기 동기화 트리거", flush=True)
            AutoplusSyncService.execute_sync()
        except Exception as e:
            print(f"[AutoplusSync] 초기 동기화 실패: {e}", flush=True)

        import time
        while True:
            time.sleep(24 * 3600)
            try:
                print("[AutoplusSync] 24시간 주기 정기 동기화 트리거", flush=True)
                AutoplusSyncService.execute_sync()
            except Exception as e:
                print(f"[AutoplusSync] 정기 동기화 실패: {e}", flush=True)

    t = threading.Thread(target=_run_loop, daemon=True, name="AutoplusDataSyncScheduler")
    t.start()
    print("[AutoplusSync] 24시간 자동 동기화 스케줄러 등록 완료", flush=True)
