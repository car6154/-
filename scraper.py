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