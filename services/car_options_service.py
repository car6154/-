# services/car_options_service.py
"""
차량별 신차 출고옵션 / 헤이딜러 장착옵션 영구 보관 및 실시간 복원 서비스
- 차량번호(차대번호) 기준으로 옵션 목록, 신차 출고가 내역(차얼마), 헤이딜러 스펙 설명을 JSON에 영구 보존
- 매입장부 및 정산장부에서 시세 역추적 스캔 시 옵션 정보를 100% 무손실로 메인 화면에 복원
"""

import os
import re
import json
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

class CarOptionsService:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "car_options_db.json")
    _lock = threading.Lock()
    _memory_cache: Dict[str, Dict[str, Any]] = {}
    _loaded = False

    @classmethod
    def _ensure_db_dir(cls):
        os.makedirs(os.path.dirname(cls.DB_PATH), exist_ok=True)

    @classmethod
    def _load_db(cls) -> Dict[str, Any]:
        if cls._loaded:
            return cls._memory_cache
        cls._ensure_db_dir()
        if os.path.exists(cls.DB_PATH):
            try:
                with open(cls.DB_PATH, "r", encoding="utf-8") as f:
                    cls._memory_cache = json.load(f)
            except Exception as e:
                print(f"[CarOptionsService] DB 로드 오류: {e}")
                cls._memory_cache = {}
        else:
            cls._memory_cache = {}
        cls._loaded = True
        return cls._memory_cache

    @classmethod
    def _save_db_unlocked(cls, db: Dict[str, Any]):
        cls._ensure_db_dir()
        tmp_path = cls.DB_PATH + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            if os.path.exists(cls.DB_PATH):
                os.replace(tmp_path, cls.DB_PATH)
            else:
                os.rename(tmp_path, cls.DB_PATH)
        except Exception as e:
            print(f"[CarOptionsService] DB 저장 오류: {e}")

    @classmethod
    def clean_option_list(cls, opt_input: Any) -> List[str]:
        """문자열(쉼표/슬래시 구분) 또는 리스트로부터 깨끗한 옵션명 리스트 추출"""
        if not opt_input:
            return []
        
        raw_items = []
        if isinstance(opt_input, str):
            # 슬래시 또는 쉼표 구분
            raw_items = re.split(r'[/,]+', opt_input)
        elif isinstance(opt_input, (list, tuple, set)):
            for x in opt_input:
                if isinstance(x, dict):
                    name = x.get('name') or x.get('optionName') or ''
                    if name:
                        raw_items.append(str(name))
                elif isinstance(x, str):
                    raw_items.append(x)
        
        clean_list = []
        for item in raw_items:
            # 괄호 가격 (xx만) 제거 또는 보존 여부 결정: 이름 자체만 깔끔하게 정제
            c_text = str(item).strip()
            if not c_text or c_text in ('없음', '-', '⚠️정보없음', '⚠️조회실패', '코드매칭실패', 'nan', 'None'):
                continue
            # 중복 방지
            if c_text not in clean_list:
                clean_list.append(c_text)
                
        return clean_list

    @classmethod
    def save_car_options(
        cls, 
        car_number: str, 
        options: Any = None, 
        spec_desc: str = "", 
        chaolma_data: Optional[Dict[str, Any]] = None
    ):
        """특정 차량번호의 옵션 정보 영구 저장"""
        if not car_number or not str(car_number).strip():
            return
            
        c_num = str(car_number).replace(" ", "").strip()
        with cls._lock:
            db = cls._load_db()
            entry = db.get(c_num, {})
            
            clean_opts = cls.clean_option_list(options) if options is not None else entry.get("options", [])
            if clean_opts:
                entry["options"] = clean_opts
                
            if spec_desc:
                entry["spec_desc"] = spec_desc
                
            if chaolma_data and isinstance(chaolma_data, dict) and chaolma_data.get("success"):
                entry["chaolma_data"] = chaolma_data
                # 차얼마 데이터의 옵션 목록도 자동 반영
                if not entry.get("options"):
                    ch_opts = [o.get("name") for o in chaolma_data.get("options", []) if o.get("name")]
                    if ch_opts:
                        entry["options"] = cls.clean_option_list(ch_opts)
                        
            entry["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db[c_num] = entry
            cls._save_db_unlocked(db)

    @classmethod
    def get_car_options(cls, car_number: str) -> Dict[str, Any]:
        """특정 차량번호의 저장된 옵션 및 출고 스펙 정보 반환"""
        if not car_number or not str(car_number).strip():
            return {}
        c_num = str(car_number).replace(" ", "").strip()
        with cls._lock:
            db = cls._load_db()
            return db.get(c_num, {})
