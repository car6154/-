# scripts/build_crawl_targets.py
import os
import re
import json
import time
import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TARGETS_INDEX_FILE = os.path.join(DATA_DIR, "encar_crawl_targets_index.json")

MFG_ORDER = [
    {"code": "001", "name": "현대"},
    {"code": "002", "name": "기아"},
    {"code": "007", "name": "제네시스"},
    {"code": "005", "name": "르노코리아"},
    {"code": "004", "name": "KGM"},
    {"code": "003", "name": "쉐보레"}
]

s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

def build_index():
    # 기존 카탈로그에서 연식 기준(2013년 이후) 확인
    with open(os.path.join(DATA_DIR, "encar_newcar_catalog.json"), "r", encoding="utf-8") as f:
        existing_cat = json.load(f)

    all_targets = []
    
    for mfg in MFG_ORDER:
        mfg_code = mfg["code"]
        mfg_name = mfg["name"]
        print(f"\n[{mfg_name}] 모델그룹 조회 중...")
        url_grp = f"https://www.encar.com/common/combo/modelgroupfordb.json?method=carList&mnfccd={mfg_code}"
        r_grp = s.get(url_grp, timeout=5)
        groups = r_grp.json()
        
        mfg_pairs = 0
        for g in groups:
            gid = g.get("abbreviation")
            gname = g.get("name")
            url_mdl = f"https://www.encar.com/common/combo/cardbmodel.json?method=carList&mnfccd={mfg_code}&mdlgroupcd={gid}"
            r_mdl = s.get(url_mdl, timeout=5)
            models = r_mdl.json()
            time.sleep(0.1)

            for m in models:
                mid = m.get("abbreviation")
                mname = m.get("name")
                
                # 연식 조회
                url_yr = f"https://www.encar.com/common/combo/jatoYr.json?method=carList&mnfccd={mfg_code}&mdlcd={mid}"
                r_yr = s.get(url_yr, timeout=5)
                yrs = r_yr.json()
                time.sleep(0.1)

                valid_years = []
                for y in yrs:
                    yr_val = str(y.get("abbreviation") or y.get("label") or "").strip()
                    if yr_val.isdigit() and int(yr_val) >= 2013:
                        valid_years.append(yr_val)

                for y in sorted(list(set(valid_years)), reverse=True):
                    all_targets.append({
                        "mfg_code": mfg_code,
                        "mfg_name": mfg_name,
                        "group_id": gid,
                        "group_name": gname,
                        "model_id": mid,
                        "model_name": mname,
                        "year": y
                    })
                    mfg_pairs += 1

        print(f"  -> {mfg_name}: (모델, 연식) 쌍 총 {mfg_pairs}개")

    print(f"\n전체 타깃 총합: {len(all_targets)}개")
    with open(TARGETS_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(all_targets, f, ensure_ascii=False, indent=2)
    print(f"인덱스 저장 완료: {TARGETS_INDEX_FILE}")

if __name__ == "__main__":
    build_index()

