# -*- coding: utf-8 -*-
"""
services/kcar_service.py
K-Car 공식 직영 매물 검색 및 실시간 소매 시세 통계 서비스
- K-Car 공식 직영 검색 API (POST https://api.kcar.com/bc/search/list/drct)
- AES-128-CBC 암호화 (Key: SKFJ2424DasfaJRI, IV: sfq241sf3dscs321)
- 백엔드 단일 진실 공급원(SSOT): 통계(평균, 최저, 최고, 중앙값, 연식별, 가격분포) 일괄 산출
"""
import os
import re
import json
import time
import base64
import urllib.request
import urllib.parse
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from services.option_package_service import normalize_opt_name as norm_opt_name
from services.part_codes import resolve_part_code, is_outer_part, is_inner_part

KEY = b"SKFJ2424DasfaJRI"
IV = b"sfq241sf3dscs321"

# 케이카 상세 JATO 옵션 캐시 (carCd -> {"timestamp": float, "options": List[Dict]})
_KCAR_JATO_CACHE: Dict[str, Dict[str, Any]] = {}
_KCAR_JATO_CACHE_TTL = 3600  # 1시간

# 유상 외장 컬러 식별 키워드 (제이 결정: 펄, 매트, 메탈릭)
COLOR_OPTION_KEYWORDS = ("펄", "매트", "메탈릭")


def is_color_option(name: str) -> bool:
    """유상 외장 컬러 항목 판정 (펄, 매트, 메탈릭)"""
    if not name:
        return False
    norm = norm_opt_name(name)
    return any(k in norm for k in COLOR_OPTION_KEYWORDS)


def fetch_kcar_jato_options(car_cd: str) -> Optional[List[Dict[str, Any]]]:
    """
    케이카 차량 상세 JATO 옵션 목록(carJatoOptList) 조회
    반환:
      - List[Dict]: 정상 조회 성공 (선택옵션 없으면 빈 배열 [])
      - None: 네트워크 통신 실패 (비상 폴백 필요)
    """
    if not car_cd or not str(car_cd).strip():
        return []

    car_cd_clean = str(car_cd).strip()
    now_ts = time.time()
    cached = _KCAR_JATO_CACHE.get(car_cd_clean)
    if cached and (now_ts - cached.get("timestamp", 0) < _KCAR_JATO_CACHE_TTL):
        return cached.get("options", [])

    url = f"https://api.kcar.com/bc/car-info-detail-of-ng?i_sCarCd={car_cd_clean}&bltbdKnd=CM050"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://www.kcar.com/bc/detail/carInfoDtl?i_sCarCd={car_cd_clean}',
        'Accept': 'application/json, text/plain, */*'
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            d = data.get('data', {})
            jato_list = d.get('carJatoOptList')
            if jato_list is None:
                jato_list = []
            _KCAR_JATO_CACHE[car_cd_clean] = {
                "timestamp": now_ts,
                "options": jato_list
            }
            return jato_list
    except Exception as e:
        print(f"[K-Car JATO API 오류] carCd='{car_cd_clean}': {e}", flush=True)
        return None


_KCAR_DETAIL_CACHE: Dict[str, Dict[str, Any]] = {}
_KCAR_DETAIL_CACHE_TTL = 600  # 10분 캐시

# 케이카 3Dview API(https://api.kcar.com/bc/dgnos/3dview) 실측 부위명 한글 매핑
_KCAR_3D_PART_KR_MAP = {
    'bonnet': '후드(보닛)',
    'roof': '루프 패널',
    'trunk': '트렁크리드',
    'cabin': '캐빈/바디',
    'front-fender-left': '프론트 휀더(좌)',
    'front-door-left': '프론트 도어(좌)',
    'back-door-left': '리어 도어(좌)',
    'front-fender-right': '프론트 휀더(우)',
    'front-door-right': '프론트 도어(우)',
    'back-door-right': '리어 도어(우)',
    'front-panel': '프론트 패널',
    'radiator': '라디에이터 서포트',
    'crossmember': '크로스멤버',
    'dash-panel': '대쉬 패널',
    'floor-panel': '플로어 패널',
    'packagetray': '패키지 트레이',
    'trunk-floor-panel': '트렁크 플로어',
    'rear-panel': '리어 패널',
    'sidemember-front-left': '프론트 사이드멤버(좌)',
    'inside-panel-left': '인사이드 패널(좌)',
    'wheelhouse-front-left': '프론트 휠하우스(좌)',
    'a-pillar-left': 'A필러(좌)',
    'b-pillar-left': 'B필러(좌)',
    'quarter-panel-left': '쿼터 패널(좌)',
    'wheelhouse-back-left': '리어 휠하우스(좌)',
    'sidemember-back-left': '리어 사이드멤버(좌)',
    'sidesill-left': '사이드실 패널(좌)',
    'sidemember-front-right': '프론트 사이드멤버(우)',
    'inside-panel-right': '인사이드 패널(우)',
    'wheelhouse-front-right': '프론트 휠하우스(우)',
    'a-pillar-right': 'A필러(우)',
    'b-pillar-right': 'B필러(우)',
    'quarter-panel-right': '쿼터 패널(우)',
    'wheelhouse-back-right': '리어 휠하우스(우)',
    'sidemember-back-right': '리어 사이드멤버(우)',
    'sidesill-right': '사이드실 패널(우)',
}


def _fetch_kcar_3d_damage(car_cd_clean: str, headers: Dict[str, str], base_accident_type: str, base_change_cnt: int, base_metal_cnt: int):
    """케이카 3D 진단 부위별 실측 상세 조회 (https://api.kcar.com/bc/dgnos/3dview)"""
    replace_names: List[str] = []
    repair_names: List[str] = []
    damage_parts_raw: List[Dict[str, str]] = []
    change_cnt = base_change_cnt
    metal_cnt = base_metal_cnt
    accident_type = base_accident_type

    try:
        dgnos_url = f"https://api.kcar.com/bc/dgnos/3dview?i_sCarCd={car_cd_clean}"
        dgnos_req = urllib.request.Request(dgnos_url, headers=headers)
        with urllib.request.urlopen(dgnos_req, timeout=4) as dgnos_resp:
            dgnos_json = json.loads(dgnos_resp.read().decode('utf-8'))
            dgnos_data = dgnos_json.get('data', {})
            ext_items = dgnos_data.get('exteriorData', []) or []
            frm_items = dgnos_data.get('frameData', []) or []
            has_inner_damage = False
            has_outer_damage = False

            for item in (ext_items + frm_items):
                part_id = str(item.get('part') or '').strip()
                part_status = str(item.get('status') or '').strip()
                if not part_id or part_status == '1':
                    continue

                kr_label = _KCAR_3D_PART_KR_MAP.get(part_id, part_id)
                damage_parts_raw.append({
                    "part": part_id,
                    "status": part_status,
                    "name": kr_label
                })

                if part_status == '2':  # 교환 (X)
                    replace_names.append(kr_label)
                elif part_status == '3':  # 판금/용접 (W)
                    repair_names.append(kr_label)

                # 외판 / 골격 구분 판정 (services.part_codes 단일 기준)
                code = resolve_part_code(part_id) or resolve_part_code(kr_label)
                if code:
                    if is_inner_part(code):
                        has_inner_damage = True
                    elif is_outer_part(code):
                        has_outer_damage = True
                else:
                    if item in frm_items:
                        has_inner_damage = True
                    else:
                        has_outer_damage = True

            if replace_names or repair_names:
                change_cnt = len(replace_names)
                metal_cnt = len(repair_names)
                if has_inner_damage:
                    accident_type = '사고'
                elif has_outer_damage and accident_type == '무사고':
                    accident_type = '단순수리'
    except Exception:
        pass

    return replace_names, repair_names, damage_parts_raw, change_cnt, metal_cnt, accident_type


def fetch_kcar_car_detail(car_cd: str, include_3d: bool = True) -> Optional[Dict[str, Any]]:
    """K-Car 단일 차량 상세 정보 조회 (car-info-detail-of-ng 단 1회 호출)
    - 기본 스펙, 날짜(광고/성능/발급), 사고 판정 및 교환/판금, 보험 이력, 소유/용도, 옵션, 타이어(mm) 추출
    - 차량번호(cno), 차대번호(vin)는 보안을 위해 절대 반환하지 않음
    """
    if not car_cd or not str(car_cd).strip():
        return None

    car_cd_clean = str(car_cd).strip()
    now_ts = time.time()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://www.kcar.com/bc/detail/carInfoDtl?i_sCarCd={car_cd_clean}',
        'Accept': 'application/json, text/plain, */*'
    }

    cached = _KCAR_DETAIL_CACHE.get(car_cd_clean)
    if cached and (now_ts - cached.get("timestamp", 0) < _KCAR_DETAIL_CACHE_TTL):
        cached_data = cached.get("data")
        if cached_data:
            if not include_3d or cached_data.get("has3d"):
                return cached_data
            # 프리패치(include_3d=False)로 캐시된 항목을 상세 카드 클릭(include_3d=True)할 때 3D 도면만 추가 조회
            acc_obj = cached_data.get("accident") or {}
            rep_names, fix_names, dmg_parts, chg_cnt, mtl_cnt, acc_type = _fetch_kcar_3d_damage(
                car_cd_clean,
                headers,
                str(acc_obj.get("accidentType") or "무사고"),
                int(acc_obj.get("changeCount") or 0),
                int(acc_obj.get("metalCount") or 0)
            )
            acc_obj["accidentType"] = acc_type
            acc_obj["changeCount"] = chg_cnt
            acc_obj["metalCount"] = mtl_cnt
            acc_obj["replaceNames"] = rep_names
            acc_obj["repairNames"] = fix_names
            acc_obj["damageParts"] = dmg_parts
            cached_data["accident"] = acc_obj
            cached_data["replaceNames"] = rep_names
            cached_data["repairNames"] = fix_names
            cached_data["has3d"] = True
            return cached_data

    url = f"https://api.kcar.com/bc/car-info-detail-of-ng?i_sCarCd={car_cd_clean}&bltbdKnd=CM050"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            d = data.get('data', {})
            if not d:
                return None

            rvo = d.get('rvo', {})
            m = d.get('masterInfo', {})
            ch = d.get('carhistory', {})

            # 1. 기본 정보
            model_nm = rvo.get('modelNm') or rvo.get('carWhlNm') or ''
            grd_nm = rvo.get('grdNm') or ''
            grd_dtl_nm = rvo.get('grdDtlNm') or ''
            grade_full = f"{grd_nm} {grd_dtl_nm}".strip()
            sal_prc = int(rvo.get('salprc') or 0)
            milg = int(rvo.get('milg') or 0)
            color = rvo.get('extrColorNm') or ''
            center = rvo.get('cntrNm') or ''
            car_stat = rvo.get('statCdNm') or '판매중'
            year_val = rvo.get('regModelyr') or rvo.get('prdcnYr') or ''
            mfg_dt = rvo.get('mfgDt') or ''
            first_reg_dt = rvo.get('fstCarRegYm') or m.get('firstregdt') or ''

            # 2. 날짜 정보 및 성능점검일 기준 재고일(오늘 - 성능점검일) 산출
            reg_dttm = rvo.get('regDttm') or m.get('regDttm') or ''
            pfmnc_dt = str(m.get('pfmncCkqtDt') or '').strip()
            issue_dt = m.get('issuedt') or ''
            insp_nm = m.get('inspNm') or ''

            check_date_str = "-"
            holding_days: Optional[int] = None
            pfmnc_digits = re.sub(r'\D', '', pfmnc_dt)
            if len(pfmnc_digits) >= 8:
                check_date_str = f"{pfmnc_digits[2:4]}-{pfmnc_digits[4:6]}-{pfmnc_digits[6:8]}"
                try:
                    p_dt = datetime.strptime(pfmnc_digits[:8], "%Y%m%d")
                    holding_days = max(0, (datetime.now() - p_dt).days)
                except Exception:
                    holding_days = None

            # 3. 사고 판정 및 교환/판금
            # 실측 매핑: acdtHistYn: '1'(없음)/'2'(있음), smplReprYn: '1'(없음)/'2'(있음)
            acdt_yn = str(m.get('acdtHistYn') or rvo.get('acdtHistYn') or '1').strip()
            smpl_yn = str(m.get('smplReprYn') or '1').strip()

            if acdt_yn == '2':
                accident_type = '사고'
            elif smpl_yn == '2':
                accident_type = '단순수리'
            else:
                accident_type = '무사고'

            change_cnt = int(d.get('changeCnt') or 0)
            metal_cnt = int(d.get('metalCnt') or 0)

            # 3-1. 케이카 3D 진단 부위별 실측 상세 조회 (include_3d=True일 때만 호출)
            replace_names: List[str] = []
            repair_names: List[str] = []
            damage_parts_raw: List[Dict[str, str]] = []

            if include_3d:
                replace_names, repair_names, damage_parts_raw, change_cnt, metal_cnt, accident_type = _fetch_kcar_3d_damage(
                    car_cd_clean, headers, accident_type, change_cnt, metal_cnt
                )

            # 4. 보험 내역 (carhistory)
            gnrl_ttls = int(ch.get('gnrlTtlsAcdtCnt') or 0)
            fldg_cnt = int(ch.get('fldgAcdtCnt') or 0)
            rbr_cnt = int(ch.get('rbrTtlsAcdtCnt') or 0)
            my_acc_cnt = int(ch.get('owncarDmgeAcdtCnt') or 0)
            my_acc_amt = int(ch.get('owncarDmgeInsrAmtSum') or 0)
            othr_acc_cnt = int(ch.get('othrcarWrdgAcdtCnt') or 0)
            othr_acc_amt = int(ch.get('othrcarWrdgInsrAmtSum') or 0)

            # 5. 소유 및 주행
            is_rental = (rvo.get('rentRegYn') == 'Y') or (ch.get('useCd') == 1)
            is_commercial = (ch.get('bizuseHistYn') == 'Y')
            owner_change_cnt = int(ch.get('ownrChngCnt') or len(d.get('carOwnrChngHistList') or []))

            milg_histories = []
            for mh in d.get('carHistMilgList', []):
                milg_histories.append({
                    "date": mh.get('milgClctDt') or mh.get('regDttm') or '',
                    "mileage": mh.get('milg'),
                    "org": mh.get('milgOffrOrg') or ''
                })

            # 6. 선택 옵션 (유상 외장 컬러 제외) - 표준 OptionItem 배열 구성
            jato_opts = []
            opt_total_prc = 0
            for o in d.get('carJatoOptList', []):
                opt_name = o.get('optNm') or ''
                if not opt_name or is_color_option(opt_name):
                    continue
                p_raw = int(o.get('optPrc') or 0)
                p_man = p_raw // 10000 if p_raw >= 10000 else p_raw
                opt_code = str(o.get('optCd') or '')
                jato_opts.append({
                    "code": opt_code,
                    "name": opt_name,
                    "raw_name": opt_name,
                    "price": p_man * 10000,
                    "price_man": p_man,
                    "source": "api" if p_man > 0 else "unpriced",
                    "match_status": "exact",
                    "desc": ""
                })
                opt_total_prc += p_man

            # 7. 타이어 (4본 잔여 트레드 mm 실측값만, 추정 km 제외)
            tires = []
            for t in d.get('tireDtlList', []):
                sub_nm = t.get('subCdNm') or ''
                if '휠' in sub_nm:
                    continue
                rem_mm = t.get('tirResQty')
                try:
                    rem_val = float(rem_mm) if rem_mm is not None else 0.0
                except (ValueError, TypeError):
                    rem_val = 0.0
                tires.append({
                    "position": sub_nm,
                    "remainMm": rem_val,
                    "width": t.get('tirSidWidth') or '',
                    "ratio": t.get('tirFlatRt') or '',
                    "inch": t.get('tirInch') or '',
                    "dotYear": t.get('tirPrdcnYr') or '',
                    "dotWeek": t.get('tirPrdcnWkcnt') or ''
                })

            res = {
                "carCd": car_cd_clean,
                "modelName": model_nm,
                "gradeFullName": grade_full,
                "year": str(year_val),
                "mfgDate": str(mfg_dt),
                "firstRegDate": str(first_reg_dt),
                "mileage": milg,
                "price": sal_prc,
                "color": color,
                "center": center,
                "status": car_stat,
                "detailUrl": f"https://www.kcar.com/bc/detail/carInfoDtl?i_sCarCd={car_cd_clean}",
                "checkDate": check_date_str,
                "holdingDays": holding_days,
                "has3d": bool(include_3d),
                "dates": {
                    "regDate": str(reg_dttm),
                    "pfmncDate": str(pfmnc_dt),
                    "issueDate": str(issue_dt),
                    "inspName": str(insp_nm)
                },
                "accident": {
                    "accidentType": accident_type,
                    "acdtHistYn": acdt_yn,
                    "smplReprYn": smpl_yn,
                    "changeCount": change_cnt,
                    "metalCount": metal_cnt,
                    "replaceNames": replace_names,
                    "repairNames": repair_names,
                    "damageParts": damage_parts_raw
                },
                "replaceNames": replace_names,
                "repairNames": repair_names,
                "insurance": {
                    "totalLoss": gnrl_ttls > 0,
                    "flood": fldg_cnt > 0,
                    "theft": rbr_cnt > 0,
                    "myAccidentCount": my_acc_cnt,
                    "myAccidentCost": my_acc_amt,
                    "otherAccidentCount": othr_acc_cnt,
                    "otherAccidentCost": othr_acc_amt
                },
                "history": {
                    "isRental": is_rental,
                    "isCommercial": is_commercial,
                    "ownerChangeCount": owner_change_cnt,
                    "mileageHistories": milg_histories
                },
                "options": {
                    "items": jato_opts,
                    "totalPrice": opt_total_prc
                },
                "tires": tires
            }

            _KCAR_DETAIL_CACHE[car_cd_clean] = {
                "timestamp": now_ts,
                "data": res
            }
            return res
    except Exception as e:
        print(f"[K-Car Detail API 오류] carCd='{car_cd_clean}': {e}", flush=True)
        return None


def fallback_calc_comp_opt_from_optnnm(optn_nm: str, catalog_map: Dict[str, int]) -> int:
    """상세 API 통신 실패 시 비상 격리 폴백: optnNm 파이프 파싱 + 부분문자열 매칭"""
    if not optn_nm:
        return 0
    tokens = [t.strip() for t in optn_nm.split('|') if t.strip()]
    raw_sum = 0
    for t in tokens:
        if is_color_option(t):
            continue
        t_norm = norm_opt_name(t)
        matched_p = catalog_map.get(t_norm, 0)
        if matched_p == 0:
            for cn_norm, cp in catalog_map.items():
                if (t_norm in cn_norm and len(t_norm) >= 2) or (cn_norm in t_norm and len(cn_norm) >= 2):
                    matched_p = cp
                    break
        if matched_p > 0:
            raw_sum += matched_p
    return raw_sum

