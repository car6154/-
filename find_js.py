import re
with open('encar_test2.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Let's just find the whole JavaScript object array that might contain the damages
match = re.search(r'var\s+carDamage\s*=\s*\[(.*?)\];', html, re.DOTALL)
if match:
    print('carDamage: ', match.group(1)[:500])
else:
    print('carDamage not found')

match2 = re.search(r'data\s*:\s*\[(\{.*?code:\s*["\']002["\'].*?\})\]', html, re.DOTALL)
if match2:
    print('data: ', match2.group(1)[:500])
else:
    print('data not found')
    
# Or maybe parse standard Encar format: fnStats
# The states are usually passed or hardcoded
import json
print(html[html.find('fnAction'):html.find('fnAction')+500])
