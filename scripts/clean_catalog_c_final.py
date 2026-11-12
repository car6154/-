# -*- coding: utf-8 -*-
"""
scripts/clean_catalog_c_final.py
[11-12-10] 제이책(C) 시뮬레이션 검출 흠결 정화 및 다나와 옵션 설명 보강
1. 11-12-08/09에서 중복 부활한 구형 엔카 기본 등급(1,541개, 연료명 미통일 83개 포함) 제거 -> 12,047개 정제 등급 복원
   (11-12-08/09에서 수정한 정상 가격 487건 및 추가한 악세사리 45개 연식은 100% 유지)
2. _accessories 내에 혼입된 0원짜리 일반 패키지 옵션 해설표를 등급 옵션 desc로 이관 후 _accessories에서 제거
   (진짜 순정 악세사리만 남기고, 등급 옵션에 가격이 있는 악세사리는 가격 복원)
3. 엔카 출처 등급 중 옵션 설명(desc)이 비어있는 항목에 다나와 원본(별칭 포함) 옵션 desc 매칭 보강
"""

import os
import re
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_C_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_c.json")
V14_BACKUP_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_c_v14_backup_2026-11-12.json")
SRC_V2_FILE = os.path.join(PROJECT_ROOT, "data", "catalog_by_source_v2.json")
ALIAS_FILE = os.path.join(PROJECT_ROOT, "data", "model_alias_table.json")

REAL_ACC_KEYWORDS = [
    '필름', '휠 캡', '휠캡', '스텝', '매트', '공기청정기', '트레일러', '러기지 파티션',
    '카고', '가드', '발판', '루프모니터', '루프 모니터', '배기', '텐트', '기어', '엠블럼',
    '커버', '데칼', '바디킷', '스포일러', '네트', '선바이저', '바이저', '몰딩', '페달',
    '워머', '냉온', '시트백', '테이블', '행거', '하네스', '크래들', '키케이스', '차박',
    '캠핑', '후석 스마트 엔터테인먼트'
]


