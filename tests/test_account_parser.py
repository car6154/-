# tests/test_account_parser.py
"""
services/account_parser.py 단위 테스트.
실제 문자·카톡 계좌 텍스트 형태 5종 이상에 대해 분리 정확성을 검증합니다.
(실계좌번호 금지, 형식만 같은 더미 사용)
"""
import pytest
from services.account_parser import parse_account_text


def test_standard_format():
    """예시 1: 표준 은행명 + 하이픈 계좌 + 예금주"""
    text = "국민은행 123456-78-901234 홍길동"
    res = parse_account_text(text)
    assert res["bank_name"] == "국민은행"
    assert res["bank_code"] == "004"
    assert res["account_no"] == "123456-78-901234"
    assert res["holder"] == "홍길동"


def test_name_first_and_bank_alias():
    """예시 2: 예금주 먼저 + 은행 약칭 + 하이픈 계좌"""
    text = "홍길동 국민 123-456789-0123"
    res = parse_account_text(text)
    assert res["bank_name"] == "국민은행"
    assert res["bank_code"] == "004"
    assert res["account_no"] == "123-456789-0123"
    assert res["holder"] == "홍길동"


def test_prefix_and_brackets():
    """예시 3: 안내 문구 접두어 + 괄호 표기"""
    text = "입금계좌: 신한 110-123-456789 (예금주: 김철수)"
    res = parse_account_text(text)
    assert res["bank_name"] == "신한은행"
    assert res["bank_code"] == "088"
    assert res["account_no"] == "110-123-456789"
    assert res["holder"] == "김철수"


def test_account_first_and_nonghyup():
    """예시 4: 계좌번호 먼저 + 농협 + 예금주"""
    text = "352-0123-4567-89 농협 이영희"
    res = parse_account_text(text)
    assert res["bank_name"] == "NH농협은행"
    assert res["bank_code"] == "011"
    assert res["account_no"] == "352-0123-4567-89"
    assert res["holder"] == "이영희"


def test_unhyphenated_account_and_amount_noise():
    """예시 5: 하이픈 없는 계좌번호 + 인터넷전문은행 + 금액/인사 노이즈"""
    text = "토스뱅크 100012345678 박민수 50만원 입금부탁드립니다"
    res = parse_account_text(text)
    assert res["bank_name"] == "토스뱅크"
    assert res["bank_code"] == "092"
    assert res["account_no"] == "100012345678"
    assert res["holder"] == "박민수"


def test_phone_number_distinction():
    """예시 6: 연락처(010)와 계좌번호 충돌 구분"""
    text = "010-9876-5432 연락주시고 기업은행 012-345678-9012 강감찬으로 보내주세요"
    res = parse_account_text(text)
    assert res["bank_name"] == "기업은행"
    assert res["bank_code"] == "003"
    assert res["account_no"] == "012-345678-9012"
    assert res["holder"] == "강감찬"


def test_empty_or_no_account_text():
    """예시 7: 빈 값 및 정보 미포함 텍스트 (추측하지 않고 빈 문자열 반환)"""
    res1 = parse_account_text("")
    assert res1 == {"bank_name": "", "bank_code": "", "account_no": "", "holder": ""}

    res2 = parse_account_text("안녕하세요 내일 뵙겠습니다.")
    assert res2 == {"bank_name": "", "bank_code": "", "account_no": "", "holder": ""}
