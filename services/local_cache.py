"""
services/local_cache.py
로컬 파일 기반 캐시 관리자 (Single Source of Truth)
- 메모리 dict와 로컬 JSON 파일 동기화 (서버 재시작 시에도 캐시 보존)
- 원자적 파일 교체(atomic replace via temp file)로 파일 손상 방지
- JSON 파싱 실패 시 예외 없이 캐시 미적중 처리 (프로세스 다운 방지)
- TTL 만료 검사 및 만료된 데이터 자동 정리
"""
import os
import json
import time
import uuid
import threading
from typing import Any, Dict, Optional


class LocalFileCache:
    def __init__(self, filepath: str, ttl: int, memory_dict: Optional[Dict[str, Any]] = None):
        self.filepath = os.path.abspath(filepath)
        self.ttl = int(ttl)
        # 외부 메모리 dict 참조를 유지하여 기존 글로벌 딕셔너리와 완벽 호환
        self.memory: Dict[str, Any] = memory_dict if memory_dict is not None else {}
        self._lock = threading.Lock()
        self._ensure_dir()
        self._load_from_file_to_memory()

    def _ensure_dir(self):
        d = os.path.dirname(self.filepath)
        if d:
            os.makedirs(d, exist_ok=True)

    def _read_file_unlocked(self) -> Dict[str, Any]:
        """JSON 파일에서 캐시 데이터를 안전하게 읽어옴 (오류 시 빈 dict 반환)"""
        if not os.path.exists(self.filepath):
            return {}
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            # JSONDecodeError, OS error 등 어떤 예외가 발생해도 프로세스 중단 없이 캐시 없음 처리
            pass
        return {}

    def _load_from_file_to_memory(self):
        """초기화 시 파일의 유효 데이터를 메모리 dict에 복원"""
        with self._lock:
            data = self._read_file_unlocked()
            now = time.time()
            for k, v in data.items():
                if isinstance(v, dict) and (now - v.get("timestamp", 0) < self.ttl):
                    self.memory[k] = v

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        캐시 항목 조회.
        1. 메모리에 유효한 데이터가 있으면 즉시 반환 (디스크 I/O 없음)
        2. 메모리에 없으면 파일에서 읽어와 메모리에 복원 후 유효하면 반환
        3. 만료되었거나 없으면 None 반환
        """
        if not key:
            return None
        key_str = str(key).strip()
        if not key_str:
            return None

        now = time.time()
        with self._lock:
            # 1. 메모리 확인
            entry = self.memory.get(key_str)
            if entry and isinstance(entry, dict):
                if now - entry.get("timestamp", 0) < self.ttl:
                    return entry
                # 만료된 경우 메모리에서 제거
                self.memory.pop(key_str, None)

            # 2. 파일에서 확인 (서버 재시작 흉내 또는 메모리 초기화 후 복원)
            file_data = self._read_file_unlocked()
            file_entry = file_data.get(key_str)
            if file_entry and isinstance(file_entry, dict):
                if now - file_entry.get("timestamp", 0) < self.ttl:
                    self.memory[key_str] = file_entry
                    return file_entry

        return None

    def set(self, key: str, value: Dict[str, Any]):
        """
        캐시 항목 저장 (메모리 갱신 + 원자적 임시 파일 쓰기)
        """
        if not key:
            return
        key_str = str(key).strip()
        if not key_str:
            return

        with self._lock:
            # 1. 메모리 갱신
            self.memory[key_str] = value

            # 2. 파일 저장 (기존 유효 파일 내용과 병합)
            try:
                self._ensure_dir()
                file_data = self._read_file_unlocked()
                file_data.update(self.memory)

                # 만료 데이터 정리하여 파일 비대화 방지
                now = time.time()
                cleaned = {
                    k: v for k, v in file_data.items()
                    if isinstance(v, dict) and (now - v.get("timestamp", 0) < self.ttl)
                }
                # 방금 저장한 항목은 반드시 포함
                cleaned[key_str] = value

                dir_name = os.path.dirname(self.filepath)
                temp_filename = f"{os.path.basename(self.filepath)}.{uuid.uuid4().hex[:8]}.tmp"
                temp_path = os.path.join(dir_name, temp_filename)

                try:
                    with open(temp_path, "w", encoding="utf-8") as f:
                        json.dump(cleaned, f, ensure_ascii=False, indent=2)
                    os.replace(temp_path, self.filepath)
                finally:
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
            except Exception as e:
                # 캐시 파일 쓰기 실패가 비즈니스 로직 조회를 방해하지 않음
                print(f"[LocalFileCache] 캐시 파일 쓰기 실패 ({self.filepath}): {e}", flush=True)

    def clear(self):
        """메모리와 파일 캐시 전체 삭제"""
        with self._lock:
            self.memory.clear()
            if os.path.exists(self.filepath):
                try:
                    os.remove(self.filepath)
                except Exception as e:
                    print(f"[LocalFileCache] 캐시 파일 삭제 실패 ({self.filepath}): {e}", flush=True)
