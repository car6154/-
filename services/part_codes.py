"""
services/part_codes.py - 자동차 사고/손상 부위 표준 코드 및 한글 매핑 단일 진실 공급원 (Single Source of Truth)
- 엔카, 국토부 성능점검(P-Code), 오토플러스, 헤이딜러, 케이카 3Dview의 모든 부위명을 단일 표준 코드로 일원화
- 2D 사고도면 슬롯 및 호가 감가(외판/골격 구분) 기준 통합
"""

from typing import Optional, Set, Dict

# ----------------------------------------------------
# 1. 표준 외판 부위 코드 집합 (14개)
# ----------------------------------------------------
OUTER_PART_CODES: Set[str] = {
    'RADIATOR_SUPPORT', 'HOOD', 'F_FENDER_L', 'F_FENDER_R',
    'SIDE_SILL_L', 'FRONT_DOOR_L', 'FRONT_DOOR_R', 'SIDE_SILL_R',
    'REAR_DOOR_L', 'REAR_DOOR_R', 'QUARTER_L', 'QUARTER_R',
    'ROOF', 'TRUNK'
}

# ----------------------------------------------------
# 2. 표준 주요골격 부위 코드 집합 (20개)
# ----------------------------------------------------
INNER_PART_CODES: Set[str] = {
    'FRONT_PANEL', 'SIDE_MEMBER_FRONT_L', 'SIDE_MEMBER_FRONT_R',
    'FRONT_WHEEL_HOUSE_L', 'FRONT_WHEEL_HOUSE_R', 'CROSS_MEMBER',
    'INSIDE_PANEL_L', 'INSIDE_PANEL_R', 'DASH_PANEL',
    'A_PILLAR_L', 'A_PILLAR_R', 'B_PILLAR_L', 'B_PILLAR_R',
    'C_PILLAR_L', 'C_PILLAR_R', 'FLOOR_PANEL',
    'SIDE_MEMBER_REAR_L', 'SIDE_MEMBER_REAR_R', 'TRUNK_FLOOR', 'REAR_PANEL'
}

# ----------------------------------------------------
# 3. 표준 부위 한국어 명칭 사전
# ----------------------------------------------------
PART_NAMES_KR: Dict[str, str] = {
    # 외판
    'RADIATOR_SUPPORT': '라디에이터 서포트',
    'HOOD': '후드(보닛)',
    'F_FENDER_L': '프론트 휀더(좌)',
    'F_FENDER_R': '프론트 휀더(우)',
    'SIDE_SILL_L': '사이드실 패널(좌)',
    'SIDE_SILL_R': '사이드실 패널(우)',
    'FRONT_DOOR_L': '프론트 도어(좌)',
    'FRONT_DOOR_R': '프론트 도어(우)',
    'REAR_DOOR_L': '리어 도어(좌)',
    'REAR_DOOR_R': '리어 도어(우)',
    'QUARTER_L': '쿼터 패널(좌)',
    'QUARTER_R': '쿼터 패널(우)',
    'ROOF': '루프 패널',
    'TRUNK': '트렁크리드',
    # 골격
    'FRONT_PANEL': '프론트 패널',
    'SIDE_MEMBER_FRONT_L': '프론트 사이드멤버(좌)',
    'SIDE_MEMBER_FRONT_R': '프론트 사이드멤버(우)',
    'FRONT_WHEEL_HOUSE_L': '프론트 휠하우스(좌)',
    'FRONT_WHEEL_HOUSE_R': '프론트 휠하우스(우)',
    'CROSS_MEMBER': '크로스멤버',
    'INSIDE_PANEL_L': '인사이드 패널(좌)',
    'INSIDE_PANEL_R': '인사이드 패널(우)',
    'DASH_PANEL': '대쉬 패널',
    'A_PILLAR_L': 'A필러(좌)',
    'A_PILLAR_R': 'A필러(우)',
    'B_PILLAR_L': 'B필러(좌)',
    'B_PILLAR_R': 'B필러(우)',
    'C_PILLAR_L': 'C필러(좌)',
    'C_PILLAR_R': 'C필러(우)',
    'FLOOR_PANEL': '플로어 패널',
    'SIDE_MEMBER_REAR_L': '리어 사이드멤버(좌)',
    'SIDE_MEMBER_REAR_R': '리어 사이드멤버(우)',
    'TRUNK_FLOOR': '트렁크 플로어',
    'REAR_PANEL': '리어 패널',
}

