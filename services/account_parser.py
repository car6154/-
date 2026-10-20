# services/account_parser.py
"""
계좌 텍스트 파서 모듈.
- 문자·카톡으로 전달받는 다양한 형태의 계좌 정보(순서·표기 혼합)를 파싱
- 은행명: COM030 금융기관 코드표 및 약칭 매핑을 통해 정식명/코드 변환
- 계좌번호: 숫자+하이픈 10~16자리 패턴 (주민번호, 전화번호, 날짜와 충돌 방지)
- 예금주: 남은 한글 이름 토큰 (2~4자)
- 결과: {bank_name, bank_code, account_no, holder} (추측하지 않고 미확인 시 빈 문자열 반환)
"""

import re
from typing import Dict, Any, Optional, Tuple, List

# 1. COM030 금융기관 코드 및 정식명 테이블
BANK_CODE_MAP = {
    "001": "한국은행",
    "002": "산업은행",
    "003": "기업은행",
    "004": "국민은행",
    "007": "수협은행",
    "008": "수출입은행",
    "011": "NH농협은행",
    "012": "농축협",
    "020": "우리은행",
    "023": "SC제일은행",
    "027": "한국씨티은행",
    "031": "아이엠뱅크(구 대구은행)",
    "032": "부산은행",
    "034": "광주은행",
    "035": "제주은행",
    "037": "전북은행",
    "039": "경남은행",
    "045": "새마을금고",
    "048": "신협",
    "050": "저축은행",
    "052": "모간스탠리은행",
    "054": "HSBC은행",
    "055": "도이치은행",
    "057": "제이피모간체이스은행",
    "058": "미즈호은행",
    "059": "엠유에프지은행",
    "060": "BOA은행",
    "061": "비엔피파리바은행",
    "062": "중국공상은행",
    "063": "중국은행",
    "064": "산림조합중앙회",
    "065": "대화은행",
    "066": "교통은행",
    "067": "중국건설은행",
    "071": "우체국",
    "081": "하나은행",
    "088": "신한은행",
    "089": "케이뱅크",
    "090": "카카오뱅크",
    "092": "토스뱅크",
    "152": "인도네시아느가라은행"
}

# 2. 은행 약칭 및 별칭 -> (코드, 정식명) 매핑 사전
# 긴 단어가 먼저 매칭되도록 정렬하여 사용
BANK_ALIASES = [
    # 카카오 / 토스 / 케이뱅크
    ("카카오뱅크", "090"), ("카카오", "090"), ("카뱅", "090"),
    ("토스뱅크", "092"), ("토스", "092"),
    ("케이뱅크", "089"), ("케이", "089"), ("케뱅", "089"),

    # 국민은행
    ("kb국민은행", "004"), ("국민은행", "004"), ("kb국민", "004"), ("kb은행", "004"), ("국민", "004"), ("kb", "004"),

    # 신한은행
    ("신한은행", "088"), ("신한", "088"),

    # 우리은행
    ("우리은행", "020"), ("우리", "020"),

    # 하나은행
    ("keb하나은행", "081"), ("keb하나", "081"), ("하나은행", "081"), ("하나", "081"),

    # 농협
    ("nh농협은행", "011"), ("nh농협", "011"), ("농협은행", "011"), ("농협", "011"), ("nh", "011"),
    ("단위농협", "012"), ("농축협", "012"), ("축협", "012"),

    # 기업은행
    ("ibk기업은행", "003"), ("기업은행", "003"), ("ibk기업", "003"), ("기업", "003"), ("ibk", "003"),

    # 우체국
    ("우체국은행", "071"), ("우체국", "071"),

    # 새마을 / 신협 / 저축은행
    ("새마을금고", "045"), ("새마을", "045"),
    ("신용협동조합", "048"), ("신협", "048"),
    ("sbi저축은행", "050"), ("ok저축은행", "050"), ("웰컴저축은행", "050"), ("저축은행", "050"), ("저축", "050"),

    # SC제일 / 씨티
    ("sc제일은행", "023"), ("sc제일", "023"), ("제일은행", "023"),
    ("한국씨티은행", "027"), ("씨티은행", "027"), ("한국씨티", "027"), ("씨티", "027"),

    # 지방은행
    ("아이엠뱅크", "031"), ("대구은행", "031"), ("대구", "031"), ("아이엠", "031"), ("im뱅크", "031"),
    ("부산은행", "032"), ("부산", "032"),
    ("경남은행", "039"), ("경남", "039"),
    ("광주은행", "034"), ("광주", "034"),
    ("전북은행", "037"), ("전북", "037"),
    ("제주은행", "035"), ("제주", "035"),

    # 기타 특수은행
    ("수협은행", "007"), ("수협", "007"),
    ("산업은행", "002"), ("산은", "002"),
    ("산림조합중앙회", "064"), ("산림조합", "064"),
    ("수출입은행", "008"), ("수출입", "008"),
    ("한국은행", "001")
]

