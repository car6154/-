import urllib.request, json, urllib.parse, re

encar_url = 'https://www.encar.com/dc/dc_carsearchlist.do?carType=kor&searchType=model&TG.R=A#!%7B%22action%22%3A+%22%28And.Hidden.N._.%28C.CarType.Y._.%28C.Manufacturer.%5Cud604%5Cub300._.%28C.ModelGroup.%5Cuc5d1%5Cuc13c%5Cud2b8._.%28C.Model.%5Cuc5d1%5Cuc13c%5Cud2b8%28%5Cuc2e0%5Cud615_%29._.%28C.BadgeGroup.%5Cuac00%5Cuc194%5Cub9b0+1400cc._.Badge.1_.4+VVT+%5Cubaa8%5Cub358.%29%29%29%29%29_.Year.range%28201501..201712%29._.Mileage.range%28120000..160000%29.%29%22%2C+%22toggle%22%3A+%7B%7D%2C+%22layer%22%3A+%22%22%2C+%22sort%22%3A+%22Mileage%22%2C+%22page%22%3A+1%2C+%22limit%22%3A+20%7D'

decoded_url = urllib.parse.unquote_plus(encar_url)
json_match = re.search(r'#!(\{.*\})', decoded_url)
json_data = json.loads(json_match.group(1))
condition = json_data.get('action', '')
print("Condition from JSON:", repr(condition))
wide_condition = re.sub(r'\.?_\.Mileage\.range\(\d+\.\.\d+\)', '', condition)
wide_condition = re.sub(r'\.{2,}\)', '.)', wide_condition)
print("Wide condition:", repr(wide_condition))

safe_condition = urllib.parse.quote(wide_condition)
print("Safe condition:", safe_condition)

api_url = f'https://api.encar.com/search/car/list/general?count=true&q={safe_condition}&sr=%7CModifiedDate%7C0%7C30'

headers = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  'Referer': 'http://www.encar.com/',
  'Accept': 'application/json'
}

req = urllib.request.Request(api_url, headers=headers)
res = urllib.request.urlopen(req)
data = json.loads(res.read().decode())
print("Cars count:", data.get("Count"))
