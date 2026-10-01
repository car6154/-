import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

from services.master_mapping import MasterMappingService

with MasterMappingService._lock:
    db = MasterMappingService._load_db()
    models = db.get('models', {})
    norm = db.get('normalized_models', {})

print("=== Carnival entries in models ===")
for k, v in models.items():
    if '카니발' in k or '카니발' in v.get('model_group', ''):
        print(f"Key: [{k}], Brand: [{v.get('brand')}], MG: [{v.get('model_group')}], EncarModel: [{v.get('encar_model')}], Aliases: {v.get('aliases')}")

print("\n=== Carnival entries in normalized_models ===")
for k, v in norm.items():
    if '카니발' in k:
        print(f"  [{k}] -> [{v}]")

print("\n=== Test resolve_encar_model for Carnival ===")
res1 = MasterMappingService.resolve_encar_model('기아', '올뉴카니발', '디젤 9인승 프레스티지', 2017)
print("1. 올뉴카니발 (2017):", res1)

res2 = MasterMappingService.resolve_encar_model('기아', '더 뉴카니발(YP)', '9인승 디젤 노블레스 스페셜', 2019)
print("2. 더 뉴카니발(YP) (2019):", res2)

res3 = MasterMappingService.resolve_encar_model('기아', '카니발 4세대', '9인승 디젤 프레스티지', 2021)
print("3. 카니발 4세대 (2021):", res3)
