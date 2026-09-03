import traceback

try:
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    target = "heydealer_json_str = result['detail']"
    replacement = """heydealer_json_str = result['detail']
                if not heydealer_json_str.strip() or not heydealer_json_str.strip().startswith('{'):
                    raise Exception(f'헤이딜러 응답이 비정상입니다(차단 또는 삭제된 매물일 수 있습니다). 응답: {heydealer_json_str[:100]}')"""

    if target in content:
        new_content = content.replace(target, replacement)
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('Replaced successfully')
    else:
        print('Target not found')
except Exception as e:
    traceback.print_exc()