# KCar 제조사 및 모델 코드 매핑 테이블 (https://market-api.kcar.com/api/v1/ds/getModelListCount 공식 전수 기준)
# [필수 규칙] 하이브리드 모델 등록 시 양방향 어순 등록:
# 1. '[차종] [N세대] 하이브리드'와 '[차종] 하이브리드 [N세대]' 양방향 모두 등록할 것.
# 2. '더 뉴 [차종] [N세대] 하이브리드' vs '더 뉴 [차종] 하이브리드 [N세대]' 등 수식어 포함형도 대칭 등록.
# 3. frontend/src/utils/kcarUrl.ts의 KCAR_MODEL_GROUPS와 100% 동일하게 유지할 것.
# 4. 신규 추가 후 tests/test_kcar_hybrid_variants.py 실행 필수.
KCAR_MNUFTR_MAP = {
    "현대": "001",
    "기아": "002",
    "쉐보레": "003",
    "쉐보레(GM대우)": "003",
    "쉐보레(대우)": "003",
    "GM대우": "003",
    "KGM": "004",
    "KG모빌리티": "004",
    "KG모빌리티(쌍용)": "004",
    "쌍용": "004",
    "르노코리아": "005",
    "르노코리아(삼성)": "005",
    "르노삼성": "005",
    "제네시스": "007",
    "아우디": "011",
    "BMW": "012",
    "벤츠": "013",
    "볼보": "017",
    "렉서스": "035",
    "테슬라": "087",
    "포르쉐": "015",
    "도요타": "031",
    "미니": "054",
    "BYD": "093",
    "랜드로버": "020",
    "폭스바겐": "014",
    "포드": "024",
    "폴스타": "091",
    "지프": "083",
    "혼다": "027",
    "링컨": "044",
    "푸조": "021",
    "캐딜락": "043",
    "람보르기니": "049",
    "벤틀리": "050",
    "페라리": "041",
    "마세라티": "053",
    "재규어": "019",
    "GMC": "056",
    "롤스로이스": "047",
    "피아트": "018",
    "맥라렌": "084",
    "인피니티": "058",
    "마이바흐": "080",
    "스마트": "081",
    "닛산": "033",
    "크라이슬러": "023",
    "시트로엥": "022",
    "지커": "094",
    "포톤": "085",
    "북기은상": "086",
    "동풍소콘": "090",
    "사브": "016",
    "스바루": "052",
    "애스턴마틴": "070",
    "마쯔다": "029",
    "이스즈": "028",
    "스즈키": "037",
    "험머": "048",
    "닷지": "034",
    "미쯔비시": "030",
    "대우버스": "088",
    "기타 제조사": "006",
}

