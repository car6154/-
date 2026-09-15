import urllib.request

url = "https://www.kcar.com/_nuxt/732b1db.js"
js = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=10).read().decode("utf-8", errors="ignore")

idx = js.find("searchAutoList:function")
if idx == -1:
    idx = js.find("searchAutoList")
print(js[idx:idx+300])
