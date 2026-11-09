# -*- coding: utf-8 -*-
import json

with open('data/batch-51-kgm-lineup.json', encoding='utf-8') as f:
    data = json.load(f)

danawa = data.get('danawa', {})
print(f'Total cars in batch-51: {len(danawa)}')
for car in sorted(danawa.keys()):
    years = sorted(danawa[car].keys())
    g_count = sum(len(danawa[car][y]) for y in years)
    o_count = sum(sum(len(g.get('options', {})) for g in danawa[car][y].values()) for y in years)
    print(f' - {car}: {len(years)} years ({years[0]}~{years[-1]}), {g_count} grades, {o_count} options')

# 베리 뉴 티볼리 2020년식 V3 검증
vnt_2020 = danawa.get('베리 뉴 티볼리', {}).get('2020', {})
print('\n=== 베리 뉴 티볼리 2020년식 검증 ===')
print('2020 grades count:', len(vnt_2020))
v3_key = [k for k in vnt_2020 if 'V3' in k and '2WD' in k]
print('V3 2WD grade key:', v3_key)
if v3_key:
    v3 = vnt_2020[v3_key[0]]
    print('base_price:', v3.get('base_price'))
    print('base_price_man:', v3.get('base_price_man'))
    print('standard_features count:', len(v3.get('standard_features', [])))
    print('standard_features sample:', v3.get('standard_features', [])[:3])
    print('options count:', len(v3.get('options', {})))
    for opt_name, opt_val in list(v3.get('options', {}).items())[:5]:
        print(f"   {opt_name}: {opt_val.get('price'):,}원 ({opt_val.get('price_man')}만) | desc: {opt_val.get('desc')[:30]}...")

# 전수 가격 일치 재검증
mismatches = 0
for car, ys in danawa.items():
    for y, gs in ys.items():
        for g, val in gs.items():
            bp = val.get('base_price', 0)
            bpm = val.get('base_price_man', 0)
            if abs(bp - bpm * 10000) > 0.01:
                mismatches += 1
            for oname, oval in val.get('options', {}).items():
                p = oval.get('price', 0)
                pm = oval.get('price_man', 0)
                if p != pm * 10000:
                    mismatches += 1
print(f'\nTotal price mismatches across all 511 grades & options: {mismatches}')