# (제조사코드, 모델그룹코드): {모델명: 모델코드}
KCAR_MODEL_GROUP_MAP = {
    # 현대 (001)
    ("001", "001"): {  # i30
        "i30": "084",
        "i30(신형)": "117",
        "더 뉴 i30": "130",
        "i30 (PD)": "140",
        "i30 cw": "094",
    },
    ("001", "004"): {  # 그랜저
        "그랜저 TG": "040",
        "더 럭셔리 그랜저": "101",
        "그랜저 뉴 럭셔리": "103",
        "그랜저 HG": "106",
        "그랜저 HG 하이브리드": "125",
        "그랜저 IG": "141",
        "그랜저 IG 하이브리드": "143",
        "그랜저 6세대 하이브리드": "143",
        "그랜저 하이브리드 6세대": "143",
        "더 뉴 그랜저": "171",
        "더 뉴 그랜저 IG": "171",
        "더 뉴 그랜저 하이브리드": "174",
        "더 뉴 그랜저 IG 하이브리드": "174",
        "그랜저 (GN7)": "199",
        "그랜저 하이브리드 (GN7)": "200",
        "그랜저 (GN7) 하이브리드": "200",
        "그랜저 7세대 하이브리드": "200",
        "그랜저 하이브리드 7세대": "200",
        "디 올 뉴 그랜저 하이브리드": "200",
        "디 올 뉴 그랜저 (GN7) 하이브리드": "200",
        "디 올 뉴 그랜저 하이브리드 (GN7)": "200",
        "더 뉴 그랜저 (GN7)": "230",
        "더 뉴 그랜저 하이브리드 (GN7)": "231",
        "더 뉴 그랜저 (GN7) 하이브리드": "231",
        "뉴 그랜저 XG": "069",
        "그랜저 XG": "020",
    },
    ("001", "010"): {  # 마이티
        "올 뉴 마이티": "162",
        "e-마이티": "079",
        "마이티2": "054",
    },
    ("001", "011"): {  # 베라크루즈
        "베라크루즈": "082",
    },
    ("001", "012"): {  # 베르나
        "베르나 트랜스폼": "097",
        "베르나(신형)": "042",
        "New 베르나": "070",
        "베르나": "004",
    },
    ("001", "015"): {  # 스타렉스
        "그랜드 스타렉스": "083",
        "더 뉴 그랜드 스타렉스": "148",
        "스타렉스": "026",
        "스타렉스 점보": "035",
    },
    ("001", "017"): {  # 싼타페
        "싼타페 CM": "080",
        "싼타페 DM": "111",
        "싼타페 더 프라임": "134",
        "싼타페 TM": "150",
        "더 뉴 싼타페": "177",
        "더 뉴 싼타페 하이브리드": "191",
        "더 뉴 싼타페 하이브리드 (TM)": "191",
        "더 뉴 싼타페 (TM) 하이브리드": "191",
        "싼타페 하이브리드 (TM)": "191",
        "디 올 뉴 싼타페": "208",
        "디 올 뉴 싼타페 하이브리드": "209",
        "디 올 뉴 싼타페 (MX5) 하이브리드": "209",
        "디 올 뉴 싼타페 하이브리드 (MX5)": "209",
        "싼타페 5세대 하이브리드": "209",
        "싼타페 하이브리드 5세대": "209",
        "싼타페 (MX5) 하이브리드": "209",
        "싼타페 하이브리드 (MX5)": "209",
        "싼타페": "038",
        "싼타페 (TM) 하이브리드": "191",
    },
    ("001", "018"): {  # 쏘나타
        "NF 쏘나타": "039",
        "NF 쏘나타 트랜스폼": "092",
        "YF 쏘나타": "098",
        "쏘나타 하이브리드": "108",
        "쏘나타 더 브릴리언트": "115",
        "LF 쏘나타": "126",
        "LF 쏘나타 하이브리드": "128",
        "쏘나타 하이브리드 (LF)": "128",
        "쏘나타 하이브리드 LF": "128",
        "쏘나타 뉴 라이즈": "142",
        "쏘나타 뉴 라이즈 하이브리드": "144",
        "쏘나타 DN8": "163",
        "쏘나타 (DN8)": "163",
        "쏘나타 DN8 하이브리드": "169",
        "쏘나타 (DN8) 하이브리드": "169",
        "쏘나타 하이브리드 (DN8)": "169",
        "쏘나타 하이브리드 DN8": "169",
        "쏘나타 8세대 하이브리드": "169",
        "쏘나타 하이브리드 8세대": "169",
        "쏘나타 디 엣지": "203",
        "쏘나타 디 엣지 하이브리드": "204",
        "쏘나타 하이브리드 디 엣지": "204",
        "쏘나타 (DN8) 하이브리드 디 엣지": "204",
        "쏘나타 뉴 라이즈 플러그 인 하이브리드": "166",
        "LF 쏘나타 플러그 인 하이브리드": "170",
        "뉴 EF 쏘나타": "061",
        "쏘나타 (LF) 하이브리드": "128",
    },
    ("001", "019"): {  # 아반떼
        "아반떼 HD": "081",
        "아반떼 하이브리드": "095",
        "아반떼 MD": "104",
        "아반떼 쿠페": "121",
        "더 뉴 아반떼": "123",
        "아반떼 AD": "136",
        "더 뉴 아반떼 AD": "154",
        "아반떼 (CN7)": "176",
        "아반떼 하이브리드 (CN7)": "181",
        "아반떼 (CN7) 하이브리드": "181",
        "아반떼 7세대 하이브리드": "181",
        "아반떼 하이브리드 7세대": "181",
        "아반떼 N": "195",
        "더 뉴 아반떼 (CN7)": "206",
        "더 뉴 아반떼 하이브리드 (CN7)": "207",
        "더 뉴 아반떼 (CN7) 하이브리드": "207",
        "더 뉴 아반떼 하이브리드": "207",
        "더 뉴 아반떼 7세대 하이브리드": "207",
        "더 뉴 아반떼 N": "211",
        "디 올 뉴 아반떼 (CN8)": "232",
        "디 올 뉴 아반떼 하이브리드 (CN8)": "233",
        "디 올 뉴 아반떼 (CN8) 하이브리드": "233",
        "뉴 아반떼 XD": "071",
        "아반떼 XD": "037",
        "더 뉴 아반떼 하이브리드 7세대": "207",
    },
    ("001", "021"): {  # 에쿠스
        "에쿠스(신형)": "100",
        "에쿠스": "022",
    },
    ("001", "022"): {  # 엑센트
        "엑센트(신형)": "105",
    },
    ("001", "025"): {  # 제네시스
        "제네시스 DH": "124",
        "더 뉴 제네시스 쿠페": "112",
        "제네시스 쿠페": "093",
        "제네시스": "088",
    },
    ("001", "026"): {  # 카운티
        "카운티 일렉트릭": "187",
        "뉴 카운티": "998",
        "e-카운티": "086",
        "카운티": "064",
    },
    ("001", "029"): {  # 클릭
        "뉴 클릭": "041",
        "클릭": "068",
    },
    ("001", "030"): {  # 테라칸
        "테라칸": "062",
    },
    ("001", "031"): {  # 투스카니
        "투스카니(신형)": "102",
        "투스카니": "067",
    },
    ("001", "032"): {  # 투싼
        "투싼 ix": "096",
        "뉴 투싼 ix": "122",
        "올 뉴 투싼": "133",
        "더 올뉴투싼": "133",
        "올 뉴 투싼 TL": "155",
        "투싼 (4세대)": "179",
        "투싼 4세대": "179",
        "투싼 (NX4)": "179",
        "투싼 하이브리드 (4세대)": "183",
        "투싼 4세대 하이브리드": "183",
        "투싼 하이브리드 4세대": "183",
        "투싼 (NX4) 하이브리드": "183",
        "투싼 하이브리드 (NX4)": "183",
        "투싼 NX4 하이브리드": "183",
        "더 뉴 투싼": "213",
        "더 뉴 투싼 하이브리드": "214",
        "더 뉴 투싼 4세대 하이브리드": "214",
        "더 뉴 투싼 하이브리드 4세대": "214",
        "디 올 뉴 투싼": "234",
        "디 올 뉴 투싼 하이브리드": "235",
        "투싼 (4세대) 하이브리드": "183",
        "투싼": "076",
    },
    ("001", "034"): {  # 트라제 XG
        "트라제 XG": "027",
    },
    ("001", "037"): {  # 포터
        "포터2 LPi 2.5 터보 특장": "215",
        "포터2 LPi 2.5 터보 카고": "212",
        "포터2 일렉트릭": "175",
        "포터2 CRDi 특장": "158",
        "포터2 CRDi 카고": "159",
        "포터2 터보인터쿨러 카고": "160",
        "뉴포터": "060",
    },
    ("001", "043"): {  # 대형트럭
        "대형트럭": "075",
    },
    ("001", "044"): {  # 메가트럭
        "메가트럭": "089",
    },
    ("001", "045"): {  # 에어로버스
        "뉴 슈퍼에어로시티": "189",
        "e-에어로타운": "087",
        "슈퍼에어로시티": "078",
        "에어로스페이스": "099",
        "에어로타운": "072",
        "에어로시티": "066",
        "에어로버스": "074",
    },
    ("001", "046"): {  # 유니버스
        "유니버스": "085",
    },
    ("001", "048"): {  # 벨로스터
        "벨로스터": "107",
        "더 뉴 벨로스터": "129",
        "벨로스터 (JS)": "149",
        "벨로스터-N": "156",
    },
    ("001", "049"): {  # i40
        "i40": "109",
        "i40 살룬": "110",
        "더 뉴 i40": "131",
        "더 뉴 i40 살룬": "132",
    },
    ("001", "050"): {  # 맥스크루즈
        "맥스크루즈": "118",
        "더 뉴 맥스크루즈": "135",
    },
    ("001", "051"): {  # 아슬란
        "아슬란": "127",
    },
    ("001", "052"): {  # 쏠라티
        "쏠라티": "137",
    },
    ("001", "053"): {  # 아이오닉
        "아이오닉 하이브리드": "138",
        "아이오닉 일렉트릭": "139",
        "더 뉴 아이오닉 하이브리드": "161",
        "더 뉴 아이오닉 일렉트릭": "172",
        "아이오닉 5": "186",
        "아이오닉 6": "198",
        "아이오닉 5 N": "210",
        "더 뉴 아이오닉 5": "216",
        "아이오닉 9": "223",
        "더 뉴 아이오닉 6": "225",
        "더 뉴 아이오닉 6 N": "226",
        "더 뉴 아이오닉 플러그인 하이브리드": "165",
        "아이오닉 플러그인 하이브리드": "164",
    },
    ("001", "055"): {  # 코나
        "코나": "146",
        "코나 일렉트릭": "152",
        "코나 하이브리드": "173",
        "더 뉴 코나": "180",
        "더 뉴 코나 하이브리드": "182",
        "코나 N": "194",
        "코나 (SX2)": "201",
        "코나 하이브리드 (SX2)": "202",
        "코나 (SX2) 하이브리드": "202",
        "코나 2세대 하이브리드": "202",
        "코나 하이브리드 2세대": "202",
        "디 올 뉴 코나 하이브리드": "202",
        "디 올 뉴 코나 (SX2) 하이브리드": "202",
        "디 올 뉴 코나 하이브리드 (SX2)": "202",
        "코나 일렉트릭 (SX2)": "205",
    },
    ("001", "056"): {  # 넥쏘
        "넥쏘": "151",
        "디 올 뉴 넥쏘": "224",
    },
    ("001", "058"): {  # 팰리세이드
        "팰리세이드": "157",
        "더 뉴 팰리세이드": "197",
        "디 올 뉴 팰리세이드": "221",
        "디 올 뉴 팰리세이드 하이브리드": "222",
        "팰리세이드 하이브리드": "222",
    },
    ("001", "059"): {  # 베뉴
        "베뉴": "167",
    },
    ("001", "061"): {  # 포레스트
        "포레스트": "178",
    },
    ("001", "063"): {  # 스타리아
        "스타리아": "185",
        "스타리아 하이브리드": "217",
        "더 뉴 스타리아": "227",
        "더 뉴 스타리아 하이브리드": "228",
        "더 뉴 스타리아 일렉트릭": "229",
    },
    ("001", "064"): {  # 파비스
        "파비스": "188",
    },
    ("001", "067"): {  # 캐스퍼
        "캐스퍼": "196",
        "캐스퍼 일렉트릭": "219",
        "더 뉴 캐스퍼": "220",
    },
    ("001", "068"): {  # ST1
        "ST1": "218",
    },
    # 기아 (002)
    ("002", "001"): {  # K5
        "K5": "092",
        "K5 하이브리드": "097",
        "더 뉴 K5": "106",
        "K5 2세대": "118",
        "K5 하이브리드 2세대": "121",
        "K5 2세대 하이브리드": "121",
        "더 뉴 K5 2세대": "135",
        "더 뉴 K5 하이브리드 2세대": "139",
        "더 뉴 K5 2세대 하이브리드": "139",
        "K5 3세대": "157",
        "신형 K5": "157",
        "K5 3세대 하이브리드": "162",
        "K5 하이브리드 3세대": "162",
        "더 뉴 K5 3세대": "188",
        "더 뉴 K5 3세대 하이브리드": "189",
        "더 뉴 K5 하이브리드 3세대": "189",
        "더 뉴 K5 하이브리드": "189",
    },
    ("002", "002"): {  # K7
        "K7": "089",
        "더 프레스티지 K7": "096",
        "더 뉴 K7": "104",
        "K7 하이브리드": "111",
        "올 뉴 K7": "122",
        "올 뉴 K7 하이브리드": "129",
        "올 뉴 K7 하이브리드 2세대": "129",
        "K7 하이브리드 2세대": "129",
        "K7 2세대 하이브리드": "129",
        "K7 프리미어": "152",
        "K7 프리미어 하이브리드": "154",
        "올 뉴 K7 2세대 하이브리드": "129",
    },
    ("002", "009"): {  # 로체
        "로체 이노베이션": "084",
        "로체 어드밴스": "081",
        "로체": "040",
    },
    ("002", "013"): {  # 모닝
        "뉴모닝": "083",
        "올 뉴 모닝": "095",
        "더 뉴 모닝": "116",
        "올 뉴 모닝 (JA)": "130",
        "모닝 어반": "165",
        "더 뉴 모닝 (JA)": "184",
        "모닝": "069",
    },
    ("002", "015"): {  # 모하비
        "모하비": "080",
        "더 뉴 모하비": "123",
        "모하비 더 마스터": "156",
    },
    ("002", "018"): {  # 봉고III
        "봉고III 미니버스": "071",
        "봉고프론티어": "052",
    },
    ("002", "025"): {  # 스포티지
        "스포티지 R": "091",
        "더 뉴 스포티지 R": "107",
        "스포티지 4세대": "119",
        "스포티지 더 볼드": "141",
        "디 올 뉴 스포티지": "175",
        "스포티지 5세대": "175",
        "디 올 뉴 스포티지 하이브리드": "176",
        "디 올 뉴 스포티지 하이브리드 5세대": "176",
        "스포티지 5세대 하이브리드": "176",
        "스포티지 하이브리드 5세대": "176",
        "더 뉴 스포티지": "198",
        "더 뉴 스포티지 하이브리드": "199",
        "더 뉴 스포티지 5세대 하이브리드": "199",
        "더 뉴 스포티지 하이브리드 5세대": "199",
        "New 스포티지": "072",
        "디 올 뉴 스포티지 5세대 하이브리드": "176",
    },
    ("002", "026"): {  # 쎄라토
        "뉴쎄라토": "041",
        "쎄라토": "038",
    },
    ("002", "027"): {  # 쏘렌토
        "쏘렌토 R": "087",
        "뉴 쏘렌토 R": "102",
        "올 뉴 쏘렌토": "114",
        "더 뉴 쏘렌토": "133",
        "쏘렌토 4세대": "163",
        "신형 쏘렌토 (MQ4)": "163",
        "쏘렌토 4세대 하이브리드": "164",
        "쏘렌토 하이브리드 4세대": "164",
        "쏘렌토 하이브리드 (4세대)": "164",
        "신형 쏘렌토 하이브리드": "164",
        "더 뉴 쏘렌토 4세대": "185",
        "더 뉴 쏘렌토 4세대 하이브리드": "186",
        "더 뉴 쏘렌토 하이브리드 4세대": "186",
        "더 뉴 쏘렌토 하이브리드": "186",
        "뉴쏘렌토": "077",
        "쏘렌토": "036",
        "쏘렌토 (4세대) 하이브리드": "164",
    },
    ("002", "028"): {  # 쏘울
        "쏘울 부스터": "147",
        "쏘울 부스터 EV": "148",
        "더 뉴 쏘울": "128",
        "쏘울 EV": "112",
        "올 뉴 쏘울": "110",
        "쏘울": "086",
    },
    ("002", "033"): {  # 오피러스
        "오피러스 프리미엄": "093",
        "뉴오피러스": "082",
        "오피러스": "037",
    },
    ("002", "034"): {  # 옵티마
        "옵티마": "035",
    },
    ("002", "036"): {  # 카니발
        "그랜드 카니발": "074",
        "뉴카니발": "075",
        "카니발 R": "090",
        "올 뉴 카니발": "113",
        "더 뉴 카니발": "137",
        "카니발 (4세대)": "166",
        "카니발 4세대": "166",
        "신형 카니발": "166",
        "더 뉴 카니발 4세대": "190",
        "더 뉴 카니발 하이브리드 4세대": "191",
        "더 뉴 카니발 4세대 하이브리드": "191",
        "더 뉴 카니발 하이브리드": "191",
        "카니발 하이브리드 4세대": "191",
        "카니발 4세대 하이브리드": "191",
        "카니발 하이브리드": "191",
        "하이브리드 4세대": "191",
    },
    ("002", "037"): {  # 카렌스
        "뉴카렌스": "076",
        "올 뉴 카렌스": "105",
        "더 뉴 카렌스": "127",
    },
    ("002", "051"): {  # 포르테
        "포르테 해치백": "094",
        "포르테 쿱": "088",
        "포르테": "085",
    },
    ("002", "053"): {  # 프라이드
        "더 뉴 프라이드": "115",
        "올 뉴 프라이드": "098",
        "프라이드(신형)": "039",
        "프라이드": "002",
    },
    ("002", "058"): {  # 레이
        "레이": "099",
        "더 뉴 레이": "134",
        "레이 EV": "153",
        "더 뉴 기아 레이": "182",
        "더 뉴 기아 레이 EV": "187",
    },
    ("002", "059"): {  # K9
        "K9": "101",
        "더 뉴 K9": "117",
        "더 K9": "138",
        "더 뉴 K9 2세대": "174",
    },
    ("002", "060"): {  # K3
        "K3": "103",
        "더 뉴 K3": "120",
        "올 뉴 K3": "136",
        "K3 GT": "142",
        "더 뉴 K3 2세대": "171",
        "더 뉴 K3 GT 2세대": "172",
        "더 뉴 K3 유로": "125",
        "더 뉴 K3 쿱": "124",
        "K3 유로": "109",
        "K3 쿱": "108",
    },
    ("002", "061"): {  # 니로
        "니로": "126",
        "니로 하이브리드": "126",
        "니로 EV": "140",
        "니로 플러그인 하이브리드": "149",
        "더 뉴 니로": "150",
        "더 뉴 니로 하이브리드": "150",
        "디 올 뉴 니로": "177",
        "디 올 뉴 니로 하이브리드": "177",
        "니로 하이브리드 2세대": "177",
        "니로 2세대 하이브리드": "177",
        "디 올 뉴 니로 EV": "179",
        "니로 플러스": "180",
        "더 뉴 니로 (SG2)": "206",
        "더 뉴 니로 플러그인 하이브리드": "151",
    },
    ("002", "062"): {  # 스팅어
        "스팅어": "131",
        "스팅어 마이스터": "167",
    },
    ("002", "063"): {  # 스토닉
        "스토닉": "132",
    },
    ("002", "064"): {  # 봉고III 트럭
        "더 뉴 봉고III 트럭 LPi 2.5 터보 카고": "192",
        "더 뉴 봉고III 트럭 LPi 2.5 터보 특장": "193",
        "더 뉴 봉고III 트럭 EV 특장": "178",
        "더 뉴 봉고III 트럭 EV 카고": "168",
        "더 뉴 봉고III 트럭 CRDi 카고": "158",
        "더 뉴 봉고III 트럭 LPi 카고": "160",
        "더 뉴 봉고III 트럭 LPi 특장": "161",
        "더 뉴 봉고III 트럭 특장": "159",
        "봉고III 트럭 LPi 카고": "144",
        "봉고III 트럭 CRDi 카고": "143",
        "봉고III 트럭 터보인터쿨러(Tci) 카고": "145",
        "봉고III 트럭 특장": "146",
    },
    ("002", "065"): {  # 셀토스
        "셀토스": "155",
        "더 뉴 셀토스": "181",
        "디 올 뉴 셀토스": "204",
        "디 올 뉴 셀토스 하이브리드": "205",
        "셀토스 하이브리드": "205",
    },
    ("002", "066"): {  # K8
        "K8": "169",
        "K8 하이브리드": "173",
        "더 뉴 K8": "196",
        "더 뉴 K8 하이브리드": "197",
    },
    ("002", "067"): {  # EV6
        "EV6": "170",
        "더 뉴 EV6": "195",
    },
    ("002", "068"): {  # EV9
        "EV9": "183",
    },
    ("002", "069"): {  # EV3
        "EV3": "194",
    },
    ("002", "070"): {  # 타스만
        "타스만": "200",
    },
    ("002", "071"): {  # EV4
        "EV4": "201",
    },
    ("002", "072"): {  # PV5
        "PV5": "202",
    },
    ("002", "073"): {  # EV5
        "EV5": "203",
    },
    # 쉐보레(GM대우) (003)
    ("003", "004"): {  # 다마스
        "뉴 다마스": "070",
        "다마스 II": "029",
    },
    ("003", "007"): {  # 라보
        "뉴 라보": "071",
    },
    ("003", "008"): {  # 라세티
        "라세티 프리미어": "065",
        "라세티": "028",
    },
    ("003", "013"): {  # 마티즈
        "마티즈 크리에이티브": "066",
        "마티즈 클래식": "067",
        "All New 마티즈": "054",
        "마티즈 II": "022",
    },
    ("003", "016"): {  # 베리타스
        "베리타스": "064",
    },
    ("003", "023"): {  # 윈스톰
        "윈스톰 맥스": "063",
        "윈스톰": "057",
    },
    ("003", "025"): {  # 젠트라
        "젠트라 X": "059",
        "젠트라": "030",
    },
    ("003", "028"): {  # 토스카
        "토스카 프리미엄6": "062",
        "토스카": "031",
    },
    ("003", "035"): {  # G2X
        "G2X": "058",
    },
    ("003", "038"): {  # 알페온
        "알페온": "068",
    },
    ("003", "040"): {  # 올란도
        "올란도": "072",
    },
    ("003", "041"): {  # 크루즈
        "크루즈": "073",
        "크루즈5": "078",
        "어메이징 뉴 크루즈": "084",
        "올 뉴 크루즈": "093",
        "어메이징 뉴 크루즈 5": "085",
    },
    ("003", "042"): {  # 아베오
        "더 뉴 아베오 세단": "090",
        "더 뉴 아베오 해치백": "091",
        "아베오 세단": "080",
        "아베오 해치백": "074",
    },
    ("003", "043"): {  # 스파크
        "스파크": "075",
        "스파크 EV": "083",
        "더 넥스트 스파크": "086",
        "더 뉴 스파크": "096",
    },
    ("003", "044"): {  # 카마로
        "더 뉴 카마로 ": "099",
        "올 뉴 카마로": "089",
        "카마로": "076",
    },
    ("003", "045"): {  # 캡티바
        "캡티바": "077",
    },
    ("003", "046"): {  # 말리부
        "말리부": "079",
        "올 뉴 말리부": "088",
        "더 뉴 말리부": "098",
    },
    ("003", "047"): {  # 콜벳
        "콜벳": "081",
    },
    ("003", "048"): {  # 트랙스
        "트랙스": "082",
        "더 뉴 트랙스": "092",
        "트랙스 크로스오버": "108",
    },
    ("003", "049"): {  # 임팔라
        "임팔라": "087",
    },
    ("003", "050"): {  # 볼트(Volt)
        "볼트(Volt)": "094",
    },
    ("003", "051"): {  # 볼트 EV
        "볼트 EV": "095",
        "뉴 볼트 EV": "104",
    },
    ("003", "052"): {  # 이쿼녹스
        "이쿼녹스": "097",
        "더 넥스트 이쿼녹스": "107",
    },
    ("003", "053"): {  # 콜로라도
        "콜로라도": "100",
        "리얼 뉴 콜로라도": "103",
        "올 뉴 콜로라도": "110",
    },
    ("003", "054"): {  # 트래버스
        "트래버스": "101",
        "더 뉴 트래버스": "111",
    },
    ("003", "055"): {  # 트레일블레이저
        "트레일블레이저": "102",
        "더 뉴 트레일블레이저": "109",
    },
    ("003", "056"): {  # 볼트 EUV
        "볼트 EUV": "105",
    },
    ("003", "057"): {  # 타호
        "타호": "106",
    },
    # KGM (004)
    ("004", "003"): {  # 렉스턴
        "렉스턴 W": "103",
        "G4 렉스턴": "111",
        "렉스턴 스포츠": "113",
        "렉스턴 스포츠 칸": "114",
        "올 뉴 렉스턴": "117",
        "더 뉴 렉스턴 스포츠": "118",
        "더 뉴 렉스턴 스포츠 칸": "119",
        "렉스턴 뉴 아레나": "122",
        "더 뉴 렉스턴 스포츠 쿨멘": "126",
        "더 뉴 렉스턴 스포츠 칸 쿨멘": "127",
        "슈퍼 렉스턴": "024",
        "렉스턴 II": "018",
        "뉴렉스턴": "015",
        "렉스턴": "011",
    },
    ("004", "004"): {  # 로디우스
        "로디우스 유로": "104",
        "뉴로디우스": "021",
        "로디우스": "013",
    },
    ("004", "005"): {  # 무쏘
        "무쏘 (Q300)": "136",
        "무쏘 스포츠 (Q250)": "133",
        "무쏘 칸 (Q250)": "132",
        "무쏘 EV": "131",
        "무쏘 스포츠": "012",
    },
    ("004", "006"): {  # 액티언
        "액티언 (J120)": "130",
        "액티언 하이브리드 (J120)": "135",
        "액티언 (J120) 하이브리드": "135",
        "액티언 하이브리드": "135",
        "액티언 스포츠": "019",
        "액티언": "017",
    },
    ("004", "008"): {  # 체어맨
        "체어맨 H 뉴 클래식": "101",
        "뉴체어맨 W": "100",
        "체어맨 W": "022",
        "체어맨 H": "023",
        "뉴체어맨": "014",
    },
    ("004", "010"): {  # 카이런
        "뉴카이런": "020",
        "카이런": "016",
    },
    ("004", "011"): {  # 코란도
        "코란도 C": "099",
        "코란도 스포츠": "102",
        "코란도 투리스모": "105",
        "뉴코란도 C": "106",
        "더 뉴 코란도 스포츠": "109",
        "뉴 스타일 코란도 C": "110",
        "뷰티풀 코란도": "115",
        "코란도 이모션": "120",
        "코란도 EV": "129",
    },
    ("004", "012"): {  # 티볼리
        "티볼리": "107",
        "티볼리 에어": "108",
        "티볼리 아머": "112",
        "베리 뉴 티볼리": "116",
        "더 뉴 티볼리": "124",
        "더 뉴 티볼리 에어": "125",
    },
    ("004", "013"): {  # 토레스
        "토레스": "121",
        "토레스 EVX": "123",
        "더 뉴 토레스": "128",
        "더 뉴 토레스 하이브리드": "134",
        "토레스 하이브리드": "134",
        "뉴 토레스": "137",
        "뉴 토레스 하이브리드": "138",
    },
    # 르노코리아(삼성) (005)
    ("005", "001"): {  # SM3
        "SM3": "002",
        "뉴SM3": "054",
        "SM3 네오": "062",
        "SM3 Z.E": "060",
        "SM3 뉴 제너레이션": "005",
    },
    ("005", "002"): {  # SM5
        "뉴SM5(신형)": "055",
        "뉴SM5 플래티넘": "058",
        "SM5 노바": "064",
        "SM5 뉴 임프레션": "006",
        "뉴SM5": "004",
        "SM5": "001",
    },
    ("005", "003"): {  # SM7
        "All New SM7": "057",
        "SM7 노바": "063",
        "SM7 New Art": "007",
        "SM7": "003",
    },
    ("005", "004"): {  # QM5
        "QM5 네오": "061",
        "뉴QM5": "056",
        "QM5": "053",
    },
    ("005", "009"): {  # QM3
        "QM3": "059",
        "뉴QM3": "067",
    },
    ("005", "010"): {  # SM6
        "SM6": "065",
        "더 뉴 SM6": "074",
    },
    ("005", "011"): {  # QM6
        "QM6": "066",
        "더 뉴 QM6": "071",
        "뉴 QM6": "077",
        "더 뉴 QM6 F/L": "079",
    },
    ("005", "012"): {  # 트위지
        "트위지": "068",
    },
    ("005", "013"): {  # 클리오
        "클리오": "069",
    },
    ("005", "014"): {  # 마스터
        "마스터": "070",
        "뉴 마스터": "075",
    },
    ("005", "015"): {  # XM3
        "XM3": "072",
        "XM3 하이브리드": "078",
        "XM3 E-TECH 하이브리드": "078",
    },
    ("005", "016"): {  # 캡처
        "캡처": "073",
    },
    ("005", "017"): {  # 조에
        "조에": "076",
    },
    ("005", "018"): {  # 아르카나 
        "아르카나 하이브리드": "080",
        "아르카나 E-TECH 하이브리드": "080",
        "아르카나": "081",
    },
    ("005", "019"): {  # 그랑 콜레오스
        "그랑 콜레오스": "082",
        "그랑 콜레오스 하이브리드": "083",
        "그랑 콜레오스 E-TECH 하이브리드": "083",
    },
    ("005", "020"): {  # 세닉 E-테크 일렉트릭
        "세닉 E-테크 일렉트릭": "084",
    },
    ("005", "021"): {  # 필랑트
        "필랑트": "085",
    },
    # 기타 제조사 (006)
    ("006", "001"): {  # 기타
        "전기차": "035",
    },
    ("006", "002"): {  # 대우버스-BS
        "대우버스-BS": "001",
    },
    ("006", "006"): {  # 타타대우-노부스
        "타타대우-노부스": "005",
    },
    ("006", "007"): {  # 타타대우-프리마
        "타타대우-프리마": "006",
    },
    ("006", "008"): {  # 타타대우-대형트럭
        "타타대우-대형트럭": "007",
    },
    ("006", "013"): {  # 타타대우-더 쎈
        "더 쎈": "034",
    },
    # 제네시스 (007)
    ("007", "001"): {  # EQ900
        "EQ900": "001",
    },
    ("007", "002"): {  # G80
        "G80": "002",
        "G80 (RG3)": "007",
        "더 올 뉴 G80": "007",
        "디 올 뉴 G80": "007",
        "올 뉴 G80": "007",
        "G80 (RG3) 일렉트리파이드": "010",
        "G80 (RG3 F/L)": "015",
        "더 뉴 G80": "015",
        "G80 (RG3 F/L) 일렉트리파이드": "018",
    },
    ("007", "003"): {  # G70
        "G70": "003",
        "더 뉴 G70": "008",
    },
    ("007", "004"): {  # G90
        "G90": "005",
        "G90 (RS4)": "012",
        "더 뉴 G90": "012",
        "디 올 뉴 G90": "012",
        "신형 G90": "012",
    },
    ("007", "005"): {  # GV80
        "GV80": "006",
        "GV80 쿠페": "014",
        "GV80 (F/L)": "016",
        "더 뉴 GV80": "016",
        "디 올 뉴 GV80": "016",
        "GV80 하이브리드": "022",
    },
    ("007", "006"): {  # GV70
        "GV70": "009",
        "eGV70": "013",
        "GV70 (F/L)": "017",
        "더 뉴 GV70": "017",
        "디 올 뉴 GV70": "017",
        "eGV70 (F/L)": "019",
    },
    ("007", "007"): {  # GV60
        "GV60": "011",
        "더 뉴 GV60": "020",
        "GV60 마그마": "021",
    },
    # 아우디 (011)
    ("011", "001"): {  # A3
        "A3 (8Y)": "063",
        "뉴 A3": "024",
        "뉴 A3 ": "024",
        "A3 (8P)": "043",
    },
    ("011", "002"): {  # A4
        "A4 (B9)": "041",
        "뉴 A4 (B8)": "011",
        "A4 (B7)": "044",
    },
    ("011", "003"): {  # A8
        "A8 (D5)": "052",
        "뉴 A8 (D4)": "013",
        "A8 (D3)": "046",
    },
    ("011", "004"): {  # A6
        "A6 (C9)": "083",
        "A6 (C8)": "048",
        "뉴 A6 (C7)": "004",
        "A6 (C6)": "045",
        "A6": "007",
    },
    ("011", "005"): {  # TT
        "TT (8S)": "038",
        "뉴 TT": "023",
        "TT": "010",
    },
    ("011", "011"): {  # S3
        "S3 (8Y)": "071",
        "S3": "014",
    },
    ("011", "012"): {  # S4
        "S4 (B9)": "064",
        "뉴 S4": "032",
        "S4": "015",
    },
    ("011", "013"): {  # Q7
        "Q7 (4M)": "040",
        "Q7": "016",
    },
    ("011", "014"): {  # S6
        "S6 (C8)": "054",
        "S6": "017",
    },
    ("011", "015"): {  # RS4
        "RS4": "018",
    },
    ("011", "016"): {  # RS6
        "RS6 (C8)": "070",
        "RS6": "019",
    },
    ("011", "017"): {  # R8
        "R8 (4S)": "042",
        "R8": "020",
    },
    ("011", "018"): {  # S5
        "S5 (B10)": "079",
        "S5 (F5)": "065",
        "S5": "021",
    },
    ("011", "019"): {  # S8
        "S8 (D5)": "056",
        "S8": "022",
    },
    ("011", "020"): {  # Q5
        "Q5 (FY)": "053",
        "Q5": "025",
        "Q5 (80A)": "080",
    },
    ("011", "021"): {  # A5
        "A5 (B10)": "078",
        "A5 (F5)": "047",
        "A5": "026",
    },
    ("011", "022"): {  # TTS
        "TTS (8S)": "039",
        "TTS": "027",
    },
    ("011", "023"): {  # RS5
        "RS5 (F5)": "066",
        "RS5": "028",
    },
    ("011", "024"): {  # TTRS
        "TTRS": "029",
    },
    ("011", "025"): {  # A7
        "A7 (4K)": "051",
        "A7": "030",
    },
    ("011", "026"): {  # Q3
        "Q3 (F3)": "049",
        "Q3": "031",
        "Q3 (FJ)": "084",
    },
    ("011", "029"): {  # S7
        "S7 (4K)": "055",
        "S7": "033",
    },
    ("011", "030"): {  # SQ5
        "SQ5 (FY)": "060",
        "SQ5": "034",
    },
    ("011", "031"): {  # RS7
        "RS7 (4K)": "068",
        "RS7": "035",
    },
    ("011", "032"): {  # A1
        "A1 (8X)": "036",
    },
    ("011", "033"): {  # RS3
        "RS3 (8Y)": "072",
        "RS3 (8P)": "037",
    },
    ("011", "034"): {  # Q8
        "Q8 (4M)": "050",
    },
    ("011", "035"): {  # Q2
        "Q2": "057",
    },
    ("011", "036"): {  # e-트론
        "e-트론": "058",
    },
    ("011", "037"): {  # SQ8
        "SQ8": "059",
    },
    ("011", "038"): {  # e-트론 GT
        "더 뉴 e-트론 GT": "082",
        "e-트론 GT": "062",
    },
    ("011", "039"): {  # Q4 e-트론
        "Q4 e-트론": "067",
    },
    ("011", "040"): {  # RSQ8
        "RS Q8": "069",
    },
    ("011", "041"): {  # SQ7
        "SQ7 (4M)": "073",
    },
    ("011", "042"): {  # Q8 e-트론
        "Q8 e-트론": "074",
    },
    ("011", "044"): {  # Q6 e-트론
        "Q6 e-트론": "076",
    },
    ("011", "046"): {  # A6 e-트론
        "A6 e-트론": "081",
    },
    # BMW (012)
    ("012", "001"): {  # 1시리즈
        "1시리즈 (F70)": "103",
        "1시리즈 (F40)": "076",
        "1시리즈 (F20)": "020",
        "1시리즈 (E82)": "059",
    },
    ("012", "002"): {  # 3시리즈
        "3시리즈 (G20)": "069",
        "3시리즈 (F30)": "038",
        "3시리즈 (E90)": "001",
        "3시리즈 (E46)": "005",
    },
    ("012", "003"): {  # 5시리즈
        "5시리즈 (G60)": "095",
        "5시리즈 (G30)": "060",
        "5시리즈 (F10)": "039",
        "5시리즈 (E60)": "002",
    },
    ("012", "004"): {  # 6시리즈
        "6시리즈 (F12)": "018",
        "6시리즈 (E63)": "015",
    },
    ("012", "005"): {  # 7시리즈
        "7시리즈 (G70)": "091",
        "7시리즈 (G11 F/L)": "066",
        "7시리즈 (G11)": "036",
        "7시리즈 (F01)": "003",
        "7시리즈 (E65)": "040",
    },
    ("012", "006"): {  # 8시리즈
        "8시리즈 (G15)": "077",
    },
    ("012", "007"): {  # X3
        "X3 (G45)": "100",
        "X3 (G01)": "062",
        "X3 (F25)": "028",
        "X3 (E83)": "014",
    },
    ("012", "008"): {  # X5
        "X5 (G05)": "065",
        "X5 (F15)": "030",
        "X5 (E70)": "022",
        "X5 (E53)": "009",
    },
    ("012", "009"): {  # Z4
        "Z4 (G29)": "070",
        "Z4 (E89)": "025",
        "Z4 (E85)": "011",
    },
    ("012", "011"): {  # X6
        "X6 (G06)": "078",
        "X6 (F16)": "023",
        "X6 (E71)": "019",
    },
    ("012", "014"): {  # X1
        "X1 (U11)": "094",
        "X1 (F48)": "037",
        "X1 (U11) ": "094",
        "X1 (E84)": "021",
    },
    ("012", "015"): {  # 그란투리스모 (GT)
        "6시리즈 GT (G32)": "061",
        "3시리즈 GT (F34)": "029",
        "5시리즈 GT (F07)": "026",
    },
    ("012", "017"): {  # 4시리즈
        "4시리즈 (G22)": "082",
        "4시리즈 (F32)": "012",
    },
    ("012", "018"): {  # 2시리즈
        "2시리즈 그란쿠페 (F44)": "072",
        "2시리즈 액티브 투어러 (U06)": "090",
        "2시리즈 그란쿠페 (F74)": "104",
        "2시리즈 (G42)": "088",
        "2시리즈 액티브 투어러 (F45)": "034",
        "2시리즈 (F22)": "031",
    },
    ("012", "019"): {  # i3
        "i3 (I01)": "032",
    },
    ("012", "020"): {  # X4
        "X4 (G02)": "068",
        "X4 (F26)": "033",
    },
    ("012", "021"): {  # i8
        "i8 (I12)": "035",
    },
    ("012", "022"): {  # 1M
        "1M (E82)": "041",
    },
    ("012", "023"): {  # M2
        "M2 (G87)": "096",
        "M2 (F87)": "042",
    },
    ("012", "024"): {  # M3
        "M3 (G80)": "083",
        "M3 (F80)": "043",
        "M3 (E90)": "044",
        "M3 (E46)": "045",
    },
    ("012", "025"): {  # M4
        "M4 (G82)": "084",
        "M4 (F82)": "047",
    },
    ("012", "026"): {  # M5
        "M5 (G90)": "101",
        "M5 (F90)": "063",
        "M5 (F10)": "048",
    },
    ("012", "027"): {  # M6
        "M6 (F12)": "051",
        "M6 (E63)": "052",
    },
    ("012", "029"): {  # X5M
        "X5M (F95)": "079",
        "X5M (F85)": "055",
        "X5M (E70)": "056",
    },
    ("012", "030"): {  # X6M
        "X6M (F96)": "080",
        "X6M (F16)": "057",
        "X6M (E71)": "058",
    },
    ("012", "031"): {  # X2
        "X2 (U10)": "098",
        "X2 (F39)": "067",
    },
    ("012", "032"): {  # X7
        "X7 (G07)": "071",
    },
    ("012", "033"): {  # X4M
        "X4M (F98)": "073",
    },
    ("012", "034"): {  # X3M
        "X3M (F97)": "074",
    },
    ("012", "035"): {  # M8
        "M8 (G15)": "075",
    },
    ("012", "036"): {  # iX3
        "iX3 (G08)": "085",
        "iX3 (NA5)": "107",
    },
    ("012", "037"): {  # iX
        "iX (i20 F/L)": "106",
        "iX (i20)": "086",
    },
    ("012", "038"): {  # i4
        "i4 (G26)": "087",
        "i4 (G26 F/L)": "105",
    },
    ("012", "039"): {  # i7
        "i7 (G70)": "089",
    },
    ("012", "040"): {  # iX1
        "iX1 (U11)": "092",
    },
    ("012", "041"): {  # XM
        "XM (G09)": "093",
    },
    ("012", "042"): {  # i5
        "i5 (G60)": "097",
    },
    ("012", "043"): {  # iX2
        "iX2 (U10)": "102",
    },
    # 벤츠 (013)
    ("013", "001"): {  # C-클래스
        "C-클래스 W206": "096",
        "C-클래스 W205": "067",
        "C-클래스 W204": "012",
        "C-클래스 W203": "003",
    },
    ("013", "002"): {  # CL-클래스
        "CL-클래스 C216": "061",
        "CL-클래스 C215": "013",
    },
    ("013", "003"): {  # CLS-클래스
        "CLS-클래스 C257": "083",
        "CLS-클래스 W218": "062",
        "CLS-클래스 W219": "021",
    },
    ("013", "004"): {  # E-클래스
        "E-클래스 W214": "104",
        "E-클래스 W213": "072",
        "E-클래스 W212": "001",
        "E-클래스 W211": "019",
        "E-클래스 W210": "078",
    },
    ("013", "005"): {  # S-클래스
        "S-클래스 W223": "092",
        "S-클래스 W222": "065",
        "S-클래스 W221": "002",
        "S-클래스": "005",
    },
    ("013", "006"): {  # SL-클래스
        "더 뉴 SL-클래스": "100",
        "뉴 SL-클래스": "060",
        "SL-클래스": "007",
    },
    ("013", "007"): {  # SLK-클래스
        "뉴 SLK-클래스": "022",
        "SLK-클래스": "008",
    },
    ("013", "008"): {  # M-클래스
        "M-클래스 W166": "063",
        "M-클래스 W164": "082",
    },
    ("013", "009"): {  # B-클래스
        "B-클래스 W246": "075",
        "B-클래스 W245": "054",
    },
    ("013", "012"): {  # CLK-클래스
        "CLK-클래스 C209": "009",
    },
    ("013", "013"): {  # G-클래스 
        "G-클래스 W465": "106",
        "G-클래스 W463b": "085",
        "G-클래스 W463": "010",
    },
    ("013", "016"): {  # V-클래스
        "V-클래스 W447 (F/L)": "112",
        "V-클래스": "016",
    },
    ("013", "022"): {  # GL-클래스
        "GL-클래스 X166": "053",
        "GL-클래스 X164": "081",
    },
    ("013", "024"): {  # GLK-클래스
        "GLK-클래스 X204": "057",
    },
    ("013", "026"): {  # SLS AMG
        "SLS AMG": "059",
    },
    ("013", "029"): {  # A-클래스
        "A-클래스 W177": "087",
        "A-클래스 W176": "064",
    },
    ("013", "030"): {  # 스프린터
        "스프린터": "015",
    },
    ("013", "031"): {  # CLA-클래스
        "CLA-클래스 C118": "088",
        "CLA-클래스 C117": "066",
        "CLA-클래스 C119": "110",
    },
    ("013", "032"): {  # GLA-클래스
        "GLA-클래스 H247": "091",
        "GLA-클래스 X156": "068",
    },
    ("013", "033"): {  # AMG GT
        "AMG GT C192": "108",
        "AMG GT": "069",
    },
    ("013", "034"): {  # GLC-클래스
        "GLC-클래스 X254": "101",
        "GLC-클래스 X253": "071",
        "Electric GLC": "109",
    },
    ("013", "035"): {  # GLE-클래스
        "GLE-클래스 W167": "086",
        "GLE-클래스 W166": "070",
    },
    ("013", "036"): {  # SLC-클래스
        "SLC-클래스 R172": "073",
    },
    ("013", "037"): {  # GLS-클래스
        "GLS-클래스 X167": "093",
        "GLS-클래스 X166": "074",
    },
    ("013", "038"): {  # GLB-클래스
        "GLB-클래스 X247": "089",
    },
    ("013", "039"): {  # EQC-클래스
        "EQC N293": "090",
    },
    ("013", "040"): {  # EQA-클래스
        "EQA H243": "094",
    },
    ("013", "041"): {  # EQS-클래스
        "EQS V297": "095",
        "EQS SUV X296": "099",
    },
    ("013", "042"): {  # EQB-클래스
        "EQB X243": "097",
    },
    ("013", "044"): {  # EQE-클래스
        "EQE V295": "098",
        "EQE SUV X294": "102",
    },
    ("013", "045"): {  # CLE-클래스
        "CLE-클래스 C236": "105",
    },
    ("013", "046"): {  # EQG-클래스
        "EQG 580 W465": "107",
    },
    # 폭스바겐 (014)
    ("014", "001"): {  # CC
        "뉴 CC": "021",
        "CC": "017",
    },
    ("014", "002"): {  # 티구안
        "티구안 올스페이스": "035",
        "티구안 2세대": "034",
        "뉴 티구안": "022",
        "티구안": "016",
    },
    ("014", "003"): {  # 비틀
        "더 비틀": "030",
        "뉴 비틀": "005",
    },
    ("014", "004"): {  # 제타
        "올 뉴 제타": "040",
        "뉴 제타": "018",
        "제타": "012",
    },
    ("014", "005"): {  # 투아렉
        "투아렉 3세대": "039",
        "뉴 투아렉": "020",
        "투아렉": "009",
    },
    ("014", "006"): {  # 파사트
        "더 파사트": "038",
        "파사트 GT (B8)": "036",
        "더 뉴 파사트": "029",
        "뉴 파사트": "007",
        "파사트": "003",
        "파사트 바리안트": "013",
    },
    ("014", "007"): {  # 골프
        "골프 8세대": "042",
        "골프 7세대": "031",
        "골프 6세대": "023",
        "골프 5세대": "024",
        "골프 4세대": "025",
        "골프 3세대": "026",
    },
    ("014", "010"): {  # 보라
        "보라": "008",
    },
    ("014", "011"): {  # 페이톤
        "페이톤": "010",
    },
    ("014", "014"): {  # EOS
        "EOS": "014",
    },
    ("014", "015"): {  # 폴로
        "폴로": "015",
    },
    ("014", "016"): {  # 시로코
        "시로코": "019",
    },
    ("014", "017"): {  # 기타
        "기타": "999",
    },
    ("014", "019"): {  # 아테온
        "아테온": "037",
    },
    ("014", "020"): {  # T-Roc
        "T-Roc": "041",
    },
    ("014", "021"): {  # 아틀라스
        "아틀라스 2세대": "047",
        "아틀라스": "043",
    },
    ("014", "022"): {  # ID
        "ID.5": "046",
        "ID.4": "044",
    },
    # 포르쉐 (015)
    ("015", "001"): {  # 911
        "911 (992)": "022",
        "911 (991)": "025",
        "911 (997)": "001",
    },
    ("015", "002"): {  # 카이엔
        "더 뉴 카이엔 (PO536)": "018",
        "뉴 카이엔": "015",
        "카이엔": "005",
    },
    ("015", "003"): {  # 카이맨
        "카이맨": "008",
    },
    ("015", "004"): {  # 파나메라
        "더 뉴 파나메라 (972)": "026",
        "파나메라 (971)": "017",
        "파나메라 (970)": "011",
    },
    ("015", "005"): {  # 박스터
        "박스터": "002",
    },
    ("015", "013"): {  # 마칸
        "마칸 일렉트릭": "027",
        "마칸": "013",
    },
    ("015", "014"): {  # 718
        "718 박스터": "014",
        "718 카이맨": "019",
    },
    ("015", "016"): {  # 타이칸
        "더 뉴 타이칸": "028",
        "더 뉴 타이칸 크로스 투리스모": "029",
        "타이칸 크로스 투리스모": "024",
        "타이칸": "023",
    },
    # 사브 (016)
    ("016", "001"): {  # 9-3
        "뉴 9-3": "005",
        "9-3": "003",
    },
    ("016", "002"): {  # 9-5
        "뉴 9-5": "006",
        "9-5": "004",
    },
    ("016", "003"): {  # 900
        "900": "001",
    },
    ("016", "004"): {  # 9000
        "9000": "002",
    },
    # 볼보 (017)
    ("017", "001"): {  # XC70
        "XC70": "009",
    },
    ("017", "005"): {  # S40
        "S40": "004",
    },
    ("017", "007"): {  # S80
        "S80 (2세대)": "030",
        "S80": "006",
    },
    ("017", "009"): {  # S60
        "S60 3세대": "028",
        "S60": "008",
        "S60 크로스컨트리": "023",
    },
    ("017", "010"): {  # XC90
        "XC90 2세대": "024",
        "XC90": "010",
    },
    ("017", "012"): {  # V50
        "V50": "012",
    },
    ("017", "013"): {  # C30
        "C30": "013",
    },
    ("017", "015"): {  # S90
        "S90": "016",
    },
    ("017", "016"): {  # XC60
        "XC60 2세대": "026",
        "XC60": "017",
    },
    ("017", "017"): {  # V60
        "V60 크로스컨트리 2세대": "029",
        "V60 크로스컨트리": "022",
        "V60": "018",
    },
    ("017", "020"): {  # V40
        "V40 크로스컨트리": "021",
        "V40": "019",
    },
    ("017", "022"): {  # V90
        "V90 크로스컨트리": "025",
    },
    ("017", "023"): {  # XC40
        "XC40 리차지": "031",
        "XC40": "027",
    },
    ("017", "024"): {  # C40
        "C40 리차지": "032",
    },
    ("017", "025"): {  # EX30
        "EX30 크로스컨트리": "036",
        "EX30": "033",
    },
    ("017", "026"): {  # EX40
        "EX40": "035",
    },
    ("017", "027"): {  # EX90
        "EX90": "037",
    },
    ("017", "028"): {  # ES90
        "ES90": "038",
    },
    # 피아트 (018)
    ("018", "006"): {  # 500
        "500C": "007",
        "500": "006",
    },
    ("018", "008"): {  # 프리몬트
        "프리몬트": "008",
    },
    ("018", "010"): {  # 500X
        "500X": "010",
    },
    # 재규어 (019)
    ("019", "001"): {  # XF
        "XF (X260)": "019",
        "New XF": "015",
        "XF": "009",
    },
    ("019", "002"): {  # XJ
        "All New XJ": "013",
        "New XJ": "007",
    },
    ("019", "006"): {  # X-TYPE
        "X-TYPE": "004",
    },
    ("019", "007"): {  # S-TYPE
        "S-TYPE": "005",
    },
    ("019", "010"): {  # XJR
        "XJR": "010",
    },
    ("019", "011"): {  # XKR
        "XKR-S": "016",
        "XKR": "011",
    },
    ("019", "012"): {  # XK
        "XK": "012",
    },
    ("019", "015"): {  # F-TYPE
        "F-TYPE": "017",
    },
    ("019", "016"): {  # XE
        "XE": "018",
    },
    ("019", "017"): {  # F-PACE
        "F-PACE": "020",
    },
    ("019", "018"): {  # E-PACE
        "E-PACE": "021",
    },
    ("019", "019"): {  # I-PACE
        "I-Pace": "022",
    },
    # 랜드로버 (020)
    ("020", "001"): {  # 디스커버리
        "디스커버리 5 (F/L)": "019",
        "디스커버리 5": "014",
        "디스커버리 4": "010",
        "디스커버리 3": "006",
        "디스커버리 2": "009",
        "디스커버리": "002",
    },
    ("020", "002"): {  # 프리랜더
        "프리랜더2": "007",
        "프리랜더": "003",
    },
    ("020", "003"): {  # 레인지로버
        "레인지로버 5세대": "020",
        "레인지로버 4세대": "013",
        "레인지로버": "001",
    },
    ("020", "005"): {  # 디펜더
        "디펜더 (L663)": "018",
        "디펜더": "005",
    },
    ("020", "006"): {  # 레인지로버 스포츠
        "레인지로버 스포츠 3세대": "021",
        "레인지로버 스포츠 2세대": "004",
        "레인지로버 스포츠": "008",
    },
    ("020", "008"): {  # 레인지로버 이보크
        "레인지로버 이보크 2세대": "016",
        "레인지로버 이보크": "012",
    },
    ("020", "010"): {  # 디스커버리 스포츠
        "디스커버리 스포츠 2세대": "017",
        "디스커버리 스포츠": "011",
    },
    ("020", "011"): {  # 레인지로버 벨라
        "레인지로버 벨라": "015",
    },
    # 푸조 (021)
    ("021", "001"): {  # 206
        "206RC": "011",
        "206CC": "007",
        "206": "031",
        "206SW": "012",
    },
    ("021", "002"): {  # 207
        "207SW": "026",
        "207CC": "020",
        "207GT": "021",
        "207RC": "022",
    },
    ("021", "003"): {  # 307
        "307": "010",
        "307CC": "008",
        "307HDi": "024",
        "307SW": "009",
    },
    ("021", "004"): {  # 308
        "308 3세대": "051",
        "308SW 2세대": "041",
        "308 2세대": "040",
        "308": "028",
        "308CC": "029",
        "308SW": "027",
    },
    ("021", "005"): {  # 407
        "407": "014",
        "407SW": "015",
        "407쿠페": "025",
    },
    ("021", "006"): {  # 607
        "607": "013",
    },
    ("021", "016"): {  # 3008
        "3008 3세대": "053",
        "3008 2세대": "044",
        "3008": "033",
    },
    ("021", "017"): {  # RCZ
        "RCZ": "034",
    },
    ("021", "018"): {  # 508
        "508SW 2세대": "049",
        "508 2세대": "046",
        "508 RXH": "043",
        "508": "035",
        "508SW": "037",
    },
    ("021", "022"): {  # 208
        "e-208 2세대": "047",
        "208": "038",
    },
    ("021", "024"): {  # 2008
        "2008 2세대": "048",
        "e-2008 2세대": "050",
        "2008": "042",
    },
    ("021", "025"): {  # 5008
        "5008 3세대": "054",
        "5008": "045",
    },
    ("021", "026"): {  # 408
        "408": "052",
    },
    # 시트로엥 (022)
    ("022", "004"): {  # C5
        "C5 에어크로스": "017",
        "C5": "004",
    },
    ("022", "005"): {  # C3
        "C3 에어크로스": "016",
        "C3": "005",
    },
    ("022", "006"): {  # DS3
        "e-DS3 크로스백": "019",
        "DS3 크로스백": "018",
        "DS3 카브리오": "009",
        "DS3": "006",
    },
    ("022", "008"): {  # DS4
        "DS4 2세대": "020",
        "DS4 크로스백": "012",
        "DS4": "007",
    },
    ("022", "009"): {  # DS5
        "DS5": "008",
    },
    ("022", "010"): {  # C4 피카소
        "C4 피카소": "011",
        "그랜드 C4 피카소": "010",
    },
    ("022", "011"): {  # C4 칵투스
        "C4 칵투스": "013",
    },
    ("022", "012"): {  # C4 스페이스투어러
        "그랜드 C4 스페이스투어러": "014",
    },
    ("022", "013"): {  # DS7
        "DS7 크로스백": "015",
    },
    # 크라이슬러 (023)
    ("023", "001"): {  # 300C
        "더 뉴 300C": "032",
        "올 뉴 300C": "031",
        "300C": "019",
    },
    ("023", "003"): {  # 세브링
        "뉴 세브링": "028",
        "세브링": "010",
    },
    ("023", "006"): {  # 캐러밴
        "캐러밴": "003",
    },
    ("023", "011"): {  # 300M
        "300M": "008",
    },
    ("023", "012"): {  # PT 크루저
        "PT 크루저": "009",
    },
    ("023", "013"): {  # 보이저
        "보이저": "011",
    },
    ("023", "019"): {  # 그랜드 보이저
        "그랜드 보이저": "018",
    },
    ("023", "021"): {  # 퍼시피카
        "퍼시피카": "021",
    },
    ("023", "022"): {  # 크로스파이어
        "크로스파이어": "022",
    },
    ("023", "030"): {  # 200
        "200 2세대": "034",
        "200 1세대": "033",
    },
    # 포드 (024)
    ("024", "001"): {  # 몬데오
        "몬데오 4세대": "029",
        "몬데오 3세대": "023",
        "몬데오": "004",
    },
    ("024", "002"): {  # 토러스
        "뉴 토러스": "026",
        "토러스": "005",
    },
    ("024", "005"): {  # 윈드스타
        "윈드스타": "003",
    },
    ("024", "006"): {  # 머스탱
        "올 뉴 머스탱": "039",
        "머스탱": "006",
    },
    ("024", "007"): {  # 익스플로러
        "익스플로러 6세대 (F/L)": "040",
        "익스플로러 6세대": "034",
        "익스플로러": "007",
    },
    ("024", "008"): {  # 이스케이프
        "이스케이프": "008",
    },
    ("024", "011"): {  # 익스페디션
        "익스페디션 5세대": "041",
        "익스페디션": "011",
    },
    ("024", "016"): {  # 브롱코
        "브롱코 6세대": "037",
    },
    ("024", "018"): {  # 포커스
        "포커스": "018",
    },
    ("024", "019"): {  # F150
        "F150": "019",
    },
    ("024", "020"): {  # 프리스타일
        "프리스타일": "020",
    },
    ("024", "021"): {  # S-MAX
        "S-MAX": "021",
    },
    ("024", "023"): {  # 레인저
        "레인저 4세대": "038",
        "레인저 3세대": "035",
    },
    ("024", "024"): {  # F250
        "F250": "025",
    },
    ("024", "025"): {  # 퓨전
        "퓨전": "027",
    },
    ("024", "027"): {  # F350
        "F350": "028",
    },
    ("024", "028"): {  # 쿠가
        "쿠가 2세대": "030",
    },
    ("024", "029"): {  # 트랜짓
        "트랜짓": "033",
    },
    # 혼다 (027)
    ("027", "001"): {  # CR-V
        "CR-V 6세대": "104",
        "CR-V 5세대": "100",
        "New CR-V": "023",
        "CR-V": "003",
    },
    ("027", "002"): {  # 레전드
        "레전드 5세대": "027",
        "레전드 4세대": "020",
    },
    ("027", "003"): {  # 어코드
        "어코드 11세대": "106",
        "어코드 10세대": "102",
        "올뉴어코드": "014",
        "어코드": "001",
    },
    ("027", "004"): {  # 시빅
        "시빅": "002",
    },
    ("027", "006"): {  # 인사이트
        "인사이트": "005",
    },
    ("027", "007"): {  # 오딧세이
        "오딧세이 5세대": "103",
        "오딧세이": "006",
    },
    ("027", "013"): {  # Fit
        "Fit": "013",
    },
    ("027", "017"): {  # 리지라인
        "리지라인": "018",
    },
    ("027", "018"): {  # 스트림
        "스트림": "019",
    },
    ("027", "019"): {  # 파일럿
        "파일럿 4세대": "105",
        "파일럿 3세대": "031",
        "파일럿": "021",
    },
    ("027", "020"): {  # CR-Z
        "CR-Z": "022",
    },
    ("027", "022"): {  # 크로스투어
        "크로스투어": "024",
    },
    ("027", "027"): {  # S660
        "S660": "030",
    },
    ("027", "028"): {  # HR-V
        "HR-V": "032",
    },
    # 이스즈 (028)
    ("028", "001"): {  # 로데오
        "로데오": "001",
    },
    ("028", "002"): {  # 비크로스
        "비크로스": "002",
    },
    ("028", "003"): {  # 트루퍼
        "트루퍼": "003",
    },
    ("028", "005"): {  # 엘프
        "엘프": "004",
    },
    # 마쯔다 (029)
    ("029", "001"): {  # MX-6
        "MX-6": "001",
    },
    ("029", "002"): {  # MX-3
        "MX-3": "002",
    },
    ("029", "003"): {  # MX-5 MIATA
        "MX-5 MIATA": "003",
    },
    ("029", "004"): {  # RX-7
        "RX-7": "004",
    },
    ("029", "005"): {  # 밀레니아
        "밀레니아": "005",
    },
    ("029", "006"): {  # 프로티지
        "프로티지": "006",
    },
    ("029", "007"): {  # 626
        "626": "007",
    },
    ("029", "008"): {  # 유노스
        "유노스": "008",
    },
    ("029", "009"): {  # RX-8
        "RX-8": "009",
    },
    ("029", "010"): {  # AZ-1
        "AZ-1": "010",
    },
    ("029", "011"): {  # 데미오
        "데미오": "011",
    },
    ("029", "012"): {  # 마쯔다 5
        "마쯔다 5": "012",
    },
    ("029", "013"): {  # 마쯔다 6
        "마쯔다 6": "013",
    },
    ("029", "014"): {  # CX-7
        "CX-7": "014",
    },
    ("029", "015"): {  # CX-9
        "CX-9": "015",
    },
    ("029", "016"): {  # MPV
        "MPV": "016",
    },
    ("029", "018"): {  # 마쯔다 3
        "마쯔다 3": "017",
    },
    ("029", "019"): {  # CX-5
        "CX-5": "018",
    },
    # 미쯔비시 (030)
    ("030", "001"): {  # 이클립스
        "이클립스": "001",
    },
    ("030", "006"): {  # 파제로
        "파제로": "006",
    },
    ("030", "007"): {  # 랜서
        "랜서": "007",
    },
    ("030", "008"): {  # 아이
        "아이": "008",
    },
    ("030", "010"): {  # 랜서 에볼루션
        "랜서 에볼루션": "010",
    },
    ("030", "011"): {  # 아웃랜더
        "아웃랜더": "011",
    },
    ("030", "013"): {  # RVR
        "RVR": "013",
    },
    # 도요타 (031)
    ("031", "001"): {  # 캠리
        "캠리 (XV80)": "075",
        "캠리 (XV70)": "065",
        "뉴 캠리": "047",
        "캠리": "001",
    },
    ("031", "002"): {  # 아발론
        "아발론 5세대": "067",
        "아발론": "002",
    },
    ("031", "005"): {  # 코롤라
        "코롤라": "005",
    },
    ("031", "006"): {  # 랜드크루저
        "랜드크루저": "006",
    },
    ("031", "008"): {  # RAV4
        "RAV4 6세대": "076",
        "RAV4": "008",
    },
    ("031", "009"): {  # 수프라
        "GR 수프라": "068",
    },
    ("031", "020"): {  # 크라운
        "크라운 크로스오버": "070",
    },
    ("031", "022"): {  # 프리우스
        "프리우스 5세대": "074",
        "프리우스 C": "066",
        "프리우스 프라임": "062",
        "프리우스 4세대": "058",
        "프리우스 V": "026",
        "프리우스": "022",
    },
    ("031", "025"): {  # FJ 크루져
        "FJ 크루져": "025",
    },
    ("031", "027"): {  # bB
        "bB": "027",
    },
    ("031", "029"): {  # 시에나
        "시에나 4세대": "069",
        "시에나": "029",
    },
    ("031", "031"): {  # 솔라라
        "솔라라": "031",
    },
    ("031", "035"): {  # 하이랜더
        "하이랜더 4세대": "072",
        "하이랜더": "035",
    },
    ("031", "038"): {  # 툰드라
        "툰드라": "038",
    },
    ("031", "047"): {  # 86
        "GR86": "071",
        "86": "048",
    },
    ("031", "050"): {  # 알파드
        "알파드 4세대": "073",
        "알파드": "051",
    },
    ("031", "052"): {  # 벤자
        "벤자": "052",
    },
    ("031", "062"): {  # 사이언 xB
        "사이언 xB": "077",
    },
    # 닛산 (033)
    ("033", "005"): {  # 알티마
        "알티마 (L34)": "051",
        "알티마": "005",
    },
    ("033", "006"): {  # 맥시마
        "맥시마 (A36)": "047",
        "맥시마": "006",
    },
    ("033", "007"): {  # 패스파인더
        "패스파인더 4세대": "041",
        "패스파인더": "007",
    },
    ("033", "014"): {  # 휘가로
        "휘가로": "014",
    },
    ("033", "016"): {  # 마치
        "마치": "016",
    },
    ("033", "018"): {  # 350Z
        "350Z": "018",
    },
    ("033", "020"): {  # 큐브
        "큐브": "020",
    },
    ("033", "023"): {  # 로그
        "로그": "023",
    },
    ("033", "024"): {  # 무라노
        "무라노 (Z52)": "048",
        "무라노": "024",
    },
    ("033", "027"): {  # 370Z
        "370Z": "027",
    },
    ("033", "030"): {  # GT-R
        "GT-R": "030",
    },
    ("033", "038"): {  # NV
        "NV": "037",
    },
    ("033", "040"): {  # 쥬크
        "쥬크": "039",
    },
    ("033", "043"): {  # 캐시카이
        "캐시카이 2세대": "043",
    },
    ("033", "046"): {  # 리프
        "뉴 리프(ZE1)": "050",
        "리프": "046",
    },
    ("033", "047"): {  # 엑스트레일
        "엑스트레일": "049",
    },
    ("033", "048"): {  # 마이크라
        "마이크라": "052",
    },
    # 닷지 (034)
    ("034", "001"): {  # 어벤저
        "어벤저": "001",
    },
    ("034", "002"): {  # 인트레피드
        "인트레피드": "002",
    },
    ("034", "003"): {  # 램밴
        "램밴": "003",
    },
    ("034", "004"): {  # 램픽업
        "램픽업": "004",
    },
    ("034", "005"): {  # 밴
        "밴": "005",
    },
    ("034", "006"): {  # 다코타
        "다코타": "006",
    },
    ("034", "007"): {  # 바이퍼
        "바이퍼": "007",
    },
    ("034", "008"): {  # 캐러밴
        "캐러밴": "008",
    },
    ("034", "009"): {  # 듀랑고
        "듀랑고": "009",
    },
    ("034", "010"): {  # 캘리버
        "캘리버": "010",
    },
    ("034", "011"): {  # 니트로
        "니트로": "011",
    },
    ("034", "012"): {  # 그랜드 캐러밴
        "그랜드 캐러밴": "012",
    },
    ("034", "013"): {  # 매그넘
        "매그넘": "013",
    },
    ("034", "014"): {  # 챌린저
        "챌린저": "014",
    },
    ("034", "016"): {  # 차저
        "차저": "015",
    },
    # 렉서스 (035)
    ("035", "001"): {  # ES
        "올 뉴 ES": "066",
        "ES300h 7세대": "053",
        "뉴 ES300h": "037",
        "뉴 ES350": "036",
        "올 뉴 ES 일렉트릭": "067",
        "ES350": "016",
        "ES330": "009",
        "ES300": "001",
    },
    ("035", "002"): {  # GS
        "뉴 GS300": "049",
        "뉴 GS F": "046",
        "뉴 GS200t": "045",
        "뉴 GS450h": "035",
        "뉴 GS250": "032",
        "뉴 GS350": "031",
        "GS460": "026",
        "GS350": "018",
        "GS430": "012",
        "GS450h": "027",
        "GS300": "002",
    },
    ("035", "003"): {  # IS
        "뉴 IS300": "051",
        "뉴 IS200t": "041",
        "뉴 IS250": "038",
        "IS F": "030",
        "IS250": "013",
        "IS350": "017",
        "IS200": "003",
        "IS300": "014",
    },
    ("035", "004"): {  # LS
        "LS500 5세대": "052",
        "LS500h 5세대": "050",
        "LS460": "021",
        "LS460L": "022",
        "LS600hL": "025",
        "LS430": "005",
    },
    ("035", "005"): {  # RX
        "RX 5세대": "060",
        "RX450hL 4세대": "055",
        "RX450h 4세대": "044",
        "RX350 4세대": "043",
        "RX450h": "028",
        "RX350": "015",
        "RX330": "008",
        "RX400h": "019",
        "RX300": "006",
    },
    ("035", "006"): {  # SC
        "SC430": "007",
    },
    ("035", "008"): {  # LX
        "LX 4세대": "065",
    },
    ("035", "009"): {  # CT200h
        "CT200h": "029",
    },
    ("035", "013"): {  # NX
        "NX350h": "058",
        "NX450h+": "059",
        "NX300h": "034",
        "NX300": "048",
        "NX200t": "039",
    },
    ("035", "014"): {  # RC
        "RC": "042",
    },
    ("035", "015"): {  # LC
        "LC": "047",
    },
    ("035", "016"): {  # UX
        "UX300h": "063",
        "UX250h": "054",
        "UX300e": "057",
    },
    ("035", "017"): {  # RZ
        "RZ": "061",
    },
    ("035", "018"): {  # LM
        "LM": "064",
    },
    # 스즈키 (037)
    ("037", "001"): {  # 사이드킥
        "사이드킥": "001",
    },
    ("037", "002"): {  # 트윈
        "트윈": "002",
    },
    ("037", "003"): {  # 카푸치노
        "카푸치노": "003",
    },
    ("037", "004"): {  # X-90
        "X-90": "004",
    },
    ("037", "005"): {  # 스위프트
        "스위프트": "005",
    },
    ("037", "006"): {  # 웨건 R
        "웨건 R": "006",
    },
    ("037", "008"): {  # 알토라팡
        "알토라팡": "100",
    },
    ("037", "009"): {  # 허슬러
        "허슬러": "101",
    },
    ("037", "010"): {  # 그랜드 비타라
        "그랜드 비타라": "102",
    },
    ("037", "011"): {  # 알토
        "알토": "103",
    },
    ("037", "012"): {  # 짐니
        "짐니": "104",
    },
    # 쉐보레 (038)
    ("038", "001"): {  # 콜벳
        "콜벳": "001",
    },
    ("038", "002"): {  # 체비밴
        "체비밴": "002",
    },
    ("038", "003"): {  # 카마로
        "카마로": "003",
    },
    ("038", "004"): {  # 서버밴
        "서버밴": "004",
    },
    ("038", "005"): {  # 아스트로밴
        "아스트로밴": "005",
    },
    ("038", "006"): {  # 블레이저
        "트레일블레이저": "104",
        "블레이저": "006",
    },
    ("038", "007"): {  # 타호
        "타호": "007",
    },
    ("038", "008"): {  # HHR
        "HHR": "008",
    },
    ("038", "009"): {  # 실버라도
        "실버라도": "009",
    },
    ("038", "010"): {  # 아발란치
        "아발란치": "010",
    },
    ("038", "011"): {  # 루미나
        "루미나 미니밴": "011",
        "루미나": "103",
    },
    ("038", "012"): {  # 익스프레스밴
        "익스프레스밴": "012",
    },
    ("038", "014"): {  # 콜로라도
        "콜로라도": "100",
    },
    ("038", "015"): {  # SSR
        "SSR": "101",
    },
    ("038", "016"): {  # 트랙커
        "트랙커": "102",
    },
    ("038", "017"): {  # 벤처
        "벤처": "105",
    },
    ("038", "018"): {  # 트럭밴
        "트럭밴": "106",
    },
    ("038", "019"): {  # S-10
        "S-10": "107",
    },
    ("038", "020"): {  # 에퀴녹스
        "에퀴녹스": "108",
    },
    ("038", "021"): {  # 픽업트럭
        "픽업트럭": "109",
    },
    # 페라리 (041)
    ("041", "001"): {  # F355
        "F355": "001",
    },
    ("041", "003"): {  # 550
        "550": "003",
    },
    ("041", "004"): {  # 360
        "360": "004",
    },
    ("041", "005"): {  # F40
        "F40": "005",
    },
    ("041", "006"): {  # F50
        "F50": "006",
    },
    ("041", "008"): {  # 575M
        "575M": "008",
    },
    ("041", "009"): {  # 456
        "456": "009",
    },
    ("041", "010"): {  # 612
        "612": "010",
    },
    ("041", "011"): {  # F430
        "F430": "011",
    },
    ("041", "012"): {  # 엔초페라리
        "엔초페라리": "012",
    },
    ("041", "013"): {  # 512 TR
        "512 TR": "120",
    },
    ("041", "014"): {  # 캘리포니아
        "캘리포니아": "100",
    },
    ("041", "017"): {  # 599
        "599 GTO": "108",
        "599XX": "102",
        "599 GTB": "103",
    },
    ("041", "018"): {  # 458
        "458": "104",
    },
    ("041", "019"): {  # 348
        "348": "105",
    },
    ("041", "020"): {  # F12 베를리네타
        "F12 베를리네타": "106",
    },
    ("041", "021"): {  # FF
        "FF": "107",
    },
    ("041", "022"): {  # 488
        "488 피스타": "113",
        "488 GTB": "109",
        "488 스파이더": "110",
    },
    ("041", "023"): {  # GTC4 루쏘
        "GTC4 루쏘": "111",
    },
    ("041", "024"): {  # 812 
        "812 GTS": "114",
        "812 슈퍼패스트": "112",
    },
    ("041", "025"): {  # F8
        "F8 스파이더": "116",
        "F8 트리뷰토": "115",
    },
    ("041", "026"): {  # SF 90
        "SF 90 스파이더": "121",
        "SF 90 스트라달레": "117",
    },
    ("041", "027"): {  # 로마
        "로마": "118",
    },
    ("041", "028"): {  # 포르토피노
        "포르토피노": "119",
    },
    ("041", "029"): {  # 296
        "296 GTB": "122",
        "296 GTS": "123",
    },
    ("041", "030"): {  # 프로산게
        "프로산게": "124",
    },
    ("041", "031"): {  # 라페라리
        "라페라리": "125",
    },
    ("041", "032"): {  # 아말피
        "아말피": "126",
    },
    # 캐딜락 (043)
    ("043", "001"): {  # CTS
        "CTS 3세대": "105",
        "CTS 2세대": "012",
        "CTS 1세대": "001",
    },
    ("043", "002"): {  # STS
        "뉴 STS": "100",
        "STS": "008",
    },
    ("043", "003"): {  # SRX
        "올 뉴 SRX": "102",
        "SRX": "007",
    },
    ("043", "008"): {  # 에스컬레이드
        "에스컬레이드 IQ": "117",
        "에스컬레이드 5세대": "113",
        "에스컬레이드": "006",
    },
    ("043", "010"): {  # DTS
        "DTS": "010",
    },
    ("043", "011"): {  # BLS
        "BLS": "011",
    },
    ("043", "014"): {  # CTS-V
        "CTS-V": "103",
    },
    ("043", "015"): {  # ATS
        "ATS": "104",
    },
    ("043", "016"): {  # ATS-V
        "ATS-V": "106",
    },
    ("043", "017"): {  # CT6
        "CT6": "107",
    },
    ("043", "018"): {  # XT5
        "XT5": "108",
    },
    ("043", "019"): {  # XT6
        "XT6": "109",
    },
    ("043", "020"): {  # CT4
        "CT4": "110",
    },
    ("043", "021"): {  # CT5
        "CT5": "111",
    },
    ("043", "022"): {  # XT4
        "XT4": "112",
    },
    ("043", "023"): {  # CT5-V
        "CT5-V": "114",
    },
    ("043", "024"): {  # 리릭
        "리릭": "115",
    },
    ("043", "025"): {  # IQ
        "IQ": "116",
    },
    # 링컨 (044)
    ("044", "001"): {  # MKX
        "MKX 2세대": "104",
        "뉴 MKX": "101",
        "MKX": "007",
    },
    ("044", "002"): {  # MKZ
        "뉴 MKZ": "009",
        "MKZ": "006",
    },
    ("044", "003"): {  # LS
        "LS": "001",
    },
    ("044", "004"): {  # 컨티넨탈
        "컨티넨탈 10세대": "105",
        "컨티넨탈": "002",
    },
    ("044", "005"): {  # 타운카
        "타운카": "003",
    },
    ("044", "006"): {  # 에비에이터
        "에비에이터 2세대": "107",
        "에비에이터": "004",
    },
    ("044", "007"): {  # 네비게이터
        "네비게이터": "005",
    },
    ("044", "008"): {  # MKS
        "뉴 MKS": "102",
        "MKS": "008",
    },
    ("044", "010"): {  # MKT
        "MKT": "100",
    },
    ("044", "011"): {  # MKC
        "MKC": "103",
    },
    ("044", "012"): {  # 노틸러스
        "노틸러스 2세대": "109",
        "노틸러스": "106",
    },
    ("044", "013"): {  # 코세어
        "코세어": "108",
    },
    # 롤스로이스 (047)
    ("047", "001"): {  # 팬텀
        "팬텀": "001",
    },
    ("047", "002"): {  # 코니쉬
        "코니쉬": "002",
    },
    ("047", "003"): {  # 실버스퍼
        "실버스퍼": "003",
    },
    ("047", "004"): {  # 고스트
        "고스트 시리즈 2": "011",
        "고스트 2세대": "008",
        "고스트": "004",
    },
    ("047", "005"): {  # 레이스
        "레이스": "005",
    },
    ("047", "006"): {  # 던
        "던": "006",
    },
    ("047", "007"): {  # 컬리넌
        "컬리넌 시리즈2": "010",
        "컬리넌": "007",
    },
    ("047", "008"): {  # 스펙터
        "스펙터": "009",
    },
    # 험머 (048)
    ("048", "001"): {  # H1
        "H1": "001",
    },
    ("048", "002"): {  # H2
        "H2": "002",
    },
    ("048", "003"): {  # H3
        "H3T": "004",
        "H3": "003",
    },
    # 람보르기니 (049)
    ("049", "001"): {  # 무르시엘라고
        "무르시엘라고": "001",
    },
    ("049", "002"): {  # 디아블로
        "디아블로": "002",
    },
    ("049", "003"): {  # 가야르도
        "가야르도": "003",
    },
    ("049", "004"): {  # 잘파
        "잘파": "004",
    },
    ("049", "006"): {  # 레벤톤
        "레벤톤": "100",
    },
    ("049", "007"): {  # 아벤타도르
        "아벤타도르": "101",
    },
    ("049", "008"): {  # 우라칸
        "우라칸": "102",
    },
    ("049", "009"): {  # 우르스
        "우르스": "103",
    },
    ("049", "010"): {  # 레부엘토
        "레부엘토": "104",
    },
    # 벤틀리 (050)
    ("050", "001"): {  # 컨티넨탈
        "뉴 컨티넨탈": "102",
        "컨티넨탈": "003",
    },
    ("050", "002"): {  # 아르나지
        "아르나지": "001",
    },
    ("050", "003"): {  # 에이트
        "에이트": "002",
    },
    ("050", "005"): {  # 아주르
        "아주르": "100",
    },
    ("050", "006"): {  # 브룩랜즈
        "브룩랜즈": "101",
    },
    ("050", "007"): {  # 뮬산
        "뮬산": "103",
    },
    ("050", "008"): {  # 벤테이가
        "벤테이가": "104",
    },
    ("050", "009"): {  # 플라잉스퍼
        "플라잉스퍼 4세대": "108",
        "플라잉스퍼 3세대": "105",
        "플라잉스퍼 2세대": "106",
        "플라잉스퍼 1세대": "107",
    },
    ("050", "010"): {  # 토르칼
        "토르칼": "110",
    },
    # 스바루 (052)
    ("052", "002"): {  # 임프레자
        "임프레자": "002",
    },
    ("052", "003"): {  # 포레스터
        "포레스터": "003",
    },
    ("052", "004"): {  # 아웃백
        "아웃백": "004",
    },
    ("052", "005"): {  # 레거시
        "레거시": "005",
    },
    # 마세라티 (053)
    ("053", "001"): {  # 콰트로포르테
        "콰트로포르테": "001",
    },
    ("053", "005"): {  # 그란투리스모
        "그란투리스모 2세대": "016",
        "그란투리스모": "005",
    },
    ("053", "007"): {  # 그란카브리오
        "그란카브리오 2세대": "015",
        "그란카브리오": "007",
    },
    ("053", "009"): {  # 그란스포츠
        "그란스포츠": "009",
    },
    ("053", "010"): {  # 기블리
        "기블리": "010",
    },
    ("053", "011"): {  # 르반떼
        "르반떼": "011",
    },
    ("053", "012"): {  # MC20
        "MC20 첼로": "014",
        "MC20": "012",
    },
    ("053", "013"): {  # 그레칼레
        "그레칼레": "013",
    },
    ("053", "014"): {  # GT2 스트라달레
        "GT2 스트라달레": "018",
    },
    # 미니 (054)
    ("054", "001"): {  # 쿠퍼
        "쿠퍼 (4세대)": "155",
        "쿠퍼 (3세대 F/L) 5도어": "151",
        "쿠퍼 (3세대 F/L)": "150",
        "쿠퍼 (3세대)": "137",
        "쿠퍼 (3세대) 5도어": "138",
        "쿠퍼 (2세대)": "136",
        "쿠퍼 (1세대)": "135",
    },
    ("054", "002"): {  # 클럽맨
        "쿠퍼 클럽맨(2세대 F/L)": "153",
        "쿠퍼 클럽맨(2세대)": "145",
        "쿠퍼 클럽맨(1세대)": "144",
    },
    ("054", "003"): {  # 컨트리맨
        "쿠퍼 컨트리맨 (3세대)": "156",
        "쿠퍼 컨트리맨 (2세대 F/L)": "154",
        "쿠퍼 컨트리맨 (2세대)": "147",
        "쿠퍼 컨트리맨 (1세대)": "146",
    },
    ("054", "004"): {  # 로드스터
        "쿠퍼 로드스터": "143",
    },
    ("054", "006"): {  # 쿠페
        "쿠퍼 쿠페": "142",
    },
    ("054", "011"): {  # 쿠퍼 컨버터블
        "쿠퍼 컨버터블(4세대)": "160",
        "쿠퍼 컨버터블(3세대 F/L)": "152",
        "쿠퍼 컨버터블(3세대)": "141",
        "쿠퍼 컨버터블(2세대)": "140",
        "쿠퍼 컨버터블(1세대)": "139",
    },
    ("054", "012"): {  # 페이스맨
        "쿠퍼 페이스맨": "148",
    },
    ("054", "013"): {  # 쿠퍼 일렉트릭
        "더 뉴 미니 일렉트릭": "157",
        "에이스맨 일렉트릭": "159",
        "컨트리맨 일렉트릭": "158",
        "쿠퍼 일렉트릭": "149",
    },
    # GMC (056)
    ("056", "001"): {  # 소노마
        "소노마": "001",
    },
    ("056", "002"): {  # 밴츄라
        "밴츄라": "002",
    },
    ("056", "003"): {  # 사바나
        "사바나": "003",
    },
    ("056", "004"): {  # 유콘
        "유콘": "004",
    },
    ("056", "005"): {  # 지미
        "지미": "005",
    },
    ("056", "006"): {  # 시에라
        "시에라 (5세대)": "106",
        "시에라": "006",
    },
    ("056", "008"): {  # 사파리
        "사파리": "100",
    },
    ("056", "009"): {  # 터레인
        "터레인": "102",
    },
    ("056", "010"): {  # 캐니언
        "캐니언 (3세대)": "105",
        "캐니언": "103",
    },
    ("056", "011"): {  # 아카디아
        "아카디아": "104",
    },
    ("056", "012"): {  # 허머 EV
        "허머 EV": "107",
    },
    # 인피니티 (058)
    ("058", "001"): {  # FX
        "FX30d": "016",
        "FX37": "017",
        "FX50": "011",
        "FX35": "005",
        "FX45": "006",
    },
    ("058", "002"): {  # G
        "G25": "015",
        "G37": "009",
        "G35": "001",
    },
    ("058", "003"): {  # M
        "M30d": "014",
        "M37": "012",
        "M56": "013",
        "M35": "002",
        "M45": "004",
    },
    ("058", "004"): {  # Q
        "Q45": "003",
    },
    ("058", "005"): {  # QX
        "QX56": "007",
    },
    ("058", "007"): {  # EX
        "EX30d": "021",
        "EX35": "010",
        "EX37": "022",
    },
    ("058", "008"): {  # JX
        "JX35": "018",
    },
    ("058", "011"): {  # Q60
        "Q60 (CV37)": "032",
        "Q60": "024",
    },
    ("058", "012"): {  # Q70
        "Q70": "025",
    },
    ("058", "013"): {  # QX50
        "뉴 QX50": "034",
        "QX50": "026",
    },
    ("058", "014"): {  # QX60
        "QX60": "027",
    },
    ("058", "015"): {  # QX70
        "QX70": "028",
    },
    ("058", "016"): {  # QX80
        "QX80": "029",
    },
    ("058", "017"): {  # Q50
        "Q50": "030",
    },
    ("058", "018"): {  # Q30
        "Q30": "031",
    },
    ("058", "019"): {  # QX30
        "QX30": "033",
    },
    # 애스턴마틴 (070)
    ("070", "001"): {  # 뱅퀴시
        "뱅퀴시 S": "001",
        "뱅퀴시": "072",
    },
    ("070", "002"): {  # DB9
        "DB9": "002",
    },
    ("070", "003"): {  # 밴티지
        "벤티지 2세대": "078",
        "V12 Vantage": "071",
        "V8 Vantage": "003",
    },
    ("070", "004"): {  # DBS
        "DBS": "004",
    },
    ("070", "006"): {  # 라피드
        "라피드": "073",
    },
    ("070", "007"): {  # 비라지
        "비라지": "074",
    },
    ("070", "008"): {  # DB7
        "DB7": "075",
    },
    ("070", "009"): {  # DB11
        "DB11": "076",
    },
    ("070", "010"): {  # DBX
        "DBX": "077",
    },
    # 마이바흐 (080)
    ("080", "001"): {  # 57
        "57": "001",
    },
    ("080", "002"): {  # 57s
        "57s": "002",
    },
    ("080", "003"): {  # 62
        "62": "003",
    },
    ("080", "004"): {  # 62s
        "62s": "004",
    },
    ("080", "005"): {  # 62s 렌들렛
        "62s 렌들렛": "005",
    },
    ("080", "006"): {  # 57 제플린
        "57 제플린": "006",
    },
    ("080", "007"): {  # 62 제플린
        "62 제플린": "007",
    },
    # 스마트 (081)
    ("081", "001"): {  # 포투
        "포투 카브리오 3세대": "008",
        "포투 쿠페 3세대": "006",
        "포투 카브리오": "002",
        "포투 쿠페": "001",
    },
    ("081", "002"): {  # 포포
        "포포 W453": "007",
        "포포": "003",
    },
    ("081", "003"): {  # 로드스터
        "로드스터": "004",
    },
    # 지프 (083)
    ("083", "001"): {  # 랭글러
        "랭글러 (JL)": "013",
        "랭글러 (JK)": "011",
        "랭글러 (TJ)": "010",
    },
    ("083", "002"): {  # 체로키
        "뉴 그랜드 체로키": "018",
        "올 뉴 그랜드 체로키": "016",
        "체로키(KL)": "007",
        "그랜드 체로키": "003",
        "체로키": "002",
    },
    ("083", "003"): {  # 커맨더
        "커맨더": "004",
    },
    ("083", "004"): {  # 패트리어트
        "패트리어트": "005",
    },
    ("083", "005"): {  # 컴패스
        "컴패스 2세대": "012",
        "컴패스": "006",
    },
    ("083", "006"): {  # 레니게이드
        "레니게이드": "008",
    },
    ("083", "008"): {  # 글래디에이터
        "글래디에이터 (JT)": "014",
    },
    ("083", "009"): {  # 어벤저
        "어벤저": "017",
    },
    # 맥라렌 (084)
    ("084", "001"): {  # 650S
        "650S": "001",
    },
    ("084", "002"): {  # 570S
        "570S": "002",
    },
    ("084", "003"): {  # 720S
        "720S": "006",
    },
    ("084", "004"): {  # 675LT
        "675LT": "005",
    },
    ("084", "005"): {  # 570GT
        "570GT": "003",
    },
    ("084", "006"): {  # 600LT
        "600LT": "004",
    },
    ("084", "007"): {  # 765LT
        "765LT": "007",
    },
    ("084", "008"): {  # GT
        "GT": "008",
    },
    ("084", "009"): {  # MP4-12C
        "MP4-12C": "009",
    },
    ("084", "010"): {  # 아투라
        "아투라": "010",
    },
    # 포톤 (085)
    ("085", "001"): {  # 툰랜드
        "툰랜드": "001",
    },
    # 북기은상 (086)
    ("086", "001"): {  # CK 미니밴
        "CK 미니밴": "001",
    },
    ("086", "002"): {  # CK 미니트럭
        "CK 미니트럭": "002",
    },
    ("086", "003"): {  # 켄보 600
        "켄보 600": "003",
    },
    # 테슬라 (087)
    ("087", "001"): {  # 모델 S
        "모델 S": "001",
    },
    ("087", "002"): {  # 모델 X
        "모델 X": "002",
    },
    ("087", "003"): {  # 모델 3
        "모델 3 하이랜드": "005",
        "모델 3": "003",
    },
    ("087", "004"): {  # 모델 Y
        "모델 Y 주니퍼": "006",
        "모델 Y": "004",
    },
    ("087", "005"): {  # 사이버트럭
        "사이버트럭": "007",
    },
    # 대우버스 (088)
    ("088", "001"): {  # 레스타
        "레스타": "001",
    },
    ("088", "002"): {  # FX
        "FX": "002",
    },
    # 동풍소콘 (090)
    ("090", "001"): {  # 펜곤 ix5
        "펜곤 ix5": "001",
    },
    ("090", "002"): {  # C35
        "C35": "002",
    },
    ("090", "003"): {  # C31
        "C31": "003",
    },
    ("090", "004"): {  # C32
        "C32": "004",
    },
    ("090", "005"): {  # SX6
        "SX6": "005",
    },
    # 폴스타 (091)
    ("091", "001"): {  # 폴스타 2
        "폴스타 2": "001",
    },
    ("091", "002"): {  # 폴스타 4
        "폴스타 4": "002",
    },
    ("091", "003"): {  # 폴스타 3
        "폴스타 3": "003",
    },
    # BYD (093)
    ("093", "001"): {  # 아토 3
        "아토 3": "001",
    },
    ("093", "002"): {  # T4K
        "T4K": "002",
    },
    ("093", "003"): {  # 씰
        "씰": "003",
    },
    ("093", "004"): {  # 씨라이언 7
        "씨라이언 7": "004",
    },
    ("093", "005"): {  # 돌핀
        "돌핀": "005",
    },
    ("093", "006"): {  # 씨라이언 6 DM-i
        "씨라이언 6 DM-i": "006",
    },
    # 지커 (094)
    ("094", "001"): {  # 7X
        "7X": "001",
    },
}


