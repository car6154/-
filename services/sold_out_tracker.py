# services/sold_out_tracker.py
import os
import re
import json
import threading
from datetime import datetime

class SoldOutTracker:
    """
    엔카 매물 스냅샷 추적 및 완판 실거래가·소요재고일수 역추적 엔진
    - IP 차단 위험 0%: 일상 검색 트래픽의 매물 데이터를 로컬 DB에 자동 누적
    - 완판 매물 발생 시 스냅샷과 매칭하여 실제 판매가 및 정확한 재고일수 역산
    """
    SNAPSHOT_FILE = os.path.join("data", "encar_snapshots.json")
    SOLD_HISTORY_FILE = os.path.join("data", "encar_sold_history.json")
    TRACKED_CARS_FILE = os.path.join("data", "tracked_cars.json")
    _file_lock = threading.Lock()
    _memory_cache = None

    @classmethod
    def _load_json(cls, filepath):
        with cls._file_lock:
            if not os.path.exists(filepath):
                return {}
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}

    @classmethod
    def _save_json(cls, filepath, data):
        with cls._file_lock:
            try:
                temp_path = f"{filepath}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                if os.path.exists(filepath):
                    os.remove(filepath)
                os.rename(temp_path, filepath)
                try:
                    from services.gdrive_backup_service import GDriveBackupService
                    GDriveBackupService.on_file_changed("snapshots", source="sold_out_tracker")
                except Exception:
                    pass
            except Exception as e:
                print(f"[SoldOutTracker] Save error ({filepath}): {e}")

    @classmethod
    def record_active_listings(cls, df, is_complete=True):
        """
        검색 화면에 표출된 실시간 활성 매물들을 로컬 스냅샷에 기록
        - AGENTS.md 3-3 규칙:
          1. 수집이 오류 없이 끝까지 완료됨 (is_complete=True)
          2. 연속 미발견 횟수(consecutive_misses) 추적 (1회 미발견 시 상태 유지, 횟수만 1 기록)
          3. 연속 2회 이상 미발견 시 '판매완료 추정'으로 자동 전이
          4. 다시 검색 노출 시 '판매중' 복귀 및 consecutive_misses = 0 초기화
        """
        if df is None or df.empty:
            return 0

        snapshots = cls._load_json(cls.SNAPSHOT_FILE)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        today_date_str = datetime.now().strftime("%Y-%m-%d")
        updated_count = 0
        current_seen_cids = set()

        for _, row in df.iterrows():
            cid = str(row.get('_carid', '')).strip()
            if not cid or not cid.isdigit() or len(cid) < 6:
                # 링크에서 carid 추출 시도
                link = str(row.get('링크', ''))
                m = re.search(r'(?:carid=|detail/)(\d+)', link)
                if m:
                    cid = m.group(1)
                else:
                    continue

            current_seen_cids.add(cid)
            name = str(row.get('차량명', '')).strip()
            year = str(row.get('연식', '')).strip()
            
            # 주행거리 정제
            raw_mil = str(row.get('주행거리', ''))
            mil_num = 0
            m_mil = re.search(r'([0-9,]+)', raw_mil)
            if m_mil:
                try: mil_num = int(m_mil.group(1).replace(',', ''))
                except: pass

            # 판매가 정제
            raw_prc = str(row.get('판매가', ''))
            prc_num = 0
            m_prc = re.search(r'([0-9,]+)', raw_prc)
            if m_prc:
                try: prc_num = int(m_prc.group(1).replace(',', ''))
                except: pass

            perf_date = str(row.get('성능일', '')).strip()
            if perf_date in ('-', '⚠️미등록', '미검사/사진', '⚠️조회실패'):
                perf_date = ''

            inv_days = str(row.get('재고', '')).strip()

            if cid not in snapshots:
                snapshots[cid] = {
                    "carid": cid,
                    "name": name,
                    "year": year,
                    "mileage": mil_num,
                    "price": prc_num,
                    "perf_date": perf_date,
                    "inv_days": inv_days,
                    "first_seen": today_date_str,
                    "first_seen_time": now_str,
                    "last_seen": today_date_str,
                    "status": "판매중",
                    "consecutive_misses": 0
                }
                updated_count += 1
            else:
                item = snapshots[cid]
                item["last_seen"] = today_date_str
                item["status"] = "판매중"
                item["consecutive_misses"] = 0
                item.pop("estimated_sold_date", None)
                item.pop("last_asking_price", None)
                item.pop("price_type", None)
                item.pop("is_asking_price", None)
                if prc_num > 0:
                    item["price"] = prc_num
                if perf_date and not item.get("perf_date"):
                    item["perf_date"] = perf_date
                if inv_days and inv_days != '-':
                    item["inv_days"] = inv_days

        # AGENTS.md 3-3: 수집이 오류 없이 정상 완료(is_complete=True)된 경우에만 연속 미발견 추적
        if is_complete and current_seen_cids:
            model_sample_names = [str(r.get('차량명', '')) for _, r in df.iterrows() if r.get('차량명')]
            for s_cid, s_item in snapshots.items():
                if s_cid in current_seen_cids:
                    continue
                s_name = s_item.get("name", "")
                is_matching_scope = any(cls._is_same_model(s_name, m_name) for m_name in model_sample_names[:5])
                if not is_matching_scope:
                    continue

                curr_status = s_item.get("status", "판매중")
                if curr_status in ("판매중", "active"):
                    misses = s_item.get("consecutive_misses", 0) + 1
                    s_item["consecutive_misses"] = misses
                    if misses >= 2:
                        s_item["status"] = "판매완료 추정"
                        if not s_item.get("estimated_sold_date"):
                            s_item["estimated_sold_date"] = today_date_str
                    updated_count += 1

        if updated_count > 0:
            cls._save_json(cls.SNAPSHOT_FILE, snapshots)
            print(f"[SoldOutTracker] 매물 스냅샷 갱신 완료 ({updated_count}건 변동, 총 {len(snapshots):,}건 보관 중)")

        return updated_count

    @classmethod
    def verify_car_status(cls, car_id: str, update_snapshot: bool = True):
        """
        엔카 공식 리드사이드 API를 통해 매물의 실제 판매완료/판매중 상태를 실측 확정 (AGENTS.md 3-3 준수)
        - HTTP 404: '판매완료' 확정 (update_snapshot=True인 경우 스냅샷 업데이트)
        - HTTP 200: '판매중' 확정 (consecutive_misses=0 초기화)
        - HTTP 407, 403, 429, 5xx, 타임아웃, 예외: '확인불가' (절대 판매완료 처리 금지)
        """
        import requests
        cid = re.sub(r'\D', '', str(car_id))
        if not cid:
            return {"status": "확인불가", "carId": car_id, "statusCode": 0, "isSold": None, "detail": "유효하지 않은 차량 ID"}

        api_url = f"https://api.encar.com/v1/readside/vehicle/{cid}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Referer": f"https://fem.encar.com/cars/detail/{cid}"
        }

        try:
            res = requests.get(api_url, headers=headers, timeout=5)
            status_code = res.status_code
            today_str = datetime.now().strftime("%Y-%m-%d")

            if status_code == 404:
                if update_snapshot:
                    snapshots = cls._load_json(cls.SNAPSHOT_FILE)
                    if cid in snapshots:
                        snapshots[cid]["status"] = "판매완료"
                        snapshots[cid]["verified_at"] = today_str
                        snapshots[cid]["confirmed_sold_date"] = today_str
                        cls._save_json(cls.SNAPSHOT_FILE, snapshots)
                return {
                    "status": "판매완료",
                    "carId": cid,
                    "statusCode": 404,
                    "isSold": True,
                    "verifiedAt": today_str
                }
            elif status_code == 200:
                if update_snapshot:
                    snapshots = cls._load_json(cls.SNAPSHOT_FILE)
                    if cid in snapshots:
                        snapshots[cid]["status"] = "판매중"
                        snapshots[cid]["consecutive_misses"] = 0
                        snapshots[cid]["verified_at"] = today_str
                        snapshots[cid].pop("estimated_sold_date", None)
                        snapshots[cid].pop("last_asking_price", None)
                        snapshots[cid].pop("price_type", None)
                        snapshots[cid].pop("is_asking_price", None)
                        cls._save_json(cls.SNAPSHOT_FILE, snapshots)
                return {
                    "status": "판매중",
                    "carId": cid,
                    "statusCode": 200,
                    "isSold": False,
                    "verifiedAt": today_str
                }
            elif status_code in (403, 407, 429) or status_code >= 500:
                return {
                    "status": "확인불가",
                    "carId": cid,
                    "statusCode": status_code,
                    "isSold": None,
                    "detail": f"HTTP {status_code} 차단/오류 응답 수신"
                }
            else:
                return {
                    "status": "확인불가",
                    "carId": cid,
                    "statusCode": status_code,
                    "isSold": None,
                    "detail": f"비정형 응답 코드: {status_code}"
                }
        except Exception as e:
            return {
                "status": "확인불가",
                "carId": cid,
                "statusCode": 0,
                "isSold": None,
                "detail": f"네트워크/타임아웃 오류: {str(e)}"
            }

    @classmethod
    def get_tracked_cars(cls):
        """관심 추적 차량 목록 반환"""
        return cls._load_json(cls.TRACKED_CARS_FILE)

    @classmethod
    def add_tracked_car(cls, car_id: str, car_name: str = "", car_number: str = "", price: int = 0, source: str = "cockpit", memo: str = ""):
        """관심 추적 차량 등록 (이미 존재하면 업데이트)"""
        cid = re.sub(r'\D', '', str(car_id))
        if not cid:
            return {"success": False, "error": "유효한 carid가 아닙니다."}

        tracked = cls.get_tracked_cars()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_str = datetime.now().strftime("%Y-%m-%d")

        snapshots = cls._load_json(cls.SNAPSHOT_FILE)
        snap = snapshots.get(cid, {})

        current_price = price or snap.get("price", 0)

        item = tracked.get(cid, {})
        item.update({
            "carid": cid,
            "carName": car_name or snap.get("name", "") or item.get("carName", ""),
            "carNumber": car_number or item.get("carNumber", ""),
            "price": current_price,
            "last_asking_price": current_price,
            "is_asking_price": True,
            "price_type": "호가 (팔리기 직전 호가)",
            "source": source or item.get("source", "cockpit"),
            "addedAt": item.get("addedAt", now_str),
            "lastCheckedAt": item.get("lastCheckedAt"),
            "status": item.get("status", "판매중"),
            "consecutive_misses": item.get("consecutive_misses", 0),
            "estimated_sold_date": item.get("estimated_sold_date"),
            "memo": memo or item.get("memo", "")
        })
        tracked[cid] = item
        cls._save_json(cls.TRACKED_CARS_FILE, tracked)

        # 스냅샷 DB에도 해당 carid가 없으면 등록하여 추적 보장
        if cid not in snapshots:
            snapshots[cid] = {
                "carid": cid,
                "name": item["carName"],
                "year": snap.get("year", ""),
                "mileage": snap.get("mileage", 0),
                "price": current_price,
                "last_asking_price": current_price,
                "is_asking_price": True,
                "price_type": "호가 (팔리기 직전 호가)",
                "first_seen": today_str,
                "first_seen_time": now_str,
                "last_seen": today_str,
                "status": "판매중",
                "consecutive_misses": 0
            }
            cls._save_json(cls.SNAPSHOT_FILE, snapshots)

        return {"success": True, "carid": cid, "item": item}

    @classmethod
    def remove_tracked_car(cls, car_id: str):
        """관심 추적 차량 등록 해제"""
        cid = re.sub(r'\D', '', str(car_id))
        if not cid:
            return {"success": False, "error": "유효한 carid가 아닙니다."}

        tracked = cls.get_tracked_cars()
        if cid in tracked:
            del tracked[cid]
            cls._save_json(cls.TRACKED_CARS_FILE, tracked)
            return {"success": True, "carid": cid}
        return {"success": False, "error": "등록되지 않은 차량입니다."}

    @classmethod
    def check_all_tracked_cars(cls, pacing_sec: float = 2.0):
        """
        관심 carid 목록을 순회하며 엔카 readside API로 재확인
        - 엔카 페이싱(기본 2초) 준수
        - 407, 403, 429, 5xx, 타임아웃 수신 시 즉시 중단(Abort) & 미발견 횟수 미포함
        - 404 수신 시 미발견 횟수 +1
          - 1회 미발견: 상태 '판매중' 유지
          - 2회 연속 미발견: 상태 '판매완료 추정', 마지막 저장 가격을 '팔리기 직전 호가'로 확정
        - 200 수신 시: '판매중' 확정, consecutive_misses=0 초기화
        """
        import time
        tracked = cls.get_tracked_cars()
        if not tracked:
            return {"total": 0, "checked": 0, "updated": 0, "aborted": False, "message": "추적 대상 차량 없음"}

        snapshots = cls._load_json(cls.SNAPSHOT_FILE)
        today_str = datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        checked_count = 0
        updated_count = 0
        aborted = False
        abort_reason = ""

        # 이미 판매완료(404 확정)된 차량은 제외하고 점검
        cars_to_check = [cid for cid, item in tracked.items() if item.get("status") != "판매완료"]

        print(f"[SoldOutTracker] 관심 차량 재확인 시작: 총 {len(cars_to_check)}대 대상 (페이싱 {pacing_sec}초)", flush=True)

        for idx, cid in enumerate(cars_to_check):
            if idx > 0 and pacing_sec > 0:
                time.sleep(pacing_sec)

            # verify_car_status 재사용 (스냅샷 자동갱신은 끄고 결과만 수신)
            res = cls.verify_car_status(cid, update_snapshot=False)
            status_code = res.get("statusCode", 0)

            # 407, 403, 429, 5xx, 타임아웃 등 에러/차단 시: 미발견 횟수에 포함하지 않고 즉시 중단!
            if status_code in (407, 403, 429) or status_code >= 500 or status_code == 0:
                aborted = True
                abort_reason = f"HTTP {status_code} 수신 (차단/네트워크 오류 감지)"
                print(f"[SoldOutTracker] 관심 차량 {cid} 확인 중 {abort_reason} -> 즉시 중단합니다.", flush=True)
                break

            checked_count += 1
            item = tracked[cid]
            item["lastCheckedAt"] = now_str

            if status_code == 200:
                # 판매중 정상 노출 (부활 시 이전 추정 날짜 및 호가 필드 정리)
                item["status"] = "판매중"
                item["consecutive_misses"] = 0
                item["last_seen"] = today_str
                item.pop("estimated_sold_date", None)
                item.pop("last_asking_price", None)
                item.pop("price_type", None)
                item.pop("is_asking_price", None)
                if cid in snapshots:
                    snapshots[cid]["status"] = "판매중"
                    snapshots[cid]["consecutive_misses"] = 0
                    snapshots[cid]["last_seen"] = today_str
                    snapshots[cid].pop("estimated_sold_date", None)
                    snapshots[cid].pop("last_asking_price", None)
                    snapshots[cid].pop("price_type", None)
                    snapshots[cid].pop("is_asking_price", None)
                updated_count += 1

            elif status_code == 404:
                # 404만 미발견으로 카운트
                misses = item.get("consecutive_misses", 0) + 1
                item["consecutive_misses"] = misses

                # 마지막 저장 가격 확보
                last_price = item.get("price") or (snapshots.get(cid, {}).get("price", 0)) or item.get("last_asking_price", 0)
                item["last_asking_price"] = last_price
                item["is_asking_price"] = True
                item["price_type"] = "호가 (팔리기 직전 호가)"

                if misses < 2:
                    # 1회 미발견: 상태는 판매중 유지
                    item["status"] = "판매중"
                    print(f"[SoldOutTracker] 관심 차량 {cid}: 1회 미발견 감지 (상태 유지, 연속 미발견=1)", flush=True)
                else:
                    # 2회 연속 미발견: 판매완료 추정으로 전이 + 호가 확정
                    item["status"] = "판매완료 추정"
                    # estimated_sold_date는 misses==2로 전이되는 순간에만 기록하고 misses>=3일 때 덮어쓰지 않음
                    if not item.get("estimated_sold_date"):
                        item["estimated_sold_date"] = today_str
                    print(f"[SoldOutTracker] 관심 차량 {cid}: {misses}회 연속 미발견 -> '판매완료 추정' (추정일: {item.get('estimated_sold_date')}, 직전 호가: {last_price}만)", flush=True)

                # 스냅샷에도 동일하게 반영
                if cid in snapshots:
                    snapshots[cid]["consecutive_misses"] = misses
                    snapshots[cid]["last_asking_price"] = last_price
                    snapshots[cid]["is_asking_price"] = True
                    snapshots[cid]["price_type"] = "호가 (팔리기 직전 호가)"
                    if misses >= 2:
                        snapshots[cid]["status"] = "판매완료 추정"
                        if not snapshots[cid].get("estimated_sold_date"):
                            snapshots[cid]["estimated_sold_date"] = today_str
                updated_count += 1

        cls._save_json(cls.TRACKED_CARS_FILE, tracked)
        if updated_count > 0:
            cls._save_json(cls.SNAPSHOT_FILE, snapshots)

        res_msg = f"재확인 완료: {checked_count}/{len(cars_to_check)}대 검사, {updated_count}건 갱신"
        if aborted:
            res_msg += f" (중단 사유: {abort_reason})"

        print(f"[SoldOutTracker] {res_msg}", flush=True)
        return {
            "total": len(cars_to_check),
            "checked": checked_count,
            "updated": updated_count,
            "aborted": aborted,
            "abortReason": abort_reason,
            "message": res_msg
        }

    @classmethod
    def start_tracked_cars_scheduler(cls, interval_hours: float = 12.0):
        """관심 차량 주기적(하루 2회, 12시간) 재확인 백그라운드 스레드 데몬"""
        import threading
        import time

        def _scheduler_loop():
            # 서버 기동 후 초기화 작업 완료 대기 (60초 후 1회차 점검)
            time.sleep(60)
            try:
                print("[SoldOutTracker] 관심 차량 스케줄러 기동 1회차 점검 시작", flush=True)
                cls.check_all_tracked_cars(pacing_sec=2.0)
            except Exception as e:
                print(f"[SoldOutTracker] 관심 차량 1회차 점검 예외: {e}", flush=True)

            while True:
                time.sleep(interval_hours * 3600)
                try:
                    print(f"[SoldOutTracker] 관심 차량 {interval_hours}시간 정기 재확인 점검 시작", flush=True)
                    cls.check_all_tracked_cars(pacing_sec=2.0)
                except Exception as e:
                    print(f"[SoldOutTracker] 관심 차량 정기 점검 예외: {e}", flush=True)

        t = threading.Thread(target=_scheduler_loop, daemon=True, name="TrackedCarsScheduler")
        t.start()
        print(f"[SoldOutTracker] 관심 차량 {interval_hours}시간 주기 스케줄러 등록 완료", flush=True)

    CORE_MODELS = [
        # 현대
        '아반떼', '쏘나타', '그랜저', '아이오닉', '베뉴', '코나', '투싼', '싼타페', '팰리세이드', '스타리아', '스타렉스', '포터', '캐스퍼', '벨로스터', 'i30', 'i40',
        # 기아
        '모닝', '레이', 'k3', 'k5', 'k7', 'k8', 'k9', '스팅어', '니로', '셀토스', '스포티지', '쏘렌토', '모하비', '카니발', '봉고', 'ev6', 'ev9',
        # 제네시스
        'g70', 'g80', 'g90', 'gv60', 'gv70', 'gv80', 'eq900',
        # 쉐보레
        '스파크', '크루즈', '말리부', '임팔라', '트랙스', '트레일블레이저', '이쿼녹스', '트래버스', '타호', '콜로라도', '올란도', '볼트',
        # 르노/르노코리아
        'sm3', 'sm5', 'sm6', 'sm7', 'qm3', 'qm5', 'qm6', 'xm3', '아르카나', '클리오', '마스터',
        # KGM/쌍용
        '티볼리', '코란도', '토레스', '렉스턴', '액티언', '체어맨',
        # 수입 주요
        'c클래스', 'e클래스', 's클래스', 'cla', 'cls', 'glc', 'gle', 'gls',
        '3시리즈', '5시리즈', '7시리즈', 'x1', 'x3', 'x4', 'x5', 'x6', 'x7',
        'a4', 'a6', 'a7', 'a8', 'q3', 'q5', 'q7', 'q8',
        '골프', '티구안', '파사트', '아테온'
    ]

    @classmethod
    def _is_same_model(cls, name1, name2):
        def clean_token(n):
            t = str(n).lower()
            t = re.sub(r'[\(\)\[\]_\-\s/]', '', t)
            for b in ['현대', '기아', '제네시스', '쉐보레', '르노코리아', '르노삼성', '쌍용', 'kg모빌리티', '벤츠', 'bmw', '아우디', '폭스바겐', '볼보']:
                if t.startswith(b) and len(t) > len(b):
                    t = t[len(b):]
            return t

        n1 = clean_token(name1)
        n2 = clean_token(name2)
        if not n1 or not n2:
            return False

        c1 = [c for c in cls.CORE_MODELS if c in n1]
        c2 = [c for c in cls.CORE_MODELS if c in n2]
        if c1 or c2:
            return bool(set(c1) & set(c2))
        return (n1 in n2) or (n2 in n1)

    @classmethod
    def enrich_sold_cars(cls, cars_sample, target_year=None, expected_model=None):
        """
        엔카 완판 매물 리스트(cars_sample)에 스냅샷 실거래가 및 완판 소요 재고일수 정밀 매칭
        - 차종(model) 엄격 일치: 타 차종 스냅샷 오매칭(예: 크루즈에 싼타페 매칭) 원천 차단
        - 연식(year) 2자리 엄격 일치 (예: 16년식 == 16년식)
        - 주행거리(mileage) 오차 20km 이내 일치 (엔카 완판 매물은 광고 당시 주행거리 유지)
        - 스냅샷 미매칭 매물은 어떠한 가짜 추정치도 넣지 않고 est_price=0, est_days=0 ('-' 표출용) 유지
        """
        if not cars_sample:
            return {
                "enriched_cars": [],
                "sold_avg_price": 0,
                "sold_avg_days": 0,
                "sold_days_min": 0,
                "sold_days_max": 0,
                "matched_hits": 0,
                "total_cars": 0
            }

        snapshots = cls._load_json(cls.SNAPSHOT_FILE)
        enriched = []
        prices = []
        days_list = []

        for c in cars_sample:
            c_copy = dict(c)
            c_name = str(c.get('name', '')).strip()
            c_year = str(c.get('year', '')).strip()
            c_mil = c.get('mileage', 0)
            try:
                c_mil = int(c_mil)
            except (ValueError, TypeError):
                c_mil = 0
            c_sold_date = str(c.get('sold_date', '')).strip()

            m_yr_c = re.search(r'(\d{2})', c_year)
            yr_c = m_yr_c.group(1) if m_yr_c else ""

            matched_snapshot = None
            if snapshots and c_mil > 0:
                for cid, s in snapshots.items():
                    s_mil = s.get("mileage", 0)
                    try:
                        s_mil = int(s_mil)
                    except (ValueError, TypeError):
                        s_mil = 0

                    # 1) 주행거리 엄격 일치 (오차 20km 이내)
                    if abs(s_mil - c_mil) > 20 or s_mil <= 0:
                        continue

                    # 2) 차종 일치 (동일 모델명인지 엄격 검증)
                    s_name = s.get("name", "")
                    if not cls._is_same_model(c_name, s_name):
                        continue

                    # 3) 연식 일치 (2자리 연식 비교)
                    s_yr = str(s.get("year", ""))
                    m_yr_s = re.search(r'(\d{2})', s_yr)
                    yr_s = m_yr_s.group(1) if m_yr_s else ""
                    if yr_c and yr_s and yr_c != yr_s:
                        continue

                    matched_snapshot = s
                    break

            est_price = 0
            est_days = 0
            if matched_snapshot:
                est_price = matched_snapshot.get("price", 0)
                perf_d = matched_snapshot.get("perf_date") or matched_snapshot.get("first_seen")
                raw_inv = matched_snapshot.get("inv_days", "")

                # 재고일수 역산
                if perf_d and c_sold_date:
                    try:
                        clean_sold = c_sold_date.replace('/', '-').replace('.', '-')[:10]
                        clean_ref = perf_d.replace('/', '-').replace('.', '-')[:10]
                        dt_sold = datetime.strptime(clean_sold, "%Y-%m-%d")
                        dt_ref = datetime.strptime(clean_ref, "%Y-%m-%d")
                        diff = (dt_sold - dt_ref).days
                        if diff >= 0:
                            est_days = diff if diff > 0 else 1
                    except Exception:
                        pass

                # snapshot에 inv_days 숫자가 있고 first_seen 날짜가 있을 경우 보정
                if not est_days and raw_inv and raw_inv != '-':
                    m_inv = re.search(r'(\d+)', str(raw_inv))
                    if m_inv:
                        base_days = int(m_inv.group(1))
                        f_seen = matched_snapshot.get("first_seen")
                        if f_seen and c_sold_date:
                            try:
                                dt_sold = datetime.strptime(c_sold_date.replace('/', '-')[:10], "%Y-%m-%d")
                                dt_seen = datetime.strptime(f_seen[:10], "%Y-%m-%d")
                                extra = max(0, (dt_sold - dt_seen).days)
                                est_days = base_days + extra
                            except Exception:
                                est_days = base_days
                        else:
                            est_days = base_days

                if est_price > 0:
                    prices.append(est_price)
                if est_days > 0:
                    days_list.append(est_days)

            c_copy["est_price"] = est_price
            c_copy["est_days"] = est_days
            enriched.append(c_copy)

        return {
            "enriched_cars": enriched,
            "sold_avg_price": int(sum(prices) / len(prices)) if prices else 0,
            "sold_avg_days": int(sum(days_list) / len(days_list)) if days_list else 0,
            "sold_days_min": min(days_list) if days_list else 0,
            "sold_days_max": max(days_list) if days_list else 0,
            "matched_hits": len(prices),
            "total_cars": len(enriched)
        }

