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

        cleaned_cars = []
        for c in buy_cars:
            car_no = str(c.get("carNumber", "")).replace(" ", "").strip()
            if not car_no or len(car_no) < 6:
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

        cls.backup_file(SETTLEMENT_CSV)
        cars_by_no = {c["carNumber"]: c for c in cleaned_cars}

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

        existing_cars = set()
        updated_count = 0
        new_rows = []

        # 1) 기존 행 갱신 (단, 2026년 9월 이전 과거 건은 필터링하여 자동 제거)
        date_idx = h_map.get("매입일", 1)
        for r in rows:
            if len(r) > car_no_idx:
                c_no = r[car_no_idx].strip()
                b_date = r[date_idx].strip() if len(r) > date_idx else ""

                # 2026년 9월 이전 매입건(04., 05., 06., 07., 08. 등) 필터링
                m_d = re.search(r"(?:20\d{2}[-/.])?0?(\d{1,2})[-/.]", b_date)
                if m_d:
                    m_val = int(m_d.group(1))
                    if m_val < 9:
                        continue  # 9월 이전 과거 데이터 제거

                existing_cars.add(c_no)
                if c_no in cars_by_no:
                    c_info = cars_by_no[c_no]
                    def update_val(col_name: str, new_val: Any):
                        pos = h_map.get(col_name)
                        if pos is not None and new_val is not None:
                            while len(r) <= pos: r.append("")
                            r[pos] = str(new_val).strip()

                    # 매입가
                    if c_info["buyPrice"] > 0:
                        update_val("매입가", c_info["buyPrice"])
                    # 매입일
                    if c_info["buyDate"]:
                        update_val("매입일", c_info["buyDate"])
                    # 외판 (0보다 크면)
                    if c_info["outerRepairs"] > 0:
                        update_val("외판수리", c_info["outerRepairs"])
                        # 상품화 비용이 비어있으면 판수*13 제안
                        pos_rep = h_map.get("상품화")
                        if pos_rep and (not r[pos_rep] or _safe_int(r[pos_rep]) == 0):
                            update_val("상품화", c_info["outerRepairs"] * 13)
                    # 수수료 (헤딜+영업사원 수수료)
                    if c_info["heydealerFee"] > 0:
                        update_val("헤딜수수료", c_info["heydealerFee"])
                    # 상품화비용 직접 명시 건
                    if c_info["repairCost"] > 0:
                        update_val("상품화", c_info["repairCost"])

                    updated_count += 1
            new_rows.append(r)

        # 2) 신규 차량 추가 (Upsert 최상단 삽입)
        added_count = 0
        max_order = 0
        for r in new_rows:
            if len(r) > 0:
                max_order = max(max_order, _safe_int(r[0]))

        for c_no, c_info in cars_by_no.items():
            if c_no not in existing_cars:
                max_order += 1
                row_new = [""] * len(header)
                def set_new(col_name: str, val: Any):
                    pos = h_map.get(col_name)
                    if pos is not None:
                        row_new[pos] = str(val if val is not None else "").strip()

                rep_cost = c_info["repairCost"] if c_info["repairCost"] > 0 else (c_info["outerRepairs"] * 13 if c_info["outerRepairs"] > 0 else 0)

                set_new("순차", str(max_order))
                set_new("매입일", c_info["buyDate"])
                set_new("상태", "보유/상품화중")
                set_new("차량번호", c_no)
                set_new("차종", c_info["carName"])
                set_new("판매가", "0")
                set_new("재고일", str(c_info["stockDays"]))
                set_new("매입가", str(c_info["buyPrice"]))
                set_new("외판수리", str(c_info["outerRepairs"]))
                set_new("상품화", str(rep_cost))
                set_new("헤딜수수료", str(c_info["heydealerFee"]))
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

        # 원자적 파일 교체
        temp_path = f"{SETTLEMENT_CSV}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(new_rows)
            os.replace(temp_path, SETTLEMENT_CSV)
        except Exception as e:
            if os.path.exists(temp_path): os.remove(temp_path)
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
                "scrapDeduction": scrap_deduction
            })

        return cars

    @classmethod
    def clean_pre_september_inventory(cls) -> int:
        """2026년 9월 1일 이전 과거 매입 데이터 정리 (보유재고 정산표 정화)"""
        if not os.path.exists(SETTLEMENT_CSV):
            return 0
        cls.backup_file(SETTLEMENT_CSV)
        header = []
        clean_rows = []
        removed_count = 0
        for enc in ['utf-8-sig', 'utf-8', 'cp949']:
            try:
                with open(SETTLEMENT_CSV, 'r', encoding=enc) as f:
                    reader = csv.reader(f)
                    header = next(reader, [])
                    h_map = {col.strip(): i for i, col in enumerate(header)}
                    date_idx = h_map.get("매입일", 1)
                    for r in reader:
                        if not r: continue
                        b_date = r[date_idx].strip() if len(r) > date_idx else ""
                        m_d = re.search(r"(?:20\d{2}[-/.])?0?(\d{1,2})[-/.]", b_date)
                        if m_d:
                            m_val = int(m_d.group(1))
                            if m_val < 9:
                                removed_count += 1
                                continue
                        clean_rows.append(r)
                break
            except Exception:
                continue

        if header and removed_count > 0:
            temp_path = f"{SETTLEMENT_CSV}.tmp"
            try:
                with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(clean_rows)
                os.replace(temp_path, SETTLEMENT_CSV)
                print(f"[AutoplusAdminService] 9월 이전 과거 매입 데이터 {removed_count}건 정산표에서 정리 완료", flush=True)
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

            return cls.process_highplus_buy_data(cars)
        except Exception as e:
            return {"success": False, "message": f"백엔드 매입연동 호출 실패: {str(e)}", "syncedCount": 0}

