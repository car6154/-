import re, requests

resp = requests.get('https://dealer.heydealer.com/assets/index-Dn0N5zya.js')
text = resp.text

# In JS, let's find `b$e=e=>async()=>(await ft.get(`/cars/${e}/`)).data`
idx = text.find('ft.get(`/cars/${')
if idx != -1:
    print("Found ft.get(/cars/${:")
    print(text[max(0, idx-100):min(len(text), idx+200)])

# Find usages of b$e or whatever the function is
m = re.search(r'([a-zA-Z0-9_$]+)=e=>async\(\)=>\(await ft\.get\(`/cars/\$\{e\}/`\)\)\.data', text)
if m:
    fn_name = m.group(1)
    print(f"Function name for get car detail: {fn_name}")
    # find where fn_name is called
    calls = [m.start() for m in re.finditer(re.escape(fn_name), text)]
    print(f"Calls to {fn_name}: {len(calls)}")
    for pos in calls[:5]:
        print("---")
        print(text[max(0, pos-50):min(len(text), pos+150)])