from services.kcar_grade_data import KCAR_GRADE_TREE


def resolve_kcar_grade_codes(m_cd: str, grp_cd: str, mod_cd: str, sub_model: str = "", raw_car_name: str = ""):
    """(m_cd, grp_cd, mod_cd) 모델 내에서 sub_model에 부합하는 (grd_cd, grd_dtl_cd) 반환."""
    if not sub_model or str(sub_model).strip() in ("", "전체", "-"):
        return "", ""

    m_key = f"{m_cd},{grp_cd},{mod_cd}"
    grd_map = KCAR_GRADE_TREE.get(m_key)
    if not grd_map:
        return "", ""

    def _norm(s: str) -> str:
        return re.sub(r'[\s\(\)\-_\/]+', '', str(s)).upper()

    sub_str = str(sub_model).strip()
    combined_src = f"{raw_car_name} {sub_str}".strip()
    comb_norm = _norm(combined_src)

    from services.model_matcher import ModelMatcher
    q_turbo = ModelMatcher.extract_turbo(combined_src)
    has_turbo = bool(q_turbo is True)
    has_van = ("밴" in comb_norm) or ("카고" in comb_norm)
    has_lpg = ("LPG" in comb_norm) or ("LPI" in comb_norm) or ("LPE" in comb_norm)
    has_diesel = ("디젤" in comb_norm) or ("VGT" in comb_norm) or ("TDI" in comb_norm) or ("CDI" in comb_norm) or bool(re.search(r'\d\.\d\s*D(?![A-Z])', combined_src.upper()))
    has_gasoline = ("가솔린" in comb_norm) or ("GDI" in comb_norm) or ("GDE" in comb_norm) or ("GTE" in comb_norm) or ("MPI" in comb_norm) or ("휘발유" in comb_norm)

    has_4wd = (
        ("4WD" in comb_norm) or ("AWD" in comb_norm) or
        ("4MATIC" in comb_norm) or ("XDRIVE" in comb_norm) or ("QUATTRO" in comb_norm) or
        ("4매틱" in comb_norm) or ("콰트로" in comb_norm) or ("4륜" in comb_norm) or ("사륜" in comb_norm)
    )
    has_2wd = ("2WD" in comb_norm) or ("FF" in comb_norm)

    seat_m = re.search(r'(\d+)\s*인승', combined_src)
    target_seat = f"{seat_m.group(1)}인승" if seat_m else ""

    disp_m = re.findall(r'(\d\.\d)', combined_src)
    if not disp_m:
        m_hg = re.search(r'(?:HG|TG|IG|K7|K5|SM[3567])\s*(\d)(\d)0', comb_norm)
        if m_hg:
            disp_m = [f"{m_hg.group(1)}.{m_hg.group(2)}"]
    target_disp = disp_m[0] if disp_m else ""

    special_keywords = ["하이리무진", "아웃도어", "캠핑", "특장", "택시", "장애인", "렌터카", "수출", "운전교습", "어린이", "킨더", "구급", "휠체어", "N라인", "NLINE", "GT"]

    non_van_grds = [k for k in grd_map.keys() if "밴" not in _norm(k) and "카고" not in _norm(k)] or list(grd_map.keys())
    turbo_flags = [("터보" in _norm(k) or bool(re.search(r'\d\.\d\s*T(?![A-Z])', k.upper()))) for k in non_van_grds]
    has_both_turbo_and_na = any(turbo_flags) and not all(turbo_flags)

    spec_ignore = {
        "가솔린", "디젤", "전기", "EV", "하이브리드", "HEV", "LPG", "LPI", "LPE",
        "2WD", "4WD", "AWD", "FF", "FR", "터보", "일반인판매용", "일반판매용", "일반인",
        "롱레인지", "스탠다드",
        "4MATIC", "XDRIVE", "QUATTRO", "콰트로", "4매틱", "4륜", "사륜"
    }
    extra_suffixes = ["스페셜", "플러스", "PLUS", "스포츠", "베이직", "라이트", "초이스", "어드밴스", "프리미어", "익스트림", "TUIX", "살롱"]

    best_grd_cd = ""
    best_dtl_cd = ""
    best_score = -999

    for grd_nm, g_obj in grd_map.items():
        grd_cd = g_obj["cd"]
        dtl_map = g_obj.get("dtl", {})
        g_norm = _norm(grd_nm)

        g_is_van = ("밴" in g_norm) or ("카고" in g_norm)
        if has_van != g_is_van:
            continue

        g_is_turbo = ("터보" in g_norm) or bool(re.search(r'\d\.\d\s*T(?![A-Z])', grd_nm.upper()))
        if has_both_turbo_and_na and q_turbo is not None and (bool(q_turbo) != g_is_turbo):
            continue

        g_seat_m = re.search(r'(\d+)\s*인승', grd_nm)
        g_seat = f"{g_seat_m.group(1)}인승" if g_seat_m else ""
        if target_seat and g_seat and target_seat != g_seat:
            continue

        g_disp_m = re.findall(r'(\d\.\d)', grd_nm)
        g_disp = g_disp_m[0] if g_disp_m else ""
        if target_disp and g_disp and target_disp != g_disp:
            continue

        g_is_lpg = ("LPG" in g_norm) or ("LPI" in g_norm) or ("LPE" in g_norm)
        g_is_diesel = ("디젤" in g_norm) or ("VGT" in g_norm) or ("TDI" in g_norm)
        g_is_gas = ("가솔린" in g_norm) or ("GDI" in g_norm) or ("GDE" in g_norm) or ("GTE" in g_norm) or ("MPI" in g_norm) or ("VVT" in g_norm)

        if has_lpg and not g_is_lpg and (g_is_diesel or g_is_gas):
            continue
        if not has_lpg and g_is_lpg:
            continue
        if has_diesel and g_is_gas:
            continue
        if has_gasoline and g_is_diesel:
            continue
        if not has_gasoline and g_is_gas and any(not ("가솔린" in _norm(k)) for k in grd_map.keys()):
            if has_diesel or any("9인승" in k or "11인승" in k for k in grd_map.keys()):
                continue

        g_is_4wd = (
            ("4WD" in g_norm) or ("AWD" in g_norm) or
            ("4MATIC" in g_norm) or ("XDRIVE" in g_norm) or ("QUATTRO" in g_norm) or
            ("콰트로" in g_norm) or ("4매틱" in g_norm) or ("4륜" in g_norm) or ("사륜" in g_norm)
        )
        g_is_2wd = ("2WD" in g_norm)
        if has_4wd and g_is_2wd:
            continue
        if has_2wd and g_is_4wd:
            continue
        if not has_4wd and not has_2wd and g_is_4wd:
            continue

        skip_special = False
        for sp in special_keywords:
            sp_n = _norm(sp)
            if sp_n in g_norm and sp_n not in comb_norm:
                skip_special = True
                break
        if skip_special:
            continue
        if "리무진" in g_norm and "하이리무진" not in g_norm and "리무진" not in comb_norm:
            continue

        score = 0
        if len(grd_map) == 1:
            score += 5
        if target_disp and g_disp == target_disp:
            score += 10
        if target_seat and g_seat == target_seat:
            score += 10
        if has_turbo and g_is_turbo:
            score += 8
        if has_2wd and g_is_2wd:
            score += 6
        if has_4wd and g_is_4wd:
            score += 6
        if has_diesel and g_is_diesel:
            score += 5
        if has_gasoline and g_is_gas:
            score += 5
        if has_lpg and g_is_lpg:
            score += 5
        if "일반" in g_norm:
            score += 2

        grd_tokens = [_norm(t) for t in re.split(r'[\s\(\)\/\-\+]+', grd_nm) if _norm(t) and _norm(t) not in spec_ignore]
        non_spec_tokens = [t for t in grd_tokens if not re.match(r'^(\d+\.\d+T?|\d+인승|GDI|GDE|GTE|VGT|EVGT|VVT|MPI|LPE|TDI)$', t)]
        if non_spec_tokens:
            if all(t in comb_norm for t in non_spec_tokens):
                bad_suffix = False
                for ex in extra_suffixes:
                    if ex in g_norm and ex not in comb_norm:
                        bad_suffix = True
                        break
                if bad_suffix:
                    continue
                score += 20 + sum(len(t) for t in non_spec_tokens)
            else:
                continue

        matched_dtl_cd = ""
        dtl_best_len = 0
        if dtl_map:
            for d_nm, d_cd in dtl_map.items():
                d_norm = _norm(d_nm)
                if not d_norm:
                    continue
                if d_norm in comb_norm:
                    if len(d_norm) > dtl_best_len:
                        dtl_best_len = len(d_norm)
                        matched_dtl_cd = d_cd

        total_score = score + (15 + dtl_best_len if matched_dtl_cd else 0)
        if total_score > best_score:
            best_score = total_score
            best_grd_cd = grd_cd
            best_dtl_cd = matched_dtl_cd

    if best_score <= 0 and not best_dtl_cd:
        return "", ""
    return best_grd_cd, best_dtl_cd


