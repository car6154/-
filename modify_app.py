import re
import json

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Parse target options after heydealer_json_str is fetched (around line 1450)
target_options_code = """                heydealer_json_str = result['detail']
                if not heydealer_json_str.strip() or not heydealer_json_str.strip().startswith('{'):
                    raise Exception(f'잘못된 응답입니다(로그인 만료 또는 차단 의심). 응답: {heydealer_json_str[:100]}')
                
                hd_detail_tmp = json.loads(heydealer_json_str).get('detail', {})
                advanced_options_tmp = hd_detail_tmp.get('advanced_options') or []
                target_options = [
                    opt.get('name', '') for opt in advanced_options_tmp 
                    if isinstance(opt, dict) and opt.get('choice') == 'loaded'
                ]
                
                auction_repairs_json = result.get('auction_repairs') or ""
"""
content = re.sub(r'                heydealer_json_str = result\[\'detail\'\]\n                if not heydealer_json_str.strip\(\) or not heydealer_json_str.strip\(\).startswith\(\'\{\'\):\n                    raise Exception.*?auction_repairs_json = result.get\(\'auction_repairs\'\) or ""\n', target_options_code, content, flags=re.DOTALL)

# 2. Encar logic (around 1508)
encar_sunroof_logic = """                    # 옵션 (간단히 선루프 유무)
                    has_sunroof = df_temp['추가옵션'].astype(str).str.contains('선루프')
                    sunroof_avg = int(df_temp[has_sunroof]['판매가'].mean()) if has_sunroof.any() else avg_price
                    no_sunroof_avg = int(df_temp[~has_sunroof]['판매가'].mean()) if (~has_sunroof).any() else avg_price
                    sunroof_gap = sunroof_avg - no_sunroof_avg
                    
                    market_data_str = f"엔카 동급 매물 평균가: {avg_price}만원\\n무사고 평균가: {no_acc_avg}만원 / 유사고 평균가: {acc_avg}만원 (사고감가 차이: {acc_gap}만원)\\n선루프 장착 매물 평균가: {sunroof_avg}만원 / 미장착 평균가: {no_sunroof_avg}만원 (옵션 차이: {sunroof_gap}만원)\\n"
"""
encar_target_opt_logic = """                    # 타겟 차량 옵션 유무별 평균
                    if target_options:
                        has_target_opt = df_temp['추가옵션'].apply(lambda x: any(opt in str(x) for opt in target_options))
                        target_opt_avg = int(df_temp[has_target_opt]['판매가'].mean()) if has_target_opt.any() else avg_price
                        no_target_opt_avg = int(df_temp[~has_target_opt]['판매가'].mean()) if (~has_target_opt).any() else avg_price
                    else:
                        target_opt_avg = avg_price
                        no_target_opt_avg = avg_price
                    opt_gap = target_opt_avg - no_target_opt_avg
                    
                    market_data_str = f"엔카 동급 매물 평균가: {avg_price}만원\\n무사고 평균가: {no_acc_avg}만원 / 유사고 평균가: {acc_avg}만원 (사고감가 차이: {acc_gap}만원)\\n유사 옵션 포함 평균가: {target_opt_avg}만원 / 미포함 평균가: {no_target_opt_avg}만원 (옵션 차이: {opt_gap}만원)\\n"
"""
content = content.replace(encar_sunroof_logic, encar_target_opt_logic)

# 3. Heydealer init vars
content = content.replace('            hd_sunroof_avg = 0\n            hd_no_sunroof_avg = 0', '            hd_target_opt_avg = 0\n            hd_no_target_opt_avg = 0')

# 4. Heydealer logic
hd_sunroof_logic = """                            # 3. 선루프 유무 차이
                            has_sunroof = base_df['옵션리스트'].apply(lambda x: any('선루프' in opt or '썬루프' in opt for opt in x))
                            hd_sunroof_avg = int(base_df[has_sunroof]['판매가_num'].mean()) if has_sunroof.any() else hd_market_avg
                            hd_no_sunroof_avg = int(base_df[~has_sunroof]['판매가_num'].mean()) if (~has_sunroof).any() else hd_market_avg"""
hd_target_opt_logic = """                            # 3. 타겟 차량 추가옵션 포함 여부 차이
                            if target_options:
                                has_target_opt = base_df['옵션리스트'].apply(lambda opts: any(opt in target_options for opt in opts))
                                hd_target_opt_avg = int(base_df[has_target_opt]['판매가_num'].mean()) if has_target_opt.any() else hd_market_avg
                                hd_no_target_opt_avg = int(base_df[~has_target_opt]['판매가_num'].mean()) if (~has_target_opt).any() else hd_market_avg
                            else:
                                hd_target_opt_avg = hd_market_avg
                                hd_no_target_opt_avg = hd_market_avg"""
content = content.replace(hd_sunroof_logic, hd_target_opt_logic)

# 5. Extract variables mapping
extract_old = """            encar_sunroof_avg = 0
            encar_no_sunroof_avg = 0
            ai_prompt = extract_car_data_for_ai(
                heydealer_json_str, 
                market_avg=avg_price if 'avg_price' in locals() else (encar_avg_price if 'encar_avg_price' in locals() else hd_market_avg),
                no_accident_avg=no_acc_avg if 'no_acc_avg' in locals() else (encar_no_acc_avg if 'encar_no_acc_avg' in locals() else hd_no_acc_avg),
                accident_avg=acc_avg if 'acc_avg' in locals() else (encar_acc_avg if 'encar_acc_avg' in locals() else hd_acc_avg),
                sunroof_avg=sunroof_avg if 'sunroof_avg' in locals() else (encar_sunroof_avg if 'encar_sunroof_avg' in locals() else hd_sunroof_avg),
                no_sunroof_avg=no_sunroof_avg if 'no_sunroof_avg' in locals() else (encar_no_sunroof_avg if 'encar_no_sunroof_avg' in locals() else hd_no_sunroof_avg),"""
extract_new = """            encar_target_opt_avg = 0
            encar_no_target_opt_avg = 0
            ai_prompt = extract_car_data_for_ai(
                heydealer_json_str, 
                market_avg=avg_price if 'avg_price' in locals() else (encar_avg_price if 'encar_avg_price' in locals() else hd_market_avg),
                no_accident_avg=no_acc_avg if 'no_acc_avg' in locals() else (encar_no_acc_avg if 'encar_no_acc_avg' in locals() else hd_no_acc_avg),
                accident_avg=acc_avg if 'acc_avg' in locals() else (encar_acc_avg if 'encar_acc_avg' in locals() else hd_acc_avg),
                target_opt_avg=target_opt_avg if 'target_opt_avg' in locals() else (encar_target_opt_avg if 'encar_target_opt_avg' in locals() else hd_target_opt_avg),
                no_target_opt_avg=no_target_opt_avg if 'no_target_opt_avg' in locals() else (encar_no_target_opt_avg if 'encar_no_target_opt_avg' in locals() else hd_no_target_opt_avg),"""
content = content.replace(extract_old, extract_new)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
