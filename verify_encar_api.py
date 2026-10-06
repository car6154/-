import requests
import json

payload = {
    "carName": "디 올 뉴 투싼",
    "detailModel": "가솔린 1.6T 2WD 인스퍼레이션",
    "manufacturer": "현대",
    "year": 2021,
    "mileage": 48000
}

res = requests.post("http://127.0.0.1:8000/api/encar/search", json=payload)
data = res.json()

print("Status Code:", res.status_code)
print("success:", data.get("success"))
print("totalCount:", data.get("totalCount"))
print("filteredCount:", data.get("filteredCount"))
print("stats:", data.get("stats"))
items = data.get("items", [])
print("items count:", len(items))

print("\n--- 상위 5개 매물 실측 정렬 검증 ---")
for i, it in enumerate(items[:5]):
    badge = it.get("badge", "-")
    year = it.get("year", "-")
    price = it.get("price", "-")
    checkDate = it.get("checkDate", "-")
    acc = it.get("accidentType", "-")
    print(f"[{i+1}] {year}년식 | {price}만원 | {badge} | 점검일:{checkDate} | 사고:{acc}")
