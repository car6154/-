# services/sold_out_tracker.py
import os
import re
import json
import time
from datetime import datetime
import pandas as pd

class SoldOutTracker:
    """
    엔카 매물 스냅샷 추적 및 완판 실거래가·소요재고일수 역추적 엔진
    - IP 차단 위험 0%: 일상 검색 트래픽의 매물 데이터를 로컬 DB에 자동 누적
    - 완판 매물 발생 시 스냅샷과 매칭하여 실제 판매가 및 정확한 재고일수 역산
    """
    SNAPSHOT_FILE = os.path.join("data", "encar_snapshots.json")
    SOLD_HISTORY_FILE = os.path.join("data", "encar_sold_history.json")
    _memory_cache = None

    @classmethod
    def _load_json(cls, filepath):
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @classmethod
    def _save_json(cls, filepath, data):
        try:
            temp_path = f"{filepath}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if os.path.exists(filepath):
                os.remove(filepath)
            os.rename(temp_path, filepath)
        except Exception as e:
            print(f"[SoldOutTracker] Save error ({filepath}): {e}")

    @classmethod
    def record_active_listings(cls, df):
        """
        검색 화면에 표출된 실시간 활성 매물들을 로컬 스냅샷에 기록 (IP 위험 0%)
        """
        if df is None or df.empty:
            return 0

        snapshots = cls._load_json(cls.SNAPSHOT_FILE)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        today_date_str = datetime.now().strftime("%Y-%m-%d")
        updated_count = 0

        for _, row in df.iterrows():
            cid = str(row.get('_carid', '')).strip()
            if not cid or not cid.isdigit() or len(cid) < 6:
                # 링크에서 carid 추출 시도
                link = str(row.get('링크', ''))
                m = re.search(r'carid=(\d+)', link)
                if m:
                    cid = m.group(1)
                else:
                    continue

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
                    "status": "active"
                }
                updated_count += 1
            else:
                item = snapshots[cid]
                item["last_seen"] = today_date_str
                if prc_num > 0:
                    item["price"] = prc_num
                if perf_date and not item.get("perf_date"):
                    item["perf_date"] = perf_date
                if inv_days and inv_days != '-':
                    item["inv_days"] = inv_days

        if updated_count > 0:
            cls._save_json(cls.SNAPSHOT_FILE, snapshots)
            print(f"[SoldOutTracker] 신규 매물 스냅샷 {updated_count}건 저장 완료 (총 {len(snapshots):,}건 보관 중)")

        return updated_count

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

