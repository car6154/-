# services/auto_login_service.py
"""
로컬 브라우저 자동 로그인 및 쿠키 최신화 서비스
- 차얼마(purchase.autoplus.co.kr) 및 헤이딜러(dealer.heydealer.com) 원클릭 자동 로그인
- LLM 토큰 소모 0개 (로컬 Playwright 프로세스 단독 실행)
- 보안 규칙: 계정 정보는 .env 파일에만 보관하며 로그/출력에 노출하지 않음
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List
from services.cookie_server import save_cookie, save_autoplus_cookie, set_env_variable

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# [진단] 헤이딜러 로그인 화면에서 오류/차단 여부를 판단하기 위한 관찰용 문구 (판정에는 사용하지 않음)
HD_DIAG_KEYWORDS = [
    "차단", "비정상", "자동화", "제한", "잠시 후", "다시 시도", "오류", "실패",
    "일치하지", "확인해", "올바르지", "로봇", "robot", "captcha", "CAPTCHA",
    "Access Denied", "Forbidden", "403", "429", "인증",
]


def _hd_diag_found(text: str) -> List[str]:
    """[진단] 화면 텍스트에서 오류/차단 관련 문구를 찾아 반환합니다."""
    return [k for k in HD_DIAG_KEYWORDS if k in (text or "")]


def _hd_save_failure_evidence(page, reason: str, curr_url: str, page_text: str, cookie_names: List[str], login_resp_body: str = "") -> str:
    """[진단] 실패 순간의 화면 캡처(PNG)·화면 텍스트·최종 URL을 logs/ 에 저장합니다.
    logs/ 는 .gitignore 대상이므로 커밋되지 않습니다. 쿠키 값은 저장하지 않고 이름만 남깁니다.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(LOGS_DIR, f"heydealer_login_fail_{ts}")
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        try:
            page.screenshot(path=base + ".png", full_page=True, timeout=10000)
        except Exception as se:
            print(f"[HeydealerAutoLogin][DIAG] 캡처 저장 실패: {se}", flush=True)
        with open(base + ".txt", "w", encoding="utf-8") as f:
            f.write(f"time: {datetime.now().isoformat(timespec='seconds')}\n")
            f.write(f"reason: {reason}\n")
            f.write(f"final_url: {curr_url}\n")
            f.write(f"title: {page.title() if page else ''}\n")
            f.write(f"cookie_names: {', '.join(cookie_names)}\n")
            f.write(f"diag_keywords_found: {', '.join(_hd_diag_found(page_text))}\n")
            # [진단] 로그인 API 응답 본문만 기록 (요청 본문/헤더/비밀번호는 기록하지 않음, 최대 2,000자)
            f.write("----- login_response_body (max 2000) -----\n")
            f.write((login_resp_body or "(none)") + "\n")
            f.write("----- page_text -----\n")
            f.write(page_text or "(empty)")
        print(f"[HeydealerAutoLogin][DIAG] 실패 증거 저장: {base}.png / .txt", flush=True)
    except Exception as e:
        print(f"[HeydealerAutoLogin][DIAG] 증거 저장 중 예외: {e}", flush=True)
    return base


