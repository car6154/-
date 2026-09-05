import sys
sys.stdout.reconfigure(encoding='utf-8')
from app import Scraper

class Mock:
    def text(self, t): pass
    def progress(self, p): pass

url = 'https://www.encar.com/dc/dc_carsearchlist.do?carType=kor&searchType=model&TG.R=A#!%7B%22action%22%3A+%22%28And.Hidden.N._.%28C.CarType.Y._.%28C.Manufacturer.%5Cud604%5Cub300._.%28C.ModelGroup.%5Cuadf8%5Cub79c%5Cuc800._.%28C.Model.%5Cuadf8%5Cub79c%5Cuc800+HG._.%28C.BadgeGroup.%5Cuac00%5Cuc194%5Cub9b0+3000cc+%5Cuc774%5Cuc0c1._.Badge.HG300+%5Cub178%5Cube14.%29%29%29%29%29_.Year.range%28201001..201212%29._.Mileage.range%28100000..140000%29.%29%22%2C+%22toggle%22%3A+%7B%7D%2C+%22layer%22%3A+%22%22%2C+%22sort%22%3A+%22Mileage%22%2C+%22page%22%3A+1%2C+%22limit%22%3A+20%7D'

df, msg = Scraper.run(url, '', Mock(), Mock())
print('Encar test with real URL:', msg, 'len:', len(df))
if not df.empty:
    print(df[['차량명', '세부모델', '연식', '주행거리', '판매가']].head())