def resolve_kcar_model_codes(raw_base_name: str, brand_hint: str = "", sub_model: str = ""):
    """base_name에서 제조사와 모델명을 추출하여 K-Car (mnuftr_cd, model_grp_cd, model_cd) 반환. 매핑 없으면 None."""
    if not raw_base_name or not str(raw_base_name).strip():
        return None

    text = str(raw_base_name).strip()
    detected_mnuftr_cd = ""

    # 1. base_name 앞부분 또는 brand_hint에서 제조사 추출
    for b_name in sorted(KCAR_MNUFTR_MAP.keys(), key=len, reverse=True):
        if text.startswith(b_name):
            detected_mnuftr_cd = KCAR_MNUFTR_MAP[b_name]
            text = text[len(b_name):].strip()
            break
    if not detected_mnuftr_cd and brand_hint and str(brand_hint).strip() != "전체":
        b_hint = str(brand_hint).strip()
        for b_name, m_cd in sorted(KCAR_MNUFTR_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if b_name in b_hint or b_hint in b_name:
                detected_mnuftr_cd = m_cd
                break

    def _norm(s: str) -> str:
        return re.sub(r'[\s\(\)\-_\/]+', '', str(s)).upper()

    norm_text = _norm(text)
    if not norm_text:
        return None

    # 제네시스 라인 특수 접두사/F/L 매핑 (더 올 뉴, 디 올 뉴, 더 뉴 G80/GV70/GV80/G90)
    GENESIS_PREFIX_MAP = [
        ("더올뉴G80", ("007", "002", "007")),
        ("디올뉴G80", ("007", "002", "007")),
        ("올뉴G80", ("007", "002", "007")),
        ("G80RG3FL", ("007", "002", "015")),
        ("더뉴G80", ("007", "002", "015")),
        ("더뉴GV70", ("007", "006", "017")),
        ("디올뉴GV70", ("007", "006", "017")),
        ("GV70FL", ("007", "006", "017")),
        ("더뉴GV80", ("007", "005", "016")),
        ("디올뉴GV80", ("007", "005", "016")),
        ("GV80FL", ("007", "005", "016")),
        ("더뉴G90", ("007", "004", "012")),
        ("디올뉴G90", ("007", "004", "012")),
        ("G90RS4", ("007", "004", "012")),
    ]
    for pfx, code_tuple in GENESIS_PREFIX_MAP:
        if norm_text.startswith(pfx):
            return code_tuple

    sub_norm = _norm(sub_model)
    is_hev_sub = ("HEV" in sub_norm or "하이브리드" in sub_norm) and ("하이브리드" not in norm_text)

    # 2. 괄호 포함 원문 및 괄호 제거 텍스트 기준 최장 일치(Longest Prefix Match) 탐색
    candidates = []
    for (m_cd, grp_cd), models_dict in KCAR_MODEL_GROUP_MAP.items():
        if detected_mnuftr_cd and m_cd != detected_mnuftr_cd:
            continue
        for m_name, mod_cd in models_dict.items():
            # '하이브리드 4세대' 단독 키는 원문에 '카니발'이 포함된 경우에만 매칭 허용
            if m_name == "하이브리드 4세대" and "카니발" not in raw_base_name:
                continue
            nm = _norm(m_name)
            if nm and (norm_text == nm or norm_text.startswith(nm)):
                candidates.append((len(nm), m_cd, grp_cd, mod_cd))
            elif is_hev_sub and "하이브리드" in nm:
                nm_no_hev = nm.replace("하이브리드", "")
                if nm_no_hev and (norm_text == nm_no_hev or norm_text.startswith(nm_no_hev)):
                    candidates.append((len(nm) + 10, m_cd, grp_cd, mod_cd))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        _, m_cd, grp_cd, mod_cd = candidates[0]
        return m_cd, grp_cd, mod_cd

    # 🌟 2차: 원문 매칭 실패 시, 공유 매처(ModelMatcher.GENERATION_PREFIXES)의 세대 접두사를 분리하여 폴백 탐색 (원문 우선 보존)
    from services.model_matcher import ModelMatcher
    stripped_norm = norm_text
    for pfx in sorted(ModelMatcher.GENERATION_PREFIXES, key=len, reverse=True):
        pfx_norm = _norm(pfx)
        if pfx_norm and stripped_norm.startswith(pfx_norm):
            stripped_norm = stripped_norm[len(pfx_norm):]
            break

    if stripped_norm and stripped_norm != norm_text:
        fallback_candidates = []
        for (m_cd, grp_cd), models_dict in KCAR_MODEL_GROUP_MAP.items():
            if detected_mnuftr_cd and m_cd != detected_mnuftr_cd:
                continue
            for m_name, mod_cd in models_dict.items():
                if m_name == "하이브리드 4세대" and "카니발" not in raw_base_name:
                    continue
                nm = _norm(m_name)
                if nm and (stripped_norm == nm or stripped_norm.startswith(nm)):
                    fallback_candidates.append((len(nm), m_cd, grp_cd, mod_cd))
                elif is_hev_sub and "하이브리드" in nm:
                    nm_no_hev = nm.replace("하이브리드", "")
                    if nm_no_hev and (stripped_norm == nm_no_hev or stripped_norm.startswith(nm_no_hev)):
                        fallback_candidates.append((len(nm) + 10, m_cd, grp_cd, mod_cd))
        if fallback_candidates:
            fallback_candidates.sort(key=lambda x: x[0], reverse=True)
            _, m_cd, grp_cd, mod_cd = fallback_candidates[0]
            return m_cd, grp_cd, mod_cd

    return None


def encrypt_kcar_payload(data: dict) -> str:
    """K-Car 공식 API용 AES-128-CBC PKCS7 암호화 (Base64 인코딩)"""
    filtered = {k: v for k, v in data.items() if v is not None and v != ""}
    raw_str = json.dumps(filtered, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(raw_str) + padder.finalize()
    cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV))
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(ct).decode('utf-8')


