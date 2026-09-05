import json

def extract_car_data_for_ai(json_payload, retail_avg=0, retail_no_acc_avg=0, retail_acc_avg=0, retail_opt_avg=0, retail_no_opt_avg=0, wholesale_avg=0, wholesale_no_acc_avg=0, wholesale_acc_avg=0, wholesale_opt_avg=0, wholesale_no_opt_avg=0, prev_year_avg=0, next_year_avg=0, auction_repairs_json=""):
    # 1. JSON 문자열을 파이썬 딕셔너리로 파싱
    data = json.loads(json_payload)
    detail = data.get('detail') or {}
    
    # 2. 핵심 변수 핀셋 추출 (최초등록연도 우선)
    car_name = detail.get('full_name') or '차명 누락'
    import re
    reg_date = detail.get('initial_registration_date') or detail.get('first_registration_date') or detail.get('registration_date') or ''
    m_year = re.search(r'(\d{4})', str(reg_date))
    year = int(m_year.group(1)) if m_year else (detail.get('year') or 0)
    
    mileage = detail.get('mileage') or 0
    new_car_price = detail.get('standard_new_car_price') or 0 # 단위: 만원
    
    # 3. 추가 옵션 정보 (car_spec 출고 정보 기준)
    car_spec = detail.get('car_spec') or {}
    spec_desc = car_spec.get('description', '')
    import re
    options = []
    for line in spec_desc.split('\n'):
        m = re.search(r'^\d+\)\s*(.*?)(?:\s*\(|$)', line.strip())
        if m:
            options.append(m.group(1).strip())
    
    # 4. 감가 요인 추출 (외판/소모품 상태 및 평가사 소견)
    condition_data = detail.get('condition_data') or {}
    basic_conditions = condition_data.get('basic') or []
    condition_basic_str = ", ".join([
        f"{item.get('label', '')}: {item.get('text', '')}" 
        for item in basic_conditions if isinstance(item, dict)
    ])
    
    inspected_condition = detail.get('inspected_condition') or {}
    inspector_comment = inspected_condition.get('comment') or '특이사항 없음'
    
    # 5. 용도 이력 추출 (렌트 이력)
    carhistory = detail.get('carhistory') or {}
    rent_history_count = carhistory.get('rent_use_record_count') or 0
    rent_status = "있음" if rent_history_count > 0 else "없음"
    
    retail_opt_line_display = f"옵션 포함 평균 {retail_opt_avg}만원 / 미포함 평균 {retail_no_opt_avg}만원\n" if retail_opt_avg != retail_no_opt_avg and len(options) > 0 else ""
    wholesale_opt_line_display = f"옵션 포함 평균 {wholesale_opt_avg}만원 / 미포함 평균 {wholesale_no_opt_avg}만원\n" if wholesale_opt_avg != wholesale_no_opt_avg and len(options) > 0 else ""

    # 6. 화면 노출용 데이터 헤더 (깔끔하게 핵심만)
    data_header_encar = f"""동급 평균: **{retail_avg}만원** (무사고 {retail_no_acc_avg}만원 / 유사고 {retail_acc_avg}만원)
{retail_opt_line_display}{year-1}년 평균 {prev_year_avg}만원 / {year+1}년 평균 {next_year_avg}만원"""

    data_header_heydealer = f"""동급 평균: **{wholesale_avg}만원** (무사고 {wholesale_no_acc_avg}만원 / 유사고 {wholesale_acc_avg}만원)
{wholesale_opt_line_display}{year-1}년 평균 {prev_year_avg}만원 / {year+1}년 평균 {next_year_avg}만원"""

    # 프롬프트 구성 시 에러 방지용 호환성
    data_header = f"(1) 예상 소매가 기준\n{data_header_encar}\n\n(2) 예상 매입가 기준\n{data_header_heydealer}"

    # 엔카 데이터 0원 여부에 따라 소매가 섹션을 코드에서 미리 확정
    if retail_avg == 0:
        retail_result_block = """금액: 0원 (엔카 매물 검색 안 됨)
산출 근거: 엔카 실시간 매물 데이터가 0원으로 조회되어 산출 불가"""
    else:
        retail_result_block = None

    # 7. AI에게 보낼 프롬프트 (풀 텍스트 - AI만 봄)
    ai_prompt = f"""[타겟 차량]
- {car_name} / {year}년식 / {mileage:,}km
- 옵션: {', '.join(options)}
- 상태: {condition_basic_str} / 평가사 소견: {inspector_comment}

[실시간 매물 데이터 - 이미 계산된 수치, 재계산 금지]
(1) 예상 소매가 기준 (엔카 판매 데이터)
- 동급 평균: {retail_avg}만원 (무사고 {retail_no_acc_avg}만원 / 유사고 {retail_acc_avg}만원)
{retail_opt_line_display}- 1년 전후 평균가 차이 ({year}년 시세 기준 {year-1}년 평균 {prev_year_avg}만원 / {year+1}년 평균 {next_year_avg}만원)

(2) 예상 매입가 기준 (헤이딜러 낙찰 데이터)
- 동급 평균: {wholesale_avg}만원 (무사고 {wholesale_no_acc_avg}만원 / 유사고 {wholesale_acc_avg}만원)
{wholesale_opt_line_display}- 1년 전후 평균가 차이 ({year}년 시세 기준 {year-1}년 평균 {prev_year_avg}만원 / {year+1}년 평균 {next_year_avg}만원)

[감가 기준표]
- 문콕 3~5만원/개, 판금도색 10~13만원/판(국산)·15~18만원(수입)
- 사고 감가: 위 예상 소매가 기준 외판 3~4%/부위, 골격 5~7%/부위, 범퍼교환 0원

[지시사항]
1. 위 (1)번 엔카 데이터를 바탕으로 타겟 차량의 옵션 및 상태를 고려해 '예상 소매가'를 산출하세요.
2. 위 (2)번 헤이딜러 데이터를 바탕으로 기본 낙찰매입가를 산출하고, 해당 매입가에서 현재 차량의 감가 요인(상품화비, 사고감가 등)을 차감하여 최종 매입가를 산출하세요.
3. 딜러 마진율은 이미 헤이딜러 낙찰 데이터(도매가)에 반영되어 있으므로, **절대로 마진율이나 마진 차감액을 계산하거나 포함하지 마세요.**
- 불필요한 서론/결론(인사말 등)은 모두 생략하고 핵심 견적만 간결하게 출력하세요.
- 데이터가 0원일 경우 상상하여 값을 채워넣지 말고 프롬프트에 주어진 값 그대로 처리하세요.

**[절대 규칙 - 위반 시 출력 무효]**
- 엔카 소매가 데이터가 0만원이면 예상 소매가는 반드시 "0원 (엔카 매물 검색 안 됨)"으로만 출력하세요.
- 도매가에서 역산하거나, 시세를 추정하거나, 어떤 방법으로든 소매가를 만들어내는 행위를 절대 금지합니다.
{f'- 아래 예상 소매가 섹션은 이미 확정되었으므로, 아래 내용을 그대로 복사하여 출력하세요.' if retail_result_block else ''}

[출력 형식 - 아래 형식만 정확히 출력하세요. 섹션 제목([예상 소매가], [최종 매입 제시가] 등)은 출력하지 마세요.]
{retail_result_block if retail_result_block else '''금액: [산출된 금액]\n산출 근거: [간단한 산출 근거]'''}

금액: [최종 매입 제시가]
산출 근거:
  1. 기본 낙찰 매입가: [금액]
  2. 감가 차감 내역: [감가된 내용 및 금액]
  3. 최종 금액: [최종 매입가]
"""
    return {
        "data_header": data_header,
        "data_header_encar": data_header_encar,
        "data_header_heydealer": data_header_heydealer,
        "ai_prompt": ai_prompt
    }

