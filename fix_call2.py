import traceback
import re

try:
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the extract_car_data_for_ai call and replace it
    target_pattern = r"ai_prompt = extract_car_data_for_ai\([\s\S]*?auction_repairs_json=auction_repairs_json\n\s*\)"
    
    replacement = """ai_prompt = extract_car_data_for_ai(
                heydealer_json_str, 
                market_avg=avg_price if 'avg_price' in locals() else (encar_avg_price if 'encar_avg_price' in locals() else hd_market_avg),
                no_accident_avg=no_acc_avg if 'no_acc_avg' in locals() else (encar_no_acc_avg if 'encar_no_acc_avg' in locals() else hd_no_acc_avg),
                accident_avg=acc_avg if 'acc_avg' in locals() else (encar_acc_avg if 'encar_acc_avg' in locals() else hd_acc_avg),
                sunroof_avg=sunroof_avg if 'sunroof_avg' in locals() else (encar_sunroof_avg if 'encar_sunroof_avg' in locals() else hd_sunroof_avg),
                no_sunroof_avg=no_sunroof_avg if 'no_sunroof_avg' in locals() else (encar_no_sunroof_avg if 'encar_no_sunroof_avg' in locals() else hd_no_sunroof_avg),
                prev_year_avg=prev_year_avg if 'prev_year_avg' in locals() else 0,
                next_year_avg=next_year_avg if 'next_year_avg' in locals() else 0,
                auction_repairs_json=auction_repairs_json
            )"""

    if re.search(target_pattern, content):
        new_content = re.sub(target_pattern, replacement, content)
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('Replaced successfully')
    else:
        print('Target not found')
except Exception as e:
    traceback.print_exc()
