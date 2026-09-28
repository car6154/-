# services/heydealer_service.py
import re
from datetime import datetime
import pandas as pd

def format_relative_date(date_val):
    """헤이딜러 경매일시를 '4일 전', '1주 전', '오늘', '1달 전' 등의 상대 시간으로 변환"""
    if not date_val or str(date_val).strip() in ['', 'None', 'nan', '-', 'null']:
        return "-"
    try:
        s = str(date_val).strip()
        time_keywords = [
            '일 전', '일전', '주 전', '주전', '달 전', '달전', '개월 전', '개월전', '년 전', '년전',
            '시간 전', '시간전', '분 전', '분전', '오늘', '어제', '방금', '진행중'
        ]
        # 이미 상대시간 표기인 경우 (예: "4일 전", "1주 전", "1일 전 ∙ 20명 입찰", "오늘")
        if any(x in s for x in time_keywords):
            m_week = re.search(r'(\d+)\s*주\s*전', s)
            if m_week:
                return f"{m_week.group(1)}주 전"
            m_day = re.search(r'(\d+)\s*일\s*전', s)
            if m_day:
                return f"{m_day.group(1)}일 전"
            m_month = re.search(r'(\d+)\s*(?:달|개월)\s*전', s)
            if m_month:
                return f"{m_month.group(1)}달 전"
            m_year = re.search(r'(\d+)\s*년\s*전', s)
            if m_year:
                return f"{m_year.group(1)}년 전"
            for w in ['오늘', '어제', '방금', '진행중']:
                if w in s:
                    return w
            m_hour = re.search(r'(\d+)\s*시간\s*전', s)
            if m_hour:
                return "오늘"
            return s

        dt = None
        # 1. 숫자 타임스탬프 (초 또는 밀리초)
        if isinstance(date_val, (int, float)) or (isinstance(date_val, str) and date_val.isdigit() and len(date_val) in (10, 13)):
            ts = float(date_val)
            if ts > 1e11:  # milliseconds
                ts /= 1000.0
            dt = datetime.fromtimestamp(ts)
        else:
            # 2. ISO / 일반 날짜 정규식 (YYYY-MM-DD or YY-MM-DD or YYYY.MM.DD or YYYY/MM/DD)
            m = re.search(r'(\d{2,4})[./-](\d{1,2})[./-](\d{1,2})', s)
            if m:
                y, mth, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if y < 100:
                    y += 2000
                dt = datetime(y, mth, d)
            else:
                # 3. 8자리 연속 숫자 (YYYYMMDD)
                m8 = re.search(r'(\d{4})(\d{2})(\d{2})', s)
                if m8:
                    dt = datetime(int(m8.group(1)), int(m8.group(2)), int(m8.group(3)))

        if dt:
            now = datetime.now()
            today = datetime(now.year, now.month, now.day)
            target_day = datetime(dt.year, dt.month, dt.day)
            diff = (today - target_day).days
            if diff == 0:
                return "오늘"
            elif diff == 1:
                return "1일 전"
            elif 2 <= diff < 7:
                return f"{diff}일 전"
            elif 7 <= diff < 30:
                return f"{diff // 7}주 전"
            elif 30 <= diff < 365:
                return f"{diff // 30}달 전"
            elif diff >= 365:
                return f"{diff // 365}년 전"
            elif diff < 0:
                return "진행중"
    except Exception:
        pass
    return "-"