import os
from google import genai
from google.genai import types

def get_gemini_estimate(prompt, status_callback=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "API 키가 설정되지 않았습니다. .env 파일을 확인해 주세요."
    
    import time
    import re
    
    # 모델 폴백 체인: 각 모델마다 별도 일일 20회 한도 -> 여러 모델을 돌려가며 사용
    models_to_try = ['gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-3.8-flash', 'gemini-3.7-flash']
    
    try:
        http_opts = types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=1)
        )
        client = genai.Client(api_key=api_key, http_options=http_opts)
        
        last_error = None
        for model_name in models_to_try:
            try:
                if status_callback:
                    status_callback(f"🤖 {model_name} 모델로 견적 산출 중...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0
                    )
                )
                return response.text
            except Exception as e:
                error_msg = str(e)
                last_error = e
                if '429' in error_msg and 'PerDay' in error_msg:
                    # 일일 한도 초과 -> 다음 모델로 전환
                    if status_callback:
                        status_callback(f"⚠️ {model_name} 일일 한도 초과, 다음 모델로 전환 중...")
                    continue
                elif '429' in error_msg:
                    # 분당 한도 -> 대기 후 같은 모델로 재시도
                    m = re.search(r'retry in (\d+\.?\d*)s', error_msg)
                    if m:
                        wait_time = float(m.group(1)) + 1.0
                        if wait_time <= 60:
                            for remaining in range(int(wait_time), 0, -1):
                                if status_callback:
                                    status_callback(f"⚠️ {model_name} 분당 한도 도달: {remaining}초 대기 후 자동 재시도...")
                                time.sleep(1)
                            # 대기 후 같은 모델로 한 번 더 시도
                            try:
                                if status_callback:
                                    status_callback(f"🤖 {model_name} 재시도 중...")
                                response = client.models.generate_content(
                                    model=model_name,
                                    contents=prompt,
                                    config=types.GenerateContentConfig(temperature=0.0)
                                )
                                return response.text
                            except:
                                continue  # 실패하면 다음 모델로
                    continue
                elif ('503' in error_msg or 'timed out' in error_msg.lower()):
                    time.sleep(3)
                    continue
                else:
                    # 기타 오류 (404 등) -> 다음 모델로
                    continue
        
        return f"Gemini API 호출 중 오류 발생: {last_error}\n(모든 모델의 무료 일일 한도(20회)가 소진되었습니다. 내일 다시 시도하시거나 과금 설정을 확인해주세요.)"
    except Exception as e:
        return f"Gemini API 호출 중 오류 발생: {e}"

