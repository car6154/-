import traceback
import re

try:
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update find_status function
    old_find_status = """def find_status(damage_data, *keywords):
                    for name, status in damage_data.items():
                        for kw in keywords:
                            if kw in name:
                                return status
                    return "정상\""""
    new_find_status = """def find_status(damage_data, *keywords):
                    for name, status in damage_data.items():
                        if all(kw in name for kw in keywords):
                            return status
                    return "정상\""""
    content = content.replace(old_find_status, new_find_status)

    # 2. Add 리어 패널 to PART_COORDS_INNER
    target_inner = '(("트렁크","플로어"),             55, 230, 110, 60, "T플", "트렁크 플로어"),\n                ]'
    replacement_inner = '(("트렁크","플로어"),             55, 230, 110, 60, "T플", "트렁크 플로어"),\n                    (("리어","패널"),                 55, 290, 110, 20, "R패", "리어 패널"),\n                ]'
    content = content.replace(target_inner, replacement_inner)

    # 3. Update text summary logic
    old_issues_loop = """issues = {}
                    for coords in [PART_COORDS_OUTER, PART_COORDS_INNER]:
                        for item in coords:
                            keywords = item[0]
                            full_label = item[6]
                            status = find_status(damage_data, *keywords)
                            if status in ["교환", "판금"]:
                                issues[full_label] = status"""
    
    new_issues_loop = """issues = {}
                    for name, status in damage_data.items():
                        if status in ["교환", "판금"]:
                            issues[name] = status"""
    content = content.replace(old_issues_loop, new_issues_loop)

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixes applied successfully.")
except Exception as e:
    traceback.print_exc()
