# services/service_manager.py
import os
import sys
import socket
import subprocess
import threading
import atexit

class ServiceManager:
    _initialized = False
    _lock = threading.Lock()
    _subprocesses = []

    @staticmethod
    def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
        """해당 포트가 이미 활성화되어 있는지 소켓으로 검사"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                return s.connect_ex((host, port)) == 0
        except Exception:
            return False

    @classmethod
    def start_all_services(cls):
        """스트림릿 기동 시 8000(FastAPI) 및 3000(React) 백그라운드 자동 기동"""
        with cls._lock:
            if cls._initialized:
                return
            cls._initialized = True

            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            creation_flag = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

            # 1. Port 8000 FastAPI Backend
            if not cls.is_port_open(8000):
                py_exe = os.path.join(base_dir, ".venv", "Scripts", "python.exe")
                if not os.path.exists(py_exe):
                    py_exe = sys.executable
                try:
                    p8000 = subprocess.Popen(
                        [py_exe, "-m", "uvicorn", "api_server:app", "--host", "127.0.0.1", "--port", "8000"],
                        cwd=base_dir,
                        creationflags=creation_flag
                    )
                    cls._subprocesses.append(p8000)
                    print("[ServiceManager] Port 8000 (FastAPI) 백그라운드 기동 완료")
                except Exception as e:
                    print(f"[ServiceManager] Port 8000 기동 실패: {e}")

            # 2. Port 3000 React Frontend
            if not cls.is_port_open(3000):
                node_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "nodejs")
                env = os.environ.copy()
                if os.path.exists(node_dir):
                    env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")
                
                npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
                try:
                    p3000 = subprocess.Popen(
                        [npm_cmd, "run", "dev"],
                        cwd=os.path.join(base_dir, "frontend"),
                        env=env,
                        shell=True,
                        creationflags=creation_flag
                    )
                    cls._subprocesses.append(p3000)
                    print("[ServiceManager] Port 3000 (React Frontend) 백그라운드 기동 완료")
                except Exception as e:
                    print(f"[ServiceManager] Port 3000 기동 실패: {e}")

    @classmethod
    def cleanup(cls):
        """프로세스 종료 시 자식 서브프로세스 정리"""
        for p in cls._subprocesses:
            try:
                p.terminate()
            except Exception:
                pass

atexit.register(ServiceManager.cleanup)