# --- 실행 테스트 ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # (여기에 앞서 낚아채신 2번째 레이의 전체 JSON 문자열을 넣으시면 됩니다)
    sample_json_string = """
    {
        "detail": {
            "full_name": "더 뉴 레이 시그니처",
            "year": 2021,
            "mileage": 64864,
            "standard_new_car_price": 1800,
            "advanced_options": [
                {"name": "내비게이션(정품)", "choice": "loaded"},
                {"name": "풀오토에어컨", "choice": "loaded"}
            ],
            "condition_data": {
                "basic": [
                    {"label": "외판", "text": "4판"},
                    {"label": "휠 기스", "text": "4개 휠"},
                    {"label": "타이어", "text": "앞 0%, 뒤 50%"}
                ]
            },
            "inspected_condition": {
                "comment": "핸들 흔들면 뚝뚝 이음.\\n양쪽 앞타이어 편마모 교환 필요."
            },
            "carhistory": {
                "rent_use_record_count": 1
            }
        }
    }
    """
    
    ai_prompt = extract_car_data_for_ai(sample_json_string)
    print("=== AI 매입 견적 시스템 프롬프트 ==\\n")
    print(ai_prompt)
    
    print("\\n=== Gemini API 응답 ===\\n")
    print(get_gemini_estimate(ai_prompt))