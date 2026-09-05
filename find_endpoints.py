import re, requests

with open('dealer_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

# fetch js files
js_files = re.findall(r'src="(/assets/[^"]+)"', html)
print("JS files:", js_files)

for js in js_files:
    url = f"https://dealer.heydealer.com{js}"
    resp = requests.get(url)
    text = resp.text
    print(f"Downloaded {js}, len: {len(text)}")
    
    # search endpoints
    apis = set(re.findall(r'["\'](/v[12]/[^"\'\s]+)["\']', text))
    print(f"Found {len(apis)} API patterns:")
    for a in sorted(apis):
        if any(w in a for w in ['car', 'auction', 'detail', 'price', 'dealer']):
            print("  ", a)
