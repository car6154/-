# refactor_app.py
import re
import os

with open(r"C:\Users\car61\Desktop\제이프로젝트\app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update parse_heydealer_comps to produce rich and robust dataframe
new_parse_hd = '''def parse_heydealer_comps(json_data):
    import pandas as pd
    rows = []
    items = []
    if isinstance(json_data, dict) and 'results' in json_data:
        items = json_data['results']
    elif isinstance(json_data, list):
        items = json_data
        
    for item in items:
        # 경매 내역 구조
        if "detail" in item and "auction" in item:
            d = item.get("detail", {})
            bid = item.get("auction", {}).get("highest_bid") or {}
            price = bid.get("price")
            mileage = d.get("mileage")
            year = d.get("year", 0)
            has_accident = len(d.get("accident_repairs", [])) > 0
            car_spec = d.get("car_spec", {}) or {}
            spec_desc = car_spec.get("description", "")
            car_name = d.get("grade_part_name") or d.get("full_name") or "헤이딜러 매물"
            car_id = item.get("car_id") or d.get("id") or ""
            link = f"https://dealer.heydealer.com/cars/{car_id}" if car_id else ""
            import re
            options = []
            for line in spec_desc.split('\\n'):
                m = re.search(r'^\\d+\\)\\s*(.*?)(?:\\s*\\(|$)', line.strip())
                if m:
                    options.append(m.group(1).strip())
            
            p_val = price // 10000 if isinstance(price, (int, float)) and price >= 10000 else price
            try: y_num = int(re.search(r'\\d{4}', str(year)).group(0)) if re.search(r'\\d{4}', str(year)) else 0
            except: y_num = 0

            rows.append({
                "차량명": car_name,
                "연식": f"{y_num}년" if y_num else "-",
                "주행거리": f"{int(mileage):,} km" if mileage else "-",
                "낙찰가": f"{int(p_val):,} 만원" if p_val else "-",
                "사고유무": "🔴 사고/단순" if has_accident else "🟢 완전무사고",
                "옵션": " / ".join(options[:4]) if options else "-",
                "링크": link,
                "판매가_num": p_val,
                "주행거리_num": mileage or 0,
                "연식_num": y_num,
                "옵션리스트": options,
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
            try: y_num = int(re.search(r'\\d{4}', str(year)).group(0)) if re.search(r'\\d{4}', str(year)) else 0
            except: y_num = 0

            rows.append({
                "차량명": car_name,
                "연식": f"{y_num}년" if y_num else "-",
                "주행거리": f"{int(mileage):,} km" if mileage else "-",
                "낙찰가": f"{int(p_val):,} 만원" if p_val else "-",
                "사고유무": "🔴 사고/단순" if has_accident else "🟢 완전무사고",
                "옵션": " / ".join(options[:4]) if options else "-",
                "링크": link,
                "판매가_num": p_val,
                "주행거리_num": mileage or 0,
                "연식_num": y_num,
                "옵션리스트": options,
            })
    return pd.DataFrame(rows)'''

# Replace old parse_heydealer_comps safely
content = re.sub(r'def parse_heydealer_comps\(json_data\):.*?return pd\.DataFrame\(rows\)', lambda m: new_parse_hd, content, flags=re.DOTALL)

with open(r"C:\Users\car61\Desktop\제이프로젝트\app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated parse_heydealer_comps successfully")
