# services/git_sync_service.py
import os
import subprocess
import threading
import logging
from datetime import datetime

logger = logging.getLogger("GitSyncService")

class GitSyncService:
    _lock = threading.Lock()
    _is_syncing = False
    _last_sync_time = None
    _last_sync_status = "대기"

    SYNC_FILES = [
        "my_car_ledger.csv",
        "my_inventory_settlement.csv",
        "data/car_options_db.json",
        "data/master_car_mapping.json"
    ]

    @classmethod
    def is_git_repo(cls) -> bool:
        return os.path.exists(".git")

    @classmethod
    def sync_pull(cls, timeout: int = 10) -> tuple[bool, str]:
        """깃허브 원격(origin/main)에서 최신 데이터를 받아와 로컬과 병합"""
        if not cls.is_git_repo():
            return False, "Git 저장소가 아닙니다."
            
        with cls._lock:
            try:
                # 1. pull 실행 (merge_ledger.py 스마트 머지 드라이버가 자동 병합)
                res = subprocess.run(
                    ["git", "pull", "origin", "main"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=timeout
                )
                cls._last_sync_time = datetime.now()
                if res.returncode == 0:
                    cls._last_sync_status = "Pull 성공"
                    return True, res.stdout.strip()
                else:
                    err_msg = res.stderr.strip() or res.stdout.strip()
                    cls._last_sync_status = f"Pull 실패: {err_msg[:50]}"
                    return False, err_msg
            except subprocess.TimeoutExpired:
                cls._last_sync_status = "Pull 타임아웃"
                return False, "원격 저장소 응답 지연(타임아웃)"
            except Exception as e:
                cls._last_sync_status = f"Pull 에러: {str(e)[:50]}"
                return False, str(e)

    @classmethod
    def _execute_push(cls, commit_msg: str, target_files: list[str]):
        """백그라운드 스레드에서 실행되는 commit & push"""
        with cls._lock:
            cls._is_syncing = True
            try:
                # 1. 대상 파일들 git add
                valid_files = [f for f in target_files if os.path.exists(f)]
                if not valid_files:
                    return

                add_cmd = ["git", "add"] + valid_files
                subprocess.run(add_cmd, capture_output=True, timeout=10)

                # 2. 커밋 (변경사항이 있을 때만 커밋됨)
                commit_cmd = ["git", "commit", "-m", commit_msg]
                c_res = subprocess.run(commit_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=10)
                
                # 변경사항이 없으면 push 생략
                if "nothing to commit" in c_res.stdout or "nothing to commit" in c_res.stderr:
                    cls._last_sync_status = "변경사항 없음"
                    return

                # 3. 푸시
                p_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15)
                cls._last_sync_time = datetime.now()
                if p_res.returncode == 0:
                    cls._last_sync_status = "Push 성공"
                else:
                    cls._last_sync_status = "Push 실패"
            except Exception as e:
                logger.error(f"Git auto push error: {e}")
                cls._last_sync_status = f"Push 에러: {e}"
            finally:
                cls._is_syncing = False

    @classmethod
    def sync_push_async(cls, commit_msg: str = "auto: sync ledger & settlement data", target_files: list[str] = None):
        """UI 블로킹 없이 백그라운드 스레드에서 자동 커밋 및 푸시 실행"""
        if not cls.is_git_repo():
            return
            
        files = target_files or cls.SYNC_FILES
        t = threading.Thread(
            target=cls._execute_push,
            args=(commit_msg, files),
            daemon=True
        )
        t.start()

    @classmethod
    def get_status_badge(cls) -> str:
        """현재 동기화 상태 배지 텍스트 반환"""
        t_str = cls._last_sync_time.strftime("%H:%M") if cls._last_sync_time else "없음"
        if cls._is_syncing:
            return "☁️ 동기화 중..."
        return f"☁️ 최신동기화: {t_str} ({cls._last_sync_status})"
