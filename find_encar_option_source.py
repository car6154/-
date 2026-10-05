import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2&mnfccd=003&mdlgroupcd=055&mdlcd=102&caryear=2021&pageAccessToken=AgV4b0I%2FssShaI8JqMK8%2FlQZcT1u4FfUYp6u1LK4vZ1uBXoAcQACAAdFbmNhckNrAAdFbmNhckN2ABVhd3MtY3J5cHRvLXB1YmxpYy1rZXkAREE2VE9OelNTQWNkTVM2dUNhSGpqNmxXMmU0dWxWbU9xUkozNXo2VzJHcjN0SXd0OW9CeHY5MTA4a0F3UkdUVk9oZz09AAEAB2F3cy1rbXMAUGFybjphd3M6a21zOmFwLW5vcnRoZWFzdC0yOjI3MjM2MjQ4NzY1MzprZXkvbXJrLWRmZWEyNmY3NTVhMzQ3MjliNjkwMjRkZWZmM2M1MWFjALgBAgEAeAuqQuSJvQ%2BRa4FSj55FZzS0sk%2B00amsb3yoAFiEYn4PAQXqVtXDmN7swhNoO5haGmMAAAB%2BMHwGCSqGSIb3DQEHBqBvMG0CAQAwaAYJKoZIhvcNAQcBMB4GCWCGSAFlAwQBLjARBAwZwvCCbaedT0z2WLECARCAO97VKVwUlxsXfFcRzcE%2FjPBhunUcaZAtxxPAFal%2BtDHShOpAjs6KjValp3x4UXXiKMIK8dMf9%2FXMmrHJAgAAEABPWtxhrIwZT0124UeixEmUfX3ceDGc%2B6jA7DmpR3iAaCGa4iypchrMnv2SazLD0tP%2F%2F%2F%2F%2FAAAAAQAAAAAAAAAAAAAAAQAAAJ60mgSx8x%2BmQtXdFgweF3WfrXeZrHozidTu%2FG5mfCrdcbcBtT0NuIDEOsgJnaI2xhTYdPkRMT%2B4TI%2F9b%2FKBLIjAZpUlTDBY8iHpIEBgRhi1BPrYp5tE%2BynCCD0AafqCRRR44Dsz%2Bo3Gt3htGedaDMr51GEGjOpmKXft75%2FeFi9L0eKrv4%2BX1bfemx9v1pyAk9ML5q61d5i0pID8%2FA%2BgFti3gKWRR5ef90ZUFUY4y%2BEAZzBlAjEAk%2B9eRddYCcTdnBKzaSHGuMME6aGkZTKZ%2B1cGpi4jRFUAe81sqKNzWRR51YYbVUBIAjA%2B%2FLrFAQqCy4mUwumezLtQmz2Dim23jZZpWx%2BlZvqB59AvxTTLH73i8my7qYKe0ak%3D'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Referer': 'https://www.encar.com/db/db_carsinfo.do?method=newpricePopV2'
}

s = requests.Session()
r = s.get(url, headers=headers)
print('status:', r.status_code, 'len:', len(r.text))
with open('debug_newprice.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
print('debug_newprice.html 저장 완료')
