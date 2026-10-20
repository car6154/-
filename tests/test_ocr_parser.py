"""
tests/test_ocr_parser.py
문서 종류 판별 및 필드 추출 로직을 단위 테스트합니다.
(개인정보 보호를 위해 실제 서류 구조를 모방한 더미값 fixture 사용)
"""
import os
import sys
import json
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.ocr_service import OCRService

# 더미 텍스트 fixtures (서류 레이아웃 구조 유지)
BIZ_RAW_TEXTS = [
    "사업자등록증",
    "(일반과세자)",
    "등록번호:123-45-67890",
    "성",
    "호 :테스트분식(본점)",
    "성",
    "명: 홍길동",
    "생 년 월 일 : 1990 년01 월 01 일",
    "개 업 연 월 일:2020 년05월01일",
    "사 업 장 소 재 지: 서울특별시 강남구 테헤란로 123.101동 101호(역삼동)",
    "사 업 의 종 류:업태음식정업",
    "종록한식 음식점업",
    "발급 사유:신규",
    "공동사업자:",
    "주류판매신고번호:123-4-56789",
    "사업범위 : 판매할 주류의 종류만을 면허장소에서 소매하여야 한다",
    "판매할주류의종류:주정이외의 주류",
    "지정조건: 1.사업범위를위반하면 면허를 취소한다",
    "2.타법령에의해 허가·등록이 취소되면 이 연허도 취소된다",
    "사업자 단위 과세 적용사업자 여부 : 여( ) 부(V)",
    "전자세금계산서 전용 전자우편주소 :",
    "2020 년 05 월 01 일",
    "강 남 세 무 서 장",
    "",
    "국세청",
    "국세청"
]

SEAL_RAW_TEXTS = [
    "인감중명법 시행령[별지 제14호서식]",
    "시스",
    "인감증명서 발급사실 확인용 번호",
    "1234- 5678-1",
    ":(년일:1990,01.01).",
    "답당자:김담당(전화:02-1234-5678)",
    "이 용지는 위조식별표시가 되이 있음",
    "민등900101-",
    "인감증명서",
    "본 인",
    "대 리인",
    "번",
    "1234567",
    "O",
    "성 명",
    "홍길동",
    "인",
    "#",
    "(한 자)",
    "()",
    "GD",
    " ",
    "감",
    " 중",
    "국 적",
    "통록증",
    "주소",
    "서울특별시 강남구 테헤란로 123, 101동 101호 (역삼동, 테스트아파트)",
    "[]부동산 매수자[√]자동차매수자",
    "성명",
    "테스트상사(주)본점(상",
    "주민등록번호",
    "매",
    "(법인명·단체명)",
    ")",
    "(법인등록번호",
    "1101111847784",
    "$",
    "부동산등기용등록번호)",
    "도",
    "주소",
    "#",
    "(사무소·",
    "경기도 수원시 팔달구 매산로 100",
    "사업장 소재지)"
]

CAR_RAW_TEXTS = [
    "자동차등록증",
    "지은소치콩지",
    "호",
    "최초등록일:",
    "2021",
    "년 01",
    "월27",
    "일",
    "①자동차등록번호",
    "123가4567",
    "② 차",
    "경형승용",
    "③ 용도",
    "자가용",
    "종",
    "④차",
    "스파크1.0",
    "명",
    "DC487",
    "2021",
    "⑤형식및 모델연도",
    "⑥차대번호",
    "KMHET41BP0A000001",
    "⑦원동기형식",
    "L5Q",
    "⑧사용본거지",
    "서울특별시 서초구 반포대로 50, 202동 202호",
    "소유자",
    "홍길동",
    "⑨ 성명(명칭)",
    "①주민(법인등록번호",
    "900101-1234567",
    "① 주",
    "소",
    "서울특별시 강남구 테헤란로 123,101동101호(역삼동,테스트아파트)",
    "※유의사향:사용연료의 종류가 전기 또는 수소인 자동차의 경우⑦번란의'원동기형식'은'구동전동기형식'을 말합니다."
]


class TestOCRParser(unittest.TestCase):
    def test_biz_registration_parsing(self):
        result = OCRService.parse_document({"texts": BIZ_RAW_TEXTS, "elapsed_sec": 7.66})
        self.assertEqual(result["document_type"], "BIZ")
        self.assertEqual(result["vendor_type"], "business")
        
        fields = result["fields"]
        self.assertEqual(fields["business_number"], "123-45-67890")
        self.assertEqual(fields["company_name"], "테스트분식(본점)")
        self.assertEqual(fields["representative_name"], "홍길동")
        self.assertEqual(fields["business_type"], "음식정업")
        self.assertEqual(fields["business_item"], "한식 음식점업")
        self.assertIn("테헤란로 123", fields["base_address"])
        self.assertIn("101동", fields["detail_address"])

    def test_seal_certificate_parsing(self):
        result = OCRService.parse_document({"texts": SEAL_RAW_TEXTS, "elapsed_sec": 25.38})
        self.assertEqual(result["document_type"], "SEAL")
        self.assertEqual(result["vendor_type"], "individual")
        
        fields = result["fields"]
        self.assertEqual(fields["name"], "홍길동")
        # 분리 검출된 앞 6자리와 뒤 7자리가 안전하게 결합되었는지 검증
        self.assertEqual(fields["resident_number"], "900101-1234567")
        self.assertIn("테헤란로 123", fields["base_address"])
        self.assertIn("101동 101호", fields["detail_address"])

    def test_car_registration_parsing(self):
        result = OCRService.parse_document({"texts": CAR_RAW_TEXTS, "elapsed_sec": 23.05})
        self.assertEqual(result["document_type"], "CAR")
        self.assertEqual(result["vendor_type"], "individual")
        
        fields = result["fields"]
        self.assertEqual(fields["owner_name"], "홍길동")
        self.assertEqual(fields["resident_number"], "900101-1234567")
        self.assertEqual(fields["car_number"], "123가4567")
        self.assertEqual(fields["car_name"], "스파크1.0")
        self.assertEqual(fields["vin"], "KMHET41BP0A000001")
        # 사용본거지가 아닌 소유자 주소 매핑 확인
        self.assertIn("테헤란로 123", fields["base_address"])
        self.assertIn("101동101호", fields["detail_address"])


if __name__ == "__main__":
    unittest.main()
