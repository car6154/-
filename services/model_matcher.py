"""
services/model_matcher.py - 모델 매칭 판정 및 스펙 정규화 전용 공유 모듈 (단일 진실 공급원)

역할:
1. 엔카 검색 엄격 필터, 케이카 엄격 필터, 팔린매물 가드의 모델명 일치 판정을 1곳으로 단일화.
2. 브랜드/세대 접두사, 연료/파워트레인 동의어(하이브리드/HEV 등), 구동방식, 터보 추출 규칙을 단일 관리.
"""

import re
from typing import Optional

# 1. 브랜드 접두사 (수입/국산 통합)
BRAND_PREFIXES = [
    '르노코리아(삼성_)', '르노코리아(삼성)', '르노삼성', '르노코리아', '르노', 'renault',
    '쉐보레(gm대우_)', '쉐보레(gm대우)', '쉐보레', 'gm대우', 'chevrolet',
    'kg모빌리티(쌍용_)', 'kg모빌리티(쌍용)', 'kg모빌리티', 'kgm', '쌍용', 'ssangyong',
    '메르세데스-벤츠', '메르세데스벤츠', '벤츠', 'mercedes-benz', 'mercedes', 'benz',
    '현대', 'hyundai', '기아', 'kia', '제네시스', 'genesis', 'bmw', '아우디', 'audi',
    '폭스바겐', 'volkswagen', 'vw', '볼보', 'volvo', '포르쉐', 'porsche',
    '렉서스', 'lexus', '토요타', '도요타', 'toyota', '혼다', 'honda', '포드', 'ford', '지프', 'jeep'
]

# 2. 세대 수식어 접두사
GENERATION_PREFIXES = [
    '디올뉴', 'theallnew', '더올뉴', '올뉴', 'allnew', '더뉴', 'thenew', '신형', '뉴', 'new'
]

# 3. 연료/파워트레인 동의어 표 (data_processor.build_car_spec 기반 단일화)
FUEL_SYNONYM_MAP = {
    '플러그인하이브리드': ['플러그인하이브리드', '플러그인', 'phev'],
    '하이브리드': ['하이브리드', 'hev', '가솔린+전기', '디젤+전기', 'lpg+전기', '가솔린전기', '디젤전기', 'lpg전기'],
    'lpg': ['lpg', 'lpi', 'lpe'],
    '수소': ['수소', 'fcev'],
    '디젤': ['디젤', '경유', 'crdi', 'vgt', 'dci', 'cdi', 'tdi', 'e-vgt', 'evgt'],
    '가솔린': ['가솔린', '휘발유', 'gdi', 't-gdi', 'tgdi', 'gde', 'mpi', 'cvvl'],
    '전기': ['전기', 'ev']
}

# 4. 구동방식 동의어 표
DRIVE_SYNONYM_MAP = {
    '4wd': ['4wd', 'awd', '4륜', '사륜', '4matic', '4매틱', 'quattro', '콰트로', 'xdrive'],
    '2wd': ['2wd', '2륜', '이륜', 'ff', 'fr']
}


