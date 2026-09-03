import traceback

try:
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_detail_html = False
    for i in range(len(lines)):
        if "detail_html = f\"\"\"" in lines[i]:
            in_detail_html = True
        elif in_detail_html and '"""' in lines[i] and 'detail_html' not in lines[i]:
            in_detail_html = False
            # also process this line if it has spaces before """
            lines[i] = lines[i].lstrip()
        elif in_detail_html:
            # strip leading spaces for HTML lines so markdown doesn't parse them as code blocks
            lines[i] = lines[i].lstrip()

    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Fixed indentation in detail_html")
except Exception as e:
    traceback.print_exc()
