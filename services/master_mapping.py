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
            "aliases": ["디올뉴투싼nx4", "디올뉴투싼", "더올뉴투싼", "더올뉴투싼nx4", "더 올뉴투싼", "더 올 뉴 투싼", "더올뉴투싼(nx4)", "투싼nx4", "투싼(nx4)", "신형투싼", "theallnewtucsonnx4"],
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
            "encar_model": "그랜저 (GN7)",
            "aliases": ["디올뉴그랜저", "더올뉴그랜저", "그랜저gn7", "gn7", "신형그랜저"],
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
        "더 뉴 레이": {
            "brand": "기아",
            "model_group": "레이",
            "encar_model": "더 뉴 레이",
            "aliases": ["더뉴레이", "더 뉴 레이"],
            "trims": {}
        },
        "더 뉴 스파크": {
            "brand": "쉐보레(GM대우_)",
            "model_group": "스파크",
            "encar_model": "더 뉴 스파크",
            "aliases": ["더뉴스파크", "더 뉴 스파크", "thenewspark"],
            "trims": {
                "LT": {
                    "badge_group": "가솔린 1000cc",
                    "badge": "LT",
                    "badge_detail": ""
                },
                "LT C-Tech": {
                    "badge_group": "가솔린 1000cc",
                    "badge": "LT",
                    "badge_detail": ""
                },
                "프리미어": {
                    "badge_group": "가솔린 1000cc",
                    "badge": "프리미어",
                    "badge_detail": ""
                },
                "LS": {
                    "badge_group": "가솔린 1000cc",
                    "badge": "LS",
                    "badge_detail": ""
                },
                "LS 베이직": {
                    "badge_group": "가솔린 1000cc",
                    "badge": "LS 베이직",
                    "badge_detail": ""
                }
            }
        },
        "더 넥스트 스파크": {
            "brand": "쉐보레(GM대우_)",
            "model_group": "스파크",
            "encar_model": "더 넥스트 스파크",
            "aliases": ["더넥스트스파크", "더 넥스트 스파크", "thenextspark"],
            "trims": {
                "LTZ": {
                    "badge_group": "가솔린 1000cc",
                    "badge": "LTZ",
                    "badge_detail": ""
                },
                "LT Plus": {
                    "badge_group": "가솔린 1000cc",
                    "badge": "LT Plus",
                    "badge_detail": ""
                },
                "LT": {
                    "badge_group": "가솔린 1000cc",
                    "badge": "LT",
                    "badge_detail": ""
                },
                "LS": {
                    "badge_group": "가솔린 1000cc",
                    "badge": "LS",
                    "badge_detail": ""
                }
            }
        },
        "레이": {
            "brand": "기아",
            "model_group": "레이",
            "encar_model": "레이",
            "aliases": ["레이", "기아레이", "ray"],
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
        "디 올뉴싼타페": {
            "brand": "현대",
            "model_group": "싼타페",
            "encar_model": "싼타페 (MX5)",
            "aliases": ["디올뉴싼타페", "디 올 뉴 싼타페 (MX5)", "싼타페mx5", "mx5", "신형싼타페"],
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
            "aliases": ["아이오닉5"],
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
        },
        "더 뉴 K3 2세대": {
            "brand": "기아",
            "model_group": "K3",
            "encar_model": "더 뉴 K3 2세대",
            "aliases": ["더뉴k32세대", "더뉴k3", "k32세대", "신형k3"],
            "trims": {}
        },
        "올 뉴 K3": {
            "brand": "기아",
            "model_group": "K3",
            "encar_model": "올 뉴 K3",
            "aliases": ["올뉴k3", "k3올뉴", "올뉴k3bd", "k3bd"],
            "trims": {}
        },
        "K3": {
            "brand": "기아",
            "model_group": "K3",
            "encar_model": "K3",
            "aliases": ["k3", "기아k3"],
            "trims": {}
        },
        "K8": {
            "brand": "기아",
            "model_group": "K8",
            "encar_model": "K8",
            "aliases": ["k8", "기아k8"],
            "trims": {}
        },
        "셀토스": {
            "brand": "기아",
            "model_group": "셀토스",
            "encar_model": "셀토스",
            "aliases": ["셀토스", "기아셀토스"],
            "trims": {}
        },
        "더 뉴 말리부": {
            "brand": "쉐보레(GM대우_)",
            "model_group": "말리부",
            "encar_model": "더 뉴 말리부",
            "aliases": ["더뉴말리부", "말리부더뉴"],
            "trims": {}
        },
        "올 뉴 말리부": {
            "brand": "쉐보레(GM대우_)",
            "model_group": "말리부",
            "encar_model": "올 뉴 말리부",
            "aliases": ["올뉴말리부", "말리부올뉴"],
            "trims": {}
        },
        "말리부": {
            "brand": "쉐보레(GM대우_)",
            "model_group": "말리부",
            "encar_model": "말리부",
            "aliases": ["말리부", "쉐보레말리부"],
            "trims": {}
        },
        "디 올뉴싼타페": {
            "brand": "현대",
            "model_group": "싼타페",
            "encar_model": "싼타페 (MX5)",
            "aliases": ["디올뉴싼타페", "디 올 뉴 싼타페 (MX5)", "싼타페mx5", "mx5", "신형싼타페"],
            "trims": {}
        },
        "더 뉴 싼타페": {
            "brand": "현대",
            "model_group": "싼타페",
            "encar_model": "더 뉴 싼타페",
            "aliases": ["더뉴싼타페", "더뉴싼타페tm"],
            "trims": {}
        },
        "싼타페 더 프라임": {
            "brand": "현대",
            "model_group": "싼타페",
            "encar_model": "싼타페 더 프라임",
            "aliases": ["싼타페더프라임", "더프라임"],
            "trims": {}
        },
        "싼타페 DM": {
            "brand": "현대",
            "model_group": "싼타페",
            "encar_model": "싼타페 DM",
            "aliases": ["싼타페dm", "싼타페(dm)"],
            "trims": {}
        },
        "베리 뉴 티볼리": {
            "brand": "KG모빌리티(쌍용_)",
            "model_group": "티볼리",
            "encar_model": "베리 뉴 티볼리",
            "aliases": ["베리뉴티볼리"],
            "trims": {}
        },
        "티볼리 아머": {
            "brand": "KG모빌리티(쌍용_)",
            "model_group": "티볼리",
            "encar_model": "티볼리 아머",
            "aliases": ["티볼리아머"],
            "trims": {}
        },
        "티볼리": {
            "brand": "KG모빌리티(쌍용_)",
            "model_group": "티볼리",
            "encar_model": "티볼리",
            "aliases": ["티볼리", "쌍용티볼리"],
            "trims": {}
        },
        "QM6": {
            "brand": "르노코리아(삼성_)",
            "model_group": "QM6",
            "encar_model": "QM6",
            "aliases": ["qm6", "르노qm6"],
            "trims": {}
        },
        "스파크": {
            "brand": "쉐보레(GM대우_)",
            "model_group": "스파크",
            "encar_model": "스파크",
            "aliases": ["스파크"],
            "trims": {}
        },
        "올 뉴 모닝": {
            "brand": "기아",
            "model_group": "모닝",
            "encar_model": "올 뉴 모닝",
            "aliases": ["올뉴모닝", "모닝올뉴"],
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
        """DB 파일 로드 또는 시드로 초기화 (시드의 최신 별칭 자동 병합)"""
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
                db = json.load(f)
            
            # 💡 기존 DB 파일에 시드의 최신 별칭/모델 정규화 자동 병합
            models = db.setdefault("models", {})
            norm_idx = db.setdefault("normalized_models", {})
            for m_name, m_info in cls.SEED_MODELS.items():
                if m_name not in models:
                    models[m_name] = m_info.copy()
                else:
                    # 기존 모델 정보에 신규 별칭 보강
                    existing_aliases = set(models[m_name].get("aliases", []))
                    new_aliases = set(m_info.get("aliases", []))
                    models[m_name]["aliases"] = list(existing_aliases | new_aliases)

                norm = cls._normalize_key(m_name)
                if norm:
                    norm_idx[norm] = m_name
                norm_encar = cls._normalize_key(m_info.get("encar_model", ""))
                if norm_encar:
                    norm_idx[norm_encar] = m_name
                for a in m_info.get("aliases", []):
                    norm_a = cls._normalize_key(a)
                    if norm_a:
                        norm_idx[norm_a] = m_name

            # 💡 DB에 등록된 전체 models에 대해서도 정규화 인덱스 누락 원천 방지
            for m_name, m_info in models.items():
                norm = cls._normalize_key(m_name)
                if norm and norm not in norm_idx:
                    norm_idx[norm] = m_name
                norm_encar = cls._normalize_key(m_info.get("encar_model", ""))
                if norm_encar and norm_encar not in norm_idx:
                    norm_idx[norm_encar] = m_name
                for a in m_info.get("aliases", []):
                    norm_a = cls._normalize_key(a)
                    if norm_a and norm_a not in norm_idx:
                        norm_idx[norm_a] = m_name

            return db
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
        # 2. 연속 공백 축약 및 양끝 공백 제거 (주의: '가솔린+전기' 등 실제 카탈로그 토큰의 + 기호는 반드시 보존)
        return re.sub(r'\s+', ' ', val).strip()

    @classmethod
    def _escape_encar_dsl_token(cls, token: str) -> str:
        """엔카 DSL용 토큰 이스케이프 (숫자 소수점 1.6 -> 1_.6, 괄호 (NX4) -> (NX4_))"""
        if not token:
            return ""
        # 1. 숫자 사이 소수점 이스케이프 (1.6 -> 1_.6, 2.0 -> 2_.0 등, 이미 이스케이프된 경우 보존)
        token = re.sub(r'(\d)(?<!_\.)\.(\d)', r'\1_.\2', token)
        # 2. 닫는 괄호 이스케이프 ( (NX4) -> (NX4_) ) 단, 이미 _) 형태인 경우는 유지
        token = re.sub(r'(?<!_)\)', '_)', token)
        return token

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

    YEAR_GENERATION_RULES = {
        "아반떼": [
            (2023, 2030, "더 뉴 아반떼 (CN7)"),
            (2020, 2023, "아반떼 (CN7)"),
            (2015, 2020, "아반떼 AD"),
        ],
        "카니발": [
            (2023, 2030, "더 뉴 카니발 4세대"),
            (2020, 2023, "카니발 4세대"),
            (2014, 2020, "올 뉴 카니발"),
        ],
        "쏘렌토": [
            (2023, 2030, "더 뉴 쏘렌토 4세대"),
            (2020, 2023, "쏘렌토 4세대"),
            (2017, 2020, "더 뉴 쏘렌토"),
            (2014, 2017, "올 뉴 쏘렌토"),
        ],
        "그랜저": [
            (2022, 2030, "그랜저 (GN7)"),
            (2019, 2022, "더 뉴 그랜저 IG"),
            (2016, 2019, "그랜저 IG"),
            (2011, 2016, "그랜저 HG"),
        ],
        "투싼": [
            (2020, 2030, "디 올 뉴 투싼 (NX4)"),
            (2018, 2020, "더 뉴 투싼"),
            (2015, 2018, "올 뉴 투싼"),
        ],
        "스포티지": [
            (2021, 2030, "스포티지 5세대"),
            (2015, 2021, "The SUV 스포티지"),
        ],
        "K5": [
            (2023, 2030, "더 뉴 K5 3세대"),
            (2019, 2023, "K5 3세대"),
        ],
        "쏘나타": [
            (2023, 2030, "쏘나타 디 엣지"),
            (2019, 2023, "쏘나타 (DN8)"),
            (2017, 2019, "쏘나타 뉴 라이즈"),
            (2014, 2017, "LF 쏘나타"),
        ],
        "K3": [
            (2021, 2025, "더 뉴 K3 2세대"),
            (2018, 2021, "올 뉴 K3"),
            (2012, 2018, "K3"),
        ],
        "QM6": [
            (2023, 2025, "더 뉴 QM6"),
            (2019, 2023, "더 뉴 QM6"),
            (2016, 2019, "QM6"),
        ],
        "티볼리": [
            (2019, 2025, "베리 뉴 티볼리"),
            (2017, 2019, "티볼리 아머"),
            (2015, 2017, "티볼리"),
        ],
        "말리부": [
            (2018, 2023, "더 뉴 말리부"),
            (2016, 2018, "올 뉴 말리부"),
            (2011, 2016, "말리부"),
        ],
        "싼타페": [
            (2023, 2025, "디 올뉴싼타페"),
            (2020, 2023, "더 뉴 싼타페"),
            (2018, 2020, "싼타페 TM"),
            (2015, 2018, "싼타페 더 프라임"),
            (2012, 2015, "싼타페 DM"),
        ],
        "모닝": [
            (2020, 2025, "모닝 어반"),
            (2017, 2020, "올 뉴 모닝 (JA)"),
            (2011, 2017, "올 뉴 모닝"),
        ],
        "레이": [
            (2017, 2030, "더 뉴 레이"),
            (2011, 2017, "레이"),
        ],
        "스파크": [
            (2018, 2024, "더 뉴 스파크"),
            (2015, 2018, "더 넥스트 스파크"),
            (2011, 2015, "스파크"),
        ],
    }

    @classmethod
    def resolve_encar_model(cls, brand: str = "", car_name: str = "", sub_model: str = "", year: any = "") -> dict:
        """
        차량명/세부모델을 기반으로 마스터 DB에서 공식 엔카 (Manufacturer, ModelGroup, Model) 추출
        반환: {'brand': ..., 'model_group': ..., 'encar_model': ..., 'matched_key': ...} or {}
        """
        full_text = f"{car_name or ''} {sub_model or ''}".strip()
        if not full_text:
            return {}

        parsed_y = 0
        if year:
            m_yr = re.search(r'(\d{2,4})', str(year))
            if m_yr:
                y_val = int(m_yr.group(1))
                parsed_y = (y_val + 2000) if y_val < 100 else y_val

        with cls._lock:
            db = cls._load_db()
            models = db.get("models", {})
            norm_idx = db.get("normalized_models", {})

            c_norm = cls._normalize_key(car_name)
            f_norm = cls._normalize_key(full_text)

            matched_master_key = None

            # 1. 차량명 단독 일치 탐색
            # 단, '아반떼', '투싼', '스파크', 'k3' 등 순수 대표 차종명이고 연식(parsed_y)이 있으면 연식 세대 규칙에 우선권 부여
            pure_model_group = False
            for mg_k in cls.YEAR_GENERATION_RULES.keys():
                if c_norm == cls._normalize_key(mg_k):
                    pure_model_group = True
                    break

            if c_norm in norm_idx and not (pure_model_group and parsed_y):
                matched_master_key = norm_idx[c_norm]

            # 2. 연식 기반 세대 모델 자동 판별 (버그 3 수정: 부분 일치보다 먼저 실행)
            if not matched_master_key and parsed_y:
                for mg_k, gen_rules in cls.YEAR_GENERATION_RULES.items():
                    norm_mg = cls._normalize_key(mg_k)
                    # c_norm과 정확히 일치하거나 의미 있는 어절로 포함되는 경우
                    if norm_mg == c_norm or (norm_mg in c_norm and len(norm_mg) >= 2):
                        for y_min, y_max, target_model in gen_rules:
                            if y_min <= parsed_y <= y_max:
                                matched_master_key = target_model
                                break
                    # 💡 버그 2 수정: 이번 mg_k에서 실제 target_model을 매칭했을 때만 루프 탈출
                    if matched_master_key and matched_master_key in models:
                        break

            # 3. 전체 텍스트(차량명+세부모델) 완전 일치 탐색
            if not matched_master_key:
                if f_norm in norm_idx:
                    matched_master_key = norm_idx[f_norm]
                elif c_norm in norm_idx:
                    matched_master_key = norm_idx[c_norm]

            TRIM_STOPWORDS = {
                '인스퍼레이션', '프리미엄', '노블레스', '시그니처', '프레스티지',
                '익스클루시브', '캘리그래피', '트렌디', '스마트', '모던', '디럭스',
                '럭셔리', '스타일', '가솔린', '디젤', '하이브리드', '터보'
            }

            # 3-1. 긴 키 우선 부분 포함 탐색 (구체적인(긴) 모델명이 짧은 모델명에 먼저 먹히지 않도록 긴 키 우선 정렬)
            if not matched_master_key:
                sorted_cands = sorted(norm_idx.items(), key=lambda x: len(x[0]), reverse=True)
                for norm_cand, m_key in sorted_cands:
                    if len(norm_cand) < 2:
                        continue
                    if norm_cand in TRIM_STOPWORDS:
                        continue
                    if norm_cand == c_norm or norm_cand == f_norm:
                        matched_master_key = m_key
                        break
                    # 의미 있는 길이(4자 이상)의 포함 관계 탐색 (예: '더뉴셀토스'가 입력에 포함된 경우)
                    if len(norm_cand) >= 4 and (norm_cand in c_norm or norm_cand in f_norm):
                        matched_master_key = m_key
                        break

            # 4. 어절(단어 경계) 단위 부분 일치 탐색 (버그 1 수정: 트림명 내부 음절 오매칭 원천 차단)
            if not matched_master_key:
                words = [w for w in re.split(r'[\s\(\)\[\]\-_,./]+', str(car_name)) if len(w) >= 2]
                best_len = 0
                for w in words:
                    w_norm = cls._normalize_key(w)
                    if w_norm in TRIM_STOPWORDS:
                        continue
                    if w_norm in norm_idx and w_norm not in TRIM_STOPWORDS:
                        matched_master_key = norm_idx[w_norm]
                        break
                    for norm_cand, m_key in norm_idx.items():
                        if norm_cand in TRIM_STOPWORDS:
                            continue
                        if norm_cand == w_norm:
                            if len(norm_cand) > best_len:
                                best_len = len(norm_cand)
                                matched_master_key = m_key

            if matched_master_key and matched_master_key in models:
                m_info = models[matched_master_key]
                enc_m = m_info.get("encar_model", "")
                all_trims = {}
                if enc_m:
                    for other_v in models.values():
                        if other_v.get("encar_model") == enc_m:
                            all_trims.update(other_v.get("trims", {}))
                # 매칭된 모델(m_info) 본인의 트림이 마지막에 적용되어 항상 우선하도록 보장
                all_trims.update(m_info.get("trims", {}))
                return {
                    "brand": m_info.get("brand") or brand or "현대",
                    "model_group": m_info.get("model_group", ""),
                    "encar_model": enc_m,
                    "matched_key": matched_master_key,
                    "trims": all_trims,
                    "soldout_codes": m_info.get("soldout_codes", {})
                }

            return {}

    @classmethod
    def generate_smart_encar_url(
        cls, 
        car_name: str, 
        sub_model: str = "", 
        year: any = "", 
        mileage: any = 0, 
        car_number: str = "",
        mileage_range: int = 30000
    ) -> str:
        """
        스마트 엔카 URL 생성:
        1순위: 차량번호가 마스터 링크(car_links)에 등록되어 있으면 직통 URL 반환!
        2순위: 마스터 DB 모델 계층 매칭 성공 시, 엔카 공식 데스크톱 Action URL 조립
        3순위: 마스터 DB 미등록 차종은 기존 SalesDataAnalyzer.generate_encar_url로 완벽 Fallback
        """
        # 1순위: 등록된 차량번호 직통 URL 확인 (주석 처리 - 항상 최신 필터로 새로 생성)
        # if car_number:
        #     direct_url = cls.get_car_link(car_number)
        #     if direct_url and any(k in direct_url for k in ["action=", "action%22", "%22action%22", '"action"']):
        #         return direct_url

        # 2순위: 마스터 DB에서 모델 계층 확인
        master_match = cls.resolve_encar_model("", car_name, sub_model, year=year)
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
                "쉐보레(대우)": "쉐보레(GM대우_)",
                "쉐보레": "쉐보레(GM대우_)",
                "KG모빌리티(쌍용)": "KG모빌리티(쌍용_)",
                "쌍용": "KG모빌리티(쌍용_)",
                "KGM": "KG모빌리티(쌍용_)"
            }
            mapped_brand = BRAND_ENCAR_MAP.get(f_brand, f_brand)

            # 세부 등급(Trim) 매칭 시도 (구조화 매칭: 연료·배기량·구동방식 필수조건 + 등급 토큰 가산점)
            matched_trim = None
            trims_dict = master_match.get("trims", {})
            if sub_model and trims_dict:
                _, matched_trim = cls.match_structured_trim(sub_model, trims_dict)

            # 모델 및 세부등급 코어 트리 조립
            bg = matched_trim.get("badge_group", "") if matched_trim else ""
            badge = matched_trim.get("badge", "") if matched_trim else ""
            bd = matched_trim.get("badge_detail", "") if matched_trim else ""
            
            # 올 뉴 카니발 전용 보정: 엔카에 BadgeGroup이 없고 등급명이 '9인승 프레스티지' 형태임
            if f_model == '올 뉴 카니발' and bg:
                seat_match = re.search(r'(\d+)\s*인승', bg)
                if seat_match:
                    seat_token = f"{seat_match.group(1)}인승"
                    if seat_token not in badge:
                        badge = f"{seat_token} {badge}".strip()
                    bg = ""
                    bd = ""

            # 💡 [하이브리드/전기차 모델 방어 로직]
            # 엔카는 '하이브리드' 또는 'EV' 모델 계층(K5 하이브리드, 쏘나타 하이브리드, 그랜저 하이브리드 등)에서
            # 별도의 BadgeGroup(연료/배기량)이 존재하지 않고 Model -> Badge 직결 구조를 취함.
            # 마스터 DB의 badge_group이 '전기', '하이브리드' 등 엔카에 존재하지 않는 그룹인 경우 생략하여 Badge 단독 검색으로 전환
            if ("하이브리드" in f_model or "EV" in f_model or "전기차" in f_model) and bg in ["전기", "하이브리드", "전기 2WD", "전기 4WD"]:
                bg = ""

            f_model_esc = cls._escape_encar_dsl_token(f_model)
            bg_clean = cls._clean_encar_token(bg)
            b_esc = cls._escape_encar_dsl_token(badge)
            bd_esc = cls._escape_encar_dsl_token(bd)

            if f_model_esc and bg_clean and b_esc and bd_esc:
                core_tree = f"(C.CarType.Y._.(C.Manufacturer.{mapped_brand}._.(C.ModelGroup.{f_mg}._.(C.Model.{f_model_esc}._.(C.BadgeGroup.{bg_clean}._.(C.Badge.{b_esc}._.BadgeDetail.{bd_esc}.))))))"
            elif f_model_esc and bg_clean and b_esc:
                core_tree = f"(C.CarType.Y._.(C.Manufacturer.{mapped_brand}._.(C.ModelGroup.{f_mg}._.(C.Model.{f_model_esc}._.(C.BadgeGroup.{bg_clean}._.Badge.{b_esc}.)))))"
            elif f_model_esc and b_esc:
                core_tree = f"(C.CarType.Y._.(C.Manufacturer.{mapped_brand}._.(C.ModelGroup.{f_mg}._.(C.Model.{f_model_esc}._.Badge.{b_esc}.))))"
            elif f_model_esc:
                core_tree = f"(C.CarType.Y._.(C.Manufacturer.{mapped_brand}._.(C.ModelGroup.{f_mg}._.Model.{f_model_esc}.)))"
            else:
                core_tree = f"(C.CarType.Y._.(C.Manufacturer.{mapped_brand}._.ModelGroup.{f_mg}.))"

            action = f"(And.Hidden.N._.{core_tree}"

            # 연식 밴드 (±1년)
            if parsed_year and parsed_year >= 2000:
                action += f"_.Year.range({parsed_year - 1}01..{parsed_year + 1}12)."

            # 주행거리 밴드 (기본 ±30,000km, 7대 미만 시 ±50,000km 확장)
            try:
                mil_val = int(re.sub(r'[^\d]', '', str(mileage)))
                if mil_val > 0:
                    base_mil = int(round(mil_val, -4))
                    min_mil = max(0, base_mil - mileage_range)
                    max_mil = base_mil + mileage_range
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
    def parse_car_spec(cls, text: str) -> dict:
        """차량 명칭/트림 텍스트에서 연료, 배기량, 구동방식, 등급/기타 토큰을 정밀 추출"""
        if not text:
            return {'fuel': None, 'disp': None, 'drive': None, 'tokens': []}
        text_clean = str(text).lower()

        # 1. 연료 (fuel)
        fuel = None
        if '플러그인' in text_clean or 'phev' in text_clean:
            fuel = '플러그인하이브리드'
        elif 'lpg' in text_clean or 'lpi' in text_clean:
            fuel = 'lpg'
        elif '하이브리드' in text_clean or 'hev' in text_clean or '가솔린+전기' in text_clean or '디젤+전기' in text_clean or 'lpg+전기' in text_clean:
            fuel = '하이브리드'
        elif 'fcev' in text_clean or '수소' in text_clean:
            fuel = '수소'
        elif '디젤' in text_clean or '경유' in text_clean or 'crdi' in text_clean or 'vgt' in text_clean or re.search(r'(?:^|[\s/_\-])r[12]\.[02]\b', text_clean) or text_clean.startswith('r2.') or ' r2.' in text_clean or '2.2d' in text_clean or '2.0d' in text_clean:
            fuel = '디젤'
        elif '가솔린' in text_clean or '휘발유' in text_clean or 'gdi' in text_clean or 't-gdi' in text_clean:
            fuel = '가솔린'
        elif re.search(r'\bev\b', text_clean) or '전기' in text_clean:
            if not re.search(r'\bev[1-9]\b', text_clean):
                fuel = '전기'

        # 2. 배기량 (disp) - \d+\.\d+ (R2.0, 1.35 등 포함) 또는 \d+cc (1600cc -> 1.6, 1350cc -> 1.35)
        disp = None
        m_disp = re.search(r'(?:[a-z가-힣]|\b)(\d+\.\d+)', text_clean)
        if m_disp:
            try:
                val = float(m_disp.group(1))
                parts = f"{val:.2f}".split('.')
                dec = parts[1].rstrip('0')
                if len(dec) == 0:
                    disp = f"{parts[0]}.0"
                elif len(dec) == 1:
                    disp = f"{parts[0]}.{dec}"
                else:
                    disp = f"{parts[0]}.{dec[:2]}"
            except Exception:
                pass
        else:
            m_cc = re.search(r'(\d{3,4})\s*cc', text_clean)
            if m_cc:
                try:
                    val = int(m_cc.group(1)) / 1000.0
                    parts = f"{val:.2f}".split('.')
                    dec = parts[1].rstrip('0')
                    if len(dec) == 0:
                        disp = f"{parts[0]}.0"
                    elif len(dec) == 1:
                        disp = f"{parts[0]}.{dec}"
                    else:
                        disp = f"{parts[0]}.{dec[:2]}"
                except Exception:
                    pass

        # 3. 구동방식 (drive) - 2WD/4WD/AWD (브랜드별 사륜 표기 4matic/4매틱/quattro/콰트로/xdrive 통합)
        drive = None
        if any(w in text_clean for w in ['4wd', 'awd', '4륜', '사륜', '4matic', '4매틱', 'quattro', '콰트로', 'xdrive']):
            drive = '4wd'
        elif any(w in text_clean for w in ['2wd', '2륜', '이륜', 'ff', 'fr']):
            drive = '2wd'

        # 4. 등급 및 기타 토큰 (tokens)
        rem = text_clean
        rem = re.sub(r'(?:[a-z가-힣]|\b)\d+\.\d+', ' ', rem)
        rem = re.sub(r'\d{3,4}\s*cc', ' ', rem)
        rem = re.sub(r'(4wd|awd|2wd|4륜|2륜|사륜|이륜|ff|fr|4matic|4매틱|quattro|콰트로|xdrive)', ' ', rem)
        rem = re.sub(r'(가솔린|휘발유|디젤|경유|하이브리드|플러그인하이브리드|전기|수소|lpg|lpi|hev|phev|ev|fcev)', ' ', rem)
        tokens = [t for t in re.split(r'[\s/()_\-]+', rem) if len(t) >= 2]

        return {'fuel': fuel, 'disp': disp, 'drive': drive, 'tokens': tokens}

    @classmethod
    def match_structured_trim(cls, sub_model: str, trims_dict: dict):
        """
        입력 세부모델과 후보 트림들을 구조화 매칭:
        - 1단계: 공백/슬래시 제거 정확 일치
        - 2단계: 구조화 매칭
          * 필수 조건: 연료, 배기량, 구동방식 중 양쪽에 모두 존재하는 스펙이 다르면 제외 (한쪽에만 없으면 통과)
          * 가산점: 통과 후보 중 등급·기타 토큰 일치 개수 + 스펙 완전 일치 보너스
        - 통과 후보 없으면 (None, None) 반환하여 틀린 트림 대체 방지
        """
        if not sub_model or not trims_dict:
            return None, None

        # 1단계: 정확 일치
        clean_sub = re.sub(r'[\s/]+', '', str(sub_model)).lower()
        for t_name, t_data in trims_dict.items():
            if re.sub(r'[\s/]+', '', str(t_name)).lower() == clean_sub:
                return t_name, t_data

        # 2단계: 구조화 매칭
        input_spec = cls.parse_car_spec(sub_model)
        in_fuel = input_spec['fuel']
        in_disp = input_spec['disp']
        in_drive = input_spec['drive']
        in_tokens = input_spec['tokens']

        candidates = []
        for t_name, t_data in trims_dict.items():
            # 후보 스펙 검사: t_name뿐만 아니라 실제 엔카 트리에 쓰일 badge_group, badge 모두와 대조
            name_spec = cls.parse_car_spec(t_name)
            tree_text = f"{t_data.get('badge_group', '')} {t_data.get('badge', '')}"
            tree_spec = cls.parse_car_spec(tree_text)

            # 1. 연료 모순 체크: t_name 또는 tree_spec에 연료가 있을 때 입력과 다르면 제외
            cand_fuels = {s for s in [name_spec['fuel'], tree_spec['fuel']] if s}
            if in_fuel and any(f != in_fuel for f in cand_fuels):
                continue

            # 2. 배기량 모순 체크: t_name 또는 tree_spec에 배기량이 있을 때 입력과 다르면 제외
            # 단, 배기량 차이 0.05 이내(예: 1.35 vs 1.3)는 동일 배기량으로 취급 (부동소수점 오차 감안 4자리 반올림)
            cand_disps = [s for s in [name_spec['disp'], tree_spec['disp']] if s]
            if in_disp and cand_disps:
                try:
                    in_d_val = float(in_disp)
                    if any(round(abs(in_d_val - float(d)), 4) > 0.05 for d in cand_disps):
                        continue
                except Exception:
                    if any(d != in_disp for d in cand_disps):
                        continue

            # 3. 구동방식 모순 체크: t_name 또는 tree_spec에 구동방식이 있을 때 입력과 다르면 제외
            cand_drives = {s for s in [name_spec['drive'], tree_spec['drive']] if s}
            if in_drive and any(dr != in_drive for dr in cand_drives):
                continue

            # 가산점 산출: 등급/기타 토큰 일치 개수
            cand_full = f"{t_name} {t_data.get('badge_group', '')} {t_data.get('badge', '')} {t_data.get('badge_detail', '')}".lower()
            token_score = sum(10 for tok in in_tokens if tok in cand_full)

            # 스펙 완전 일치 보너스
            spec_score = 0
            if in_fuel and in_fuel in cand_fuels:
                spec_score += 2
            if in_disp and cand_disps:
                try:
                    in_d_val = float(in_disp)
                    if any(round(abs(in_d_val - float(d)), 4) <= 0.05 for d in cand_disps):
                        spec_score += 3
                except Exception:
                    if in_disp in cand_disps:
                        spec_score += 3
            if in_drive and in_drive in cand_drives:
                spec_score += 2

            total_score = token_score + spec_score
            is_2wd_candidate = ('2wd' in cand_drives)
            candidates.append((total_score, is_2wd_candidate, t_name, t_data))

        if not candidates:
            return None, None

        # 점수 순 정렬 후 최고 점수 후보 선택
        # 작업 2: 입력에 구동 정보가 없을 때 동점이면 2WD 후보 우선
        if not in_drive:
            candidates.sort(key=lambda x: (x[0], 1 if x[1] else 0), reverse=True)
        else:
            candidates.sort(key=lambda x: x[0], reverse=True)

        best_score, is_2wd, best_name, best_data = candidates[0]
        return best_name, best_data

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