class ModelMatcher:
    """모델 매칭 판정 및 문자열 정규화 단일 진실 공급원"""

    @classmethod
    def clean_text(cls, text: str) -> str:
        """한글, 영문, 숫자만 남기고 소문자화 (공백 및 특수문자 제거)"""
        if not text:
            return ""
        return re.sub(r'[^가-힣a-zA-Z0-9]', '', str(text)).lower()

    @classmethod
    def extract_fuel(cls, text: str) -> str:
        """
        텍스트에서 표준 연료 명칭 추출.
        반환값: '플러그인하이브리드', '하이브리드', 'lpg', '수소', '디젤', '가솔린', '전기', 또는 빈 문자열
        """
        raw = str(text) if text else ""
        c = cls.clean_text(raw)
        if not c:
            return ""

        # 1. 플러그인하이브리드
        for syn in FUEL_SYNONYM_MAP['플러그인하이브리드']:
            if cls.clean_text(syn) in c:
                return '플러그인하이브리드'

        # 2. LPG
        for syn in FUEL_SYNONYM_MAP['lpg']:
            if cls.clean_text(syn) in c:
                return 'lpg'

        # 3. 하이브리드 (HEV 포함)
        for syn in FUEL_SYNONYM_MAP['하이브리드']:
            if cls.clean_text(syn) in c:
                return '하이브리드'

        # 4. 수소
        for syn in FUEL_SYNONYM_MAP['수소']:
            if cls.clean_text(syn) in c:
                return '수소'

        # 5. 디젤
        for syn in FUEL_SYNONYM_MAP['디젤']:
            if cls.clean_text(syn) in c:
                return '디젤'
        if re.search(r'r[12]\.[02]', raw.lower()):
            return '디젤'

        # 6. 가솔린
        for syn in FUEL_SYNONYM_MAP['가솔린']:
            if cls.clean_text(syn) in c:
                return '가솔린'

        # 7. 전기 (단, EV3, EV6, EV9 등 모델명 제외)
        if ('ev' in raw.lower() or '전기' in c) and not re.search(r'ev[1-9]', c):
            return '전기'

        return ""

    @classmethod
    def extract_drive(cls, text: str) -> str:
        """텍스트에서 구동방식 추출 ('2wd', '4wd', 또는 빈 문자열)"""
        c = cls.clean_text(text)
        if not c:
            return ""
        for syn in DRIVE_SYNONYM_MAP['4wd']:
            if cls.clean_text(syn) in c:
                return '4wd'
        for syn in DRIVE_SYNONYM_MAP['2wd']:
            if cls.clean_text(syn) in c:
                return '2wd'
        return ""

    @classmethod
    def extract_disp(cls, text: str) -> str:
        """텍스트에서 배기량 추출 (예: '1.6', '2.0', '2.5', '3.5' 등)"""
        raw = str(text) if text else ""
        m_disp = re.search(r'(?:[a-zA-Z가-힣]|\b)(\d\.\d)', raw)
        if m_disp:
            return m_disp.group(1)
        m_cc = re.search(r'(\d{3,4})\s*cc', raw, re.IGNORECASE)
        if m_cc:
            try:
                return f"{int(m_cc.group(1)) / 1000.0:.1f}"
            except Exception:
                pass
        return ""

    @classmethod
    def extract_turbo(cls, text: str, disp: str = None, fuel: str = None) -> bool:
        """터보 여부 판정 (현대/기아 1.6T HEV 자동 판정 포함)"""
        raw = str(text) if text else ""
        c = cls.clean_text(raw)
        has_turbo_kw = any(k in c for k in ['터보', 'turbo', 'tgdi']) or bool(re.search(r'\b\d\.\d+t\b', raw.lower()))

        cur_disp = disp or cls.extract_disp(raw)
        cur_fuel = fuel or cls.extract_fuel(raw)

        is_hk = any(m in c for m in ['현대', '기아', '제네시스', 'hyundai', 'kia', '싼타페', '쏘렌토', '그랜저', 'k8', '투싼', '스포티지', '카니발', '팰리세이드'])
        is_na_16 = any(m in c for m in ['니로', 'niro', '아반떼', 'avante', '코나', 'kona', '아이오닉', 'ioniq'])

        if is_hk and cur_disp == '1.6' and cur_fuel == '하이브리드' and not is_na_16:
            return True
        return has_turbo_kw

    @classmethod
    def extract_core_model(cls, text: str) -> str:
        """
        차명에서 브랜드, 세대 접두사, 연료 표기, 배기량, 구동방식, 인승 등을 정리하고
        핵심 모델명(예: '싼타페', '쏘렌토', 'gv70', 'k5' 등)을 추출.
        """
        if not text:
            return ""

        t = str(text)
        # 1. 괄호 내용 처리 (코드명 분리)
        t = re.sub(r'\([^)]*\)', ' ', t)
        # 2. 텍스트 분리 상태에서 세대 패턴 제거 (K5 3세대 -> 53세대 오인 방지)
        t = re.sub(r'(?<=\D)\s*\d+세대', ' ', t)
        t = re.sub(r'^\d+세대', ' ', t)
        # 3. 배기량, cc, 인승 사전 분리 제거
        t = re.sub(r'\b\d\.\d\b', ' ', t)
        t = re.sub(r'\b\d{3,4}\s*cc\b', ' ', t, flags=re.IGNORECASE)
        t = re.sub(r'\b\d+인승\b', ' ', t)

        c = cls.clean_text(t)

        # 4. 브랜드 접두사 제거
        for b in sorted(BRAND_PREFIXES, key=len, reverse=True):
            b_c = cls.clean_text(b)
            if c.startswith(b_c):
                c = c[len(b_c):]
                break

        # 5. 세대 수식어 접두사 제거
        for g in sorted(GENERATION_PREFIXES, key=len, reverse=True):
            g_c = cls.clean_text(g)
            if c.startswith(g_c):
                c = c[len(g_c):]
                break

        # 6. 연료/파워트레인 키워드 제거 (EV3, EV6 등 모델명 보호)
        for fuel, syns in FUEL_SYNONYM_MAP.items():
            for syn in sorted(syns, key=len, reverse=True):
                syn_c = cls.clean_text(syn)
                if not syn_c:
                    continue
                if syn_c == 'ev':
                    c = re.sub(r'ev(?![0-9])', '', c)
                else:
                    if syn_c in c:
                        c = c.replace(syn_c, '')

        # 7. 구동방식 제거
        for drive, syns in DRIVE_SYNONYM_MAP.items():
            for syn in sorted(syns, key=len, reverse=True):
                syn_c = cls.clean_text(syn)
                if syn_c and syn_c in c:
                    c = c.replace(syn_c, '')

        # 8. 터보 키워드 제거
        for turbo_kw in ['터보', 'turbo']:
            c = c.replace(turbo_kw, '')

        return c.strip()

    @classmethod
    def is_same_model(cls, expected: str, candidate: str) -> bool:
        """
        두 차명/모델명이 동일 모델인지 판정하는 백엔드 유일 공통 함수 (SSOT).
        
        규칙:
        1. 핵심 모델명(core_model)이 상호 포함되는지 검사 (예: '싼타페' in '싼타페')
        2. 두 차명 모두 유종(fuel)이 식별될 경우, 상호 일치해야 함 (예: 하이브리드 vs 가솔린은 거부)
        """
        if not expected or not candidate:
            return False

        core_exp = cls.extract_core_model(expected)
        core_cand = cls.extract_core_model(candidate)

        if len(core_exp) < 2:
            core_exp = cls.clean_text(expected)
        if len(core_cand) < 2:
            core_cand = cls.clean_text(candidate)

        # 1. 모델명 포함 여부
        model_matched = (core_exp in core_cand) or (core_cand in core_exp)
        if not model_matched:
            return False

        # 2. 유종 상호 배제 검사 (둘 다 명시된 경우만)
        fuel_exp = cls.extract_fuel(expected)
        fuel_cand = cls.extract_fuel(candidate)
        if fuel_exp and fuel_cand:
            if fuel_exp != fuel_cand:
                return False

        return True