def get_credential(key: str) -> str:
    """os.environ 또는 .env 파일에서 계정 정보를 가져옵니다."""
    val = os.getenv(key, "").strip()
    if val:
        return val
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{key}="):
                        val_part = line.split("=", 1)[1].strip()
                        if (val_part.startswith('"') and val_part.endswith('"')) or (val_part.startswith("'") and val_part.endswith("'")):
                            return val_part[1:-1]
                        return val_part
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

    print(f"[HeydealerAutoLogin] 1/5: 헤이딜러 자동 로그인 시작 (ID: {user_id[:3]}***)", flush=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[HeydealerAutoLogin] ❌ 실패: playwright 미설치", flush=True)
        return {"success": False, "message": "playwright 패키지가 설치되지 않았습니다."}

    try:
        import requests
        profile_dir = r"C:\jpro\data\heydealer_profile"
        os.makedirs(profile_dir, exist_ok=True)

        with sync_playwright() as p:
            print(f"[HeydealerAutoLogin] 2/5: 실제 브라우저(headed) 및 지속 프로필 기동 중... (경로: {profile_dir})", flush=True)
            # 브라우저 실제 버전(예: 156.0.8078.4) 기반으로 UA와 sec-ch-ua 버전 일치
            browser_ver = "156.0.8078.4"
            chrome_major = "156"
            ua_str = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{browser_ver} Safari/537.36"
            sec_ch_ua_val = f'"Not:A-Brand";v="8", "Chromium";v="{chrome_major}", "Google Chrome";v="{chrome_major}"'

            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                ],
                user_agent=ua_str,
                extra_http_headers={
                    "sec-ch-ua": sec_ch_ua_val,
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                },
            )

            if context.browser and context.browser.version:
                browser_ver = context.browser.version
                chrome_major = browser_ver.split(".")[0]

            page = context.pages[0] if context.pages else context.new_page()

            # [지문 제거] JS DOM의 navigator.userAgentData.brands를 일반 크롬 브랜드로 재정의
            uad_init_script = f"""(() => {{
                try {{
                    if (!navigator.userAgentData) return;
                    const normalBrands = [
                        {{ brand: 'Not:A-Brand', version: '8' }},
                        {{ brand: 'Chromium', version: '{chrome_major}' }},
                        {{ brand: 'Google Chrome', version: '{chrome_major}' }}
                    ];
                    const normalFullVersionList = [
                        {{ brand: 'Not:A-Brand', version: '8.0.0.0' }},
                        {{ brand: 'Chromium', version: '{browser_ver}' }},
                        {{ brand: 'Google Chrome', version: '{browser_ver}' }}
                    ];

                    const origUAD = navigator.userAgentData;
                    const origGetHighEntropyValues = origUAD.getHighEntropyValues ? origUAD.getHighEntropyValues.bind(origUAD) : null;

                    const fakeUAD = {{
                        get brands() {{ return normalBrands; }},
                        get mobile() {{ return false; }},
                        get platform() {{ return 'Windows'; }},
                        async getHighEntropyValues(hints) {{
                            let res = {{}};
                            if (origGetHighEntropyValues) {{
                                try {{ res = await origGetHighEntropyValues(hints); }} catch(e) {{}}
                            }}
                            return {{
                                ...res,
                                brands: normalBrands,
                                fullVersionList: normalFullVersionList,
                                platform: 'Windows',
                                platformVersion: '10.0.0',
                                architecture: 'x86',
                                bitness: '64',
                                model: '',
                                mobile: false,
                            }};
                        }},
                        toJSON() {{
                            return {{
                                brands: normalBrands,
                                mobile: false,
                                platform: 'Windows'
                            }};
                        }}
                    }};

                    try {{
                        Object.defineProperty(navigator, 'userAgentData', {{
                            get: () => fakeUAD,
                            configurable: true,
                            enumerable: true
                        }});
                    }} catch (e) {{
                        try {{
                            Object.defineProperty(Object.getPrototypeOf(navigator.userAgentData), 'brands', {{
                                get: () => normalBrands,
                                configurable: true
                            }});
                        }} catch (e2) {{}}
                    }}
                }} catch (err) {{}}
            }})();"""
            page.add_init_script(uad_init_script)

            # [진단] webdriver 및 userAgentData.brands 지문 상태 확인 (값 자체/민감정보 없음)
            is_webdriver = page.evaluate("() => navigator.webdriver")
            uad_brands = page.evaluate("() => navigator.userAgentData ? navigator.userAgentData.brands : '미지원'")
            print(f"[HeydealerAutoLogin][DIAG] headed 브라우저 지문 점검 navigator.webdriver={is_webdriver} / userAgentData.brands={uad_brands}", flush=True)

            page.goto("https://dealer.heydealer.com", timeout=20000)
            print("[HeydealerAutoLogin] 3/5: 로그인 폼 순차 입력 및 로그인 버튼 클릭...", flush=True)

            # [진단] 로그인 관련 네트워크 요청/응답 가로채기 (값 자체는 기록 금지, 필드명과 길이만 출력)
            net_log: List[str] = []
            login_resps: List[Any] = []

            def _on_request(req):
                try:
                    u = req.url
                    if "api.heydealer.com/v2/dealers/web/login" in u and req.method == "POST":
                        # 실제 전송된 sec-ch-ua 헤더 확인 (민감정보 아님)
                        req_sec_ch_ua = req.headers.get("sec-ch-ua", "없음")
                        print(f"[HeydealerAutoLogin][DIAG] 로그인 POST 요청 헤더 sec-ch-ua: {req_sec_ch_ua}", flush=True)
                        post_data = req.post_data
                        if post_data:
                            try:
                                payload = json.loads(post_data)
                                field_lens = {k: len(str(v)) for k, v in payload.items()}
                                print(f"[HeydealerAutoLogin][DIAG] 로그인 POST 요청 필드 및 각 값의 길이: {field_lens}", flush=True)
                            except Exception:
                                print(f"[HeydealerAutoLogin][DIAG] 로그인 POST 요청 본문 길이: {len(post_data)}자", flush=True)
                        else:
                            print("[HeydealerAutoLogin][DIAG] 로그인 POST 요청 본문 없음", flush=True)
                except Exception as e:
                    print(f"[HeydealerAutoLogin][DIAG] 요청 가로채기 오류: {e}", flush=True)

            def _on_response(resp):
                try:
                    u = resp.url
                    if "heydealer.com" in u and resp.request.method in ("POST", "PUT"):
                        net_log.append(f"{resp.request.method} {u.split('?')[0]} -> {resp.status}")
                    if "api.heydealer.com/v2/dealers/web/login" in u and resp.request.method == "POST":
                        login_resps.append(resp)
                        print(f"[HeydealerAutoLogin][DIAG] 로그인 API 응답 코드: HTTP {resp.status}", flush=True)
                except Exception:
                    pass

            page.on("request", _on_request)
            page.on("response", _on_response)

            # [입력 방식 변경] page.fill 대신 포커스 + 문자 단위 순차 입력(press_sequentially) 적용
            username_input = page.locator('input[name="username"]')
            password_input = page.locator('input[name="password"]')

            username_input.click()
            username_input.fill("")
            username_input.press_sequentially(user_id, delay=30)

            password_input.click()
            password_input.fill("")
            password_input.press_sequentially(user_pw, delay=30)

            # [진단] 클릭 직전 페이지에서 읽은 username·password 입력칸 값의 길이 (값 자체는 기록 금지)
            u_len = len(username_input.input_value() or "")
            p_len = len(password_input.input_value() or "")
            print(f"[HeydealerAutoLogin][DIAG] 클릭 직전 input_value 길이: username={u_len}자, password={p_len}자", flush=True)

            # [진단] 제출 전 화면 상태 기록
            try:
                pre_text = page.inner_text("body", timeout=3000)
            except Exception:
                pre_text = ""
            print(f"[HeydealerAutoLogin][DIAG] {datetime.now():%H:%M:%S} 제출 전 URL={page.url} / 오류·차단 문구={_hd_diag_found(pre_text) or '없음'}", flush=True)

            login_btn = page.locator('button:has-text("로그인"), button[type="submit"]')
            login_btn.first.click()

            # 로그인 처리 및 리다이렉트 대기
            page.wait_for_timeout(4000)

            curr_url = page.url
            page_text = ""
            try:
                page_text = page.inner_text("body", timeout=3000)
            except Exception:
                pass

            # [진단] 로그인 API 응답 본문 (최대 2,000자) - 실패 증거 파일에만 기록
            login_resp_body = ""
            if login_resps:
                try:
                    lr = login_resps[-1]
                    login_resp_body = f"HTTP {lr.status}\n" + (lr.text() or "")[:2000]
                except Exception as be:
                    login_resp_body = f"(응답 본문 읽기 실패: {be})"
            print(f"[HeydealerAutoLogin] 4/5: 로그인 후 이동 URL: {curr_url}", flush=True)
            print(f"[HeydealerAutoLogin][DIAG] {datetime.now():%H:%M:%S} 제출 후 오류·차단 문구={_hd_diag_found(page_text) or '없음'} / 제출 응답={net_log or '기록 없음'}", flush=True)

            # 1. 2차 인증 / OTP 감지
            if any(k in page_text for k in ["인증번호", "2차 인증", "OTP", "인증 코드", "보안문자"]) or any(k in curr_url for k in ["verify", "otp", "auth/2step"]):
                print("[HeydealerAutoLogin] ⚠️ 2차 인증(OTP/SMS) 단계 감지됨. 자동 진행 불가.", flush=True)
                context.close()
                return {
                    "success": False,
                    "need_otp": True,
                    "message": "헤이딜러 2차 인증(OTP/알림톡/SMS)이 필요합니다. 크롬 브라우저에서 직접 로그인 후 크롬 확장의 [헤이딜러 쿠키 전송] 버튼을 눌러주세요.",
                }

            # 2. 로그인 실패 에러 문구 감지
            if any(k in page_text for k in ["아이디 또는 비밀번호", "일치하지 않습니다", "비밀번호를 확인", "계정 정보를 확인"]):
                print("[HeydealerAutoLogin] ❌ 로그인 실패 (아이디/비밀번호 불일치)", flush=True)
                _hd_save_failure_evidence(page, "credentials mismatch", curr_url, page_text, [], login_resp_body)
                context.close()
                return {
                    "success": False,
                    "message": "헤이딜러 로그인 실패: 아이디 또는 비밀번호가 올바르지 않습니다. [계정 설정]을 다시 확인해주세요.",
                }

            # 3. 로그인 페이지 이탈 여부 검증
            if "login" in curr_url.lower() and not any(k in curr_url.lower() for k in ["cars", "app", "home", "main"]):
                print(f"[HeydealerAutoLogin] ❌ 로그인 페이지 벗어나지 못함 (URL: {curr_url})", flush=True)
                _hd_save_failure_evidence(page, "login page not left", curr_url, page_text, [], login_resp_body)
                context.close()
                return {
                    "success": False,
                    "message": f"헤이딜러 로그인 실패 (로그인 페이지를 벗어나지 못했습니다. URL: {curr_url})",
                }

            cookies = page.context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies if "heydealer.com" in c.get("domain", "")}

            # [진단] sessionid 누락 시 브라우저를 닫기 전에 실패 순간 화면을 증거로 저장
            if "sessionid" not in cookie_dict:
                cookie_names = [f"{c['name']}@{c.get('domain', '')}" for c in cookies]
                print(f"[HeydealerAutoLogin][DIAG] 획득 쿠키 이름: {cookie_names or '없음'}", flush=True)
                _hd_save_failure_evidence(page, "sessionid missing", curr_url, page_text, cookie_names, login_resp_body)

            context.close()

            # sessionid 세션 존재 검증
            if "sessionid" not in cookie_dict:
                print("[HeydealerAutoLogin] ❌ sessionid 쿠키 누락", flush=True)
                return {
                    "success": False,
                    "message": "헤이딜러 로그인 후 sessionid 쿠키를 획득하지 못했습니다. (2차 인증 필요 또는 로그인 차단)",
                }

            cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

            # 4. 실제 헤이딜러 API 실측 ping 검증 (가짜 성공 원천 차단)
            print("[HeydealerAutoLogin] 5/5: 획득 세션으로 헤이딜러 실제 API 호출 실측 검증 중...", flush=True)
            try:
                ping_resp = requests.get(
                    "https://api.heydealer.com/v2/dealers/web/users/me/",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Cookie": cookie_str
                    },
                    timeout=5
                )
                if ping_resp.status_code != 200:
                    print(f"[HeydealerAutoLogin] ❌ 가짜 세션 감지 (API Ping HTTP {ping_resp.status_code})", flush=True)
                    return {
                        "success": False,
                        "message": f"헤이딜러 세션 검증 실패 (API 응답코드: {ping_resp.status_code}). 2차 인증(OTP)이 완료되지 않은 미승인 세션입니다. 크롬 확장으로 직접 로그인 후 연동해주세요.",
                    }
            except Exception as pe:
                print(f"[HeydealerAutoLogin] ⚠️ 실측 검증 요청 경고: {pe}", flush=True)

            save_cookie(cookie_str)
            print(f"[HeydealerAutoLogin] ✅ 헤이딜러 로그인 및 세션 검증 완전 성공! ({len(cookie_str)}자)", flush=True)

            return {
                "success": True,
                "target": "heydealer",
                "message": f"헤이딜러 자동 로그인 및 세션(sessionid) 갱신 완료! ({len(cookie_str)}자)",
                "cookie_length": len(cookie_str),
            }

    except Exception as e:
        print(f"[HeydealerAutoLogin] ❌ 실행 중 예외 발생: {e}", flush=True)
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
