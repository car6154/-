import traceback
import re

try:
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the extract_car_data_for_ai call and replace it
    target_pattern = r"ai_prompt = extract_car_data_for_ai\([\s\S]*?auction_repairs_json=auction_repairs_json\n\s*\)"
    
    replacement = """ai_prompt = extract_car_data_for_ai(
                heydealer_json_str, 
                market_avg=hd_market_avg,
                no_accident_avg=hd_no_acc_avg,
                accident_avg=hd_acc_avg,
                sunroof_avg=hd_sunroof_avg,
                no_sunroof_avg=hd_no_sunroof_avg,
                prev_year_avg=prev_year_avg,
                next_year_avg=next_year_avg,
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