def _extract_date_val(item, auc=None, d=None, bid=None):
    # 1. tags 확인 (오직 시간 관련 키워드가 있는 경우만 추출)
    time_keywords = [
        '일 전', '일전', '주 전', '주전', '달 전', '달전', '개월 전', '개월전', '년 전', '년전',
        '시간 전', '시간전', '오늘', '어제', '방금', '진행중'
    ]
    for container in [auc, item, d, bid]:
        if isinstance(container, dict):
            tags = container.get('tags', []) or []
            for t in tags:
                txt = ''
                if isinstance(t, dict):
                    txt = t.get('short_text') or t.get('text') or t.get('name') or t.get('label') or ''
                elif isinstance(t, str):
                    txt = t
                txt = str(txt).strip()
                if txt and any(k in txt for k in time_keywords):
                    res = format_relative_date(txt)
                    if res != "-":
                        return res

    # 2. 직접 날짜/시간 필드 검사 (종료/낙찰시점 -> 생성/등록시점)
    date_keys_priority = [
        'ended_at_display', 'end_at_display', 'auction_end_at_display', 'auction_ended_at_display',
        'selected_at_display', 'closed_at_display', 'approved_at_display',
        'ended_at', 'end_at', 'auction_end_at', 'auction_ended_at',
        'selected_at', 'closed_at', 'sold_at', 'finished_at', 'completed_at',
        'deal_date', 'auction_date', 'date', 'bidded_at', 'approved_at',
        'created_at', 'registered_at', 'updated_at', 'time', 'timestamp'
    ]
    
    for container in [auc, item, bid, d]:
        if isinstance(container, dict):
            for k in date_keys_priority:
                v = container.get(k)
                if v is not None and str(v).strip() not in ['', 'None', 'nan', '-', 'null']:
                    res = format_relative_date(v)
                    if res != "-":
                        return res

    # 3. auction_histories 확인 ([{'date': '26-09-04', ...}])
    for container in [d, item, auc]:
        if isinstance(container, dict):
            ah_list = container.get('auction_histories', []) or []
            if isinstance(ah_list, list) and ah_list:
                for ah in ah_list:
                    if isinstance(ah, dict):
                        for k in ['date', 'ended_at', 'end_at', 'created_at']:
                            if ah.get(k):
                                res = format_relative_date(ah.get(k))
                                if res != "-":
                                    return res

    # 4. 텍스트 필드 (bidding_help_info, comment, description 등)에서 상대시간/날짜 정규식 추출
    for container in [d, auc, item]:
        if isinstance(container, dict):
            for tk in ['bidding_help_info', 'bidding_extra_info', 'comment', 'comment_html', 'description', 'caution_text']:
                text_val = container.get(tk)
                if text_val and isinstance(text_val, str):
                    m_rel = re.search(r'(\d+)\s*일\s*전', text_val)
                    if m_rel:
                        return f"{m_rel.group(1)}일 전"
                    m_date = re.search(r'(?:종료|일자|일시|낙찰)?\s*[:\s]*(\d{2,4}[.-]\d{1,2}[.-]\d{1,2})', text_val)
                    if m_date:
                        res = format_relative_date(m_date.group(1))
                        if res != "-":
                            return res

    # 5. 재귀/심층 검색: dict 전체에서 날짜처럼 생긴 필드 탐색
    if isinstance(item, dict):
        for k, v in item.items():
            if isinstance(v, dict):
                for sub_k in date_keys_priority:
                    if v.get(sub_k):
                        res = format_relative_date(v.get(sub_k))
                        if res != "-":
                            return res
            elif isinstance(v, str) and len(v) >= 6:
                if any(x in k.lower() for x in ['date', 'ended', 'end', 'at', 'time']):
                    res = format_relative_date(v)
                    if res != "-":
                        return res

    return "-"

