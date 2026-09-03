import traceback

try:
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    target = """            market_avg = 0
            no_acc_avg = 0
            acc_avg = 0
            sunroof_avg = 0
            no_sunroof_avg = 0"""
            
    replacement = """            hd_market_avg = 0
            hd_no_acc_avg = 0
            hd_acc_avg = 0
            hd_sunroof_avg = 0
            hd_no_sunroof_avg = 0"""

    if target in content:
        new_content = content.replace(target, replacement)
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('Replaced successfully')
    else:
        print('Target not found')
except Exception as e:
    traceback.print_exc()