def build_kcar_web_url(car_name: str, year: int = 0, detail_model: str = "", mileage: int = 0, manufacturer: str = "", mileage_range: int = 30000) -> str:
    """K-Car 공식 웹사이트 직영차 검색 바로가기 URL 동적 생성"""
    codes = resolve_kcar_model_codes(car_name, brand_hint=manufacturer, sub_model=detail_model)
    cond: Dict[str, Any] = {}
    if codes:
        cond["wr_eq_mnuftr_cd"] = codes[0]
        cond["wr_eq_model_grp_cd"] = codes[1]
        cond["wr_eq_model_cd"] = codes[2]
        grd_cd, grd_dtl_cd = resolve_kcar_grade_codes(codes[0], codes[1], codes[2], detail_model, car_name)
        if grd_cd:
            cond["wr_eq_grd_cd"] = grd_cd
            if grd_dtl_cd:
                cond["wr_eq_grd_dtl_cd"] = grd_dtl_cd
    elif car_name:
        cond["wr_txt_idx"] = car_name
        cond["wr_in_model_nm"] = car_name

    if year and year > 0:
        k_yr = 2000 + year if year < 100 else year
        cond["wr_gt_mfg_dt"] = f"{k_yr - 1}01"
        cond["wr_lt_mfg_dt"] = f"{k_yr + 1}12"

    if mileage and mileage > 0:
        rounded = round(mileage / 10000) * 10000
        cond["wr_gt_milg"] = max(0, rounded - mileage_range)
        cond["wr_lt_milg"] = rounded + mileage_range

    if cond:
        return f"https://www.kcar.com/bc/search?searchCond={urllib.parse.quote(json.dumps(cond))}"
    return "https://www.kcar.com/bc/search"