def parse_heydealer_comps(json_data):
    rows = []
    items = []
    if isinstance(json_data, dict) and 'results' in json_data:
        items = json_data['results']
    elif isinstance(json_data, list):
        items = json_data
        
    HEYDEALER_PART_MAP = {
        'bumper_front': '앞범퍼', 'bumper_rear': '뒤범퍼',
        'fender_front_driver': '앞휀더(운전석)', 'fender_front_passenger': '앞휀더(조수석)',
        'fender_rear_driver': '뒤휀더(운전석)', 'fender_rear_passenger': '뒤휀더(조수석)',
        'door_front_driver': '앞도어(운전석)', 'door_front_passenger': '앞도어(조수석)',
        'door_rear_driver': '뒤도어(운전석)', 'door_rear_passenger': '뒤도어(조수석)',
        'hood': '후드(보닛)', 'trunk_lid': '트렁크리드', 'roof': '루프',
        'radiator_support': '라디에이터 서포트', 'panel_front': '프론트패널', 'panel_rear': '리어패널',
        'front_panel': '프론트패널', 'rear_panel': '리어패널', 'trunk_floor': '트렁크플로어',
        'side_member': '사이드멤버', 'cross_member': '크로스멤버', 'inside_panel': '인사이드패널',
        'inside_panel_front_driver': '인사이드패널(앞/운전석)', 'inside_panel_front_passenger': '인사이드패널(앞/조수석)',
        'inside_panel_rear_driver': '인사이드패널(뒤/운전석)', 'inside_panel_rear_passenger': '인사이드패널(뒤/조수석)',
        'side_member_front_driver': '사이드멤버(앞/운전석)', 'side_member_front_passenger': '사이드멤버(앞/조수석)',
        'side_member_rear_driver': '사이드멤버(뒤/운전석)', 'side_member_rear_passenger': '사이드멤버(뒤/조수석)',
        'pillar_a': 'A필러', 'pillar_b': 'B필러', 'pillar_c': 'C필러',
        'pillar_a_driver': 'A필러(운전석)', 'pillar_a_passenger': 'A필러(조수석)',
        'pillar_b_driver': 'B필러(운전석)', 'pillar_b_passenger': 'B필러(조수석)',
        'pillar_c_driver': 'C필러(운전석)', 'pillar_c_passenger': 'C필러(조수석)',
        'quarter_panel_driver': '쿼터패널(운전석)', 'quarter_panel_passenger': '쿼터패널(조수석)',
        'wheel_house_front_driver': '휠하우스(앞/운전석)', 'wheel_house_front_passenger': '휠하우스(앞/조수석)',
        'wheel_house_rear_driver': '휠하우스(뒤/운전석)', 'wheel_house_rear_passenger': '휠하우스(뒤/조수석)',
    }
    HEYDEALER_REPAIR_MAP = {
        'exchange': '교환', 'replace': '교환', 'weld': '판금/용접', 'sheet_metal': '판금'
    }

    def format_hd_part(raw_p):
        if not raw_p: return '기타부위'
        p_str = str(raw_p).strip()
        if p_str in HEYDEALER_PART_MAP:
            return HEYDEALER_PART_MAP[p_str]
        
        # 언더스코어로 조합된 영문 부품명 스마트 변환
        tokens = p_str.split('_')
        pos_dict = {'front': '앞', 'rear': '뒤', 'driver': '운전석', 'passenger': '조수석', 'left': '좌', 'right': '우'}
        name_dict = {
            'bumper': '범퍼', 'fender': '휀더', 'door': '도어', 'panel': '패널',
            'member': '멤버', 'hood': '후드(보닛)', 'lid': '리드', 'trunk': '트렁크',
            'roof': '루프', 'inside': '인사이드', 'floor': '플로어', 'pillar': '필러',
            'quarter': '쿼터패널', 'radiator': '라디에이터', 'support': '서포트', 'wheel': '휠', 'house': '하우스'
        }
        res_tokens = []
        for t in tokens:
            t_low = t.lower()
            res_tokens.append(pos_dict.get(t_low, name_dict.get(t_low, t)))
        return ''.join(res_tokens) if all(k in list(pos_dict.values()) + list(name_dict.values()) for k in res_tokens) else ' '.join(res_tokens)

    for item in items:
        # 경매 내역 구조
        if "detail" in item and "auction" in item:
            d = item.get("detail", {})
            auc = item.get("auction", {}) or {}
            bid = auc.get("highest_bid") or {}
            price = bid.get("price")
            mileage = d.get("mileage")
            year = d.get("year", 0)
            
            repairs = d.get("accident_repairs", []) or []
            r_descs = []
            is_major = False
            for rep in repairs:
                p = rep.get('part') or rep.get('part_name') or ''
                t = rep.get('repair') or rep.get('type_name') or ''
                p_kr = format_hd_part(p)
                t_kr = HEYDEALER_REPAIR_MAP.get(t, t)
                if any(x in str(p).lower() for x in ['fender_rear', 'roof', 'pillar', 'panel', 'floor', 'member', 'quarter']):
                    is_major = True
                r_descs.append(f"{p_kr} ({t_kr})")
            
            repair_str = ", ".join(r_descs)
            cnt = len(repairs)
            ch = d.get('carhistory', {}) or {}
            oc = ch.get('owner_changed_count') if isinstance(ch, dict) else None

            # 헤이딜러 실제 태그 (예: ['완무 (보험0건)', '1인소유'], ['단순 (1)', '1인소유'], ['유사고', '대여'])
            tags = auc.get('tags', []) or []
            tag_texts = [t.get('short_text', '').strip() for t in tags if isinstance(t, dict) and t.get('short_text')]
            tag_texts = [t for t in tag_texts if t and t not in ['재경매', '연장']]

            if tag_texts:
                base_acc = " ".join(tag_texts)
                if any(k in base_acc for k in ['유사고', '사고']):
                    acc_icon = "🔴"
                elif any(k in base_acc for k in ['단순', '판금']):
                    acc_icon = "🟡"
                else:
                    acc_icon = "🟢"
            else:
                if cnt == 0:
                    base_acc = "무사고"
                    acc_icon = "🟢"
                elif is_major:
                    base_acc = f"사고 ({cnt})"
                    acc_icon = "🔴"
                else:
                    base_acc = f"단순 ({cnt})"
                    acc_icon = "🟡"
                if oc == 0:
                    base_acc += " 1인소유"
                
            car_spec = d.get("car_spec", {}) or {}
            spec_desc = car_spec.get("description", "")
            car_name = d.get("grade_part_name") or d.get("full_name") or "헤이딜러 매물"
            car_id = item.get("car_id") or d.get("id") or ""
            link = f"https://dealer.heydealer.com/cars/{car_id}" if car_id else ""
            options = []
            for line in spec_desc.split('\n'):
                m = re.search(r'^\d+\)\s*(.*?)(?:\s*\(|$)', line.strip())
                if m:
                    options.append(m.group(1).strip())
            
            p_val = price // 10000 if isinstance(price, (int, float)) and price >= 10000 else price
            try: y_num = int(re.search(r'\d{4}', str(year)).group(0)) if re.search(r'\d{4}', str(year)) else 0
            except: y_num = 0

            # 🚢 수출 딜러 낙찰 차량 확인 (헤이딜러 실제 필드: is_export_dealer == True)
            is_export = False
            if isinstance(bid, dict) and bid.get("is_export_dealer") is True:
                is_export = True
            elif isinstance(auc, dict) and auc.get("is_export") is True:
                is_export = True
            elif any("수출" in str(t.get("short_text") or t.get("text") or "") for t in (tags or []) if isinstance(t, dict)):
                is_export = True
            elif any("수출" in str(t) for t in (tags or []) if isinstance(t, str)):
                is_export = True

            price_display = f"{int(p_val):,} 만원" if p_val else "-"
            if is_export and price_display != "-":
                price_display = f"🚢수출 {price_display}"

            # ⏱️ 낙찰일시 및 'X일 전' 상대시간 산출
            rel_date = _extract_date_val(item, auc, d, bid)
            date_raw = (
                auc.get("ended_at_display") or auc.get("ended_at") or auc.get("end_at") or
                auc.get("selected_at") or auc.get("approved_at") or
                item.get("ended_at_display") or item.get("ended_at") or item.get("end_at") or
                item.get("created_at") or item.get("date") or ""
            )

            rows.append({
                "차량명": car_name,
                "모델명": d.get("model_part_name") or "",
                "세부모델": d.get("grade_part_name") or "",
                "연식": f"{y_num}년" if y_num else "-",
                "주행거리": f"{int(mileage):,} km" if mileage else "-",
                "낙찰가": price_display,
                "낙찰일": rel_date,
                "사고유무": f"{acc_icon} {base_acc}",
                "사고상세": repair_str,
                "옵션": " / ".join(options[:4]) if options else "-",
                "링크": link,
                "판매가_num": p_val,
                "주행거리_num": mileage or 0,
                "연식_num": y_num,
                "옵션리스트": options,
                "수출여부": is_export,
                "낙찰일시": date_raw or rel_date,
            })
        # 일반 시세 구조
        else:
            price = item.get('price')
            mileage = item.get('mileage')
            year = item.get('year', 0)
            if price is None or mileage is None:
                continue
            is_acc = item.get('is_accident')
            if is_acc is not None:
                has_accident = is_acc
            else:
                has_accident = (item.get('accident', '') == '사고')
            opts = item.get('options', item.get('tags', []))
            options = [o.strip() for o in opts.split(',')] if isinstance(opts, str) else opts
            car_name = item.get('model_name') or item.get('full_name') or "헤이딜러 매물"
            car_id = item.get('car_id', '')
            link = f"https://dealer.heydealer.com/cars/{car_id}" if car_id else ""
            
            p_val = price // 10000 if isinstance(price, (int, float)) and price >= 10000 else price
            try: y_num = int(re.search(r'\d{4}', str(year)).group(0)) if re.search(r'\d{4}', str(year)) else 0
            except: y_num = 0

            is_export = bool(item.get('is_export_dealer') is True or item.get('is_export') is True or '수출' in str(opts))
            price_display = f"{int(p_val):,} 만원" if p_val else "-"
            if is_export and price_display != "-":
                price_display = f"🚢수출 {price_display}"

            rel_date = _extract_date_val(item)
            date_raw = item.get("ended_at") or item.get("end_at") or item.get("date") or item.get("created_at") or item.get("selected_at") or ""

            rows.append({
                "차량명": car_name,
                "모델명": item.get('model_name') or "",
                "세부모델": item.get('grade_name') or "",
                "연식": f"{y_num}년" if y_num else "-",
                "주행거리": f"{int(mileage):,} km" if mileage else "-",
                "낙찰가": price_display,
                "낙찰일": rel_date,
                "사고유무": "🔴 사고" if has_accident else "🟢 무사고",
                "사고상세": "",
                "옵션": " / ".join(options[:4]) if options else "-",
                "링크": link,
                "판매가_num": p_val,
                "주행거리_num": mileage or 0,
                "연식_num": y_num,
                "옵션리스트": options,
                "수출여부": is_export,
                "낙찰일시": date_raw or rel_date,
            })
    return pd.DataFrame(rows)
