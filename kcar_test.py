import urllib.request
import re

req = urllib.request.Request('https://www.kcar.com', headers={'User-Agent': 'Mozilla/5.0'})
try:
    resp = urllib.request.urlopen(req)
    html = resp.read().decode('utf-8')
    urls = re.findall(r'href=[\'"]?([^\'" >]+)', html)
    search_urls = [u for u in urls if 'search' in u.lower()]
    print('Search URLs found:', set(search_urls))
except Exception as e:
    print('Error:', e)
