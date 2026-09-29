# services/cookie_server.py
import os
import re
import json
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COOKIE_FILE = os.path.join(BASE_DIR, "encar_cookie.txt")
AUTOPLUS_COOKIE_FILE = os.path.join(BASE_DIR, "autoplus_cookie.txt")

def set_env_variable(var_name: str, value: str):
    """안전하게 .env 파일의 환경변수를 갱신 (줄바꿈 오염, 파편 및 중복 방지)"""
    env_path = os.path.join(BASE_DIR, '.env')
    clean_val = value.replace('\r', '').replace('\n', '').strip().replace('"', '')
    lines = []
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
        except:
            lines = []

    new_lines = []
    found = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=', stripped)
        if not m:
            continue
        curr_key = m.group(1)
        if curr_key == var_name:
            new_lines.append(f'{var_name}="{clean_val}"\n')
            found = True
        else:
            new_lines.append(line if line.endswith('\n') else line + '\n')
    if not found:
        new_lines.append(f'{var_name}="{clean_val}"\n')

    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"[CookieServer] Failed to write .env: {e}", flush=True)

class CookieReceiverHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 불필요한 콘솔 로그 방지
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self):
        print(f"[CookieServer] Received POST to path: {self.path}", flush=True)
        if self.path.startswith('/api/save_cookie'):
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                raw_cookie = data.get('cookie', '').strip()
                target = data.get('target', 'heydealer').lower()
                print(f"[CookieServer] Got {target} cookie of length: {len(raw_cookie)}", flush=True)
                if raw_cookie:
                    # 중복 키 제거 및 포맷 정규화
                    cookie_map = {}
                    for part in raw_cookie.split(';'):
                        part = part.strip()
                        if '=' in part:
                            k, v = part.split('=', 1)
                            k, v = k.strip(), v.strip()
                            if k and v:
                                cookie_map[k] = v
                    cleaned_cookie = '; '.join(f'{k}={v}' for k, v in cookie_map.items()) if cookie_map else raw_cookie

                    if target == 'encar':
                        var_name = 'ENCAR_COOKIE'
                        curr_cookie = get_current_encar_cookie()
                    elif target == 'autoplus':
                        var_name = 'AUTOPLUS_COOKIE'
                        curr_cookie = get_current_autoplus_cookie()
                    else:
                        var_name = 'HEYDEALER_COOKIE'
                        curr_cookie = get_current_hd_cookie()

                    # 불필요한 파일 쓰기 방지 (동일한 쿠키면 파일 수정하지 않아 Streamlit 무한 재실행 원천 차단)
                    if curr_cookie and curr_cookie.strip() == cleaned_cookie.strip():
                        res_bytes = json.dumps({"status": "ok", "message": f"{target} Cookie unchanged"}).encode('utf-8')
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Content-Length', str(len(res_bytes)))
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(res_bytes)
                        return

                    set_env_variable(var_name, cleaned_cookie)
                    raw_cookie = cleaned_cookie

                    if target == 'encar':
                        save_cookie(raw_cookie)
                        os.environ['ENCAR_COOKIE'] = raw_cookie
                    elif target == 'autoplus':
                        save_autoplus_cookie(raw_cookie)
                        os.environ['AUTOPLUS_COOKIE'] = raw_cookie
                        try:
                            from services.chaolma_service import ChaolmaService
                            ChaolmaService.clear_cache()
                        except Exception:
                            pass
                    else:
                        os.environ['HEYDEALER_COOKIE'] = raw_cookie

                    res_bytes = json.dumps({"status": "ok", "message": f"{target} Cookie saved"}).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(res_bytes)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(res_bytes)
                    print(f"[CookieServer] Successfully saved {target} to .env and files", flush=True)
                    return
            except Exception as ex:
                print(f"[CookieServer] Error processing POST: {ex}", flush=True)
        self.send_response(400)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', '0')
        self.end_headers()

_COOKIE_SERVER = None

def start_cookie_server(port=8502):
    global _COOKIE_SERVER
    if _COOKIE_SERVER is None:
        try:
            server = ThreadingHTTPServer(('127.0.0.1', port), CookieReceiverHandler)
            server.daemon_threads = True
            _COOKIE_SERVER = server
            t = threading.Thread(target=server.serve_forever, daemon=True, name="CookieReceiverThread")
            t.start()
            print(f"[CookieServer] Started on port {port}", flush=True)
        except Exception as e:
            print(f"[CookieServer] Failed to start on {port}: {e}", flush=True)

def load_cookie():
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_cookie(cookie_str):
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        f.write(cookie_str)

def get_current_hd_cookie():
    try:
        env_f = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        if os.path.exists(env_f):
            with open(env_f, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('HEYDEALER_COOKIE='):
                        val = line.split('=', 1)[1].strip()
                        if val.startswith('"') and val.endswith('"'): val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"): val = val[1:-1]
                        return val
    except Exception:
        pass
    return os.getenv("HEYDEALER_COOKIE", "")

def get_current_encar_cookie():
    # 1. 파일에서 우선 확인
    c = load_cookie()
    if c:
        return c
    # 2. .env에서 확인
    try:
        env_f = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        if os.path.exists(env_f):
            with open(env_f, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('ENCAR_COOKIE='):
                        val = line.split('=', 1)[1].strip()
                        if val.startswith('"') and val.endswith('"'): val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"): val = val[1:-1]
                        return val
    except Exception:
        pass
    return os.getenv("ENCAR_COOKIE", "")

def load_autoplus_cookie():
    if os.path.exists(AUTOPLUS_COOKIE_FILE):
        try:
            with open(AUTOPLUS_COOKIE_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except:
            pass
    return ""

def save_autoplus_cookie(cookie_str):
    try:
        with open(AUTOPLUS_COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write(cookie_str)
        os.environ['AUTOPLUS_COOKIE'] = cookie_str
    except:
        pass

def get_current_autoplus_cookie():
    c = load_autoplus_cookie()
    if c:
        return c
    try:
        env_f = os.path.join(BASE_DIR, '.env')
        if os.path.exists(env_f):
            with open(env_f, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('AUTOPLUS_COOKIE='):
                        val = line.split('=', 1)[1].strip()
                        if val.startswith('"') and val.endswith('"'): val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"): val = val[1:-1]
                        return val
    except Exception:
        pass
    return os.getenv("AUTOPLUS_COOKIE", "")

