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
        regist_dt = ""
        
        if v_resp["status"] == 200 and v_resp["json"]:
            manage = v_resp["json"].get("manage") or {}
            spec = v_resp["json"].get("spec") or {}
            color = spec.get("colorName", "⚠️정보없음")
            regist_dt = manage.get("registDateTime") or manage.get("firstAdvertisedDateTime") or ""
            if manage.get("dummy") and manage.get("dummyVehicleId"):
                real_id = str(manage.get("dummyVehicleId"))
            applied_codes = v_resp["json"].get("options", {}).get("choice", [])

        # 1차로 c_id 조회, 404 발생 시 real_id(dummyVehicleId) 조회
        i_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/inspection/vehicle/{c_id}", c_id)
        if i_resp["status"] == 404 and real_id != str(c_id):
            i_resp = Scraper._fetch_json(session, f"https://api.encar.com/v1/readside/inspection/vehicle/{real_id}", c_id)
        
        if i_resp["status"] in [403, 429]: return {"성능일": "⚠️조회실패", "재고": "-", "사고유무": "⚠️조회실패", "추가옵션": "⚠️조회실패", "is_rate_limited": True}
        
        if i_resp["status"] == 200 and i_resp["json"]:
            master = i_resp["json"].get("master") or {}
            detail = master.get("detail") or {}

            issue_date = detail.get("issueDate", "")
            if issue_date and len(issue_date) >= 8:
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
            inv_days = "-"
            accident_status = "미검사(사진)"

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
        # 1. 고유 차량 ID (_carid) 기준 최우선 중복 제거
        if '_carid' in df_copy.columns:
            df_copy = df_copy.sort_values('data_score', ascending=False).drop_duplicates(
                subset=['_carid'], keep='first'
            )
        # 2. 동일 실물 매물 (연식, 주행거리, 판매가) 기준 2차 중복 제거 (딜러 중복등록 및 재광고 방지)
        deduped = df_copy.sort_values('data_score', ascending=False).drop_duplicates(
            subset=['차량명', '연식', '주행거리', '판매가'], keep='first'
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
            
            # 동급 매물 검색용 Action 쿼리 구성 (스마트 마스터 매핑 우선 연동)
            grade_detail = cat.get("gradeDetailName", "").strip()
            sub_combined = f"{grade} {grade_detail}".strip()
            action = f"(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.{mfg}._.(C.ModelGroup.{mg}._.Model.{model}.))))"
            search_url = f'https://www.encar.com/dc/dc_carsearchlist.do?carType={car_type}&searchType=model&tgid=&cleanList=true#!{{"action":"{action}"}}'
            try:
                from services.master_mapping import MasterMappingService
                smart_url = MasterMappingService.generate_smart_encar_url(model, sub_combined, form_year, mileage, car_number=car_no)
                if smart_url and ("action=" in smart_url or "action%22" in smart_url or "%22action%22" in smart_url):
                    search_url = smart_url
                    unq = urllib.parse.unquote(smart_url)
                    m_act = re.search(r'"action"\s*:\s*"([^"]+)"', unq)
                    if m_act:
                        action = m_act.group(1)
            except Exception:
                pass
            
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
            
            # 💡 [문자열 정제] 유니코드 이스케이프(\uXXXX) 및 + 기호를 실제 한글/공백으로 완벽 보정
            if "\\u" in condition or r"\u" in condition:
                try:
                    condition = condition.encode('utf-8').decode('unicode_escape')
                except Exception:
                    pass
            condition = condition.replace("+", " ")
            condition = re.sub(r' +', ' ', condition)
                
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

            cars = []
            try:
                cars_res = session.get(api_url, timeout=7)
                if cars_res.status_code == 200:
                    cars = cars_res.json().get("SearchResults", [])
                    # 💡 [다중 페이지 자동 수집] 1페이지(100대)가 꽉 찼을 경우 추가 페이지(2~3페이지) 연속 수집하여 누락 방지
                    if len(cars) == 100:
                        for p_start in [100, 200]:
                            try:
                                p_url = f"https://api.encar.com/search/car/list/general?count=false&q={safe_condition}&sr=%7CModifiedDate%7C{p_start}%7C100"
                                p_res = session.get(p_url, timeout=5)
                                if p_res.status_code == 200:
                                    p_cars = p_res.json().get("SearchResults", [])
                                    if p_cars:
                                        cars.extend(p_cars)
                                    if len(p_cars) < 100:
                                        break
                                else:
                                    break
                            except Exception:
                                break
            except Exception:
                cars = []
            
            # 💡 [정밀 구문 보정 Fallback]
            # 절대로 차종 전체(ModelGroup)나 전체 등급(Model Only)으로 무차별 확대하지 않고,
            # 특수문자/괄호/공백/BadgeDetail 오차만 미세 보정하여 동급 매물 원칙을 철저히 고수
            if not cars:
                fallback_candidates = []
                cur_c = condition

                # 1. 특수 제조사명 언더바 보정 (르노코리아(삼성) <-> 르노코리아(삼성_))
                for orig_b, enc_b in [("르노코리아(삼성)", "르노코리아(삼성_)"), ("쉐보레(GM대우)", "쉐보레(GM대우_)"), ("KG모빌리티(쌍용)", "KG모빌리티(쌍용_)")]:
                    if orig_b in cur_c and enc_b not in cur_c:
                        fallback_candidates.append(cur_c.replace(orig_b, enc_b))
                    elif enc_b in cur_c and orig_b not in cur_c:
                        fallback_candidates.append(cur_c.replace(enc_b, orig_b))

                # 2. 모델명 괄호 언더바 보정: (NX4) <-> (NX4_), (CN7) <-> (CN7_), (JA) <-> (JA_), (PD) <-> (PD_)
                if re.search(r'\([A-Za-z0-9]+\)', cur_c):
                    c_model_paren = re.sub(r'\(([A-Za-z0-9]+)\)', r'(\1_)', cur_c)
                    if c_model_paren != cur_c and c_model_paren not in fallback_candidates:
                        fallback_candidates.append(c_model_paren)

                # 3. BadgeDetail 완화 (동일 모델/동일 트림의 Badge 레벨까지만 유지하여 검색)
                if "BadgeDetail" in cur_c:
                    c_no_detail = re.sub(r'_\.\(C\.Badge\.([^\.]+)\._\.BadgeDetail\.[^\.]+\.\)', r'._.Badge.\1.', cur_c)
                    if c_no_detail != cur_c and c_no_detail not in fallback_candidates:
                        fallback_candidates.append(c_no_detail)

                # 4. BadgeGroup 공백 미세 보정 (예: '디젤 9인승' <-> '디젤 9 인승')
                if "BadgeGroup." in cur_c:
                    bg_m = re.search(r'BadgeGroup\.([^\.]+)\.', cur_c)
                    if bg_m:
                        orig_bg = bg_m.group(1)
                        if re.search(r'\d인승', orig_bg):
                            alt_bg = re.sub(r'(\d)인승', r'\1 인승', orig_bg)
                            fallback_candidates.append(cur_c.replace(f"BadgeGroup.{orig_bg}.", f"BadgeGroup.{alt_bg}."))
                        elif re.search(r'\d\s+인승', orig_bg):
                            alt_bg = re.sub(r'(\d)\s+인승', r'\1인승', orig_bg)
                            fallback_candidates.append(cur_c.replace(f"BadgeGroup.{orig_bg}.", f"BadgeGroup.{alt_bg}."))

                # 5. 과도하게 좁은 Year/Mileage 범위 완화 (동일 모델/트림 조건은 100% 엄격 유지)
                if "Mileage.range" in cur_c:
                    c_no_mil = re.sub(r'_\.Mileage\.range\([^)]*\)\.', '', cur_c)
                    if c_no_mil != cur_c and c_no_mil not in fallback_candidates:
                        fallback_candidates.append(c_no_mil)
                if "Year.range" in cur_c:
                    c_no_yr = re.sub(r'_\.Year\.range\([^)]*\)\.', '', cur_c)
                    if c_no_yr != cur_c and c_no_yr not in fallback_candidates:
                        fallback_candidates.append(c_no_yr)
                    c_no_both = re.sub(r'_\.(?:Year|Mileage)\.range\([^)]*\)\.', '', cur_c)
                    if c_no_both != cur_c and c_no_both not in fallback_candidates:
                        fallback_candidates.append(c_no_both)

                for fb_cond in fallback_candidates:
                    try:
                        fb_safe = urllib.parse.quote(fb_cond)
                        fb_url = f"https://api.encar.com/search/car/list/general?count=false&q={fb_safe}&sr=%7CModifiedDate%7C0%7C100"
                        fb_resp = session.get(fb_url, timeout=7)
                        if fb_resp.status_code == 200:
                            fb_cars = fb_resp.json().get("SearchResults", [])
                            if fb_cars:
                                cars = fb_cars
                                if len(cars) == 100:
                                    for p_start in [100, 200]:
                                        try:
                                            next_p_url = f"https://api.encar.com/search/car/list/general?count=false&q={fb_safe}&sr=%7CModifiedDate%7C{p_start}%7C100"
                                            next_p_res = session.get(next_p_url, timeout=5)
                                            if next_p_res.status_code == 200:
                                                next_p_cars = next_p_res.json().get("SearchResults", [])
                                                if next_p_cars:
                                                    cars.extend(next_p_cars)
                                                if len(next_p_cars) < 100:
                                                    break
                                            else:
                                                break
                                        except Exception:
                                            break
                                break
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
                    "링크": f"https://fem.encar.com/cars/detail/{car.get('Id', '')}",
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
    def fetch_sold_out_cars(carids, custom_cookie=None, target_year=None, expected_model=None):
        """
        엔카 '팔린매물 (soldoutCars)' 팝업 데이터 수집 및 소화 속도 분석
        - carids: 단일 carid 또는 우선순위 정렬된 후보 carid 리스트
        - target_year: 타겟 연식 (예: '16' 또는 '2016') - 해당 연식으로 필터링 및 통계 산출
        - expected_model: 기대 모델명 (예: '투싼') - 엔카 56만건 엉뚱한 차종 응답 방어
        """
        if not carids:
            return {"has_data": False, "msg": "carid 누락"}

        if isinstance(carids, (list, tuple, set)):
            candidate_list = [str(x).strip() for x in carids if x and str(x).strip()]
        else:
            candidate_list = [str(carids).strip()]

        if not candidate_list:
            return {"has_data": False, "msg": "유효한 carid 없음"}

        ty_str = str(target_year).strip() if target_year else ""
        ty_2d = ty_str[-2:] if len(ty_str) >= 2 else (f"{int(ty_str):02d}" if ty_str.isdigit() else ty_str)

        now_ts = time.time()
        session = requests.Session()
        cookie_val = custom_cookie or get_current_encar_cookie()

        for carid in candidate_list:
            # 1. 실패한 carid는 20초 동안만 재요청 방어 (임시 네트워크 오류 즉시 복원 지원)
            if carid in Scraper._sold_out_failed_cache:
                fail_time, fail_res = Scraper._sold_out_failed_cache[carid]
                if now_ts - fail_time < 20:
                    continue

            # 2. 캐시 확인 (carid + target_year 조합)
            cache_k = f"{carid}_{ty_2d}"
            if cache_k in Scraper._sold_out_global_cache:
                return Scraper._sold_out_global_cache[cache_k]

            if hasattr(st, "session_state"):
                if "sold_out_cars_cache" not in st.session_state:
                    st.session_state.sold_out_cars_cache = {}
                if cache_k in st.session_state.sold_out_cars_cache:
                    return st.session_state.sold_out_cars_cache[cache_k]

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": f"https://fem.encar.com/cars/detail/{carid}",
            }
            if cookie_val:
                headers["Cookie"] = cookie_val

            url = f"https://www.encar.com/dc/dc_carsearchpop.do?method=soldoutCars&carTypeCd=1&carid={carid}&wtClick_carview=067"
            try:
                res = None
                for _ in range(2):
                    try:
                        res = session.get(url, headers=headers, timeout=6.0)
                        if res.status_code == 200 and len(res.content) >= 1500:
                            break
                    except Exception:
                        time.sleep(0.2)

                if not res or res.status_code != 200 or len(res.content) < 1500:
                    Scraper._sold_out_failed_cache[carid] = (now_ts, {"has_data": False, "msg": "조회 실패"})
                    continue

                try:
                    html_text = res.content.decode('euc-kr', errors='ignore')
                except Exception:
                    html_text = res.text

                soup = BeautifulSoup(html_text, 'html.parser')

                # 검색 건수 파싱
                total_sold_count = 0
                cnt_elem = soup.select_one('.part.result strong')
                if cnt_elem:
                    try: total_sold_count = int(cnt_elem.get_text(strip=True).replace(',', ''))
                    except: pass
                if not total_sold_count:
                    cnt_match = re.search(r'검색결과[^\d]*([0-9,]+)\s*건', html_text)
                    if cnt_match:
                        try: total_sold_count = int(cnt_match.group(1).replace(',', ''))
                        except: pass

                # 엔카 56만건 전체 매물 반환 방어 (DB 매핑 오류 carid)
                if total_sold_count > 100000:
                    Scraper._sold_out_failed_cache[carid] = (now_ts, {"has_data": False, "msg": "엔카 엉뚱한 전체 매물 반환"})
                    continue

                def _parse_rows(r_list):
                    c_list = []
                    now_dt = datetime.now()
                    for r in r_list:
                        cols = r.find_all(['td', 'th'])
                        if len(cols) >= 5 and cols[0].name == 'td':
                            name_txt = cols[0].get_text(strip=True)
                            year_txt = cols[1].get_text(strip=True)
                            km_txt = cols[2].get_text(strip=True)
                            sold_date_txt = cols[4].get_text(strip=True)

                            if not km_txt or not sold_date_txt or km_txt == '-':
                                continue

                            km_num = 0
                            km_match = re.search(r'([0-9,]+)', km_txt)
                            if km_match:
                                try: km_num = int(km_match.group(1).replace(',', ''))
                                except: pass

                            days_ago = 999
                            try:
                                clean_date = sold_date_txt.replace('/', '-').replace('.', '-')
                                dt = datetime.strptime(clean_date.strip()[:10], "%Y-%m-%d")
                                days_ago = (now_dt - dt).days
                            except: pass

                            c_list.append({
                                "name": name_txt,
                                "year": year_txt,
                                "mileage": km_num,
                                "sold_date": sold_date_txt,
                                "days_ago": days_ago
                            })
                    return c_list

                parsed_cars = _parse_rows(soup.select('table tr'))

                # 💡 최근 한 달치 이상(30~40대) 넉넉한 완판 매물 확보를 위해 2페이지 추가 연동 (안전 1회 호출)
                if total_sold_count > 20 and len(parsed_cars) >= 15:
                    try:
                        url_p2 = f"https://www.encar.com/dc/dc_carsearchpop.do?method=soldoutCars&carTypeCd=1&carid={carid}&pagenum=2"
                        res_p2 = session.get(url_p2, headers=headers, timeout=4.0)
                        if res_p2.status_code == 200 and len(res_p2.content) >= 1500:
                            soup_p2 = BeautifulSoup(res_p2.content.decode('euc-kr', errors='ignore'), 'html.parser')
                            parsed_cars.extend(_parse_rows(soup_p2.select('table tr')))
                    except Exception:
                        pass

                if not parsed_cars:
                    Scraper._sold_out_failed_cache[carid] = (now_ts, {"has_data": False, "msg": "매물 없음"})
                    continue

                # 모델명 유효성 검증 (기대 모델명이 있는 경우)
                if expected_model:
                    exp_clean = re.sub(r'[^가-힣a-zA-Z0-9]', '', str(expected_model)).lower()
                    first_name_clean = re.sub(r'[^가-힣a-zA-Z0-9]', '', parsed_cars[0]['name']).lower()
                    matched_exp = False
                    for part in [exp_clean[-4:], exp_clean[:4], exp_clean]:
                        if part and (part in first_name_clean or first_name_clean in part):
                            matched_exp = True
                            break
                    if not matched_exp and len(exp_clean) >= 2:
                        Scraper._sold_out_failed_cache[carid] = (now_ts, {"has_data": False, "msg": "차종 불일치"})
                        continue

                # 연식 필터링 적용
                def _match_year(y_txt, ty2):
                    if not ty2:
                        return True
                    y_clean = str(y_txt).replace(' ', '')
                    if f"{ty2}년형" in y_clean or f"20{ty2}년형" in y_clean:
                        return True
                    if f"{ty2}/" in y_clean:
                        return True
                    if f"20{ty2}" in y_clean or f"{ty2}년식" in y_clean:
                        return True
                    return False

                if ty_2d:
                    year_matched = [c for c in parsed_cars if _match_year(c["year"], ty_2d)]
                else:
                    year_matched = []

                if year_matched:
                    filtered_cars = year_matched
                    is_year_filtered = True
                else:
                    filtered_cars = parsed_cars
                    is_year_filtered = False

                # 통계 계산 (필터링된 차량 기준)
                recent_7d = [c for c in filtered_cars if c["days_ago"] <= 7]
                recent_30d = [c for c in filtered_cars if c["days_ago"] <= 30]
                count_7d = len(recent_7d)
                count_30d = len(recent_30d)

                mileages = [c["mileage"] for c in filtered_cars if c["mileage"] > 0]
                avg_mileage = int(sum(mileages) / len(mileages)) if mileages else 0

                daily_rate = round(count_30d / 30.0, 1) if count_30d > 0 else (round(count_7d / 7.0, 1) if count_7d > 0 else 0)

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

                latest_sold_date = filtered_cars[0]["sold_date"] if filtered_cars else "-"

                result = {
                    "has_data": True,
                    "carid": carid,
                    "total_sold_count": total_sold_count or len(parsed_cars),
                    "matched_count": len(filtered_cars),
                    "is_year_filtered": is_year_filtered,
                    "target_year": ty_2d if is_year_filtered else "",
                    "count_7d": count_7d,
                    "count_30d": count_30d,
                    "daily_rate": daily_rate,
                    "avg_mileage": avg_mileage,
                    "velocity_grade": velocity_grade,
                    "velocity_badge": velocity_badge,
                    "velocity_color": velocity_color,
                    "latest_sold_date": latest_sold_date,
                    "cars_sample": filtered_cars[:35],
                    "all_cars_sample": parsed_cars[:35]
                }

                Scraper._sold_out_global_cache[cache_k] = result
                if hasattr(st, "session_state"):
                    st.session_state.sold_out_cars_cache[cache_k] = result
                return result

            except Exception as e:
                Scraper._sold_out_failed_cache[carid] = (now_ts, {"has_data": False, "msg": f"에러: {e}"})
                continue

        return {"has_data": False, "msg": "조회 가능한 팔린매물 데이터 없음"}

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

        # 1. 타겟 연식(target_year) 매물 우선 탐색 (타 연식으로 인한 기준가 왜곡 원천 차단)
        t_yr_norm = ""
        if target_year:
            m_yr = re.search(r'(\d{2,4})', str(target_year))
            if m_yr:
                t_yr_norm = f"{int(m_yr.group(1)) % 100:02d}"

        # 타겟 연식에 맞는 매물군 분리
        target_year_df = pd.DataFrame()
        if t_yr_norm and '연식' in chart_base.columns:
            target_year_df = chart_base[
                chart_base['연식'].astype(str).str.strip().apply(
                    lambda x: bool(re.match(rf'^\s*{t_yr_norm}', x))
                )
            ]

        # 벤치마크 대상 매물 DF 결정 (타겟 연식 매물 우선)
        cand_df = target_year_df if not target_year_df.empty else chart_base

        # 무사고 매물 우선 정렬
        is_no_acc = cand_df['사고유무'].astype(str).str.contains('무사고') if '사고유무' in cand_df.columns else pd.Series(False, index=cand_df.index)
        sorted_cand_df = pd.concat([cand_df[is_no_acc], cand_df[~is_no_acc]]) if is_no_acc.any() else cand_df

        target_rgsids = []
        if '_carid' in sorted_cand_df.columns:
            for cid in sorted_cand_df['_carid'].dropna().unique():
                c_str = str(cid).strip()
                if c_str and c_str.isdigit() and len(c_str) >= 6:
                    target_rgsids.append(c_str)

        if not target_rgsids and '링크' in sorted_cand_df.columns:
            for link in sorted_cand_df['링크'].dropna().unique():
                m = re.search(r'carid=(\d+)', str(link))
                if m:
                    target_rgsids.append(m.group(1))

        # 전체 매물에서 fallback
        if not target_rgsids:
            if '_carid' in chart_base.columns:
                for cid in chart_base['_carid'].dropna().unique():
                    c_str = str(cid).strip()
                    if c_str and c_str.isdigit() and len(c_str) >= 6:
                        target_rgsids.append(c_str)

        if not target_rgsids:
            return {"has_data": False, "msg": "동급 매물 ID 없음"}

        # 💡 [실매물 코호트 통계] 현재 화면의 동급(타겟 연식) 매물 실제 통계 선계산
        real_prices = pd.to_numeric(cand_df['판매가'], errors='coerce').dropna()
        real_market_avg = int(real_prices.mean()) if not real_prices.empty else 0

        # 동급 무사고 매물들의 평균가
        is_no_acc_cand = cand_df['사고유무'].astype(str).str.contains('무사고') if '사고유무' in cand_df.columns else pd.Series(False, index=cand_df.index)
        no_acc_cand_prices = pd.to_numeric(cand_df.loc[is_no_acc_cand, '판매가'], errors='coerce').dropna()
        cohort_no_acc_avg = int(no_acc_cand_prices.mean()) if not no_acc_cand_prices.empty else real_market_avg
        sample_count = len(no_acc_cand_prices) if not no_acc_cand_prices.empty else len(real_prices)

        # 2. 대표 매물로 엔카 시세리포트 호출 (이상치 매물 자동 배제)
        benchmark_report = None
        for rid in target_rgsids[:5]:
            rep = Scraper.fetch_price_report(rid)
            if rep.get("has_data") and rep.get("individual_price", 0) > 0:
                rep_ind = rep.get("individual_price", 0)
                # 실매물 평균가가 존재할 때 1.7배 초과 또는 0.4배 미만인 이종 차종 리포트는 오염 배제
                if cohort_no_acc_avg > 0 and (rep_ind > cohort_no_acc_avg * 1.7 or rep_ind < cohort_no_acc_avg * 0.4):
                    continue
                benchmark_report = rep
                break

        # 리포트가 없거나 오염된 경우 실매물 코호트 기준으로 대체 생성
        if not benchmark_report:
            if cohort_no_acc_avg > 0:
                benchmark_report = {
                    "has_data": True,
                    "rgsid": target_rgsids[0] if target_rgsids else "",
                    "min_price": int(cohort_no_acc_avg * 0.94),
                    "individual_price": cohort_no_acc_avg,
                    "max_price": int(cohort_no_acc_avg * 1.06),
                    "std_100_price": cohort_no_acc_avg,
                    "bad_ratio": 0.94,
                    "good_ratio": 1.06,
                    "base_mileage": 100000,
                    "score": 100.0
                }
            else:
                return {"has_data": False, "msg": "엔카 시세리포트 데이터 미제공 차종"}

        # 3. 엔카 표준 100점 기본가 및 상하한 밴드 계수 확보
        std_100_price = benchmark_report.get("std_100_price", 0)
        bad_ratio = benchmark_report.get("bad_ratio", 0.95)
        good_ratio = benchmark_report.get("good_ratio", 1.05)
        rep_min_price = benchmark_report.get("min_price", 0)
        rep_max_price = benchmark_report.get("max_price", 0)

        # 💡 [기준 주행거리(base_mileage)] 엔카 공식 시세리포트 표준 마일리지 최우선 사용
        rep_base_mil = benchmark_report.get("base_mileage", 0)
        if rep_base_mil and rep_base_mil > 10000:
            base_mil = int(rep_base_mil)
        else:
            real_mils = pd.to_numeric(cand_df['주행거리'].astype(str).str.replace(',', '').str.extract(r'(\d+)')[0], errors='coerce').dropna()
            if not real_mils.empty and real_mils.mean() > 10000:
                base_mil = int(real_mils.mean())
            else:
                calc_age = 4
                if t_yr_norm and t_yr_norm.isdigit():
                    yr_val = 2000 + int(t_yr_norm)
                    calc_age = max(1, datetime.now().year - yr_val)
                base_mil = calc_age * 15000

        # 💡 기준가(100점가) 앵커링:
        if cohort_no_acc_avg > 0:
            if std_100_price <= 0 or std_100_price > cohort_no_acc_avg * 1.6 or std_100_price < cohort_no_acc_avg * 0.5:
                std_100_price = cohort_no_acc_avg
            elif sample_count >= 10:
                std_100_price = int(round(cohort_no_acc_avg * 0.6 + std_100_price * 0.4))
            elif sample_count >= 5:
                std_100_price = int(round(cohort_no_acc_avg * 0.4 + std_100_price * 0.6))
            elif sample_count >= 3:
                std_100_price = int(round(cohort_no_acc_avg * 0.2 + std_100_price * 0.8))
        elif std_100_price <= 0:
            std_100_price = real_market_avg

        # 4. 대상 차량 스펙 적용
        effective_mil = target_mil if target_mil > 0 else base_mil
        mil_diff = base_mil - effective_mil  # 양수면 동급 평균보다 적게 탐 (가산점)

        # 1만km당 감가율 정규화 (2000만원대 기준 1만km당 약 25~30만원 수준)
        if std_100_price >= 2000:
            pt_per_10k = 1.3
        elif std_100_price >= 1200:
            pt_per_10k = 1.5
        else:
            pt_per_10k = 1.8

        mil_score_delta = (mil_diff / 10000.0) * pt_per_10k
        # 과도한 주행거리 점수 폭등/폭락 방지 (최대 ±8.0점 이내)
        mil_score_delta = max(-8.0, min(8.0, mil_score_delta))

        # (2) 사고 감점
        acc_score_delta = 0.0
        acc_str = str(target_accident).strip()
        if "사고" in acc_str and "무사고" not in acc_str:
            acc_score_delta = -7.0
        elif "단순" in acc_str or "교환" in acc_str:
            acc_score_delta = -3.0

        # (3) 가치평가 점수 산출
        calc_score = round(100.0 + mil_score_delta + acc_score_delta, 1)

        # (4) 대상 차량의 엔카 개별 기준가 산출 (초과 옵션 가치는 시장 매물 감안하여 현실적 순증분 반영)
        if target_opt_adj > 0:
            real_opt_adj = min(40, int(round(target_opt_adj * 0.35)))
        elif target_opt_adj < 0:
            real_opt_adj = max(-40, int(round(target_opt_adj * 0.4)))
        else:
            real_opt_adj = 0

        calc_individual_price = int(round(std_100_price * (calc_score / 100.0))) + real_opt_adj

        # 💡 [이상치 방어 클램프]
        # 표본이 3대 미만일 때는 단일 매물의 호가로 강제 클램프(Hard clamp)하지 않음!
        # (예: 시장에 12.7만km 매물 1대(1,080만)만 있을 때, 10.6만km 무사고 차량이 1,080만에 묶이는 왜곡 원천 차단)
        # 대신 엔카 공식 시세리포트의 상하한선(min_price, max_price)을 안전 잣대로 활용
        if rep_max_price > 0 and rep_min_price > 0:
            safe_ceiling = int(round(rep_max_price * 1.08))
            safe_floor = int(round(rep_min_price * 0.92))
            calc_individual_price = max(safe_floor, min(safe_ceiling, calc_individual_price))
        elif sample_count >= 5:
            market_max = int(real_prices.max())
            market_min = int(real_prices.min())
            if calc_score > 100 and calc_individual_price > market_max:
                calc_individual_price = min(calc_individual_price, int(round(market_max * 1.10)))
            elif calc_score < 100 and calc_individual_price < market_min:
                calc_individual_price = max(calc_individual_price, int(round(market_min * 0.90)))

        # (5) 엔카 적정 시세 밴드 (minPrice ~ maxPrice)
        safe_bad_ratio = max(0.94, min(0.97, bad_ratio)) if bad_ratio > 0 else 0.95
        safe_good_ratio = min(1.06, max(1.03, good_ratio)) if good_ratio > 0 else 1.05

        calc_min_price = int(round(calc_individual_price * safe_bad_ratio))
        calc_max_price = int(round(calc_individual_price * safe_good_ratio))

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

