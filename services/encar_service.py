# services/encar_service.py
import re
import json
import time
import random
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from services.data_processor import DataProcessor
from services.cookie_server import get_current_encar_cookie

class Scraper:
    @staticmethod
    def calculate_inventory_days(date_str):
        try:
            full_date_str = f"20{date_str}" 
            delta = datetime.now() - datetime.strptime(full_date_str, "%Y-%m-%d")
            return str(delta.days)
        except: return "-"

    @staticmethod
    def _fetch_json(session, url, ref_id):
        headers = {"Referer": f"https://fem.encar.com/cars/detail/{ref_id}"}
        try:
            res = session.get(url, headers=headers, timeout=5)
            json_data = None
            if res.status_code == 200:
                try: json_data = res.json()
                except: pass
            return {"status": res.status_code, "json": json_data}
        except Exception:
            return {"status": "error", "json": None}

    @staticmethod
    def clean_option_name(name):
        return re.sub(r'\([^)]*\)|\[[^\]]*\]', '', str(name)).strip()

    @staticmethod
    def fetch_car_detail(session, c_id):
        perf_date = "⚠️미등록"
        inv_days = "-"
        accident_status = "⚠️정보없음"
        color = "⚠️정보없음"
        opt_str = "없음"
        is_rate_limited = False
        acc = None
        rep = None

        v_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/vehicle/{c_id}?include=MANAGE,OPTIONS,SPEC", c_id)
        if v_resp["status"] in [403, 429]: return {"성능일": "⚠️조회실패", "재고": "-", "사고유무": "⚠️조회실패", "외장컬러": "⚠️조회실패", "추가옵션": "⚠️조회실패", "is_rate_limited": True}
        
        real_id = str(c_id)
        applied_codes = []
        
        if v_resp["status"] == 200 and v_resp["json"]:
            manage = v_resp["json"].get("manage") or {}
            spec = v_resp["json"].get("spec") or {}
            color = spec.get("colorName", "⚠️정보없음")
            if manage.get("dummy"):
                real_id = str(manage.get("dummyVehicleId", c_id))
            applied_codes = v_resp["json"].get("options", {}).get("choice", [])

        i_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/inspection/vehicle/{real_id}", c_id)
        if i_resp["status"] in [403, 429]: return {"성능일": "⚠️조회실패", "재고": "-", "사고유무": "⚠️조회실패", "추가옵션": "⚠️조회실패", "is_rate_limited": True}
        
        if i_resp["status"] == 200 and i_resp["json"]:
            master = i_resp["json"].get("master") or {}
            detail = master.get("detail") or {}

            issue_date = detail.get("issueDate", "")
            if issue_date and len(issue_date) == 8:
                perf_date = f"{issue_date[2:4]}-{issue_date[4:6]}-{issue_date[6:8]}"
                inv_days = Scraper.calculate_inventory_days(perf_date)

            acc = master.get("accdient")
            rep = master.get("simpleRepair")

            if acc is False and rep is False:
                accident_status = "완전무사고"
            elif acc is None and rep is None:
                accident_status = "정보없음"
            else:
                flags = []
                if acc: flags.append("사고")
                if rep: flags.append("단순")
                accident_status = f"({'/'.join(flags)})"
        elif i_resp["status"] == 404:
            perf_date = "미검사/사진"
            accident_status = "기록부(사진)"

        exch_cnt = 0
        sheet_cnt = 0
        
        if i_resp["status"] == 200 and i_resp["json"]:
            ij = i_resp["json"]
            all_parts = (ij.get("outers", []) or []) + (ij.get("inners", []) or [])
            if not all_parts and "master" in ij:
                all_parts = (ij["master"].get("outers", []) or []) + (ij["master"].get("inners", []) or [])
            for part in all_parts:
                status_types = part.get("statusTypes", []) or []
                codes = [str(s.get("code", "")).upper() for s in status_types if isinstance(s, dict)]
                if "X" in codes:
                    exch_cnt += 1
                elif any(c in codes for c in ["W", "C", "A", "U", "T"]):
                    sheet_cnt += 1

        if exch_cnt == 0 and sheet_cnt == 0 and acc is not False and rep is not False:
            d_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/diagnosis/vehicle/{real_id}", c_id)
            if d_resp["status"] == 200 and d_resp["json"]:
                dj = d_resp["json"]
                if "items" in dj and isinstance(dj["items"], list):
                    for it in dj["items"]:
                        raw_n = it.get("name", "")
                        if raw_n in ["CHECKER_COMMENT", "OUTER_PANEL_COMMENT"]: continue
                        rc = str(it.get("resultCode", "") or "").upper()
                        rt = str(it.get("result", "") or "")
                        if rc in ["REPLACEMENT", "EXCHANGE", "X"] or "교환" in rt:
                            exch_cnt += 1
                        elif rc in ["SHEET_METAL", "WELD", "W", "C", "A", "U", "T"] or any(k in rt for k in ["판금", "용접", "도색", "수리"]):
                            sheet_cnt += 1

                outers = dj.get("outers", []) or []
                inners = dj.get("inners", []) or []
                all_parts = outers + inners
                for part in all_parts:
                    status_types = part.get("statusTypes", []) or []
                    codes = [str(s.get("code", "")).upper() for s in status_types if isinstance(s, dict)]
                    if "X" in codes:
                        exch_cnt += 1
                    elif any(c in codes for c in ["W", "C", "A", "U", "T"]):
                        sheet_cnt += 1
                    
        if exch_cnt > 0 or sheet_cnt > 0:
            if "기록부(사진)" not in accident_status:
                if acc:
                    base_label = "사고"
                elif exch_cnt > 0 and sheet_cnt == 0:
                    base_label = "단순교환"
                elif sheet_cnt > 0 and exch_cnt == 0:
                    base_label = "단순판금"
                else:
                    base_label = "단순(교환/판금)"
                accident_status = f"{base_label} [교환:{exch_cnt} / 판금:{sheet_cnt}]"
        else:
            if acc:
                accident_status = "사고"
            elif rep:
                accident_status = "단순교환"
            elif acc is False and rep is False:
                accident_status = "완전무사고"

        if applied_codes:
            opt_cache = {}
            try:
                if 'option_catalog_cache' not in st.session_state:
                    st.session_state.option_catalog_cache = {}
                opt_cache = st.session_state.option_catalog_cache
            except Exception:
                opt_cache = {}

            if c_id not in opt_cache:
                o_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/vehicles/car/{c_id}/options/choice", c_id)
                if o_resp["status"] == 200 and o_resp["json"]:
                    opt_cache[c_id] = o_resp["json"]
                elif o_resp["status"] == 404:
                    opt_str = "없음(구버전점검)" 
                elif o_resp["status"] in [403, 429]:
                    opt_str = "⚠️조회실패"
                    is_rate_limited = True
                elif o_resp["status"] != 200:
                    opt_str = "코드매칭실패"

            if opt_str == "없음": 
                catalog = opt_cache.get(c_id, [])
                if isinstance(catalog, list) and catalog:
                    applied_opts = []
                    for opt in catalog:
                        if isinstance(opt, dict) and str(opt.get("optionCd", "")) in applied_codes:
                            name = Scraper.clean_option_name(opt.get("optionName", ""))
                            price = opt.get("price", 0)
                            if name and "외장컬러" not in name:
                                if price > 0: applied_opts.append(f"{name}({price}만)")
                                else: applied_opts.append(name)
                    if applied_opts:
                        opt_str = " / ".join(applied_opts)

        return {
            "성능일": perf_date,
            "재고": inv_days,
            "사고유무": accident_status,
            "외장컬러": color,
            "추가옵션": opt_str,
            "is_rate_limited": is_rate_limited
        }

    @staticmethod
    def dedupe_after_scan(df):
        if df.empty: return df
        df_copy = df.copy()
        
        def calculate_score(row):
            score = 0
            if str(row.get('성능일', '')) not in ['⚠️미등록', '미검사/사진', '⚠️조회실패', '-']: score += 1
            if str(row.get('사고유무', '')) not in ['⚠️정보없음', '기록부(사진)', '⚠️조회실패', '-']: score += 1
            if str(row.get('추가옵션', '')) not in ['⚠️조회실패', '코드매칭실패', '없음(구버전점검)', '-']: score += 1
            return score

        df_copy['data_score'] = df_copy.apply(calculate_score, axis=1)
        deduped = df_copy.sort_values('data_score', ascending=False).drop_duplicates(
            subset=['차량명', '세부모델', '연식', '주행거리', '판매가'], keep='first'
        )
        deduped = deduped.drop(columns=['data_score']).reset_index(drop=True)
        return deduped

    @staticmethod
    def build_search_from_car_url(car_url_or_id):
        """
        엔카 차량 상세 URL 또는 carid로부터 실시간 엔카 내부 스펙을 조회하고,
        동급 매물 검색용 공식 Action 검색 URL 및 차량 타겟 스펙 딕셔너리를 자동 역생성.
        """
        match = re.search(r'(\d{7,9})', str(car_url_or_id).strip())
        if not match:
            return {"success": False, "error": "차량 ID(carid)를 찾을 수 없습니다."}
        
        car_id = match.group(1)
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://fem.encar.com",
            "Referer": f"https://fem.encar.com/cars/detail/{car_id}"
        }
        
        try:
            v_resp = session.get(
                f"https://api.encar.com/v1/readside/vehicle/{car_id}?include=MANAGE,OPTIONS,SPEC,CATEGORY", 
                headers=headers, 
                timeout=5
            )
            if v_resp.status_code != 200:
                return {"success": False, "error": f"엔카 차량 조회 실패 (코드: {v_resp.status_code})"}
            
            v_data = v_resp.json()
            cat = v_data.get("category", {}) or {}
            spec = v_data.get("spec", {}) or {}
            
            mfg = cat.get("manufacturerName", "").strip()
            mg = cat.get("modelGroupName", "").strip()
            model = cat.get("modelName", "").strip()
            grade = cat.get("gradeName", "").strip()
            domestic = cat.get("domestic", True)
            car_type = "kor" if domestic else "for"
            
            form_year = cat.get("formYear")
            try: form_year = int(form_year) if form_year else 0
            except: form_year = 0
            
            mileage = spec.get("mileage", 0)
            try: mileage = int(mileage) if mileage else 0
            except: mileage = 0
            
            car_no = v_data.get("vehicleNo", "").strip()
            car_full_name = f"{mfg} {mg} {model} {grade}".strip()
            
            # 동급 매물 검색용 Action 쿼리 구성 (Badge 세부등급 우선 매칭)
            action = f"(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.{mfg}._.(C.ModelGroup.{mg}._.Model.{model}.))))"
            if grade:
                action_badge = f"(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.{mfg}._.(C.ModelGroup.{mg}._.(C.Model.{model}._.Badge.{grade}.)))))"
                # Badge 세부등급 쿼리를 최우선 사용 (단, API로 0대인 경우에만 전체 모델 fallback)
                try:
                    chk_url = f"https://api.encar.com/search/car/list/general?count=true&q={urllib.parse.quote(action_badge)}&sr=%7CModifiedDate%7C0%7C10"
                    chk_res = session.get(chk_url, headers=headers, timeout=3).json()
                    total_cnt = chk_res.get("Count", 0) or len(chk_res.get("SearchResults", []))
                    if total_cnt > 0:
                        action = action_badge
                except Exception:
                    # 에러 발생 시에도 동급 세부등급을 우선 적용
                    action = action_badge
            
            # 검색창에서 인식 가능한 공식 엔카 데스크톱 URL 조립
            search_url = f'https://www.encar.com/dc/dc_carsearchlist.do?carType={car_type}&searchType=model&tgid=&cleanList=true#!{{"action":"{action}"}}'
            
            # 상세 사고 및 옵션도 함께 추출
            detail_info = Scraper.fetch_car_detail(session, car_id)
            accident_status = detail_info.get("사고유무", "완전무사고")
            options_str = detail_info.get("추가옵션", "")
            
            return {
                "success": True,
                "car_id": car_id,
                "car_no": car_no,
                "car_name": car_full_name,
                "mfg": mfg,
                "model_group": mg,
                "model": model,
                "grade": grade,
                "year": form_year,
                "mileage": mileage,
                "accident": accident_status,
                "options": options_str,
                "search_url": search_url,
                "action": action
            }
        except Exception as e:
            return {"success": False, "error": f"역추적 중 오류 발생: {str(e)}"}

    @staticmethod
    def run(target_url, custom_cookie, progress_bar=None, status_text=None):
        try:
            if status_text: status_text.text("1/3: 실시간 통신 준비...")
            if progress_bar: progress_bar.progress(10)
            
            decoded_url = urllib.parse.unquote_plus(target_url.strip())
            condition = ""
            json_match = re.search(r'#!(\{.*\})', decoded_url)
            if json_match:
                try: condition = json.loads(json_match.group(1)).get("action", "")
                except: pass
                    
            if not condition:
                match = re.search(r'"action"\s*:\s*"([^"]+)"', decoded_url)
                if match: condition = match.group(1).encode('ascii', 'backslashreplace').decode('unicode_escape') if r'\u' in match.group(1) else match.group(1)
                elif 'q=' in decoded_url: 
                    try: condition = decoded_url.split('q=')[1].split('&')[0]
                    except: pass

            if not condition: return pd.DataFrame(), "❌ URL 검색 조건 누락"
                
            safe_condition = urllib.parse.quote(condition)
            api_url = f"https://api.encar.com/search/car/list/general?count=false&q={safe_condition}&sr=%7CModifiedDate%7C0%7C100"
            
            session = requests.Session()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Origin": "https://fem.encar.com",
            }
            if custom_cookie: headers["Cookie"] = custom_cookie
            session.headers.update(headers)

            cars_res = session.get(api_url).json()
            cars = cars_res.get("SearchResults", [])
            
            # 💡 [지능형 Fallback] 세부 모델명 미스매치로 0건인 경우, 상위 모델그룹으로 자동 확장 검색
            if not cars and "Model." in condition:
                fallback_cond = re.sub(r'_\.\(C\.ModelGroup\.([^\.]+)\._\.Model\.[^\.]+\.\)', r'._.ModelGroup.\1.', condition)
                fallback_cond = re.sub(r'_\.Model\.[^\.]+\.', r'', fallback_cond)
                if fallback_cond != condition:
                    try:
                        fb_safe = urllib.parse.quote(fallback_cond)
                        fb_url = f"https://api.encar.com/search/car/list/general?count=false&q={fb_safe}&sr=%7CModifiedDate%7C0%7C100"
                        fb_res = session.get(fb_url).json()
                        cars = fb_res.get("SearchResults", [])
                    except Exception:
                        pass

            if not cars: return pd.DataFrame(), "❌ 매물 없음"

            car_data_list = []
            for car in cars:
                if car.get("Price", 0) <= 0: continue
                
                sell_type = str(car.get("SellType", ""))
                if "렌트" in sell_type or "리스" in sell_type: continue
                if car.get("LeaseType"): continue 
                
                badge_group = car.get('BadgeGroup', '')
                badge = car.get('Badge', '')
                badge_detail = car.get('BadgeDetail', '')
                
                parts = []
                if badge_group: parts.append(badge_group)
                if badge and badge not in parts: parts.append(badge)
                if badge_detail and badge_detail not in parts: parts.append(badge_detail)
                
                sub_model_full = " ".join(parts).strip()

                reg_year = str(car.get("Year", ""))
                form_year = str(car.get("FormYear", ""))
                if len(reg_year) >= 4:
                    year_str = f"{reg_year[2:4]}({form_year[2:] if len(form_year)==4 else form_year})"
                else:
                    year_str = f"{reg_year}({form_year})"

                car_data_list.append({
                    "상태": "실시간", "제조사": car.get('Manufacturer', '').strip(),
                    "차량명": car.get('Model', '').strip(), "세부모델": sub_model_full, 
                    "연식": year_str, "주행거리": car.get("Mileage", 0),
                    "판매가": car.get("Price", 0), "성능일": "-", "재고": "-",
                    "사고유무": "-", "외장컬러": "-", "추가옵션": "-",
                    "링크": f"http://www.encar.com/dc/dc_cardetailview.do?carid={car.get('Id', '')}",
                    "_carid": str(car.get('Id', ''))
                })
            
            total_cars = len(car_data_list)
            consecutive_failures = 0
            
            for idx, car in enumerate(car_data_list):
                if status_text: status_text.text(f"2/3: 쾌속 정밀 스캔 중... ({idx+1}/{total_cars}대)")
                if progress_bar: progress_bar.progress(10 + int(80 * (idx + 1) / total_cars))
                
                res = Scraper.fetch_car_detail(session, car["_carid"])
                
                car["성능일"] = res["성능일"]
                car["재고"] = res["재고"]
                car["사고유무"] = res["사고유무"]
                car["외장컬러"] = res.get("외장컬러", "-")
                car["추가옵션"] = res["추가옵션"]

                if res.get("is_rate_limited"):
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        if status_text: status_text.text("⚠️ 엔카 방어막 감지! 3초 대기 후 계속 시도합니다...")
                        time.sleep(3.0)
                        consecutive_failures = 0
                else:
                    consecutive_failures = 0
                    
                time.sleep(random.uniform(0.01, 0.03))

            if status_text: status_text.text("3/3: 스캔 완료. 스마트 데이터 취합 중...")
            raw_df = pd.DataFrame(car_data_list)
            deduped_df = Scraper.dedupe_after_scan(raw_df)

            if progress_bar: progress_bar.progress(100)
            if status_text: status_text.text("✅ 스캔 및 최적화 완전 성공!")
            return DataProcessor.standardize(deduped_df), "success"
        except Exception as e:
            return pd.DataFrame(), f"❌ 에러: {str(e)}"

    @staticmethod
    def rescan(failed_indices, custom_cookie, progress_bar, status_text):
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://fem.encar.com",
        }
        if custom_cookie: headers["Cookie"] = custom_cookie
        session.headers.update(headers)
        
        consecutive_failures = 0
        total_cars = len(failed_indices)
        
        for i, idx in enumerate(failed_indices):
            status_text.text(f"♻️ 실패 매물 원터치 재스캔... ({i+1}/{total_cars}대)")
            progress_bar.progress(int(100 * (i + 1) / total_cars))
            
            time.sleep(random.uniform(0.05, 0.1)) 
            
            c_id = st.session_state.scan_data.loc[idx, '_carid']
            res = Scraper.fetch_car_detail(session, c_id)
            
            st.session_state.scan_data.loc[idx, '성능일'] = res["성능일"]
            st.session_state.scan_data.loc[idx, '재고'] = res["재고"]
            st.session_state.scan_data.loc[idx, '사고유무'] = res["사고유무"]
            st.session_state.scan_data.loc[idx, '추가옵션'] = res["추가옵션"]
            
            if res.get("is_rate_limited"):
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    status_text.text("⚠️ 보안 대기 중 (15초)...")
                    time.sleep(15.0)
                    consecutive_failures = 0
            else:
                consecutive_failures = 0
                
        status_text.text("✅ 재스캔 완료!")

    _sold_out_global_cache = {}
    _sold_out_failed_cache = {}

    @staticmethod
    def fetch_sold_out_cars(carid, custom_cookie=None):
        """엔카 '팔린매물 (soldoutCars)' 팝업 데이터 수집 및 소화 속도 분석"""
        if not carid:
            return {"has_data": False, "msg": "carid 누락"}
        
        carid = str(carid).strip()
        now_ts = time.time()

        # 1. 실패한 carid는 10분(600초) 동안 재요청 금지 (백그라운드 봇 차단 방어)
        if carid in Scraper._sold_out_failed_cache:
            fail_time, fail_res = Scraper._sold_out_failed_cache[carid]
            if now_ts - fail_time < 600:
                return fail_res

        # 2. 전역 메모리 캐시 확인
        if carid in Scraper._sold_out_global_cache:
            return Scraper._sold_out_global_cache[carid]

        # 3. session_state 캐싱 확인
        if hasattr(st, "session_state"):
            if "sold_out_cars_cache" not in st.session_state:
                st.session_state.sold_out_cars_cache = {}
            if carid in st.session_state.sold_out_cars_cache:
                return st.session_state.sold_out_cars_cache[carid]

        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": f"https://www.encar.com/dc/dc_cardetailview.do?carid={carid}",
        }
        
        cookie_val = custom_cookie or get_current_encar_cookie()
        if cookie_val:
            headers["Cookie"] = cookie_val

        # 주의: method=soldoutCars (소문자 o 필수)
        url = f"https://www.encar.com/dc/dc_carsearchpop.do?method=soldoutCars&carTypeCd=1&carid={carid}&wtClick_carview=067"
        try:
            res = session.get(url, headers=headers, timeout=3.0)
            if res.status_code != 200 or len(res.content) < 1500:
                result = {
                    "has_data": False,
                    "msg": f"조회 실패 (상태코드: {res.status_code})",
                    "status_code": res.status_code
                }
                Scraper._sold_out_failed_cache[carid] = (now_ts, result)
                if hasattr(st, "session_state"):
                    st.session_state.sold_out_cars_cache[carid] = result
                return result

            try:
                html = res.content.decode('euc-kr', errors='ignore')
            except Exception:
                html = res.text

            soup = BeautifulSoup(html, 'html.parser')

            # 1. 검색 건수 파싱 (예: <div class="part result"><p><em>검색결과</em> : <strong>70</strong>건</p></div>)
            total_sold_count = 0
            cnt_elem = soup.select_one('.part.result strong')
            if cnt_elem:
                try:
                    total_sold_count = int(cnt_elem.get_text(strip=True).replace(',', ''))
                except: pass
            if not total_sold_count:
                cnt_match = re.search(r'검색결과[^\d]*([0-9,]+)\s*건', html)
                if cnt_match:
                    try:
                        total_sold_count = int(cnt_match.group(1).replace(',', ''))
                    except: pass

            # 2. 테이블 목록 파싱
            rows = soup.select('table tr')
            parsed_cars = []
            now = datetime.now()

            for r in rows:
                cols = r.find_all(['td', 'th'])
                if len(cols) >= 5 and cols[0].name == 'td':
                    name_txt = cols[0].get_text(strip=True)
                    year_txt = cols[1].get_text(strip=True)
                    km_txt = cols[2].get_text(strip=True)
                    sold_date_txt = cols[4].get_text(strip=True)

                    if not km_txt or not sold_date_txt or km_txt == '-':
                        continue

                    # km 수치 변환
                    km_num = 0
                    km_match = re.search(r'([0-9,]+)', km_txt)
                    if km_match:
                        try:
                            km_num = int(km_match.group(1).replace(',', ''))
                        except: pass

                    # 판매일 파싱 및 일수 차이 계산 (예: 2026/09/12)
                    days_ago = 999
                    try:
                        clean_date = sold_date_txt.replace('/', '-').replace('.', '-')
                        dt = datetime.strptime(clean_date.strip()[:10], "%Y-%m-%d")
                        days_ago = (now - dt).days
                    except: pass

                    parsed_cars.append({
                        "name": name_txt,
                        "year": year_txt,
                        "mileage": km_num,
                        "sold_date": sold_date_txt,
                        "days_ago": days_ago
                    })

            if not parsed_cars and total_sold_count == 0:
                result = {"has_data": False, "msg": "팔린 매물 데이터 없음"}
                if hasattr(st, "session_state"):
                    st.session_state.sold_out_cars_cache[carid] = result
                return result

            # 3. 통계 계산
            recent_7d = [c for c in parsed_cars if c["days_ago"] <= 7]
            recent_30d = [c for c in parsed_cars if c["days_ago"] <= 30]
            count_7d = len(recent_7d)
            count_30d = len(recent_30d)

            # 주행거리 평균
            mileages = [c["mileage"] for c in parsed_cars if c["mileage"] > 0]
            avg_mileage = int(sum(mileages) / len(mileages)) if mileages else 0

            # 일평균 출고 속도
            daily_rate = round(count_30d / 30.0, 1) if count_30d > 0 else (round(count_7d / 7.0, 1) if count_7d > 0 else 0)

            # 회전 속도 평가 등급 및 배지
            if daily_rate >= 1.0 or count_30d >= 30:
                velocity_grade = "초특급 완판"
                velocity_badge = "🔥 일 1대+ 출고"
                velocity_color = "#ef4444"
            elif daily_rate >= 0.5 or count_30d >= 15:
                velocity_grade = "빠른 완판"
                velocity_badge = "⚡ 월 15대+ 출고"
                velocity_color = "#f59e0b"
            elif count_30d >= 5:
                velocity_grade = "보통 완판"
                velocity_badge = "✨ 보통 출고"
                velocity_color = "#38bdf8"
            else:
                velocity_grade = "완판 지연"
                velocity_badge = "☕ 저속 출고"
                velocity_color = "#94a3b8"

            latest_sold_date = parsed_cars[0]["sold_date"] if parsed_cars else "-"

            result = {
                "has_data": True,
                "carid": carid,
                "total_sold_count": total_sold_count or len(parsed_cars),
                "count_7d": count_7d,
                "count_30d": count_30d,
                "daily_rate": daily_rate,
                "avg_mileage": avg_mileage,
                "velocity_grade": velocity_grade,
                "velocity_badge": velocity_badge,
                "velocity_color": velocity_color,
                "latest_sold_date": latest_sold_date,
                "cars_sample": parsed_cars[:10]
            }

            Scraper._sold_out_global_cache[carid] = result
            if hasattr(st, "session_state"):
                st.session_state.sold_out_cars_cache[carid] = result
            return result

        except Exception as e:
            err_res = {"has_data": False, "msg": f"파싱 에러: {str(e)}"}
            Scraper._sold_out_failed_cache[carid] = (time.time(), err_res)
            return err_res

    @staticmethod
    def fetch_price_report(rgsid):
        """
        엔카 공식 시세리포트(viewPriceReport) API를 호출하여
        해당 차량의 평가점수, 개별 기준가, 적정시세 밴드(min~max), bad/good 계수 등을 반환합니다.
        """
        if not rgsid:
            return {"has_data": False, "msg": "rgsid 누락"}
        
        rgsid_str = str(rgsid).strip()
        if hasattr(st, "session_state"):
            if "price_report_cache" not in st.session_state:
                st.session_state.price_report_cache = {}
            if rgsid_str in st.session_state.price_report_cache:
                return st.session_state.price_report_cache[rgsid_str]

        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.encar.com/pr/pr_carsearchlist.do",
            "X-Requested-With": "XMLHttpRequest"
        }
        url = f"https://www.encar.com/pr/pr_index.do?method=viewPriceReport&type=MZ&rgsid={rgsid_str}"
        try:
            res = session.get(url, headers=headers, timeout=3.5)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    item = data[0]
                    car_info = item.get("carInfo", {}) or {}
                    
                    min_p = item.get("minPrice", 0)
                    ind_p = item.get("individualPrice", 0)
                    max_p = item.get("maxPrice", 0)
                    my_score = float(item.get("myScore", 100.0))
                    
                    try:
                        bad_ratio = float(car_info.get("bad", 0.94))
                    except:
                        bad_ratio = 0.937
                    try:
                        good_ratio = float(car_info.get("good", 1.08))
                    except:
                        good_ratio = 1.087

                    try:
                        base_mileage = int(car_info.get("mileage", 150000))
                    except:
                        base_mileage = 150000

                    actual_mil = car_info.get("mlg", 0)
                    dmnd_prc = car_info.get("dmndprc", 0)

                    # 100점 표준 기본 시세 역산 (individualPrice = 100점_기본가 * (myScore / 100))
                    score_factor = (my_score / 100.0) if my_score > 0 else 1.0
                    std_100_price = int(round(ind_p / score_factor)) if (ind_p > 0 and score_factor > 0) else ind_p

                    result = {
                        "has_data": True,
                        "rgsid": rgsid_str,
                        "min_price": min_p,
                        "individual_price": ind_p,
                        "max_price": max_p,
                        "my_score": my_score,
                        "bad_ratio": bad_ratio,
                        "good_ratio": good_ratio,
                        "std_100_price": std_100_price,
                        "base_mileage": base_mileage,
                        "actual_mileage": actual_mil,
                        "dmnd_price": dmnd_prc,
                        "model_name": car_info.get("mdlnm", ""),
                        "grade_name": car_info.get("clsheadnm", ""),
                        "year": car_info.get("yr2", "")
                    }
                    if hasattr(st, "session_state"):
                        st.session_state.price_report_cache[rgsid_str] = result
                    return result
            return {"has_data": False, "msg": f"조회 실패(코드 {res.status_code})"}
        except Exception as e:
            return {"has_data": False, "msg": f"통신 에러: {str(e)}"}

    @staticmethod
    def get_benchmarked_valuation(chart_base, target_mil=0, target_accident="", target_year="", target_options="", target_opt_adj=0):
        """
        동급 매물 리스트(chart_base)에서 실제 rgsid를 찾아 엔카 viewPriceReport를 찌르고,
        엔카 표준 100점 기준가와 상하한 밴드 계수를 획득하여
        평가 대상 차량(헤이딜러/미등록)에 맞춘 엔카 공식 적정시세 밴드와 평가점수를 산출합니다.
        (옵션 가치 보정치 target_opt_adj도 기준가에 정밀 가산)
        """
        if chart_base is None or chart_base.empty:
            return {"has_data": False, "msg": "동급 매물 없음"}

        # 1. 유효한 rgsid / carid 탐색 (완전무사고 우선, 또는 첫 번째 유효 매물)
        target_rgsids = []
        if '_carid' in chart_base.columns:
            for cid in chart_base['_carid'].dropna().unique():
                c_str = str(cid).strip()
                if c_str and c_str.isdigit() and len(c_str) >= 6:
                    target_rgsids.append(c_str)

        if not target_rgsids and '링크' in chart_base.columns:
            for link in chart_base['링크'].dropna().unique():
                m = re.search(r'carid=(\d+)', str(link))
                if m:
                    target_rgsids.append(m.group(1))

        if not target_rgsids:
            return {"has_data": False, "msg": "동급 매물 ID 없음"}

        # 2. 대표 매물 1~3대로 엔카 시세리포트 호출
        benchmark_report = None
        for rid in target_rgsids[:3]:
            rep = Scraper.fetch_price_report(rid)
            if rep.get("has_data") and rep.get("individual_price", 0) > 0:
                benchmark_report = rep
                break

        if not benchmark_report:
            return {"has_data": False, "msg": "엔카 시세리포트 데이터 미제공 차종"}

        # 3. 엔카 표준 100점 기본가 및 상하한 밴드 계수 확보
        std_100_price = benchmark_report["std_100_price"]
        bad_ratio = benchmark_report["bad_ratio"]
        good_ratio = benchmark_report["good_ratio"]
        base_mil = benchmark_report["base_mileage"]

        # 4. 대상 차량(헤이딜러 미등록차) 스펙 적용
        # (1) 주행거리 보정: 기준거리 대비 차이로 점수 산출
        effective_mil = target_mil if target_mil > 0 else benchmark_report["actual_mileage"]
        mil_diff = base_mil - effective_mil  # 양수면 기준보다 적게 탐
        
        # 차종 가격대에 따른 1만km당 점수 가중치 (경/소형 2.8점, 준중형/중형 3.2점, 대형/고가차 4.5점)
        if std_100_price >= 2000:
            pt_per_10k = 4.5
        elif std_100_price >= 1200:
            pt_per_10k = 2.8
        else:
            pt_per_10k = 3.2

        mil_score_delta = (mil_diff / 10000.0) * pt_per_10k

        # (2) 사고 감점
        acc_score_delta = 0.0
        acc_str = str(target_accident).strip()
        if "사고" in acc_str and "무사고" not in acc_str:
            acc_score_delta = -12.0
        elif "단순" in acc_str or "교환" in acc_str:
            acc_score_delta = -5.0

        # (3) 가치평가 점수 산출
        calc_score = round(100.0 + mil_score_delta + acc_score_delta, 1)

        # (4) 대상 차량의 엔카 개별 기준가 산출 (옵션 감가 보정치 합산)
        calc_individual_price = int(round(std_100_price * (calc_score / 100.0))) + int(target_opt_adj)

        # (5) 엔카 적정 시세 밴드 (minPrice ~ maxPrice)
        calc_min_price = int(round(calc_individual_price * bad_ratio))
        calc_max_price = int(round(calc_individual_price * good_ratio))

        return {
            "has_data": True,
            "benchmark_rgsid": benchmark_report["rgsid"],
            "std_100_price": std_100_price,
            "base_mileage": base_mil,
            "calc_score": calc_score,
            "calc_individual_price": calc_individual_price,
            "calc_opt_adj": int(target_opt_adj),
            "calc_min_price": calc_min_price,
            "calc_max_price": calc_max_price,
            "bad_ratio": bad_ratio,
            "good_ratio": good_ratio,
            "benchmark_model": benchmark_report.get("model_name", ""),
            "benchmark_grade": benchmark_report.get("grade_name", "")
        }

