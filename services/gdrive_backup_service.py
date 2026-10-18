# services/gdrive_backup_service.py
import os
import csv
import json
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import requests

logger = logging.getLogger("GDriveBackupService")

BASE_DIR = Path(__file__).resolve().parent.parent
LEDGER_CSV_PATH = BASE_DIR / "my_car_ledger.csv"
SETTLEMENT_CSV_PATH = BASE_DIR / "my_inventory_settlement.csv"
SNAPSHOTS_JSON_PATH = BASE_DIR / "data" / "encar_snapshots.json"

DEFAULT_WEBHOOK_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbyFTXuPkC0R9y-UftHOFmJfgBwxycMwqOabhxKVT4bcsBK9gfsscQtGCTohzFiccq71/exec"
)

LEDGER_SIDEBAR_HEADERS = [
    "등록일", "차량번호", "제조사", "차량명", "세부모델",
    "연식", "주행거리", "옵션", "매입가", "판매가",
    "외판수리", "외판수리비", "헤딜수수료", "특이사항", "상태"
]


class GDriveBackupService:
    """
    J-PRO_DB 구글 스프레드시트 & 구글드라이브 백엔드 자동 백업 서비스
    - 인증: OAuth2 Refresh Token (.env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN)
            및 Google Apps Script Webhook 폴백 지원
    - 대상: 기존 'J-PRO_DB' 스프레드시트 (매입장부 15컬럼 전체, 재고정산 20컬럼, 엔카스냅샷 요약)
            + 드라이브 원본 파일(encar_snapshots.json) 동기화
    """

    _lock = threading.Lock()
    _is_syncing = False
    _scheduler_started = False
    _last_sync_time: Optional[datetime] = None
    _last_sync_status: str = "대기"
    _spreadsheet_id: Optional[str] = None
    _access_token: Optional[str] = None
    _token_expiry: float = 0.0
    _last_mtimes: Dict[str, float] = {}

    @classmethod
    def _load_env_vars(cls) -> Dict[str, str]:
        env_map: Dict[str, str] = {}
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s:
                        continue
                    k, v = s.split("=", 1)
                    env_map[k.strip()] = v.strip().strip('"').strip("'")
            except Exception:
                pass
        for k in (
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REFRESH_TOKEN",
            "GOOGLE_JPRO_DB_SPREADSHEET_ID",
            "JPRO_GOOGLE_SHEET_WEBHOOK_URL",
        ):
            if os.environ.get(k):
                env_map[k] = os.environ[k]
        return env_map

    @classmethod
    def has_refresh_token(cls) -> bool:
        env = cls._load_env_vars()
        return bool(
            env.get("GOOGLE_CLIENT_ID")
            and env.get("GOOGLE_CLIENT_SECRET")
            and env.get("GOOGLE_REFRESH_TOKEN")
        )

    @classmethod
    def _get_access_token(cls) -> Optional[str]:
        now = time.time()
        if cls._access_token and now < cls._token_expiry - 60:
            return cls._access_token

        env = cls._load_env_vars()
        client_id = env.get("GOOGLE_CLIENT_ID", "")
        client_secret = env.get("GOOGLE_CLIENT_SECRET", "")
        refresh_token = env.get("GOOGLE_REFRESH_TOKEN", "")
        if not (client_id and client_secret and refresh_token):
            return None

        try:
            resp = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                cls._access_token = data.get("access_token")
                cls._token_expiry = now + int(data.get("expires_in", 3600))
                return cls._access_token
            else:
                logger.warning(f"[GDriveBackup] 토큰 갱신 실패 ({resp.status_code}): {resp.text[:120]}")
                return None
        except Exception as e:
            logger.warning(f"[GDriveBackup] 토큰 갱신 예외: {e}")
            return None

    @classmethod
    def _find_or_create_jpro_db(cls, token: str) -> Optional[str]:
        env = cls._load_env_vars()
        configured_id = env.get("GOOGLE_JPRO_DB_SPREADSHEET_ID") or cls._spreadsheet_id
        if configured_id:
            cls._spreadsheet_id = configured_id
            return configured_id

        headers = {"Authorization": f"Bearer {token}"}
        q = "name = 'J-PRO_DB' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
        try:
            r = requests.get(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                params={"q": q, "fields": "files(id, name, modifiedTime)", "orderBy": "modifiedTime desc"},
                timeout=10,
            )
            if r.status_code == 200:
                files = r.json().get("files", [])
                if files:
                    cls._spreadsheet_id = files[0]["id"]
                    return cls._spreadsheet_id
        except Exception as e:
            logger.warning(f"[GDriveBackup] J-PRO_DB 검색 오류: {e}")

        # 없으면 J-PRO_DB 신규 생성
        try:
            create_resp = requests.post(
                "https://sheets.googleapis.com/v4/spreadsheets",
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "properties": {"title": "J-PRO_DB"},
                    "sheets": [
                        {"properties": {"title": "매입장부"}},
                        {"properties": {"title": "재고정산"}},
                        {"properties": {"title": "엔카스냅샷"}},
                    ],
                },
                timeout=15,
            )
            if create_resp.status_code == 200:
                cls._spreadsheet_id = create_resp.json().get("spreadsheetId")
                return cls._spreadsheet_id
        except Exception as e:
            logger.warning(f"[GDriveBackup] J-PRO_DB 생성 오류: {e}")
        return None

    @classmethod
    def _ensure_sheet_tabs(cls, token: str, spreadsheet_id: str, required_titles: List[str]) -> str:
        """J-PRO_DB 내 시트 탭 목록을 확인하고, 첫 번째 시트 이름을 반환하며 누락된 탭을 생성한다."""
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        first_sheet_title = "매입장부"
        try:
            meta_resp = requests.get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
                headers=headers,
                params={"fields": "sheets.properties.title"},
                timeout=10,
            )
            if meta_resp.status_code == 200:
                sheets = meta_resp.json().get("sheets", [])
                existing_titles = [s.get("properties", {}).get("title", "") for s in sheets]
                if existing_titles:
                    first_sheet_title = existing_titles[0]
                requests_body = []
                for req_title in required_titles:
                    if req_title not in existing_titles:
                        requests_body.append({"addSheet": {"properties": {"title": req_title}}})
                if requests_body:
                    requests.post(
                        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
                        headers=headers,
                        json={"requests": requests_body},
                        timeout=10,
                    )
        except Exception as e:
            logger.warning(f"[GDriveBackup] 시트 탭 확인 경고: {e}")
        return first_sheet_title

    @classmethod
    def _read_csv_rows(cls, path: Path, fallback_headers: Optional[List[str]] = None) -> List[List[str]]:
        if not path.exists():
            return [fallback_headers] if fallback_headers else []
        for enc in ("utf-8-sig", "utf-8", "cp949"):
            try:
                with open(path, "r", encoding=enc, newline="") as f:
                    rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
                    return rows if rows else ([fallback_headers] if fallback_headers else [])
            except Exception:
                continue
        return [fallback_headers] if fallback_headers else []

    @classmethod
    def _read_snapshot_rows(cls, max_rows: int = 2000) -> List[List[str]]:
        header = [
            "차량ID", "차량명", "세부모델", "연식", "주행거리",
            "가격(만원)", "사고유무", "외장컬러", "추가옵션",
            "최초수집일", "최근수집일", "상태", "연속미발견", "링크"
        ]
        if not SNAPSHOTS_JSON_PATH.exists():
            return [header]
        try:
            raw = json.loads(SNAPSHOTS_JSON_PATH.read_text(encoding="utf-8"))
            cars_dict = raw.get("cars", raw) if isinstance(raw, dict) else {}
            if not isinstance(cars_dict, dict):
                return [header]
            rows = [header]
            for cid, info in list(cars_dict.items())[:max_rows]:
                if not isinstance(info, dict):
                    continue
                rows.append([
                    str(cid),
                    str(info.get("car_name") or info.get("차량명") or ""),
                    str(info.get("sub_model") or info.get("세부모델") or ""),
                    str(info.get("year") or info.get("연식") or ""),
                    str(info.get("mileage") or info.get("주행거리") or ""),
                    str(info.get("price") or info.get("가격") or ""),
                    str(info.get("accident") or info.get("사고유무") or "-"),
                    str(info.get("color") or info.get("외장컬러") or "-"),
                    str(info.get("options") or info.get("추가옵션") or "-"),
                    str(info.get("first_seen") or info.get("firstCrawledAt") or ""),
                    str(info.get("last_seen") or info.get("lastCrawledAt") or ""),
                    str(info.get("status") or "판매중"),
                    str(info.get("consecutive_misses", 0)),
                    f"https://fem.encar.com/cars/detail/{cid}",
                ])
            return rows
        except Exception as e:
            logger.warning(f"[GDriveBackup] 스냅샷 파싱 경고: {e}")
            return [header]

    @classmethod
    def _update_sheet_values(cls, token: str, spreadsheet_id: str, sheet_title: str, rows: List[List[str]]) -> bool:
        if not rows:
            return True
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            requests.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_title}!A1:Z5000:clear",
                headers=headers,
                timeout=15,
            )
            resp = requests.put(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_title}!A1",
                headers=headers,
                params={"valueInputOption": "USER_ENTERED"},
                json={"range": f"{sheet_title}!A1", "majorDimension": "ROWS", "values": rows},
                timeout=20,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"[GDriveBackup] 시트({sheet_title}) 업데이트 오류: {e}")
            return False

    @classmethod
    def _upload_or_update_drive_file(cls, token: str, file_name: str, file_path: Path, mime_type: str) -> bool:
        if not file_path.exists():
            return False
        headers = {"Authorization": f"Bearer {token}"}
        q = f"name = '{file_name}' and trashed = false"
        existing_id = None
        try:
            r = requests.get(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                params={"q": q, "fields": "files(id, name)"},
                timeout=10,
            )
            if r.status_code == 200:
                files = r.json().get("files", [])
                if files:
                    existing_id = files[0]["id"]
        except Exception:
            pass

        boundary = "-------JPRODriveBackupBoundary314159"
        metadata = {"name": file_name, "mimeType": mime_type}
        content_bytes = file_path.read_bytes()
        body = (
            f"--{boundary}\r\n"
            "Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8") + content_bytes + f"\r\n--{boundary}--".encode("utf-8")

        url = (
            f"https://www.googleapis.com/upload/drive/v3/files/{existing_id}?uploadType=multipart"
            if existing_id
            else "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        )
        method = requests.patch if existing_id else requests.post
        try:
            resp = method(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                data=body,
                timeout=30,
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.warning(f"[GDriveBackup] 드라이브 파일({file_name}) 업로드 경고: {e}")
            return False

    @classmethod
    def _sync_via_webhook(cls, ledger_rows: List[List[str]], settlement_rows: List[List[str]]) -> Tuple[bool, str]:
        """리프레시 토큰 미설정 시 J-PRO_DB 연결 Apps Script 웹훅으로 전체 사이드바 컬럼 동기화"""
        env = cls._load_env_vars()
        webhook_url = env.get("JPRO_GOOGLE_SHEET_WEBHOOK_URL", DEFAULT_WEBHOOK_URL)
        if not webhook_url:
            return False, "웹훅 URL 미설정"

        try:
            ledger_records = []
            if len(ledger_rows) > 1:
                hdr = ledger_rows[0]
                for r in ledger_rows[1:]:
                    rec = {hdr[i]: (r[i] if i < len(r) else "") for i in range(len(hdr))}
                    ledger_records.append(rec)

            settlement_records = []
            if len(settlement_rows) > 1:
                shdr = settlement_rows[0]
                for r in settlement_rows[1:]:
                    rec = {shdr[i]: (r[i] if i < len(r) else "") for i in range(len(shdr))}
                    settlement_records.append(rec)

            payload = {
                "action": "sync_jpro_db",
                "targetSheet": "J-PRO_DB",
                "syncedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ledgerHeaders": LEDGER_SIDEBAR_HEADERS,
                "ledgerCount": len(ledger_records),
                "ledger": ledger_records,
                "settlementCount": len(settlement_records),
                "settlement": settlement_records,
            }
            # 최신 1건 호환 필드도 함께 포함 (기존 단일 행 Apps Script와도 100% 하위 호환)
            if ledger_records:
                payload.update(ledger_records[0])

            resp = requests.post(webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 302):
                return True, f"J-PRO_DB 웹훅 동기화 완료 (장부 {len(ledger_records)}대, 정산 {len(settlement_records)}대)"
            return False, f"웹훅 응답 코드 {resp.status_code}"
        except Exception as e:
            return False, f"웹훅 전송 실패: {e}"

    @classmethod
    def sync_now(cls, reason: str = "manual", include_snapshots: bool = True) -> Tuple[bool, str]:
        """J-PRO_DB 스프레드시트에 my_car_ledger.csv, my_inventory_settlement.csv, data/encar_snapshots.json 즉시 동기화"""
        with cls._lock:
            if cls._is_syncing:
                return False, "이미 백업 동기화가 진행 중입니다."
            cls._is_syncing = True

        try:
            ledger_rows = cls._read_csv_rows(LEDGER_CSV_PATH, LEDGER_SIDEBAR_HEADERS)
            settlement_rows = cls._read_csv_rows(SETTLEMENT_CSV_PATH)

            token = cls._get_access_token()
            if token:
                spreadsheet_id = cls._find_or_create_jpro_db(token)
                if spreadsheet_id:
                    first_tab = cls._ensure_sheet_tabs(
                        token, spreadsheet_id, ["매입장부", "재고정산", "엔카스냅샷"]
                    )
                    ok_ledger = cls._update_sheet_values(token, spreadsheet_id, first_tab, ledger_rows)
                    if first_tab != "매입장부":
                        cls._update_sheet_values(token, spreadsheet_id, "매입장부", ledger_rows)
                    ok_settle = cls._update_sheet_values(token, spreadsheet_id, "재고정산", settlement_rows)

                    if include_snapshots and SNAPSHOTS_JSON_PATH.exists():
                        snap_rows = cls._read_snapshot_rows(max_rows=2000)
                        cls._update_sheet_values(token, spreadsheet_id, "엔카스냅샷", snap_rows)
                        cls._upload_or_update_drive_file(
                            token,
                            "J-PRO_DB_encar_snapshots.json",
                            SNAPSHOTS_JSON_PATH,
                            "application/json",
                        )

                    cls._last_sync_time = datetime.now()
                    if ok_ledger and ok_settle:
                        cls._last_sync_status = (
                            f"J-PRO_DB 리프레시 토큰 백업 성공 "
                            f"(장부 {max(0, len(ledger_rows)-1)}대 / 정산 {max(0, len(settlement_rows)-1)}대)"
                        )
                        return True, cls._last_sync_status

            # 리프레시 토큰이 아직 설정되지 않았거나 실패한 경우 웹훅 폴백 실행
            ok_wh, msg_wh = cls._sync_via_webhook(ledger_rows, settlement_rows)
            cls._last_sync_time = datetime.now()
            cls._last_sync_status = msg_wh
            return ok_wh, msg_wh
        except Exception as e:
            cls._last_sync_status = f"백업 오류: {e}"
            return False, cls._last_sync_status
        finally:
            cls._is_syncing = False

    @classmethod
    def sync_all_async(cls, reason: str = "event", include_snapshots: bool = False):
        """비동기 백그라운드 스레드에서 J-PRO_DB 자동 백업 실행"""
        t = threading.Thread(
            target=cls.sync_now,
            args=(reason, include_snapshots),
            daemon=True,
        )
        t.start()

    @classmethod
    def _check_files_changed(cls) -> Tuple[bool, bool]:
        """파일 변경 여부 감지: (csv_changed, snapshots_changed) 반환"""
        csv_changed = False
        snap_changed = False
        for key, p in [
            ("ledger", LEDGER_CSV_PATH),
            ("settlement", SETTLEMENT_CSV_PATH),
            ("snapshots", SNAPSHOTS_JSON_PATH),
        ]:
            if p.exists():
                mtime = p.stat().st_mtime
                prev = cls._last_mtimes.get(key, 0.0)
                if mtime > prev:
                    cls._last_mtimes[key] = mtime
                    if key == "snapshots":
                        snap_changed = True
                    else:
                        csv_changed = True
        return csv_changed, snap_changed

    @classmethod
    def start_periodic_sync(cls, interval_sec: int = 1800):
        """백엔드 기동 시 주기적으로(기본 30분) 파일 변경을 감지하여 J-PRO_DB에 자동 백업"""
        if cls._scheduler_started:
            return
        cls._scheduler_started = True

        def _loop():
            # 초기 기동 15초 후 첫 동기화 체크
            time.sleep(15)
            while True:
                try:
                    csv_changed, snap_changed = cls._check_files_changed()
                    if csv_changed or snap_changed:
                        cls.sync_now(reason="periodic_scheduler", include_snapshots=snap_changed)
                except Exception as e:
                    logger.warning(f"[GDriveBackup] 스케줄러 루프 경고: {e}")
                time.sleep(interval_sec)

        t = threading.Thread(target=_loop, daemon=True, name="JPRO_GDriveBackupScheduler")
        t.start()
        print(f"[GDriveBackup] J-PRO_DB 자동 백업 스케줄러 기동 완료 (주기: {interval_sec}초)", flush=True)

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        return {
            "hasRefreshToken": cls.has_refresh_token(),
            "spreadsheetName": "J-PRO_DB",
            "spreadsheetId": cls._spreadsheet_id,
            "isSyncing": cls._is_syncing,
            "lastSyncTime": cls._last_sync_time.strftime("%Y-%m-%d %H:%M:%S") if cls._last_sync_time else None,
            "lastSyncStatus": cls._last_sync_status,
            "targetFiles": [
                "my_car_ledger.csv",
                "my_inventory_settlement.csv",
                "data/encar_snapshots.json",
            ],
        }
