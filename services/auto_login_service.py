# services/auto_login_service.py
"""
로컬 브라우저 자동 로그인 및 쿠키 최신화 서비스
- 차얼마(purchase.autoplus.co.kr) 및 헤이딜러(dealer.heydealer.com) 원클릭 자동 로그인
- LLM 토큰 소모 0개 (로컬 Playwright 프로세스 단독 실행)
- 보안 규칙: 계정 정보는 .env 파일에만 보관하며 로그/출력에 노출하지 않음
"""

import os
import time
from typing import Dict, Any, Optional
from services.cookie_server import save_cookie, save_autoplus_cookie, set_env_variable

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")


def get_credential(key: str) -> str:
    """os.environ 또는 .env 파일에서 계정 정보를 가져옵니다."""
    val = os.getenv(key, "").strip()
    if val:
        return val
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{key}="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def save_platform_credentials(platform: str, user_id: str, user_pw: str) -> Dict[str, Any]:
    """플랫폼별 로그인 계정 정보를 .env 파일에 안전하게 저장합니다."""
    platform = platform.lower()
    if platform in ("autoplus", "chaolma"):
        id_key, pw_key = "AUTOPLUS_ID", "AUTOPLUS_PW"
        name = "차얼마 (오토플러스)"
    elif platform == "heydealer":
        id_key, pw_key = "HEYDEALER_ID", "HEYDEALER_PW"
        name = "헤이딜러"
    else:
        return {"success": False, "message": f"지원하지 않는 플랫폼입니다: {platform}"}

    set_env_variable(id_key, user_id)
    set_env_variable(pw_key, user_pw)
    os.environ[id_key] = user_id
    os.environ[pw_key] = user_pw

    return {"success": True, "message": f"{name} 자동 로그인 계정 설정이 안전하게 저장되었습니다."}


def get_credential_status() -> Dict[str, Any]:
    """플랫폼별 계정 정보 설정 여부를 확인합니다 (비밀번호는 절대 반환하지 않음)."""
    ap_id = get_credential("AUTOPLUS_ID")
    ap_pw = get_credential("AUTOPLUS_PW")
    hd_id = get_credential("HEYDEALER_ID")
    hd_pw = get_credential("HEYDEALER_PW")

    def mask_id(uid: str) -> str:
        if not uid:
            return ""
        if len(uid) <= 3:
            return uid[0] + "**"
        return uid[:3] + "*" * (len(uid) - 3)

    return {
        "hasAutoplusCredentials": bool(ap_id and ap_pw),
        "hasHeydealerCredentials": bool(hd_id and hd_pw),
        "autoplusMaskedId": mask_id(ap_id),
        "heydealerMaskedId": mask_id(hd_id),
    }


def login_autoplus() -> Dict[str, Any]:
    """차얼마(purchase.autoplus.co.kr) 자동 로그인 후 쿠키 최신화"""
    user_id = get_credential("AUTOPLUS_ID")
    user_pw = get_credential("AUTOPLUS_PW")

    if not user_id or not user_pw:
        return {
            "success": False,
            "message": "차얼마 계정(AUTOPLUS_ID / AUTOPLUS_PW)이 등록되지 않았습니다. 아래 [계정 설정]에서 입력해주세요.",
            "need_credentials": True,
        }

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"success": False, "message": "playwright 패키지가 설치되지 않았습니다."}

    alerts = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.on("dialog", lambda dialog: (alerts.append(dialog.message), dialog.accept()))

            page.goto("https://purchase.autoplus.co.kr/login/login.do", timeout=20000)
            page.fill("#userId", user_id)
            page.fill("#userPasswd", user_pw)
            page.click("#loginbtn")

            # 로그인 처리 대기
            page.wait_for_timeout(3500)

            curr_url = page.url
            if alerts:
                err_msg = alerts[-1]
                browser.close()
                return {"success": False, "message": f"차얼마 로그인 실패: {err_msg}"}

            if "login.do" in curr_url:
                browser.close()
                return {"success": False, "message": "차얼마 로그인 실패 (로그인 페이지를 벗어나지 못했습니다. 아이디/비밀번호를 확인해주세요.)"}

            # 쿠키 획득
            cookies = page.context.cookies()
            browser.close()

            if not cookies:
                return {"success": False, "message": "로그인 후 브라우저 쿠키를 가져오지 못했습니다."}

            cookie_parts = []
            for c in cookies:
                # autoplus 관련 도메인 필터링
                if "autoplus.co.kr" in c.get("domain", ""):
                    cookie_parts.append(f"{c['name']}={c['value']}")

            if not cookie_parts:
                # 전체 쿠키 대체
                cookie_parts = [f"{c['name']}={c['value']}" for c in cookies]

            cookie_str = "; ".join(cookie_parts)
            save_autoplus_cookie(cookie_str)

            return {
                "success": True,
                "target": "autoplus",
                "message": f"차얼마 자동 로그인 및 쿠키 최신화 완료! ({len(cookie_str)}자)",
                "cookie_length": len(cookie_str),
            }

    except Exception as e:
        return {"success": False, "message": f"차얼마 자동 로그인 오류 발생: {str(e)}"}


def login_heydealer() -> Dict[str, Any]:
    """헤이딜러(dealer.heydealer.com) 자동 로그인 후 쿠키 최신화"""
    user_id = get_credential("HEYDEALER_ID")
    user_pw = get_credential("HEYDEALER_PW")

    if not user_id or not user_pw:
        return {
            "success": False,
            "message": "헤이딜러 계정(HEYDEALER_ID / HEYDEALER_PW)이 등록되지 않았습니다. 아래 [계정 설정]에서 입력해주세요.",
            "need_credentials": True,
        }

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"success": False, "message": "playwright 패키지가 설치되지 않았습니다."}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://dealer.heydealer.com", timeout=20000)
            page.fill('input[name="username"]', user_id)
            page.fill('input[name="password"]', user_pw)

            login_btn = page.locator('button:has-text("로그인"), button[type="submit"]')
            login_btn.first.click()

            # 로그인 처리 및 리다이렉트 대기
            page.wait_for_timeout(4000)

            cookies = page.context.cookies()
            browser.close()

            cookie_dict = {c["name"]: c["value"] for c in cookies if "heydealer.com" in c.get("domain", "")}

            # sessionid 세션 검증
            if "sessionid" not in cookie_dict:
                return {
                    "success": False,
                    "message": "헤이딜러 로그인 후 sessionid를 찾지 못했습니다. 아이디/비밀번호 또는 2차 인증 여부를 확인해주세요.",
                }

            cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
            save_cookie(cookie_str)

            return {
                "success": True,
                "target": "heydealer",
                "message": f"헤이딜러 자동 로그인 및 세션(sessionid) 갱신 완료! ({len(cookie_str)}자)",
                "cookie_length": len(cookie_str),
            }

    except Exception as e:
        return {"success": False, "message": f"헤이딜러 자동 로그인 오류 발생: {str(e)}"}


def perform_auto_login(target: str) -> Dict[str, Any]:
    """지정한 대상 플랫폼 자동 로그인을 실행합니다."""
    target = target.lower()
    if target in ("autoplus", "chaolma"):
        return login_autoplus()
    elif target == "heydealer":
        return login_heydealer()
    else:
        return {"success": False, "message": f"알 수 없는 대상 플랫폼입니다: {target}"}