# ----------------------------------------------------
# 4. 전체 부위 명칭 / 영문 / P-Code ➔ 표준 코드 매핑 사전
# ----------------------------------------------------
PART_CODE_MAP: Dict[str, str] = {
    # 1) 한글 명칭
    '후드': 'HOOD', '본넷': 'HOOD', '보닛': 'HOOD',
    '앞휀더(좌)': 'F_FENDER_L', '프론트 휀더(좌)': 'F_FENDER_L', '프론트휀더(좌)': 'F_FENDER_L', '앞휀다(좌)': 'F_FENDER_L',
    '앞휀더(우)': 'F_FENDER_R', '프론트 휀더(우)': 'F_FENDER_R', '프론트휀더(우)': 'F_FENDER_R', '앞휀다(우)': 'F_FENDER_R',
    '앞도어(좌)': 'FRONT_DOOR_L', '프론트 도어(좌)': 'FRONT_DOOR_L', '프론트도어(좌)': 'FRONT_DOOR_L', '앞문(좌)': 'FRONT_DOOR_L',
    '앞도어(우)': 'FRONT_DOOR_R', '프론트 도어(우)': 'FRONT_DOOR_R', '프론트도어(우)': 'FRONT_DOOR_R', '앞문(우)': 'FRONT_DOOR_R',
    '뒤도어(좌)': 'REAR_DOOR_L', '리어 도어(좌)': 'REAR_DOOR_L', '리어도어(좌)': 'REAR_DOOR_L', '뒷문(좌)': 'REAR_DOOR_L', '뒤문(좌)': 'REAR_DOOR_L',
    '뒤도어(우)': 'REAR_DOOR_R', '리어 도어(우)': 'REAR_DOOR_R', '리어도어(우)': 'REAR_DOOR_R', '뒷문(우)': 'REAR_DOOR_R', '뒤문(우)': 'REAR_DOOR_R',
    '트렁크': 'TRUNK', '트렁크 리드': 'TRUNK', '트렁크리드': 'TRUNK',
    '쿼터(우)': 'QUARTER_R', '쿼터패널(우)': 'QUARTER_R', '쿼터 패널(우)': 'QUARTER_R', '뒤휀더(우)': 'QUARTER_R', '뒤휀다(우)': 'QUARTER_R',
    '쿼터(좌)': 'QUARTER_L', '쿼터패널(좌)': 'QUARTER_L', '쿼터 패널(좌)': 'QUARTER_L', '뒤휀더(좌)': 'QUARTER_L', '뒤휀다(좌)': 'QUARTER_L',
    '루프': 'ROOF', '루프 패널': 'ROOF', '루프패널': 'ROOF',
    '사이드실(좌)': 'SIDE_SILL_L', '사이드실 패널(좌)': 'SIDE_SILL_L', '사이드실(스텝)(좌)': 'SIDE_SILL_L', '사이드스텝(좌)': 'SIDE_SILL_L',
    '사이드실(우)': 'SIDE_SILL_R', '사이드실 패널(우)': 'SIDE_SILL_R', '사이드실(스텝)(우)': 'SIDE_SILL_R', '사이드스텝(우)': 'SIDE_SILL_R',
    '라디에이터': 'RADIATOR_SUPPORT', '라디에이터 서포트': 'RADIATOR_SUPPORT', '라디에이터서포트': 'RADIATOR_SUPPORT',
    '인사이드(좌)': 'INSIDE_PANEL_L', '인사이드 패널(좌)': 'INSIDE_PANEL_L', '인사이드패널(좌)': 'INSIDE_PANEL_L',
    '인사이드(우)': 'INSIDE_PANEL_R', '인사이드 패널(우)': 'INSIDE_PANEL_R', '인사이드패널(우)': 'INSIDE_PANEL_R',
    '크로스': 'CROSS_MEMBER', '크로스멤버': 'CROSS_MEMBER',
    '프론트 패널': 'FRONT_PANEL', '프론트패널': 'FRONT_PANEL', '앞패널': 'FRONT_PANEL',
    '사이드 멤버(좌)': 'SIDE_MEMBER_FRONT_L', '프론트 사이드 멤버(좌)': 'SIDE_MEMBER_FRONT_L', '프론트사이드멤버(좌)': 'SIDE_MEMBER_FRONT_L', '앞사이드멤버(좌)': 'SIDE_MEMBER_FRONT_L',
    '사이드 멤버(우)': 'SIDE_MEMBER_FRONT_R', '프론트 사이드 멤버(우)': 'SIDE_MEMBER_FRONT_R', '프론트사이드멤버(우)': 'SIDE_MEMBER_FRONT_R', '앞사이드멤버(우)': 'SIDE_MEMBER_FRONT_R',
    '리어사이드멤버(좌)': 'SIDE_MEMBER_REAR_L', '리어 사이드 멤버(좌)': 'SIDE_MEMBER_REAR_L', '뒤사이드멤버(좌)': 'SIDE_MEMBER_REAR_L',
    '리어사이드멤버(우)': 'SIDE_MEMBER_REAR_R', '리어 사이드 멤버(우)': 'SIDE_MEMBER_REAR_R', '뒤사이드멤버(우)': 'SIDE_MEMBER_REAR_R',
    '휠하우스(좌)': 'FRONT_WHEEL_HOUSE_L', '휠 하우스(좌)': 'FRONT_WHEEL_HOUSE_L', '프론트휠하우스(좌)': 'FRONT_WHEEL_HOUSE_L',
    '휠하우스(우)': 'FRONT_WHEEL_HOUSE_R', '휠 하우스(우)': 'FRONT_WHEEL_HOUSE_R', '프론트휠하우스(우)': 'FRONT_WHEEL_HOUSE_R',
    '대쉬패널': 'DASH_PANEL', '대시패널': 'DASH_PANEL', '대쉬 패널': 'DASH_PANEL', '대시 패널': 'DASH_PANEL',
    '플로어패널': 'FLOOR_PANEL', '플로어 패널': 'FLOOR_PANEL',
    '리어 패널': 'REAR_PANEL', '리어패널': 'REAR_PANEL', '뒤패널': 'REAR_PANEL',
    '트렁크 플로어': 'TRUNK_FLOOR', '트렁크플로어': 'TRUNK_FLOOR', '트렁크바닥': 'TRUNK_FLOOR',
    '필러(A)(좌)': 'A_PILLAR_L', 'A필러(좌)': 'A_PILLAR_L', 'A-필러(좌)': 'A_PILLAR_L',
    '필러(A)(우)': 'A_PILLAR_R', 'A필러(우)': 'A_PILLAR_R', 'A-필러(우)': 'A_PILLAR_R',
    '필러(B)(좌)': 'B_PILLAR_L', 'B필러(좌)': 'B_PILLAR_L', 'B-필러(좌)': 'B_PILLAR_L',
    '필러(B)(우)': 'B_PILLAR_R', 'B필러(우)': 'B_PILLAR_R', 'B-필러(우)': 'B_PILLAR_R',
    '필러(C)(좌)': 'C_PILLAR_L', 'C필러(좌)': 'C_PILLAR_L', 'C-필러(좌)': 'C_PILLAR_L',
    '필러(C)(우)': 'C_PILLAR_R', 'C필러(우)': 'C_PILLAR_R', 'C-필러(우)': 'C_PILLAR_R',

    # 2) 영문 코드 및 별칭 (호환성 보장)
    'HOOD': 'HOOD', 'BONNET': 'HOOD',
    'FRONT_FENDER_LEFT': 'F_FENDER_L', 'FRONT_FENDER_L': 'F_FENDER_L', 'FENDER_FL': 'F_FENDER_L', 'F_FENDER_L': 'F_FENDER_L',
    'FRONT_FENDER_RIGHT': 'F_FENDER_R', 'FRONT_FENDER_R': 'F_FENDER_R', 'FENDER_FR': 'F_FENDER_R', 'F_FENDER_R': 'F_FENDER_R',
    'FRONT_DOOR_LEFT': 'FRONT_DOOR_L', 'FRONT_DOOR_L': 'FRONT_DOOR_L', 'DOOR_FL': 'FRONT_DOOR_L',
    'FRONT_DOOR_RIGHT': 'FRONT_DOOR_R', 'FRONT_DOOR_R': 'FRONT_DOOR_R', 'DOOR_FR': 'FRONT_DOOR_R',
    'REAR_DOOR_LEFT': 'REAR_DOOR_L', 'REAR_DOOR_L': 'REAR_DOOR_L', 'DOOR_RL': 'REAR_DOOR_L', 'BACK_DOOR_LEFT': 'REAR_DOOR_L',
    'REAR_DOOR_RIGHT': 'REAR_DOOR_R', 'REAR_DOOR_R': 'REAR_DOOR_R', 'DOOR_RR': 'REAR_DOOR_R', 'BACK_DOOR_RIGHT': 'REAR_DOOR_R',
    'TRUNK': 'TRUNK', 'TRUNK_LID': 'TRUNK',
    'TRUNK_FLOOR': 'TRUNK_FLOOR',
    'REAR_PANEL': 'REAR_PANEL',
    'QUARTER_LEFT': 'QUARTER_L', 'QUARTER_L': 'QUARTER_L',
    'QUARTER_RIGHT': 'QUARTER_R', 'QUARTER_R': 'QUARTER_R',
    'ROOF': 'ROOF',
    'RADIATOR': 'RADIATOR_SUPPORT', 'RADIATOR_SUPPORT': 'RADIATOR_SUPPORT',
    'FRONT_PANEL': 'FRONT_PANEL',
    'FRONT_SIDE_MEMBER_L': 'SIDE_MEMBER_FRONT_L', 'SIDE_MEMBER_FRONT_L': 'SIDE_MEMBER_FRONT_L',
    'FRONT_SIDE_MEMBER_R': 'SIDE_MEMBER_FRONT_R', 'SIDE_MEMBER_FRONT_R': 'SIDE_MEMBER_FRONT_R',
    'SIDE_MEMBER_REAR_L': 'SIDE_MEMBER_REAR_L', 'REAR_SIDE_MEMBER_L': 'SIDE_MEMBER_REAR_L',
    'SIDE_MEMBER_REAR_R': 'SIDE_MEMBER_REAR_R', 'REAR_SIDE_MEMBER_R': 'SIDE_MEMBER_REAR_R',
    'FRONT_WHEEL_HOUSE_L': 'FRONT_WHEEL_HOUSE_L', 'WHEEL_HOUSE_L': 'FRONT_WHEEL_HOUSE_L',
    'FRONT_WHEEL_HOUSE_R': 'FRONT_WHEEL_HOUSE_R', 'WHEEL_HOUSE_R': 'FRONT_WHEEL_HOUSE_R',
    'CROSS_MEMBER': 'CROSS_MEMBER',
    'INSIDE_PANEL_L': 'INSIDE_PANEL_L', 'INSIDE_PANEL_R': 'INSIDE_PANEL_R',
    'DASH_PANEL': 'DASH_PANEL',
    'FLOOR_PANEL': 'FLOOR_PANEL',
    'PILLAR_A_L': 'A_PILLAR_L', 'A_PILLAR_L': 'A_PILLAR_L',
    'PILLAR_A_R': 'A_PILLAR_R', 'A_PILLAR_R': 'A_PILLAR_R',
    'PILLAR_B_L': 'B_PILLAR_L', 'B_PILLAR_L': 'B_PILLAR_L',
    'PILLAR_B_R': 'B_PILLAR_R', 'B_PILLAR_R': 'B_PILLAR_R',
    'PILLAR_C_L': 'C_PILLAR_L', 'C_PILLAR_L': 'C_PILLAR_L',
    'PILLAR_C_R': 'C_PILLAR_R', 'C_PILLAR_R': 'C_PILLAR_R',
    'SIDE_SILL_L': 'SIDE_SILL_L', 'SIDE_SILL_R': 'SIDE_SILL_R',

    # 3) 엔카 국토부 표준 부위 코드 (P-Code)
    'P010': 'HOOD', 'P021': 'F_FENDER_L', 'P022': 'F_FENDER_R',
    'P031': 'FRONT_DOOR_L', 'P032': 'FRONT_DOOR_R',
    'P033': 'REAR_DOOR_L', 'P034': 'REAR_DOOR_R',
    'P040': 'TRUNK', 'P041': 'TRUNK',
    'P061': 'QUARTER_L', 'P062': 'QUARTER_R',
    'P070': 'ROOF', 'P081': 'SIDE_SILL_L', 'P082': 'SIDE_SILL_R',
    'P101': 'SIDE_MEMBER_FRONT_L', 'P102': 'SIDE_MEMBER_FRONT_R',
    'P111': 'FRONT_WHEEL_HOUSE_L', 'P112': 'FRONT_WHEEL_HOUSE_R',
    'P120': 'CROSS_MEMBER', 'P131': 'INSIDE_PANEL_L', 'P132': 'INSIDE_PANEL_R',
    'P141': 'SIDE_MEMBER_REAR_L', 'P142': 'SIDE_MEMBER_REAR_R',
    'P150': 'TRUNK_FLOOR', 'P160': 'REAR_PANEL', 'P181': 'REAR_PANEL',
}