def extract_kcar_trim_keyword(detail_model: str) -> str:
    """세부모델/등급 문자열에서 K-Car 검색에 유효한 핵심 트림 키워드 추출"""
    if not detail_model:
        return ""
    TRIM_PATTERNS = [
        "캘리그래피", "인스퍼레이션", "익스클루시브", "르블랑", "프리미엄", "모던", "스마트",
        "시그니처", "노블레스", "프레스티지", "트렌디", "스타일", "럭셔리", "디럭스",
        "스페셜", "그래비티", "하이테크", "마스터즈", "패밀리"
    ]
    for kw in TRIM_PATTERNS:
        if kw in detail_model:
            return kw
    tokens = [t.strip() for t in detail_model.split() if len(t.strip()) >= 2]
    if tokens:
        return tokens[-1]
    return ""


def fetch_kcar_market_stats(
    car_name: str,
    year: int = 0,
    detail_model: str = "",
    mileage: int = 0,
    manufacturer: str = "",
    accident: str = "PERFECT",
    target_options: Union[str, List[Dict[str, Any]]] = ""
) -> Dict[str, Any]:
    """
    K-Car 실시간 직영 매물 검색 및 시세 통계 산출
    반환:
      - success: bool
      - count: 총 매물수
      - min, max, avg, median: 가격 통계 (만원 정수)
      - yearStats: 연식별 평균가 및 대수 리스트
      - priceBins: 가격 구간별 대수 및 비율
      - cars: 대표 매물 리스트
      - modelName, searchUrl: 부가 정보
    """
    search_url = build_kcar_web_url(car_name, year, detail_model, mileage, manufacturer)
    empty_res = {
        "success": False,
        "count": 0,
        "min": 0,
        "max": 0,
        "avg": 0,
        "avgAdj": 0,
        "accDeduction": 0,
        "adjNote": "",
        "median": 0,
        "postFilterFallback": False,
        "yearStats": [],
        "priceBins": [],
        "cars": [],
        "modelName": "",
        "searchUrl": search_url,
        "message": ""
    }

    if not car_name or not str(car_name).strip():
        empty_res["message"] = "차량명이 지정되지 않았습니다."
        return empty_res

    codes = resolve_kcar_model_codes(car_name, brand_hint=manufacturer, sub_model=detail_model)
    if not codes:
        empty_res["message"] = f"K-Car 모델 코드 매핑 없음 ('{car_name}')"
        return empty_res

    m_cd, grp_cd, mod_cd = codes
    grd_cd, grd_dtl_cd = resolve_kcar_grade_codes(m_cd, grp_cd, mod_cd, detail_model, car_name)

    # K-Car 직영 검색 API 파라미터 구성 (최대 100대)
    param: Dict[str, Any] = {
        "wr_eq_mnuftr_cd": m_cd,
        "wr_eq_model_grp_cd": grp_cd,
        "wr_eq_model_cd": mod_cd,
        "pageno": 1,
        "limit": 100
    }

    # a) 등급 코드 파라미터 (해소 시 wr_eq_grd_cd, 세부코드 시 wr_eq_grd_dtl_cd)
    # 💡 [원칙]: 등급 코드 미해소 시 wr_txt_idx를 하드 필터로 쓰지 않고 모델 단위로 폭넓게 수집 후,
    # 2단계 백엔드 정식 스펙 동등성(DataProcessor.is_strictly_same_spec)으로 엄격 분별 (TV7 등으로 인한 승용 탈락 원천 방지)
    if grd_cd:
        param["wr_eq_grd_cd"] = grd_cd
        if grd_dtl_cd:
            param["wr_eq_grd_dtl_cd"] = grd_dtl_cd

    # b) 연식 파라미터 (wr_gt_mfg_dt, wr_lt_mfg_dt: ±1년 교정)
    if year and year > 0:
        k_yr = 2000 + year if year < 100 else year
        param["wr_gt_mfg_dt"] = f"{k_yr - 1}01"
        param["wr_lt_mfg_dt"] = f"{k_yr + 1}12"

    # c) 주행거리 파라미터 (wr_gt_milg, wr_lt_milg: 만단위 반올림 후 ±3만km 통일, build_kcar_web_url 및 엔카 대칭)
    if mileage and mileage > 0:
        rounded = round(mileage / 10000) * 10000
        param["wr_gt_milg"] = max(0, rounded - 30000)
        param["wr_lt_milg"] = rounded + 30000

    print(f"[K-Car API 요청] car_name='{car_name}', year={year}, detail_model='{detail_model}', mileage={mileage} => param = {param}", flush=True)

    enc_val = encrypt_kcar_payload(param)
    req_body = json.dumps({"enc": enc_val}).encode('utf-8')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://www.kcar.com',
        'Referer': 'https://www.kcar.com/'
    }

    try:
        req = urllib.request.Request('https://api.kcar.com/bc/search/list/drct', data=req_body, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data_raw = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        empty_res["message"] = f"K-Car API 통신 오류: {str(e)}"
        return empty_res

    rows = data_raw.get('data', {}).get('rows', [])
    if not rows:
        empty_res["success"] = True
        empty_res["message"] = "현재 판매 중인 K-Car 직영 매물이 없습니다."
        return empty_res

    # d) 백엔드 2단계 정밀 후처리 필터 (엔카 filter_strictly_by_submodel 대칭 로직)
    # - 엔진 배기량 (예: 2.0 요청 시 1.6터보 배제 등)
    # - 유종 상호 배제 (가솔린 요청 시 디젤/LPi/하이브리드 배제 등)
    # - 트림 엄격 일치 (노블레스 요청 시 트렌디/프레스티지 등 배제)
    sub_raw = str(detail_model or "").strip()
    sub_clean = sub_raw.lower().replace(" ", "")

    disp_m = re.search(r'(\d\.\d)', sub_raw)
    disp_val = disp_m.group(1) if disp_m else ""

    from services.model_matcher import ModelMatcher
    q_turbo = ModelMatcher.extract_turbo(f"{manufacturer} {car_name} {sub_raw}", disp=disp_val)

    is_q_diesel = any(k in sub_clean for k in ['디젤', 'diesel', 'crdi', 'vgt'])
    is_q_gas = any(k in sub_clean for k in ['가솔린', 'gasoline', 'gdi', 'cvvl'])
    is_q_lpg = any(k in sub_clean for k in ['lpi', 'lpg'])

    from services.data_processor import DataProcessor
    target_yr_2d = f"{year % 100:02d}" if year and year > 0 else ""
    ref_grade = DataProcessor.extract_grade_keyword(detail_model)
    if not ref_grade:
        ref_grade = str(detail_model).strip()
    ref_g_clean = ref_grade.lower().replace(" ", "")

    COMPETING_GRADES = {
        "lt": ["프리미어", "premier", "ls", "ltz", "마이핏", "redline", "레드라인"],
        "ls": ["lt", "프리미어", "premier", "ltz"],
        "프리미어": ["lt", "ls", "ltz"],
        "인스퍼레이션": ["프리미엄", "모던", "스마트", "스타일", "익스클루시브", "캘리그래피"],
        "스마트": ["모던", "프리미엄", "익스클루시브", "인스퍼레이션", "스타일", "스포츠"],
        "노블레스": ["프레스티지", "트렌디", "시그니처", "그래비티"],
        "프레스티지": ["노블레스", "트렌디", "시그니처", "럭셔리", "디럭스", "그래비티"],
        "시그니처": ["노블레스", "프레스티지", "트렌디", "스탠다드", "베스트셀렉션"]
    }

    def _extract_kcar_year(r_dict: dict) -> tuple[int, str]:
        """K-Car 매물의 최초등록일(mfgDt: YYYYMM) 우선 연식 추출 (부재 시 prdcnYr 폴백)"""
        mfg = str(r_dict.get('mfgDt') or '').strip()
        if mfg:
            m = re.search(r'^(20\d{2}|19\d{2})', mfg)
            if m:
                full_y = int(m.group(1))
                return full_y, mfg

        prd = str(r_dict.get('prdcnYr') or '').strip()
        if prd:
            m = re.search(r'(\d{4})', prd)
            if m:
                full_y = int(m.group(1))
                return full_y, prd
            m_2d = re.search(r'(\d{2})', prd)
            if m_2d:
                full_y = 2000 + int(m_2d.group(1))
                return full_y, prd

        return 0, ""

    def _filter_and_strict(cand_rows):
        f_rows = []
        for r in cand_rows:
            car_whl_nm = str(r.get('carWhlNm') or r.get('modelNm') or '')
            grd_nm = str(r.get('grdNm') or '')
            grd_dtl_nm = str(r.get('grdDtlNm') or '')
            row_full = f"{car_whl_nm} {grd_nm} {grd_dtl_nm}".lower().replace(" ", "")

            # 1. 등급 코드가 풀린 경우 코드 동등 비교, 안 풀린 경우 2단계 엄격 스펙 필터에 위임
            if grd_cd:
                if str(r.get('grdCd') or '') != grd_cd:
                    continue
                if grd_dtl_cd and str(r.get('grdDtlCd') or '') != grd_dtl_cd:
                    continue


            # 2. 배기량 엄격 일치
            if disp_val and re.search(r'\d\.\d', row_full) and disp_val not in row_full:
                continue

            # 3. 터보 일치 검사 (공통 ModelMatcher 기준: 양쪽 중 한쪽이라도 미지(None)면 통과)
            row_turbo = ModelMatcher.extract_turbo(f"{manufacturer} {car_name} {car_whl_nm} {grd_nm} {grd_dtl_nm}")
            if q_turbo is not None and row_turbo is not None and bool(q_turbo) != bool(row_turbo):
                continue

            # 4. 유종 상호 배제
            if is_q_diesel and not any(k in row_full for k in ['디젤', 'crdi', 'vgt']):
                continue
            if is_q_lpg and not any(k in row_full for k in ['lpi', 'lpg']):
                continue

            f_rows.append(r)

        # 🌟 정식 스펙 동등성 기반 엄격 필터링 (엔카와 100% 동일 단일 기준 적용)
        from services.data_processor import DataProcessor
        # (DataProcessor, ModelMatcher는 상위 스코프에서 이미 임포트됨 - UnboundLocalError 방지)
        target_spec = DataProcessor.build_car_spec(
            text=detail_model,
            car_name=car_name,
            year=year
        )

        import collections
        kcar_gate_counts = collections.Counter()
        s_rows = []
        for r in f_rows:
            # 0. 공유 모듈(ModelMatcher)로 동일 모델 검증
            cand_name = str(r.get('modelNm') or r.get('carWhlNm') or '')
            if car_name and cand_name and not ModelMatcher.is_same_model(car_name, cand_name):
                kcar_gate_counts["GATE_MODEL"] += 1
                continue

            # 1. 등급 코드가 있는 경우 코드 일치 우선 확인 (API 필터 뒤집기 방지)
            is_code_matched = False
            if grd_cd:
                if str(r.get('grdCd') or '') != grd_cd:
                    kcar_gate_counts["GATE_GRADE_CODE"] += 1
                    continue
                if grd_dtl_cd and str(r.get('grdDtlCd') or '') != grd_dtl_cd:
                    kcar_gate_counts["GATE_GRADE_DETAIL_CODE"] += 1
                    continue
                is_code_matched = True

            # 2. 후보 매물 스펙 빌드
            r_yr_full, _ = _extract_kcar_year(r)
            cand_text = f"{r.get('carWhlNm', '')} {r.get('modelNm', '')} {r.get('grdNm', '')} {r.get('grdDtlNm', '')}".strip()
            cand_spec = DataProcessor.build_car_spec(
                text=cand_text,
                car_name=str(r.get('modelNm', '') or car_name),
                year=r_yr_full,
                mfg_date=str(r.get('mfgDt', ''))
            )

            # 3. 정식 스펙 동등성 검사 (코드가 일치했으면 ignore_grade=True로 등급 재파싱 실패 방지, 연식·차체·기본제원만 검사)
            ok, reason = DataProcessor.is_strictly_same_spec(
                target_spec,
                cand_spec,
                check_year=bool(target_yr_2d),
                ignore_grade=is_code_matched,
                return_gate=True
            )
            if not ok:
                kcar_gate_counts[reason] += 1
                continue

            s_rows.append(r)

        print(f"[K-Car 엄격 게이트 로그] 총 {len(f_rows)}대 중 {len(s_rows)}대 엄격 통과 | 탈락 사유: {dict(kcar_gate_counts)}", flush=True)
        return f_rows, s_rows

    filtered_rows, strict_rows = _filter_and_strict(rows)

    post_filter_fallback = False
    strict_has_data = bool(strict_rows)
    target_rows = strict_rows if strict_has_data else []
    post_filter_fallback = not strict_has_data

    strict_car_cds = {str(r.get('carCd', '')).strip() for r in strict_rows}

    # 매물 유효 데이터 추출 (엄격 매물 기준)
    valid_cars = []
    prices = []
    for r in target_rows:
        try:
            prc = int(r.get('prc') or 0)
            if prc <= 0:
                continue
            milg = int(r.get('milg') or 0)
            r_yr_full, _ = _extract_kcar_year(r)
            yr_num = r_yr_full % 100 if r_yr_full > 0 else 0
            full_yr_str = str(r_yr_full) if r_yr_full > 0 else str(r.get('prdcnYr') or '')

            car_cd = r.get('carCd') or ''
            raw_optn = r.get('optnNm') or ''
            valid_cars.append({
                "carCd": car_cd,
                "modelName": r.get('modelNm') or '',
                "carName": r.get('carWhlNm') or r.get('modelNm') or '',
                "price": prc,
                "mileage": milg,
                "year": yr_num,
                "fullYear": full_yr_str,
                "grade": r.get('grdNm') or '',
                "gradeDetail": r.get('grdDtlNm') or '',
                "center": r.get('cntrNm') or '',
                "color": r.get('extrColorNm') or '',
                "accident": r.get('acdtHistCnts') or '무사고',
                "optnNm": raw_optn,
                "isStrict": True,
                "detailUrl": f"https://www.kcar.com/bc/detail/carInfoDtl?i_sCarCd={car_cd}" if car_cd else ""
            })
            prices.append(prc)
        except Exception:
            continue

    # 넓은 목록 추출 (filtered_rows 기반 ±1년 목록, 가격 오름차순, 최대 20대)
    wide_cars = []
    wide_source = filtered_rows if filtered_rows else rows
    for r in wide_source:
        try:
            prc = int(r.get('prc') or 0)
            if prc <= 0:
                continue
            milg = int(r.get('milg') or 0)
            r_yr_full, _ = _extract_kcar_year(r)
            yr_num = r_yr_full % 100 if r_yr_full > 0 else 0
            full_yr_str = str(r_yr_full) if r_yr_full > 0 else str(r.get('prdcnYr') or '')

            car_cd = r.get('carCd') or ''
            raw_optn = r.get('optnNm') or ''
            is_st = str(car_cd).strip() in strict_car_cds
            wide_cars.append({
                "carCd": car_cd,
                "modelName": r.get('modelNm') or '',
                "carName": r.get('carWhlNm') or r.get('modelNm') or '',
                "price": prc,
                "mileage": milg,
                "year": yr_num,
                "fullYear": full_yr_str,
                "grade": r.get('grdNm') or '',
                "gradeDetail": r.get('grdDtlNm') or '',
                "center": r.get('cntrNm') or '',
                "color": r.get('extrColorNm') or '',
                "accident": r.get('acdtHistCnts') or '무사고',
                "optnNm": raw_optn,
                "isStrict": is_st,
                "detailUrl": f"https://www.kcar.com/bc/detail/carInfoDtl?i_sCarCd={car_cd}" if car_cd else ""
            })
        except Exception:
            continue

    wide_cars.sort(key=lambda x: x["price"])

    # 타겟 연식 계산 및 넓은 범위(wide_cars) 기준 연식별 평균가·가격 분포 산출 (엔카와 1:1 통일)
    target_yr = (year % 100 if year > 100 else year) if (year and year > 0) else 0
    year_map: Dict[int, Dict[str, int]] = {}
    for c in wide_cars:
        y = c["year"]
        if y <= 0:
            continue
        if y not in year_map:
            year_map[y] = {"count": 0, "sum": 0}
        year_map[y]["count"] += 1
        year_map[y]["sum"] += c["price"]

    sorted_years = sorted(year_map.keys(), reverse=True)
    year_stats = [
        {
            "year": y,
            "avg": int(year_map[y]["sum"] / year_map[y]["count"]),
            "count": year_map[y]["count"],
            "isTarget": (y == target_yr) if target_yr > 0 else False,
        }
        for y in sorted_years
    ]

    wide_prices = sorted([c["price"] for c in wide_cars if c.get("price", 0) > 0])
    wide_cnt = len(wide_prices)
    price_bins = []
    if wide_cnt >= 3 and wide_prices[-1] > wide_prices[0]:
        w_min, w_max = wide_prices[0], wide_prices[-1]
        span = w_max - w_min
        bin_step = max(50, round((span / 4) / 50) * 50)
        curr = w_min
        for i in range(4):
            is_last = (i == 3)
            next_limit = w_max + 1 if is_last else curr + bin_step
            b_cnt = sum(1 for p in wide_prices if (curr <= p <= w_max if is_last else curr <= p < next_limit))
            ratio = round((b_cnt / wide_cnt) * 100) if wide_cnt > 0 else 0
            label = f"{curr:,}~{w_max:,}만" if is_last else f"{curr:,}~{next_limit:,}만"
            price_bins.append({
                "label": label,
                "min": curr,
                "max": w_max if is_last else next_limit,
                "count": b_cnt,
                "ratio": ratio,
            })
            curr = next_limit
            if curr > w_max:
                break
    elif wide_cnt > 0:
        price_bins.append({
            "label": f"{wide_prices[0]:,}~{wide_prices[-1]:,}만",
            "min": wide_prices[0],
            "max": wide_prices[-1],
            "count": wide_cnt,
            "ratio": 100,
        })

    if not strict_has_data or not prices:
        # 💡 [원칙]: 엄격 매물이 없으면 무효 매물 가격으로 평균/최저가를 슬쩍 메우지 않고 엄격 통계 0대 반환
        return {
            "success": True,
            "count": 0,
            "strictCount": 0,
            "validCount": 0,
            "wideCount": len(wide_cars),
            "strictHasData": False,
            "min": None,
            "max": None,
            "avg": None,
            "avgAdj": None,
            "median": None,
            "wideAvg": None,
            "wideAvgAdj": None,
            "wideMedian": None,
            "accDeduction": 0,
            "adjNote": "",
            "postFilterFallback": True,
            "yearStats": year_stats,
            "priceBins": price_bins,
            "cars": [],
            "wideCars": wide_cars[:20],
            "modelName": rows[0].get('modelNm') or '' if rows else '',
            "searchUrl": search_url,
            "message": "동일 연식·동일 등급 엄격 매물 없음 (해당 없음)"
        }

    prices.sort()
    count = len(prices)
    min_p = prices[0]
    max_p = prices[-1]
    all_strict_avg = int(sum(prices) / count)
    mid_idx = count // 2
    median_p = round((prices[mid_idx - 1] + prices[mid_idx]) / 2) if count % 2 == 0 else prices[mid_idx]

    # 💡 [제이 8번 규칙] 케이카 기준가를 전체 엄격 평균에서 무사고 평균(acdtHistCnts '무사고' 행만)으로 변경.
    # 무사고가 0대면 전체 엄격 평균으로 대체.
    no_acc_cars = [
        c for c in valid_cars 
        if c.get("accident") == "무사고" or str(c.get("accident", "")).strip() in ("무사고", "")
    ]
    no_acc_prices = [c["price"] for c in no_acc_cars]
    if no_acc_prices:
        avg_p = int(sum(no_acc_prices) / len(no_acc_prices))
        print(f"[K-Car 기준가 산출] 무사고 {len(no_acc_prices)}대 평균 기준가 적용: {avg_p}만원 (전체 엄격 {count}대 평균: {all_strict_avg}만원)", flush=True)
    else:
        avg_p = all_strict_avg
        print(f"[K-Car 기준가 산출] 무사고 0대 => 전체 엄격 평균 기준가 대체: {avg_p}만원", flush=True)

    # e) A로직 주행거리 보정 및 옵션 델타 확장 (get_benchmarked_valuation 대칭 공식)
    avg_adj = avg_p
    adj_note = ""

    # 1. 목표 차량 옵션 원가 및 카탈로그 사전 구축
    has_target_opts = bool(target_options)
    target_opt_raw = 0
    target_opt_items = []

    if has_target_opts:
        if isinstance(target_options, str):
            for m in re.finditer(r'([가-힣a-zA-Z0-9\s\-_+]+?)\s*\(([\d,]+)만(?:원)?\)', target_options):
                opt_name = m.group(1).strip()
                if opt_name and opt_name not in ('옵션총액', '순정옵션총액'):
                    if is_color_option(opt_name):
                        print(f"[K-Car 목표 옵션 제외] 유상 컬러='{opt_name}' 제외됨", flush=True)
                        continue
                    p_val = int(m.group(2).replace(',', ''))
                    target_opt_items.append({"name": opt_name, "price": p_val})
            if target_opt_items:
                target_opt_raw = sum(item["price"] for item in target_opt_items)
            else:
                m_tot = re.search(r'\[(?:순정)?옵션총액:?\s*([\d,]+)만(?:원)?\]', target_options)
                target_opt_raw = int(m_tot.group(1).replace(',', '')) if m_tot else 0
        elif isinstance(target_options, (list, tuple)):
            for o in target_options:
                if isinstance(o, dict):
                    n = str(o.get("name") or o.get("standard_name") or "").strip()
                    if is_color_option(n):
                        print(f"[K-Car 목표 옵션 제외] 유상 컬러='{n}' 제외됨", flush=True)
                        continue
                    p = o.get("price") or o.get("standard_price_man") or 0
                    p_val = int(p) // 10000 if int(p) >= 10000 else int(p)
                    if n:
                        target_opt_items.append({"name": n, "price": p_val})
            target_opt_raw = sum(item["price"] for item in target_opt_items)

    # 기본 카탈로그 옵션가 사전 (만원 단위) - 비상 폴백용
    DEFAULT_CATALOG_PRICES = {
        "선루프": 80,
        "와이드선루프": 79,
        "듀얼선루프": 80,
        "파노라마선루프": 115,
        "hud": 120,
        "헤드업디스플레이": 120,
        "드라이브와이즈": 110,
        "스마트센스": 105,
        "현대스마트센스": 105,
        "서라운드뷰": 80,
        "어라운드뷰": 80,
        "모니터링": 70,
        "모니터링팩": 70,
        "스타일": 85,
        "컴포트": 60,
        "컴포트시트": 60,
        "컨비니언스": 100,
        "크렐": 60,
        "jbl": 60,
        "보스": 60,
        "렉시콘": 120,
        "프리미엄사운드": 60,
        "빌트인캠": 65,
        "스마트커넥트": 60,
        "후측방경보": 45,
        "후측방": 45,
    }

    catalog_price_map = dict(DEFAULT_CATALOG_PRICES)
    for item in target_opt_items:
        n_norm = norm_opt_name(item["name"])
        if n_norm and item["price"] > 0:
            catalog_price_map[n_norm] = item["price"]
            if "헤드업" in n_norm or "hud" in n_norm:
                catalog_price_map["hud"] = item["price"]
                catalog_price_map["헤드업디스플레이"] = item["price"]
            if "선루프" in n_norm:
                catalog_price_map["선루프"] = item["price"]
                catalog_price_map["파노라마선루프"] = item["price"]

    # 연식 잔가율 계산 헬퍼 (chaolma_service.calculate_option_depreciation 기준)
    def _get_residual_rate(yr_val: int) -> float:
        if yr_val <= 0:
            return 0.50
        full_yr = 2000 + yr_val if yr_val < 100 else yr_val
        curr_yr = datetime.now().year
        age = max(0, curr_yr - full_yr)
        if age < 1:
            return 0.80
        elif age < 3:
            return 0.50
        elif age < 5:
            return 0.35
        else:
            return 0.20

    # 목표 차량 감가 후 잔존 옵션가
    target_opt_deprec = int(round(target_opt_raw * _get_residual_rate(year))) if has_target_opts else 0

    # 비교군 차량 상세 JATO 옵션 병렬 조회 (ThreadPoolExecutor 5 workers, 메모리 캐시 1시간)
    jato_results: Dict[str, Optional[List[Dict[str, Any]]]] = {}
    if has_target_opts and valid_cars:
        car_cds = [c["carCd"] for c in valid_cars if c.get("carCd")]
        if car_cds:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(car_cds))) as executor:
                future_to_cd = {executor.submit(fetch_kcar_jato_options, cd): cd for cd in car_cds}
                for future in concurrent.futures.as_completed(future_to_cd):
                    cd = future_to_cd[future]
                    try:
                        jato_results[cd] = future.result()
                    except Exception as e:
                        print(f"[K-Car JATO Future 오류] carCd='{cd}': {e}", flush=True)
                        jato_results[cd] = None

    if valid_cars:
        # pt 구간 기준: K-Car 원본 avg_p (단일 기준가)
        if avg_p >= 2000:
            pt_per_10k = 1.3
        elif avg_p >= 1200:
            pt_per_10k = 1.5
        else:
            pt_per_10k = 1.8

        adj_prices = []
        mil_diffs = []
        opt_adjs = []

        calc_cars = no_acc_cars if no_acc_cars else valid_cars
        for c in calc_cars:
            c_mil = c["mileage"]
            c_price = c["price"]

            # (1) 주행거리 보정
            if mileage and mileage > 0:
                mil_delta = ((c_mil - mileage) / 10000.0) * pt_per_10k
                mil_delta = max(-8.0, min(8.0, mil_delta))
                mil_adj_p = round(c_price * (100.0 + mil_delta) / 100.0)
                mil_diffs.append(c_mil - mileage)
            else:
                mil_adj_p = c_price

            # (2) 옵션 델타 보정 (엔카식 반영률 35%/40% 및 ±40만 캡, 상세 API 공인 가격)
            real_opt_adj = 0
            if has_target_opts:
                c_cd = c.get("carCd") or ""
                c_jato = jato_results.get(c_cd)

                if c_jato is not None:
                    # 정상 상세 API 응답 (빈 배열 []이면 옵션 없는 기본 사양으로 0원 정상 처리)
                    comp_opt_raw = 0
                    for opt in c_jato:
                        opt_nm = str(opt.get("optNm") or "").strip()
                        if is_color_option(opt_nm):
                            print(f"[K-Car 비교군 옵션 제외] carCd='{c_cd}', 유상 컬러='{opt_nm}' 제외됨", flush=True)
                            continue
                        opt_prc = opt.get("optPrc") or 0
                        p_val = int(opt_prc) // 10000 if int(opt_prc) >= 10000 else int(opt_prc)
                        comp_opt_raw += p_val
                else:
                    # 상세 API 통신 실패 (None) 시에만 비상 격리 카탈로그 폴백 (부분문자열 포함)
                    comp_opt_raw = fallback_calc_comp_opt_from_optnnm(c.get("optnNm") or "", catalog_price_map)

                comp_rate = _get_residual_rate(c["year"])
                comp_opt_deprec = int(round(comp_opt_raw * comp_rate))

                opt_diff = target_opt_deprec - comp_opt_deprec
                if opt_diff > 0:
                    real_opt_adj = min(40, int(round(opt_diff * 0.35)))
                elif opt_diff < 0:
                    real_opt_adj = max(-40, int(round(opt_diff * 0.40)))
                else:
                    real_opt_adj = 0

            opt_adjs.append(real_opt_adj)
            adj_prices.append(mil_adj_p + real_opt_adj)

        if adj_prices:
            avg_adj = int(round(sum(adj_prices) / len(adj_prices)))

            notes = []
            if mil_diffs:
                mean_mil_diff = int(round(sum(mil_diffs) / len(mil_diffs)))
                sign_str = f"+{mean_mil_diff:,}" if mean_mil_diff >= 0 else f"{mean_mil_diff:,}"
                notes.append(f"{len(adj_prices)}대 보정 (평균 {sign_str}km 차이)")
            elif has_target_opts:
                notes.append(f"{len(adj_prices)}대 보정")

            if has_target_opts and opt_adjs:
                mean_opt_adj = int(round(sum(opt_adjs) / len(opt_adjs)))
                if mean_opt_adj != 0:
                    notes.append(f"옵션 {mean_opt_adj:+}만원 반영")

            adj_note = " · ".join(notes)

    # f) 목표 차량 사고 차감 적용 (무사고 PERFECT 0%, 단순수리 MINOR 3%, 그 외 골격/결격 7%)
    acc_upper = str(accident or "PERFECT").strip().upper()
    if acc_upper in ("PERFECT", "무사고", "CLEAN", ""):
        acc_deduction = 0
    elif acc_upper in ("MINOR", "단순수리", "단순교환"):
        acc_deduction = 3
    else:
        acc_deduction = 7

    if acc_deduction > 0:
        avg_adj = int(round(avg_adj * (100 - acc_deduction) / 100.0))
        acc_str = f"사고 -{acc_deduction}% 적용"
        adj_note = f"{adj_note} · {acc_str}" if adj_note else acc_str

    # 차량 정렬 (가격 오름차순, 최대 20대)
    valid_cars.sort(key=lambda x: x["price"])

    return {
        "success": True,
        "count": len(strict_rows) if strict_has_data else 0,
        "strictCount": len(strict_rows),
        "wideCount": len(wide_cars),
        "strictHasData": strict_has_data,
        "min": min_p if strict_has_data else None,
        "max": max_p if strict_has_data else None,
        "avg": avg_p if strict_has_data else None,
        "avgAdj": avg_adj if strict_has_data else None,
        "median": median_p if strict_has_data else None,
        # 넓은 범위 참고용 필드 (슬쩍 메우지 않고 별도 필드로 보존)
        "wideAvg": avg_p if not strict_has_data else None,
        "wideAvgAdj": avg_adj if not strict_has_data else None,
        "wideMedian": median_p if not strict_has_data else None,
        "accDeduction": acc_deduction,
        "adjNote": adj_note,
        "postFilterFallback": post_filter_fallback,
        "yearStats": year_stats,
        "priceBins": price_bins,
        "cars": valid_cars[:20],
        "wideCars": wide_cars[:20],
        "modelName": rows[0].get('modelNm') or '',
        "searchUrl": search_url,
        "message": "" if strict_has_data else "동일 연식·동일 등급 엄격 매물 없음 (해당 없음)"
    }

