import requests
carid = '37936136'
url = f'http://www.encar.com/dc/dc_cardetailview.do?method=kidiInspectView&carid={carid}'
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
html = resp.text
with open('encar_test.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Done, len: {len(html)}')