def norm_opt_name(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = s.replace('ⅰ', '1').replace('ⅱ', '2').replace('ⅲ', '3').replace('ⅳ', '4').replace('ⅴ', '5')
    s = re.sub(r'\biii\b', '3', s)
    s = re.sub(r'\bii\b', '2', s)
    s = re.sub(r'\bi\b', '1', s)
    return re.sub(r'[\s\(\)\[\]\-_/·,\+&]+', '', s)


def main():
    cat = json.load(open(CATALOG_C_FILE, "r", encoding="utf-8"))
    v14 = json.load(open(V14_BACKUP_FILE, "r", encoding="utf-8"))
    src_v2 = json.load(open(SRC_V2_FILE, "r", encoding="utf-8"))
    danawa = src_v2.get("danawa", {})
    alias_table = json.load(open(ALIAS_FILE, "r", encoding="utf-8")) if os.path.exists(ALIAS_FILE) else {}

    # 1. 11-12-08/09에서 잘못 부활한 구형 엔카 기본 등급 제거 (v14 기준 등급 키만 유지)
    removed_zombie_grades = 0
    for m, yrs in list(cat.items()):
        for y, ydata in list(yrs.items()):
            v14_ydata = v14.get(m, {}).get(y, {})
            for gname in list(ydata.keys()):
                if gname.startswith('_'):
                    continue
                if gname not in v14_ydata:
                    del ydata[gname]
                    removed_zombie_grades += 1

    print(f"[1/3] 중복 부활한 구형 엔카 기본 등급 제거: {removed_zombie_grades}개")

    # 2. 다나와 모델 매핑 구성 (별칭 포함)
    cm_to_dms = {}
    for cm in cat.keys():
        dms = [cm]
        if cm in alias_table and alias_table[cm].get('danawa_model'):
            dms.append(alias_table[cm]['danawa_model'])
        # 추가 수동 별칭 (G80 RG3 -> 더 뉴 G80, G80 등)
        extra_map = {
            'G80 (RG3)': ['더 뉴 G80', 'G80'],
            '일렉트리파이드 G80 (RG3)': ['G80 EV F/L', 'G80 EV'],
            '일렉트리파이드 GV70': ['GV70 EV F/L', 'GV70 EV'],
            '더 뉴 그랜저 (GN7)': ['디 올 뉴 그랜저', '그랜저'],
            '그랜저 (GN7)': ['디 올 뉴 그랜저', '그랜저'],
            '더 뉴 쏘렌토 4세대': ['더 뉴 쏘렌토', '쏘렌토'],
            '쏘렌토 4세대': ['쏘렌토', '더 뉴 쏘렌토'],
            '더 뉴 카니발 4세대': ['더 뉴 카니발', '카니발'],
            '카니발 4세대': ['카니발', '더 뉴 카니발'],
            '싼타페 (MX5)': ['디 올 뉴 싼타페', '싼타페'],
            '코란도 EV (이모션)': ['코란도 이모션'],
            '아이오닉 하이브리드': ['아이오닉 HEV', '아이오닉 PHEV'],
            '쏘나타 뉴 라이즈 하이브리드': ['LF쏘나타 뉴 라이즈PHEV', 'LF쏘나타 뉴 라이즈 HEV'],
            'LF 쏘나타 하이브리드': ['LF쏘나타 HEV', 'LF쏘나타 PHEV'],
            '무쏘 스포츠 칸 (Q261)': ['무쏘 칸'],
            '더 뉴 렉스턴 스포츠 칸': ['무쏘 칸', '더 뉴 렉스턴 스포츠 칸'],
        }
        if cm in extra_map:
            for em in extra_map[cm]:
                if em not in dms:
                    dms.append(em)
        cm_to_dms[cm] = dms

    # 3. _accessories 정화 및 옵션 desc 보강
    removed_zero_pkg_from_acc = 0
    restored_acc_prices = 0
    enriched_opt_descs = 0

    for cm, yrs in cat.items():
        dms = cm_to_dms.get(cm, [cm])
        for y, ydata in yrs.items():
            # 해당 (차종, 연식)의 다나와 옵션 desc 사전 구축
            danawa_desc_map = {}
            for dm in dms:
                dy_data = danawa.get(dm, {}).get(y, {})
                if isinstance(dy_data, dict):
                    for dg_name, dg_data in dy_data.items():
                        if not isinstance(dg_data, dict):
                            continue
                        for ok, ov in dg_data.get('options', {}).items():
                            if isinstance(ov, dict) and ov.get('desc'):
                                nok = norm_opt_name(ok)
                                if nok and (nok not in danawa_desc_map or len(ov['desc']) > len(danawa_desc_map[nok])):
                                    danawa_desc_map[nok] = ov['desc']

            # 해당 연식 등급들의 옵션 가격 사전 구축 (0원 악세사리 가격 복원용)
            grade_opt_price_map = {}
            for gname, gdata in ydata.items():
                if gname.startswith('_'):
                    continue
                opts = gdata.get('options', {})
                opt_items = opts.items() if isinstance(opts, dict) else [(o.get('name', ''), o) for o in opts if isinstance(o, dict)]
                for ok, ov in opt_items:
                    if isinstance(ov, dict) and (ov.get('price') or 0) > 0:
                        grade_opt_price_map[norm_opt_name(ok)] = ov['price']

            # _accessories 검사 및 정화
            accs = ydata.get('_accessories', {})
            if isinstance(accs, dict) and accs:
                new_accs = {}
                for ak, av in accs.items():
                    if not isinstance(av, dict):
                        continue
                    p = av.get('price') or 0
                    desc = av.get('desc') or ''
                    nak = norm_opt_name(ak)

                    if p > 0:
                        new_accs[ak] = av
                    else:
                        # 0원인 경우: 먼저 desc를 danawa_desc_map에 보강
                        if desc and desc != '-' and nak:
                            if nak not in danawa_desc_map or len(desc) > len(danawa_desc_map[nak]):
                                danawa_desc_map[nak] = desc

                        # 진짜 순정 악세사리인지 판별
                        is_real_acc = any(kw in ak for kw in REAL_ACC_KEYWORDS)
                        if is_real_acc:
                            # 등급 옵션에 가격이 있는지 확인
                            restored_p = grade_opt_price_map.get(nak, 0)
                            if not restored_p:
                                for gk, gp in grade_opt_price_map.items():
                                    if nak and len(nak) >= 4 and (nak in gk or gk in nak):
                                        restored_p = gp
                                        break
                            if restored_p > 0:
                                av['price'] = restored_p
                                av['price_man'] = int(round(restored_p / 10000.0))
                                restored_acc_prices += 1
                            new_accs[ak] = av
                        else:
                            removed_zero_pkg_from_acc += 1

                if new_accs:
                    ydata['_accessories'] = new_accs
                elif '_accessories' in ydata:
                    del ydata['_accessories']

            # 등급 옵션 desc 보강
            for gname, gdata in ydata.items():
                if gname.startswith('_'):
                    continue
                opts = gdata.get('options', {})
                opt_items = opts.items() if isinstance(opts, dict) else [(o.get('name', ''), o) for o in opts if isinstance(o, dict)]
                for ok, ov in opt_items:
                    if not isinstance(ov, dict):
                        continue
                    if ov.get('kind', 'optional') != 'optional':
                        continue
                    cur_desc = ov.get('desc')
                    # desc가 없거나 단순 가격 문자열('3,000,000')인 경우 다나와 설명으로 보강
                    if not cur_desc or re.fullmatch(r'[\d,\s원만]+', str(cur_desc).strip()):
                        nok = norm_opt_name(ok)
                        matched_desc = danawa_desc_map.get(nok)
                        if not matched_desc and len(nok) >= 4:
                            for dk, dv in danawa_desc_map.items():
                                if len(dk) >= 4 and (nok in dk or dk in nok):
                                    matched_desc = dv
                                    break
                        if matched_desc:
                            ov['desc'] = matched_desc
                            enriched_opt_descs += 1

    print(f"[2/3] _accessories 내 0원 일반 패키지 해설표 제거: {removed_zero_pkg_from_acc}개 (진짜 악세사리 가격 복원: {restored_acc_prices}개)")
    print(f"[3/3] 등급 선택 옵션 다나와 상세 설명(desc) 추가 보강: {enriched_opt_descs}개")

    with open(CATALOG_C_FILE, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)
    print("-> data/catalog_c.json 저장 완료!")


if __name__ == "__main__":
    main()
