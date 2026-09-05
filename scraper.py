# scraper.py
import requests
import urllib.parse
import json
import re
import concurrent.futures
import pandas as pd
from bs4 import BeautifulSoup

class EncarScraper:
    @staticmethod
    def run_scan(target_url, progress_callback=None):
        try:
            if progress_callback: progress_callback("1/4: 엔카 검색 조건을 분석 중입니다...")
            
            decoded_url = urllib.parse.unquote_plus(target_url.strip())
            condition = ""

            json_match = re.search(r'#!(\{.*\})', decoded_url)
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1))
                    condition = json_data.get("action", "")
                except: pass

            if not condition:
                match = re.search(r'"action"\s*:\s*"([^"]+)"', decoded_url)
                if match:
                    condition = match.group(1)
                    if r'\u' in condition:
                        condition = condition.encode('ascii', 'backslashreplace').decode('unicode_escape')
                elif 'q=' in decoded_url:
                    condition = decoded_url.split('q=')[1].split('&')[0]

            if not condition:
                raise Exception("URL에서 검색 조건을 찾을 수 없습니다. 주소를 다시 확인해 주세요.")

            condition = re.sub(r'\.?_\.Mileage\.range\(\d+\.\.\d+\)', '', condition)
            condition = re.sub(r'\.{2,}\)', '.)', condition)
            safe_condition = urllib.parse.quote(condition)
            
            api_url = f"https://api.encar.com/search/car/list/general?count=false&q={safe_condition}&sr=%7CModifiedDate%7C0%7C100"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://www.encar.com/",
                "Accept": "application/json"
            }

            if progress_callback: progress_callback("2/4: 전체 시장 데이터를 수집 중입니다...")
            response = requests.get(api_url, headers=headers)
            cars = response.json().get("SearchResults", [])

            if not cars:
                raise Exception("조건에 맞는 매물이 없거나 서버가 응답하지 않았습니다.")

            car_data_list = []
            for car in cars:
                price = car.get("Price", 0)
                mileage = car.get("Mileage", 0)
                if price <= 0 or mileage < 1000: continue
                
                # [버그 수정] 차량명과 세부 모델(등급)을 완벽하게 분리
                car_data_list.append({
                    "id": str(car.get('Id', '')),
                    "차량명": str(car.get('Model', '')).strip(),
                    "세부 모델": f"{car.get('Badge', '')} {car.get('BadgeDetail', '')}".strip(),
                    "연식": str(car.get("Year", car.get("FormYear", "미상")))[:4],
                    "주행거리": mileage,
                    "매입가": price * 10000, 
                    "지점판매가": price, 
                    "E URL": f"http://www.encar.com/dc/dc_cardetailview.do?pageid=dc_carsearch&listAdvType=normal&carid={car.get('Id', '')}",
                    "홈페이지상태": "실시간(엔카)"
                })

            if progress_callback: progress_callback(f"3/4: {len(car_data_list)}대 매물의 성능기록부를 타격합니다! (약 5초 소요)")

            valid_cars = []

            def process_car(car):
                try:
                    c_id = car["id"]
                    inspect_url = f"http://www.encar.com/md/sl/mdsl_regcar.do?method=inspectionView&carid={c_id}"
                    inspect_headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": "http://www.encar.com/"
                    }
                    res = requests.get(inspect_url, headers=inspect_headers, timeout=5)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    text = soup.get_text(separator=" ", strip=True)

                    if "등록된 성능점검 기록부가 없습니다" in text or "차량번호를 찾을 수 없습니다" in text:
                        car["사고유무"] = "⚠️미등록(수동확인)"
                        return car

                    gyo_matches = re.findall(r'교환\s*[:]?\s*(\d+)', text)
                    pan_matches = re.findall(r'판금\s*[:]?\s*(\d+)', text)

                    gyo = sum(int(x) for x in gyo_matches)
                    pan = sum(int(x) for x in pan_matches)

                    if gyo == 0 and pan == 0:
                        car["사고유무"] = "✅완전무사고(0/0)"
                    else:
                        car["사고유무"] = f"⚠️사고/단순(교환{gyo}/판금{pan})"
                    
                    return car
                except Exception:
                    car["사고유무"] = "⚠️로딩지연(수동확인)"
                    return car

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                results = executor.map(process_car, car_data_list[:100])

            for r in results:
                if r is not None:
                    r.pop('id', None) 
                    valid_cars.append(r)

            if progress_callback: progress_callback("4/4: 데이터 정리가 완료되었습니다.")
            
            return pd.DataFrame(valid_cars)

        except Exception as e:
            raise Exception(str(e))

