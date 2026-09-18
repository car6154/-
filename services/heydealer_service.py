# services/heydealer_service.py
import re
import pandas as pd

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

            rows.append({
                "차량명": car_name,
                "모델명": d.get("model_part_name") or "",
                "세부모델": d.get("grade_part_name") or "",
                "연식": f"{y_num}년" if y_num else "-",
                "주행거리": f"{int(mileage):,} km" if mileage else "-",
                "낙찰가": price_display,
                "사고유무": f"{acc_icon} {base_acc}",
                "사고상세": repair_str,
                "옵션": " / ".join(options[:4]) if options else "-",
                "링크": link,
                "판매가_num": p_val,
                "주행거리_num": mileage or 0,
                "연식_num": y_num,
                "옵션리스트": options,
                "수출여부": is_export,
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

            rows.append({
                "차량명": car_name,
                "모델명": item.get('model_name') or "",
                "세부모델": item.get('grade_name') or "",
                "연식": f"{y_num}년" if y_num else "-",
                "주행거리": f"{int(mileage):,} km" if mileage else "-",
                "낙찰가": price_display,
                "사고유무": "🔴 사고" if has_accident else "🟢 무사고",
                "사고상세": "",
                "옵션": " / ".join(options[:4]) if options else "-",
                "링크": link,
                "판매가_num": p_val,
                "주행거리_num": mileage or 0,
                "연식_num": y_num,
                "옵션리스트": options,
                "수출여부": is_export,
            })
    return pd.DataFrame(rows)
