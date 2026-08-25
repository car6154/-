import requests
carid = '37936136'
url = f'http://www.encar.com/md/sl/mdsl_regcar.do?method=inspectionViewNew&carid={carid}'
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
html = resp.text
with open('encar_test2.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Done, len: {len(html)}')
