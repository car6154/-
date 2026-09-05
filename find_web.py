import re

with open('dealer_page.html', 'r', encoding='utf-8') as f:
    pass

import requests
resp = requests.get('https://dealer.heydealer.com/assets/index-Dn0N5zya.js')
text = resp.text

idx = 0
found = []
while True:
    idx = text.find('/v2/dealers/web/', idx)
    if idx == -1: break
    snippet = text[max(0, idx-50):min(len(text), idx+100)]
    found.append(snippet)
    idx += len('/v2/dealers/web/')

print(f"Total occurrences: {len(found)}")
for s in found[:20]:
    print("---")
    print(repr(s))
