import re
import json

# ==========================================
# 1. Update heydealer_ai.py
# ==========================================
with open('heydealer_ai.py', 'r', encoding='utf-8') as f:
    ai_content = f.read()

# Replace the signature and variables
old_sig = """def extract_car_data_for_ai(json_payload, market_avg=0, no_accident_avg=0, accident_avg=0, target_opt_avg=0, no_target_opt_avg=0, prev_year_avg=0, next_year_avg=0, auction_repairs_json=""):"""
new_sig = """def extract_car_data_for_ai(json_payload, retail_avg=0, retail_no_acc_avg=0, retail_acc_avg=0, retail_opt_avg=0, retail_no_opt_avg=0, wholesale_avg=0, wholesale_no_acc_avg=0, wholesale_acc_avg=0, wholesale_opt_avg=0, wholesale_no_opt_avg=0, prev_year_avg=0, next_year_avg=0, auction_repairs_json=""):"""
ai_content = ai_content.replace(old_sig, new_sig)

# Replace options parsing
old_opt = """    # 3. 추가 옵션 정보 (choice가 'loaded'인 것만)
    advanced_options = detail.get('advanced_options') or []
    options = [
        opt.get('name', '') for opt in advanced_options 
        if isinstance(opt, dict) and opt.get('choice') == 'loaded'
    ]"""
new_opt = """    # 3. 추가 옵션 정보 (car_spec 출고 정보 기준)
    car_spec = detail.get('car_spec') or {}
    spec_desc = car_spec.get('description', '')
    import re
    options = []
    for line in spec_desc.split('\\n'):
        m = re.search(r'^\\d+\\)\\s*(.*?)(?:\\s*\\(|$)', line.strip())
        if m:
            options.append(m.group(1).strip())"""
ai_content = ai_content.replace(old_opt, new_opt)

# Replace prompt structure
old_prompt = """    opt_line = f"- 타겟 차량과 유사한 추가옵션 포함 매물 평균 {target_opt_avg}만원 / 미포함 평균 {no_target_opt_avg}만원\\n" if target_opt_avg != no_target_opt_avg and len(options) > 0 else ""
    
    # 6. AI(LLM)에게 던질 궁극의 프롬프트 동적 조립 (사용자 요청 포맷 적용)
    prompt = f\"\"\"
[타겟 차량]
- {car_name} / {year}년식 / {mileage:,}km
- 옵션: {', '.join(options)}
- 상태: {condition_basic_str} / 평가사 소견: {inspector_comment}

[실시간 엔카 매물 데이터 - 이미 계산된 수치, 재계산 금지]
- 동급 평균가: {market_avg}만원
- 무사고 평균 {no_accident_avg}만원 / 유사고 평균 {accident_avg}만원
{opt_line}- 1년 전후 평균가 차이 
({year}년 시세 기준 {year-1}년 평균 {prev_year_avg}만원 / {year+1}년 평균 {next_year_avg}만원)

[감가 기준표]
- 문콕 3~5만원/개, 판금도색 10~13만원/판(국산)·15~18만원(수입)
- 사고 감가: 위 예상 소매가 기준 외판 3~4%/부위, 골격 5~7%/부위, 범퍼교환 0원

[지시사항]
1. 위 표에서 옵션·사고여부에 맞는 값을 그대로 채택해 '예상 소매가' 확정 (재추정 금지)
2. 이 확정된 소매가를 기준으로 부위별 상품화비·사고감가 내역을 도출하고 매입가를 계산하세요.
- 불필요한 서론/결론(인사말 등)은 모두 생략하고 핵심 견적만 간결하게 출력하세요.
- 소매가 추정 근거 (간단히)
- 매입 마진율 (딜러 통상 마진 반영)
- **최종 매입 제시가** (명확하게 강조)
\"\"\""""