# 불용어(Stopwords) 패턴 (예금주 추출 시 제외)
STOPWORDS = {
    "예금주", "받는분", "수취인", "입금", "송금", "계좌", "은행", "계좌번호", "성명", "이름", "차량대금",
    "알선수수료", "수수료", "보내주세요", "확인", "부탁드립니다", "입금요청", "원", "잔금", "계약금",
    "연락주세요", "연락주시고", "보내드립니다", "입금완료", "안녕하세요", "감사합니다", "내일", "오늘", "입금계좌"
}

# 한국어 명사 뒤에 붙는 조사/호칭 접미사
POSTPOSITIONS = ("으로", "에게", "명의", "통장", "귀하", "앞", "님", "씨", "은", "는", "이", "가", "로")


def parse_account_text(raw_text: str) -> Dict[str, str]:
    """
    문자/메신저 계좌 텍스트에서 은행명, 은행코드, 계좌번호, 예금주를 분리 추출합니다.

    Returns:
        {
            "bank_name": str,   # 예: '국민은행'
            "bank_code": str,   # 예: '004'
            "account_no": str,  # 예: '123456-78-901234' 또는 '123456789012'
            "holder": str       # 예: '홍길동'
        }
    """
    result = {
        "bank_name": "",
        "bank_code": "",
        "account_no": "",
        "holder": ""
    }

    if not raw_text or not raw_text.strip():
        return result

    text = raw_text.strip()

    # 1. 은행명 추출
    found_bank_code = ""
    found_bank_name = ""
    bank_span = None

    # 대소문자 무시 검색 (영문 약칭 KB, IBK, NH 등 지원)
    lower_text = text.lower()
    for alias, code in BANK_ALIASES:
        pattern = r'(?<![가-힣a-zA-Z0-9])' + re.escape(alias) + r'(?![가-힣a-zA-Z0-9])'
        match = re.search(pattern, lower_text)
        if match:
            found_bank_code = code
            found_bank_name = BANK_CODE_MAP.get(code, alias)
            bank_span = match.span()
            break

    if not found_bank_code:
        # 단어 경계 없이 포함 검색 (예: '홍길동국민은행123...')
        for alias, code in BANK_ALIASES:
            # 2글자 이상인 경우만 포함 검색 허용 (KB 등 2글자 이하의 오매칭 방지)
            if len(alias) >= 2 and alias in lower_text:
                found_bank_code = code
                found_bank_name = BANK_CODE_MAP.get(code, alias)
                idx = lower_text.find(alias)
                bank_span = (idx, idx + len(alias))
                break

    if found_bank_code:
        result["bank_code"] = found_bank_code
        result["bank_name"] = found_bank_name

    # 2. 계좌번호 추출
    # 하이픈 포함/미포함 숫자열 후보 검색
    # 주민번호(6자리-[1-8]6자리), 전화번호(010, 02, 031 등) 회피
    account_candidate = ""
    account_span = None

    # 전화번호 패턴: 01[016789]-?\d{3,4}-?\d{4}, 0[2-6][0-9]?-?\d{3,4}-?\d{4}
    phone_spans = [m.span() for m in re.finditer(r'(?:01[016789]|02|0[3-6][1-5])-?\d{3,4}-?\d{4}', text)]
    # 주민번호 패턴: \d{6}-[1-8]\d{6}
    jumin_spans = [m.span() for m in re.finditer(r'\d{6}\s*-\s*[1-8]\d{6}', text)]
    # 날짜 패턴: 20\d{2}[-./]\d{1,2}[-./]\d{1,2}
    date_spans = [m.span() for m in re.finditer(r'20\d{2}[-./]\d{1,2}[-./]\d{1,2}', text)]

    excluded_spans = phone_spans + jumin_spans + date_spans

    def is_overlap(span, exclusions):
        for ex in exclusions:
            if not (span[1] <= ex[0] or span[0] >= ex[1]):
                return True
        return False

    # (A) 하이픈이 포함된 계좌번호 패턴: 10~16자리 디짓, 하이픈 1개 이상
    # 예: 123-456-789012, 123456-78-901234
    for m in re.finditer(r'\b(?:\d+[-–—])+\d+\b', text):
        cand = m.group(0).replace('–', '-').replace('—', '-')
        digits_only = re.sub(r'\D', '', cand)
        if 10 <= len(digits_only) <= 16:
            if not is_overlap(m.span(), excluded_spans):
                account_candidate = cand
                account_span = m.span()
                break

    # (B) 하이픈 없는 순수 10~16자리 숫자열
    if not account_candidate:
        for m in re.finditer(r'\b\d{10,16}\b', text):
            cand = m.group(0)
            if not is_overlap(m.span(), excluded_spans):
                account_candidate = cand
                account_span = m.span()
                break

    if account_candidate:
        result["account_no"] = account_candidate

    # 3. 예금주 추출
    # 최소한 은행명 또는 계좌번호 중 하나는 검출된 계좌 문맥일 때만 예금주를 탐색 (추측 방지)
    if not result["bank_code"] and not result["account_no"]:
        return result

    # 원문에서 은행명 영역과 계좌번호 영역, 전화번호/주민번호 등을 공백으로 치환
    clean_chars = list(text)
    spans_to_mask = []
    if bank_span:
        spans_to_mask.append(bank_span)
    if account_span:
        spans_to_mask.append(account_span)
    spans_to_mask.extend(excluded_spans)

    for sp in spans_to_mask:
        for i in range(max(0, sp[0]), min(len(clean_chars), sp[1])):
            clean_chars[i] = ' '

    masked_text = "".join(clean_chars)

    # 특수문자 제거 후 단어 단위로 분리
    tokens = re.findall(r'[가-힣a-zA-Z]+', masked_text)

    # 불용어 제외 및 한글 2~4자 이름 후보 필터링
    holder_candidate = ""
    for tok in tokens:
        tok_clean = tok.strip()
        if tok_clean in STOPWORDS:
            continue

        # "(예금주:홍길동)" 처럼 붙어있던 불용어 접두사 제거
        for sw in STOPWORDS:
            if tok_clean.startswith(sw):
                tok_clean = tok_clean[len(sw):]
            if tok_clean.endswith(sw):
                tok_clean = tok_clean[:-len(sw)]

        # 조사/호칭 접미사 제거 (예: "강감찬으로" -> "강감찬", "홍길동님" -> "홍길동")
        for post in POSTPOSITIONS:
            if tok_clean.endswith(post) and len(tok_clean) > len(post) + 1:
                tok_clean = tok_clean[:-len(post)]
                break

        if not tok_clean:
            continue

        # 2~4글자 순수 한글 (한국인 성명 기준)
        if re.fullmatch(r'[가-힣]{2,4}', tok_clean) and tok_clean not in STOPWORDS:
            holder_candidate = tok_clean
            break

    if holder_candidate:
        result["holder"] = holder_candidate

    return result