class HeydealerScraper:
    @staticmethod
    def build_session(cookie_str):
        """초기 쿠키 문자열로 새 requests.Session을 생성합니다."""
        session = requests.Session()
        session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "App-Os": "pc",
            "App-Type": "dealer",
            "App-Version": "1.9.0",
            "Origin": "https://dealer.heydealer.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
        })
        # 쿠키 문자열을 파싱하여 세션에 등록
        # api/dealer 두 도메인 모두에 쿠키 등록 (헤이딜러는 두 도메인 모두 사용)
        for domain in ['api.heydealer.com', 'dealer.heydealer.com']:
            for item in cookie_str.split(';'):
                item = item.strip()
                if '=' in item:
                    k, v = item.split('=', 1)
                    session.cookies.set(k.strip(), v.strip(), domain=domain)
        # 초기 csrftoken 헤더 설정
        HeydealerScraper._sync_csrf_header(session)
        return session

    @staticmethod
    def _sync_csrf_header(session):
        """
        session의 쿠키 jar에서 최신 csrftoken을 읽어 X-Csrftoken 헤더를 동기화합니다.
        서버가 Set-Cookie로 csrftoken을 갱신할 때마다 이 함수를 호출해야 합니다.
        """
        csrf = None
        for cookie in session.cookies:
            if cookie.name == 'csrftoken':
                csrf = cookie.value
                break
                
        if csrf:
            session.headers['X-Csrftoken'] = csrf

    @staticmethod
    def save_session_to_env(session, env_path=None):
        """
        현재 session의 쿠키를 .env 파일의 HEYDEALER_COOKIE에 자동으로 저장합니다.
        앱 재시작 후에도 최신 쿠키로 자동 복원됩니다.
        """
        import os, re
        if env_path is None:
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        
        # 세션 쿠키 jar를 'key=value; key=value' 형식으로 직렬화
        cookie_parts = [f"{c.name}={c.value}" for c in session.cookies]
        if not cookie_parts:
            return
        new_cookie_str = "; ".join(cookie_parts)

        # .env 파일 읽기
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            content = ""

        new_line = f'HEYDEALER_COOKIE="{new_cookie_str}"'
        if 'HEYDEALER_COOKIE=' in content:
            content = re.sub(r'HEYDEALER_COOKIE=.*', new_line, content)
        else:
            content = content.rstrip('\n') + '\n' + new_line + '\n'

        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)

    @staticmethod
    def fetch_auction_repairs(car_id, session):
        """
        차량 ID로 헤이딜러 낙찰 이력 데이터를 가져옵니다.
        엔드포인트: GET /v2/dealers/web/accident_repairs_for_auction/?car={car_id}
        """
        auction_url = f"https://api.heydealer.com/v2/dealers/web/accident_repairs_for_auction/?car={car_id}"
        HeydealerScraper._sync_csrf_header(session)
        try:
            resp = session.get(auction_url, timeout=10)
            HeydealerScraper._sync_csrf_header(session)
            if resp.status_code == 200:
                return resp.text  # JSON 문자열 반환
        except Exception:
            pass
        return None  # 실패해도 전체 흐름에는 영향 없음

    @staticmethod
    def fetch_market_prices(params_dict, session):
        """
        차량 상세 데이터의 price_info.params를 바탕으로 동급 낙찰시세를 가져옵니다.
        엔드포인트: GET /v2/dealers/web/price/cars/?...
        """
        import urllib.parse
        query_parts = ["page=1"]
        for k, v in params_dict.items():
            if isinstance(v, list):
                for item in v:
                    query_parts.append(f"{k}={urllib.parse.quote(str(item))}")
            else:
                query_parts.append(f"{k}={urllib.parse.quote(str(v))}")
        
        if 'period' not in params_dict:
            query_parts.append("period=c")
        if 'order' not in params_dict:
            query_parts.append("order=recent")
            
        query_string = "&".join(query_parts)
        market_url = f"https://api.heydealer.com/v2/dealers/web/price/cars/?{query_string}"
        HeydealerScraper._sync_csrf_header(session)
        try:
            resp = session.get(market_url, timeout=10)
            HeydealerScraper._sync_csrf_header(session)
            if resp.status_code == 200:
                return resp.text
            else:
                print(f"[헤이딜러] fetch_market_prices 응답 코드: {resp.status_code}, 내용: {resp.text[:100]}")
        except Exception as e:
            print(f"[헤이딜러] fetch_market_prices 예외: {e}")
        return None


    @staticmethod
    def fetch_car_detail(url_or_id, cookie_str=None, session=None):
        """
        session이 있으면 재사용 (쿠키 자동 갱신), 없으면 cookie_str로 일회성 요청.
        차량 상세 정보와 낙찰 이력 데이터를 함께 반환합니다.
        반환값: dict { 'detail': str(JSON), 'auction_repairs': str(JSON) or None }
        """
        if session is None:
            if not cookie_str or not cookie_str.strip():
                raise Exception("헤이딜러 세션 쿠키가 제공되지 않았습니다. UI에 쿠키를 입력하거나 .env 파일에 HEYDEALER_COOKIE를 설정해주세요.")
            session = HeydealerScraper.build_session(cookie_str)
            
        car_id = url_or_id.strip()
        # URL에서 차량 ID 추출
        match = re.search(r'/cars/([a-zA-Z0-9]+)', car_id)
        if match:
            car_id = match.group(1)
        elif "/" in car_id or "heydealer.com" in car_id:
            raise Exception("유효한 헤이딜러 차량 ID 또는 URL 형식이 아닙니다.")
            
        api_url = f"https://api.heydealer.com/v2/dealers/web/cars/{car_id}/"
        session.headers['Referer'] = f"https://dealer.heydealer.com/cars/{car_id}/"

        # 요청 직전에 csrftoken 헤더를 최신 쿠키와 동기화 (로테이션 대응 핵심)
        HeydealerScraper._sync_csrf_header(session)
        
        response = session.get(api_url)

        # 응답 후에도 혹시 Set-Cookie로 csrftoken이 바뀌었으면 즉시 동기화
        HeydealerScraper._sync_csrf_header(session)
        
        if response.status_code in (401, 403):
            raise Exception(f"인증 오류 ({response.status_code}): 세션이 만료되었거나 쿠키가 올바르지 않습니다. 다시 로그인 후 쿠키를 업데이트해 주세요.")
        elif response.status_code == 404:
            raise Exception("해당 차량은 헤이딜러에서 이미 마감되었거나 존재하지 않는 매물입니다(404). 현재 진행 중인 다른 매물 URL을 입력해 주세요.")
        elif response.status_code != 200:
            raise Exception(f"API 요청 실패 ({response.status_code}): {response.text[:200]}")

        # 성공 시 최신 쿠키를 .env에 자동 저장 (앱 재시작 후에도 최신 쿠키 유지)
        try:
            HeydealerScraper.save_session_to_env(session)
        except Exception:
            pass  # .env 저장 실패해도 요청 결과에는 영향 없음

        detail_json = response.text
        market_prices_json = None

        # 디버그용 덤프 저장
        try:
            with open("last_heydealer_detail.json", "w", encoding="utf-8") as f:
                f.write(detail_json)
        except Exception:
            pass

        # 낙찰 이력 데이터 자동 추가 요청 (실패해도 무시)
        auction_repairs_json = HeydealerScraper.fetch_auction_repairs(car_id, session)

        # 동급 낙찰시세 자동 요청 + 엔카 URL 추출
        encar_url = None
        try:
            parsed = json.loads(detail_json)
            
            # 재귀적으로 price_info / params 탐색
            params = None
            def find_params(obj):
                nonlocal params
                if params or not isinstance(obj, dict): return
                if "params" in obj and isinstance(obj["params"], dict) and ("model" in obj["params"] or "grade" in obj["params"]):
                    params = obj["params"]
                    return
                if "price_info" in obj and isinstance(obj["price_info"], dict):
                    p = obj["price_info"].get("params")
                    if isinstance(p, dict):
                        params = p
                        return
                for k, v in obj.items():
                    if isinstance(v, dict):
                        find_params(v)

            find_params(parsed)

            # 직접 model/grade로 params 구성 (fallback)
            if not params:
                det = parsed.get("detail", {}) if isinstance(parsed.get("detail"), dict) else parsed
                m_id = det.get("model") or det.get("model_id")
                g_id = det.get("grade") or det.get("grade_id")
                y_val = det.get("year")
                if m_id and g_id:
                    params = {
                        "model": m_id,
                        "grade": g_id,
                        "year": [y_val - 1, y_val, y_val + 1] if y_val else []
                    }

            if params:
                market_prices_json = HeydealerScraper.fetch_market_prices(params, session)
            
            # 재귀적으로 external_url (encar) 탐색
            def find_encar_url(obj):
                nonlocal encar_url
                if encar_url or not isinstance(obj, dict): return
                if "external_url" in obj and isinstance(obj["external_url"], dict):
                    if obj["external_url"].get("encar"):
                        encar_url = obj["external_url"]["encar"]
                        return
                if "encar" in obj and isinstance(obj["encar"], str) and obj["encar"].startswith("http"):
                    encar_url = obj["encar"]
                    return
                for k, v in obj.items():
                    if isinstance(v, dict):
                        find_encar_url(v)

            find_encar_url(parsed)
        except Exception as e:
            print(f"[헤이딜러] 마켓/엔카 URL 추출 실패: {e}")

        return {
            'detail': detail_json,
            'auction_repairs': auction_repairs_json,
            'market_prices': market_prices_json,
            'encar_url': encar_url
        }