new_prompt = """    retail_opt_line = f"- 옵션 포함 평균 {retail_opt_avg}만원 / 미포함 평균 {retail_no_opt_avg}만원\\n" if retail_opt_avg != retail_no_opt_avg and len(options) > 0 else ""
    wholesale_opt_line = f"- 옵션 포함 평균 {wholesale_opt_avg}만원 / 미포함 평균 {wholesale_no_opt_avg}만원\\n" if wholesale_opt_avg != wholesale_no_opt_avg and len(options) > 0 else ""
    
    # 6. AI(LLM)에게 던질 궁극의 프롬프트 동적 조립 (사용자 요청 포맷 적용)
    prompt = f\"\"\"
[타겟 차량]
- {car_name} / {year}년식 / {mileage:,}km
- 옵션: {', '.join(options)}
- 상태: {condition_basic_str} / 평가사 소견: {inspector_comment}

[실시간 매물 데이터 - 이미 계산된 수치, 재계산 금지]
(1) 예상 소매가 기준 (엔카 판매 데이터)
- 동급 평균: {retail_avg}만원 (무사고 {retail_no_acc_avg}만원 / 유사고 {retail_acc_avg}만원)
{retail_opt_line}
(2) 예상 매입가 기준 (헤이딜러 낙찰 데이터)
- 동급 평균: {wholesale_avg}만원 (무사고 {wholesale_no_acc_avg}만원 / 유사고 {wholesale_acc_avg}만원)
{wholesale_opt_line}- 1년 전후 평균가 차이 
({year}년 시세 기준 {year-1}년 평균 {prev_year_avg}만원 / {year+1}년 평균 {next_year_avg}만원)

[감가 기준표]
- 문콕 3~5만원/개, 판금도색 10~13만원/판(국산)·15~18만원(수입)
- 사고 감가: 위 예상 소매가 기준 외판 3~4%/부위, 골격 5~7%/부위, 범퍼교환 0원

[지시사항]
1. 위 (1)번 엔카 데이터를 바탕으로 타겟 차량의 옵션 및 상태를 고려해 '예상 소매가'를 산출하세요.
2. 위 (2)번 헤이딜러 데이터를 바탕으로 기본 낙찰매입가를 산출하고, 해당 매입가에서 현재 차량의 감가 요인(상품화비, 사고감가 등)을 차감하여 최종 매입가를 도출하세요.
3. 딜러 마진율은 이미 헤이딜러 낙찰 데이터(도매가)에 반영되어 있으므로, **절대로 마진율이나 마진 차감액을 계산하거나 포함하지 마세요.**
- 불필요한 서론/결론(인사말 등)은 모두 생략하고 핵심 견적만 간결하게 출력하세요.
- 예상 소매가 (간단한 산출 근거 포함)
- **최종 매입 제시가** (헤이딜러 기준 매입가에서 상품화 감가 적용 후 최종 금액, 마진 언급 금지)
\"\"\""""
ai_content = ai_content.replace(old_prompt, new_prompt)

with open('heydealer_ai.py', 'w', encoding='utf-8') as f:
    f.write(ai_content)

# ==========================================
# 2. Update app.py
# ==========================================
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

# Update option parsing in app.py
old_app_opt = """                hd_detail_tmp = json.loads(heydealer_json_str).get('detail', {})
                advanced_options_tmp = hd_detail_tmp.get('advanced_options') or []
                target_options = [
                    opt.get('name', '') for opt in advanced_options_tmp 
                    if isinstance(opt, dict) and opt.get('choice') == 'loaded'
                ]"""
new_app_opt = """                hd_detail_tmp = json.loads(heydealer_json_str).get('detail', {})
                car_spec_tmp = hd_detail_tmp.get('car_spec') or {}
                spec_desc_tmp = car_spec_tmp.get('description', '')
                import re
                target_options = []
                for line in spec_desc_tmp.split('\\n'):
                    m = re.search(r'^\\d+\\)\\s*(.*?)(?:\\s*\\(|$)', line.strip())
                    if m:
                        target_options.append(m.group(1).strip())"""
app_content = app_content.replace(old_app_opt, new_app_opt)

# Update extract_car_data_for_ai call
old_extract = """            ai_prompt = extract_car_data_for_ai(
                heydealer_json_str, 
                market_avg=avg_price if 'avg_price' in locals() else (encar_avg_price if 'encar_avg_price' in locals() else hd_market_avg),
                no_accident_avg=no_acc_avg if 'no_acc_avg' in locals() else (encar_no_acc_avg if 'encar_no_acc_avg' in locals() else hd_no_acc_avg),
                accident_avg=acc_avg if 'acc_avg' in locals() else (encar_acc_avg if 'encar_acc_avg' in locals() else hd_acc_avg),
                target_opt_avg=target_opt_avg if 'target_opt_avg' in locals() else (encar_target_opt_avg if 'encar_target_opt_avg' in locals() else hd_target_opt_avg),
                no_target_opt_avg=no_target_opt_avg if 'no_target_opt_avg' in locals() else (encar_no_target_opt_avg if 'encar_no_target_opt_avg' in locals() else hd_no_target_opt_avg),
                prev_year_avg=prev_year_avg if 'prev_year_avg' in locals() else 0,
                next_year_avg=next_year_avg if 'next_year_avg' in locals() else 0,
                auction_repairs_json=auction_repairs_json
            )"""
new_extract = """            ai_prompt = extract_car_data_for_ai(
                heydealer_json_str, 
                retail_avg=avg_price if 'avg_price' in locals() else 0,
                retail_no_acc_avg=no_acc_avg if 'no_acc_avg' in locals() else 0,
                retail_acc_avg=acc_avg if 'acc_avg' in locals() else 0,
                retail_opt_avg=target_opt_avg if 'target_opt_avg' in locals() else 0,
                retail_no_opt_avg=no_target_opt_avg if 'no_target_opt_avg' in locals() else 0,
                wholesale_avg=hd_market_avg,
                wholesale_no_acc_avg=hd_no_acc_avg,
                wholesale_acc_avg=hd_acc_avg,
                wholesale_opt_avg=hd_target_opt_avg,
                wholesale_no_opt_avg=hd_no_target_opt_avg,
                prev_year_avg=prev_year_avg if 'prev_year_avg' in locals() else 0,
                next_year_avg=next_year_avg if 'next_year_avg' in locals() else 0,
                auction_repairs_json=auction_repairs_json
            )"""
app_content = app_content.replace(old_extract, new_extract)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)

print("done")
