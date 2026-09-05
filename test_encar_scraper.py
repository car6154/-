import urllib.parse
from app import Scraper

class Mock:
    def text(self, t):
        pass
    def progress(self, p):
        pass

# Test Encar Search with Action condition
keyword = "캐스퍼"
action = f"(And.Hidden.N._.Keyword.{keyword}.)"
url = f"https://www.encar.com/dc/dc_carsearchlist.do?carType=kor#!{{\"action\":\"{action}\"}}"

print("Scanning Encar url:", url)
df, msg = Scraper.run(url, "", Mock(), Mock())
print("Scan message:", msg)
print("Scanned rows:", len(df))
if not df.empty:
    print("Sample:\n", df[['차량명', '세부모델', '연식', '주행거리', '판매가']].head())
