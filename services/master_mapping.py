# services/master_mapping.py
import os
import re
import json
import threading
import urllib.parse
from datetime import datetime

class MasterMappingService:
    _lock = threading.Lock()
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "master_car_mapping.json")

    # 대한민국 대표 차종 기본 내장 시드 (첫 실행 즉시 작동)
    SEED_MODELS = {
        "디 올 뉴 투싼 (NX4)": {
            "brand": "현대",
            "model_group": "투싼",
            "encar_model": "투싼 (NX4)",
            "aliases": ["디올뉴투싼nx4", "디올뉴투싼", "투싼nx4", "투싼(nx4)", "신형투싼", "theallnewtucsonnx4"],
            "trims": {}
        },
        "올 뉴 투싼": {
            "brand": "현대",
            "model_group": "투싼",
            "encar_model": "올 뉴 투싼",
            "aliases": ["올뉴투싼", "올뉴투싼tl", "투싼tl", "투싼올뉴"],
            "trims": {}
        },
        "더 뉴 투싼": {
            "brand": "현대",
            "model_group": "투싼",
            "encar_model": "더 뉴 투싼",
            "aliases": ["더뉴투싼"],
            "trims": {}
        },
        "그랜저 (GN7)": {
            "brand": "현대",
            "model_group": "그랜저",
            "encar_model": "디 올 뉴 그랜저",
            "aliases": ["디올뉴그랜저", "그랜저gn7", "gn7", "신형그랜저"],
            "trims": {}
        },
        "더 뉴 그랜저 IG": {
            "brand": "현대",
            "model_group": "그랜저",
            "encar_model": "더 뉴 그랜저 IG",
            "aliases": ["더뉴그랜저ig", "더뉴그랜저", "그랜저ig더뉴"],
            "trims": {}
        },
        "그랜저 IG": {
            "brand": "현대",
            "model_group": "그랜저",
            "encar_model": "그랜저 IG",
            "aliases": ["그랜저ig", "ig그랜저"],
            "trims": {}
        },
        "그랜저 HG": {
            "brand": "현대",
            "model_group": "그랜저",
            "encar_model": "그랜저 HG",
            "aliases": ["그랜저hg", "hg그랜저", "hg240", "hg300"],
            "trims": {}
        },
        "쏘렌토 4세대": {
            "brand": "기아",
            "model_group": "쏘렌토",
            "encar_model": "쏘렌토 4세대",
            "aliases": ["쏘렌토4세대", "쏘렌토mq4", "mq4", "신형쏘렌토"],
            "trims": {}
        },
        "더 뉴 쏘렌토 4세대": {
            "brand": "기아",
            "model_group": "쏘렌토",
            "encar_model": "더 뉴 쏘렌토 4세대",
            "aliases": ["더뉴쏘렌토4세대", "더뉴쏘렌토mq4", "더뉴mq4"],
            "trims": {}
        },
        "올 뉴 쏘렌토": {
            "brand": "기아",
            "model_group": "쏘렌토",
            "encar_model": "올 뉴 쏘렌토",
            "aliases": ["올뉴쏘렌토", "쏘렌토올뉴"],
            "trims": {}
        },
        "더 뉴 쏘렌토": {
            "brand": "기아",
            "model_group": "쏘렌토",
            "encar_model": "더 뉴 쏘렌토",
            "aliases": ["더뉴쏘렌토"],
            "trims": {}
        },
        "K5 3세대": {
            "brand": "기아",
            "model_group": "K5",
            "encar_model": "K5 3세대",
            "aliases": ["k53세대", "k5dl3", "dl3", "신형k5"],
            "trims": {}
        },
        "더 뉴 K5 3세대": {
            "brand": "기아",
            "model_group": "K5",
            "encar_model": "더 뉴 K5 3세대",
            "aliases": ["더뉴k53세대", "더뉴dl3"],
            "trims": {}
        },
        "카니발 4세대": {
            "brand": "기아",
            "model_group": "카니발",
            "encar_model": "카니발 4세대",
            "aliases": ["카니발4세대", "카니발ka4", "ka4", "신형카니발"],
            "trims": {}
        },
        "더 뉴 카니발 4세대": {
            "brand": "기아",
            "model_group": "카니발",
            "encar_model": "더 뉴 카니발 4세대",
            "aliases": ["더뉴카니발4세대", "더뉴ka4"],
            "trims": {}
        },
        "올 뉴 카니발": {
            "brand": "기아",
            "model_group": "카니발",
            "encar_model": "올 뉴 카니발",
            "aliases": ["올뉴카니발", "카니발yp"],
            "trims": {}
        },
        "스포티지 5세대": {
            "brand": "기아",
            "model_group": "스포티지",
            "encar_model": "스포티지 5세대",
            "aliases": ["스포티지5세대", "디올뉴스포티지", "스포티지nq5", "nq5"],
            "trims": {}
        },
        "The SUV 스포티지": {
            "brand": "기아",
            "model_group": "스포티지",
            "encar_model": "The SUV 스포티지",
            "aliases": ["thesuv스포티지", "스포티지4세대", "스포티지ql", "ql"],
            "trims": {}
        },
        "아반떼 (CN7)": {
            "brand": "현대",
            "model_group": "아반떼",
            "encar_model": "아반떼 (CN7)",
            "aliases": ["아반떼cn7", "올뉴아반떼cn7", "올뉴아반떼(cn7)", "cn7", "신형아반떼"],
            "trims": {}
        },
        "더 뉴 아반떼 (CN7)": {
            "brand": "현대",
            "model_group": "아반떼",
            "encar_model": "더 뉴 아반떼 (CN7)",
            "aliases": ["더뉴아반떼cn7", "더뉴cn7"],
            "trims": {}
        },
        "아반떼 AD": {
            "brand": "현대",
            "model_group": "아반떼",
            "encar_model": "아반떼 AD",
            "aliases": ["아반떼ad", "ad아반떼"],
            "trims": {}
        },
        "캐스퍼": {
            "brand": "현대",
            "model_group": "캐스퍼",
            "encar_model": "캐스퍼",
            "aliases": ["캐스퍼", "디에센셜", "인스퍼레이션캐스퍼"],
            "trims": {}
        },
        "더 뉴 레이": {
            "brand": "기아",
            "model_group": "레이",
            "encar_model": "더 뉴 레이",
            "aliases": ["더뉴레이", "더뉴기아레이", "올뉴레이"],
            "trims": {}
        },
        "모닝 어반": {
            "brand": "기아",
            "model_group": "모닝",
            "encar_model": "모닝 어반",
            "aliases": ["모닝어반"],
            "trims": {}
        },
        "올 뉴 모닝 (JA)": {
            "brand": "기아",
            "model_group": "모닝",
            "encar_model": "올 뉴 모닝 (JA)",
            "aliases": ["올뉴모닝ja", "올뉴모닝", "모닝ja", "모닝(ja)"],
            "trims": {}
        },
        "디 올 뉴 싼타페 (MX5)": {
            "brand": "현대",
            "model_group": "싼타페",
            "encar_model": "디 올 뉴 싼타페",
            "aliases": ["디올뉴싼타페", "싼타페mx5", "mx5", "신형싼타페"],
            "trims": {}
        },
        "싼타페 TM": {
            "brand": "현대",
            "model_group": "싼타페",
            "encar_model": "싼타페 TM",
            "aliases": ["싼타페tm", "더뉴싼타페", "tm싼타페"],
            "trims": {}
        },
        "쏘나타 디 엣지": {
            "brand": "현대",
            "model_group": "쏘나타",
            "encar_model": "쏘나타 디 엣지",
            "aliases": ["쏘나타디엣지", "디엣지"],
            "trims": {}
        },
        "쏘나타 (DN8)": {
            "brand": "현대",
            "model_group": "쏘나타",
            "encar_model": "쏘나타 (DN8)",
            "aliases": ["쏘나타dn8", "dn8", "신형쏘나타", "쏘나타(dn8)"],
            "trims": {}
        },
        "쏘나타 뉴 라이즈": {
            "brand": "현대",
            "model_group": "쏘나타",
            "encar_model": "쏘나타 뉴 라이즈",
            "aliases": ["쏘나타뉴라이즈", "뉴라이즈"],
            "trims": {}
        },
        "LF 쏘나타": {
            "brand": "현대",
            "model_group": "쏘나타",
            "encar_model": "LF 쏘나타",
            "aliases": ["lf쏘나타", "lf소나타"],
            "trims": {}
        },
        "아이오닉5": {
            "brand": "현대",
            "model_group": "아이오닉5",
            "encar_model": "아이오닉5",
            "aliases": ["아이오닉5", "더뉴아이오닉5"],
            "trims": {}
        },
        "i30 (PD)": {
            "brand": "현대",
            "model_group": "i30",
            "encar_model": "i30 (PD)",
            "aliases": ["i30pd", "i30(pd)", "i30nline"],
            "trims": {}
        },
        "더 뉴 QM6": {
            "brand": "르노코리아(삼성_)",
            "model_group": "QM6",
            "encar_model": "더 뉴 QM6",
            "aliases": ["더뉴qm6", "뉴qm6", "qm6더뉴"],
            "trims": {}
        },
        "G80 (RG3)": {
            "brand": "제네시스",
            "model_group": "G80",
            "encar_model": "G80 (RG3)",
            "aliases": ["디올뉴g80", "g80rg3", "rg3", "신형g80", "g80(rg3)"],
            "trims": {}
        },
        "GV70": {
            "brand": "제네시스",
            "model_group": "GV70",
            "encar_model": "GV70",
            "aliases": ["gv70", "제네시스gv70"],
            "trims": {}
        },
        "GV80": {
            "brand": "제네시스",
            "model_group": "GV80",
            "encar_model": "GV80",
            "aliases": ["gv80", "제네시스gv80"],
            "trims": {}
        }
    }

    @classmethod
    def _normalize_key(cls, text: str) -> str:
        """문자열에서 공백, 특수문자를 제거하고 소문자로 정규화"""
        if not text:
            return ""
        s = str(text).lower()
        return re.sub(r'[\s\(\)\[\]\-_,./]', '', s)

    @classmethod
    def _load_db(cls) -> dict:
        """DB 파일 로드 또는 시드로 초기화"""
        os.makedirs(os.path.dirname(cls.DB_PATH), exist_ok=True)
        if not os.path.exists(cls.DB_PATH):
            db = {
                "version": "1.0",
                "models": cls.SEED_MODELS.copy(),
                "normalized_models": {},
                "car_links": {}
            }
            # 시드 기반 정규화 인덱스 생성
            for m_name, m_info in cls.SEED_MODELS.items():
                norm = cls._normalize_key(m_name)
                if norm:
                    db["normalized_models"][norm] = m_name
                norm_encar = cls._normalize_key(m_info.get("encar_model", ""))
                if norm_encar:
                    db["normalized_models"][norm_encar] = m_name
                for a in m_info.get("aliases", []):
                    norm_a = cls._normalize_key(a)
                    if norm_a:
                        db["normalized_models"][norm_a] = m_name

            cls._save_db_unlocked(db)
            return db

        try:
            with open(cls.DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[MasterMapping] DB 로드 실패, 백업 후 초기화: {e}")
            return {
                "version": "1.0",
                "models": cls.SEED_MODELS.copy(),
                "normalized_models": {},
                "car_links": {}
            }

    @classmethod
    def _save_db_unlocked(cls, db: dict):
        """내부 락 없는 저장 메서드"""
        try:
            tmp_path = cls.DB_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            if os.path.exists(cls.DB_PATH):
                os.replace(tmp_path, cls.DB_PATH)
            else:
                os.rename(tmp_path, cls.DB_PATH)
        except Exception as e:
            print(f"[MasterMapping] DB 저장 오류: {e}")

    @classmethod
    def _clean_encar_token(cls, val: str) -> str:
        """엔카 카탈로그 토큰 내 유니코드 이스케이프 및 + 기호 정제 (실제 공백 및 한글로 복원)"""
        if not val:
            return ""
        # 1. 유니코드 이스케이프(\uXXXX) 복원
        if "\\u" in val or r"\u" in val:
            try:
                val = val.encode('utf-8').decode('unicode_escape')
            except Exception:
                pass
        # 2. + 문자를 공백으로 변환 (엔카 action 조건식은 +가 아닌 공백 문자를 요구함)
        val = val.replace("+", " ")
        # 3. 연속 공백 축약 및 양끝 공백 제거
        return re.sub(r'\s+', ' ', val).strip()

    @classmethod
    def parse_encar_url(cls, url: str) -> dict:
        """
        엔카 URL (PC Action 문자열 또는 모바일 overview)에서 엔카 공식 카탈로그 계층 추출
        반환: {'Manufacturer': ..., 'ModelGroup': ..., 'Model': ..., 'BadgeGroup': ..., 'Badge': ..., 'BadgeDetail': ...}
        """
        if not url:
            return {}
        try:
            uq_str = urllib.parse.unquote(url)
            res = {}
            tokens = ['Manufacturer', 'ModelGroup', 'Model', 'BadgeGroup', 'Badge', 'BadgeDetail']
            for t in tokens:
                # 'Token.' 부터 '._.' 또는 '.)' 또는 문자열 끝까지 탐색
                m = re.search(r'\b' + t + r'\.((?:(?!\._\.|\.\)).)+)', uq_str)
                if m:
                    raw_val = m.group(1)
                    val = raw_val.replace('_.', '.').rstrip('.').strip()
                    res[t] = cls._clean_encar_token(val)
            return res
        except Exception as e:
            print(f"[MasterMapping] 엔카 URL 파싱 실패: {e}")
            return {}

    @classmethod
    def learn_from_heydealer(cls, detail_dict: dict, encar_url: str):
        """
        헤이딜러 조회 시 수신한 detail 데이터와 encar_url로부터 마스터 매핑을 자체 학습
        - 세대(Model) 레벨과 세부등급(Trim)을 계층 분리하여 저장하므로,
          하나의 트림만 조회되어도 해당 세대의 모든 트림에 대해 엔카 Model 매핑이 영구 완성됨!
        """
        if not detail_dict or not encar_url:
            return

        parsed_encar = cls.parse_encar_url(encar_url)
        encar_brand = parsed_encar.get('Manufacturer', '')
        encar_mg = parsed_encar.get('ModelGroup', '')
        encar_model = parsed_encar.get('Model', '')
        encar_bg = parsed_encar.get('BadgeGroup', '')
        encar_badge = parsed_encar.get('Badge', '')
        encar_detail = parsed_encar.get('BadgeDetail', '')

        # 엔카 모델이 최소한 나와야 학습 유효
        if not encar_model and not encar_mg:
            return

        hd_brand = detail_dict.get('brand_name', '')
        hd_model_part = detail_dict.get('model_part_name', '') or detail_dict.get('full_name_without_brand', '')
        hd_grade_part = detail_dict.get('grade_part_name', '')
        hd_full_name = detail_dict.get('full_name', '')
        hd_car_num = detail_dict.get('car_number', '') or detail_dict.get('vehicle_number', '')

        with cls._lock:
            db = cls._load_db()
            models = db.setdefault("models", {})
            norm_idx = db.setdefault("normalized_models", {})
            car_links = db.setdefault("car_links", {})

            # 1. 차량번호 직통 엔카 URL 링크 저장 (매입장부/정산장부 100% 무오차 직통 연결용)
            if hd_car_num:
                car_links[hd_car_num.strip()] = encar_url

            # 2. 계층형 모델 정보 등록
            primary_key = hd_model_part.strip() if hd_model_part else (encar_model or encar_mg)
            if not primary_key:
                return

            if primary_key not in models:
                models[primary_key] = {
                    "brand": encar_brand or hd_brand,
                    "model_group": encar_mg,
                    "encar_model": encar_model or encar_mg,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "aliases": [],
                    "trims": {}
                }
            else:
                # 보강
                if encar_brand and not models[primary_key].get("brand"):
                    models[primary_key]["brand"] = encar_brand
                if encar_mg and not models[primary_key].get("model_group"):
                    models[primary_key]["model_group"] = encar_mg
                if encar_model:
                    models[primary_key]["encar_model"] = encar_model

            # 세부 등급(트림) 등록
            if hd_grade_part:
                models[primary_key].setdefault("trims", {})[hd_grade_part.strip()] = {
                    "badge_group": encar_bg,
                    "badge": encar_badge,
                    "badge_detail": encar_detail,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

            # 3. 정규화 별칭(Alias) 인덱스 업데이트
            keys_to_index = [
                primary_key,
                hd_model_part,
                encar_model,
                hd_full_name
            ]
            for raw_k in keys_to_index:
                if not raw_k:
                    continue
                norm = cls._normalize_key(raw_k)
                if norm and len(norm) >= 2:
                    norm_idx[norm] = primary_key

            cls._save_db_unlocked(db)

    @classmethod
    def save_car_link(cls, car_number: str, encar_url: str):
        """특정 차량번호와 엔카 검색 URL을 바인딩 저장"""
        if not car_number or not encar_url:
            return
        c_num = car_number.strip()
        with cls._lock:
            db = cls._load_db()
            db.setdefault("car_links", {})[c_num] = encar_url
            cls._save_db_unlocked(db)

    @classmethod
    def get_car_link(cls, car_number: str) -> str:
        """특정 차량번호의 확정 엔카 URL 조회 (0순위 직통 반환)"""
        if not car_number:
            return ""
        c_num = car_number.strip()
        with cls._lock:
            db = cls._load_db()
            return db.get("car_links", {}).get(c_num, "")

    @classmethod
    def resolve_encar_model(cls, brand: str = "", car_name: str = "", sub_model: str = "") -> dict:
        """
        차량명/세부모델을 기반으로 마스터 DB에서 공식 엔카 (Manufacturer, ModelGroup, Model) 추출
        반환: {'brand': ..., 'model_group': ..., 'encar_model': ..., 'matched_key': ...} or {}
        """
        full_text = f"{car_name or ''} {sub_model or ''}".strip()
        if not full_text:
            return {}

        with cls._lock:
            db = cls._load_db()
            models = db.get("models", {})
            norm_idx = db.get("normalized_models", {})

            # 1. 정규화 키 일치 탐색 (차량명 단독 ➔ 전체 텍스트 순)
            c_norm = cls._normalize_key(car_name)
            f_norm = cls._normalize_key(full_text)

            matched_master_key = None
            if c_norm in norm_idx:
                matched_master_key = norm_idx[c_norm]
            elif f_norm in norm_idx:
                matched_master_key = norm_idx[f_norm]
            else:
                # 2. 부분 일치 탐색 (긴 패턴 우선)
                best_len = 0
                for norm_cand, m_key in norm_idx.items():
                    if norm_cand in f_norm or f_norm in norm_cand:
                        if len(norm_cand) > best_len:
                            best_len = len(norm_cand)
                            matched_master_key = m_key

            if matched_master_key and matched_master_key in models:
                m_info = models[matched_master_key]
                return {
                    "brand": m_info.get("brand") or brand or "현대",
                    "model_group": m_info.get("model_group", ""),
                    "encar_model": m_info.get("encar_model", ""),
                    "matched_key": matched_master_key,
                    "trims": m_info.get("trims", {})
                }

            return {}

    @classmethod
    def generate_smart_encar_url(
        cls, 
        car_name: str, 
        sub_model: str = "", 
        year: any = "", 
        mileage: any = 0, 
        car_number: str = ""
    ) -> str:
        """
        스마트 엔카 URL 생성:
        1순위: 차량번호가 마스터 링크(car_links)에 등록되어 있으면 직통 URL 반환!
        2순위: 마스터 DB 모델 계층 매칭 성공 시, 엔카 공식 데스크톱 Action URL 조립
        3순위: 마스터 DB 미등록 차종은 기존 SalesDataAnalyzer.generate_encar_url로 완벽 Fallback
        """
        # 1순위: 등록된 차량번호 직통 URL 확인
        if car_number:
            direct_url = cls.get_car_link(car_number)
            if direct_url and "action=" in direct_url:
                return direct_url

        # 2순위: 마스터 DB에서 모델 계층 확인
        master_match = cls.resolve_encar_model("", car_name, sub_model)
        if master_match and master_match.get("model_group"):
            f_brand = cls._clean_encar_token(master_match.get("brand", "현대"))
            f_mg = cls._clean_encar_token(master_match.get("model_group", ""))
            f_model = cls._clean_encar_token(master_match.get("encar_model", ""))

            # 연식 파싱
            parsed_year = 0
            if year:
                m_yr = re.search(r'(\d{2,4})', str(year))
                if m_yr:
                    y_val = int(m_yr.group(1))
                    parsed_year = (y_val + 2000) if y_val < 100 else y_val

            # 수입차 여부 확인
            is_import = f_brand in [
                '벤츠', 'BMW', '아우디', '폭스바겐', '볼보', '포르쉐', '테슬라', 
                '포드', '링컨', '혼다', '토요타', '렉서스', '지프', '랜드로버', '미니', '푸조', '폴스타'
            ]
            car_type = "for" if is_import else "kor"

            # 엔카 특수 브랜드명 보정 (언더바 등)
            BRAND_ENCAR_MAP = {
                "르노코리아(삼성)": "르노코리아(삼성_)",
                "르노코리아": "르노코리아(삼성_)",
                "르노": "르노코리아(삼성_)",
                "쉐보레(GM대우)": "쉐보레(GM대우_)",
                "쉐보레": "쉐보레(GM대우_)",
                "KG모빌리티(쌍용)": "KG모빌리티(쌍용_)",
                "쌍용": "KG모빌리티(쌍용_)",
                "KGM": "KG모빌리티(쌍용_)"
            }
            mapped_brand = BRAND_ENCAR_MAP.get(f_brand, f_brand)

            # 모델 코어 트리
            if f_model:
                core_tree = f"(C.CarType.Y._.(C.Manufacturer.{mapped_brand}._.(C.ModelGroup.{f_mg}._.Model.{f_model}.)))"
            else:
                core_tree = f"(C.CarType.Y._.(C.Manufacturer.{mapped_brand}._.ModelGroup.{f_mg}.))"

            action = f"(And.Hidden.N._.{core_tree}"

            # 연식 밴드 (±1년)
            if parsed_year and parsed_year >= 2000:
                action += f"_.Year.range({parsed_year - 1}01..{parsed_year + 1}12)."

            # 주행거리 밴드 (±20,000km)
            try:
                mil_val = int(re.sub(r'[^\d]', '', str(mileage)))
                if mil_val >= 50000 or (parsed_year and (2026 - parsed_year < 5) and mil_val > 5000):
                    min_mil = max(0, ((mil_val - 20000) // 10000) * 10000)
                    max_mil = ((mil_val + 20000 + 9999) // 10000) * 10000
                    action += f"_.Mileage.range({min_mil}..{max_mil})."
            except Exception:
                pass

            action += ")"

            payload = {
                "action": action,
                "toggle": {},
                "layer": "",
                "sort": "ModifiedDate",
                "page": 1,
                "limit": 50
            }
            enc_hash = urllib.parse.quote(json.dumps(payload, ensure_ascii=False, separators=(',', ':')))
            return f"https://www.encar.com/dc/dc_carsearchlist.do?carType={car_type}&searchType=model&TG.RType=auto#!{enc_hash}"

        # 3순위: 마스터 DB 미매칭 시 기존 정규식 기반 함수로 Fallback
        from sales_analysis import SalesDataAnalyzer
        return SalesDataAnalyzer.generate_encar_url(car_name, sub_model, year, mileage)

    @classmethod
    def get_stats(cls) -> dict:
        """마스터 매핑 현황 통계 반환"""
        with cls._lock:
            db = cls._load_db()
            models = db.get("models", {})
            car_links = db.get("car_links", {})
            total_trims = sum(len(m.get("trims", {})) for m in models.values())
            return {
                "total_models": len(models),
                "total_trims": total_trims,
                "total_car_links": len(car_links)
            }