def resolve_part_code(title: str) -> Optional[str]:
    """
    원시 부위 문자열(한글 명칭, 영문 식별자, 국토부 P-코드 등)을 단일 표준 부위 코드로 변환
    - 긴 키워드 우선 탐색으로 부분일치 가로채기 방지 (예: '트렁크 플로어' > '트렁크')
    """
    if not title:
        return None
    raw = str(title).strip()
    if not raw:
        return None

    raw_upper = raw.upper()
    if raw_upper in PART_CODE_MAP:
        return PART_CODE_MAP[raw_upper]

    # 공백 제거 대조
    raw_nospace = raw.replace(" ", "")
    if raw_nospace in PART_CODE_MAP:
        return PART_CODE_MAP[raw_nospace]
    raw_nospace_upper = raw_upper.replace(" ", "")
    if raw_nospace_upper in PART_CODE_MAP:
        return PART_CODE_MAP[raw_nospace_upper]

    # 긴 키워드(더 구체적인 명칭) 우선 순회
    for k in sorted(PART_CODE_MAP.keys(), key=len, reverse=True):
        if k in raw or k.upper() in raw_upper:
            return PART_CODE_MAP[k]

    return None


def is_outer_part(code: str) -> bool:
    """외판 부위 여부 확인"""
    return code in OUTER_PART_CODES


def is_inner_part(code: str) -> bool:
    """주요 골격 부위 여부 확인"""
    return code in INNER_PART_CODES


def get_part_korean_name(code: str) -> str:
    """표준 부위 코드 또는 원시 명칭을 표준 한국어 명칭으로 반환"""
    resolved = resolve_part_code(code)
    if resolved and resolved in PART_NAMES_KR:
        return PART_NAMES_KR[resolved]
    return code
