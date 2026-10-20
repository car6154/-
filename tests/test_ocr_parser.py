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

    def test_seal_certificate_with_buyer_guard(self):
        """인감증명서 중단 매수자(법인) 블록이 존재해도 상단 본인 정보만 추출되는지 검증"""
        texts_with_buyer = [
            "인감증명서",
            "인감증명법 시행령",
            "성 명",
            "홍길동",
            "주민등록번호",
            "900101-1234567",
            "주소",
            "서울특별시 강남구 테헤란로 123, 101동 101호",
            "용도",
            "자동차 매도용",
            "매수자",
            "성명(법인명) : 더미모터스(주)",
            "주민(법인)등록번호 : 110111-1234567",
            "주소 : 서울특별시 영등포구 여의대로 108"
        ]
        result = OCRService.parse_document({"texts": texts_with_buyer, "elapsed_sec": 0.5})
        self.assertEqual(result["document_type"], "SEAL")
        fields = result["fields"]
        self.assertEqual(fields["name"], "홍길동")
        self.assertEqual(fields["resident_number"], "900101-1234567")
        self.assertIn("테헤란로 123", fields["base_address"])
        # 매수자(더미모터스, 여의대로 108) 정보로 오염되지 않았는지 단언
        self.assertNotIn("더미모터스", fields["name"])
        self.assertNotIn("여의대로", fields["address"])

    def test_exif_orientation_preprocessing(self):
        """합성 이미지에 EXIF Orientation=6(90도 회전) 태그를 부착해 전처리가 치수를 바로잡는지 검증"""
        import io
        from PIL import Image
        from services.ocr_worker import preprocess_image_orientation

        im = Image.new("RGB", (400, 200), color="white")
        exif = im.getexif()
        exif[0x0112] = 6  # 90도 CW 회전 태그
        buf = io.BytesIO()
        im.save(buf, format="JPEG", exif=exif)
        buf.seek(0)

        with Image.open(buf) as loaded_img:
            self.assertEqual(loaded_img.size, (400, 200))
            fixed_img = preprocess_image_orientation(loaded_img)
            self.assertEqual(fixed_img.size, (200, 400))

    def test_car_registration_layout_failure_reproduction(self):
        """
        자동차등록증 실물 서식 행 순서(좌우 칸 섞임) 재현:
        - ④차명 "스파크 1.0" vs ⑤형식 "DC487"
        - ⑧사용본거지(서초구) vs 소유자 ⑪주소(강남구 테헤란로)
        """
        texts = [
            "자동차등록증",
            "①자동차등록번호",
            "123가4567",
            "②차종",
            "경형승용",
            "③용도",
            "자가용",
            "④차명",
            "⑤형식 및 모델연도",
            "DC487",
            "스파크 1.0",
            "2021",
            "⑥차대번호",
            "KMHET41BP0A000001",
            "⑦원동기형식",
            "L5Q",
            "⑧사용본거지",
            "서울특별시 서초구 반포대로 50, 202동 202호",
            "소유자",
            "⑨성명(명칭)",
            "홍길동",
            "⑩주민(법인)등록번호",
            "900101-1234567",
            "⑪주소",
            "홍길동",
            "서울특별시 강남구 테헤란로 123, 101동 101호 (역삼동, 테스트아파트)"
        ]
        result = OCRService.parse_document({"texts": texts, "elapsed_sec": 0.88})
        self.assertEqual(result["document_type"], "CAR")
        fields = result["fields"]
        self.assertEqual(fields["car_number"], "123가4567")
        self.assertEqual(fields["vin"], "KMHET41BP0A000001")
        self.assertEqual(fields["owner_name"], "홍길동")
        self.assertEqual(fields["resident_number"], "900101-1234567")
        # 실패 재현 대상 1: 차명에 DC487 대신 스파크 1.0이 들어와야 함
        self.assertEqual(fields["car_name"], "스파크 1.0")
        # 실패 재현 대상 2: 기본주소에 성명(홍길동)이나 사용본거지(서초구) 대신 ⑪주소(테헤란로 123)가 들어와야 함
        self.assertIn("테헤란로 123", fields["base_address"])
        self.assertIn("101동 101호", fields["detail_address"])

    def test_seal_certificate_header_applicant_failure_reproduction(self):
        """
        인감증명서 실물 서식 재현:
        - 본인 표 상단 "신청인: 홍길동(생년월일:1990.01.01)" 머리줄
        - 본인 표에서 '성', '명', '주', '소' 라벨 분절
        - 하단 매수자 블록 존재
        """
        texts = [
            "인감증명서",
            "인감증명법 시행령[별지 제14호서식]",
            "신청인: 홍길동(생년월일:1990.01.01)",
            "인감증명서 발급사실 확인용 번호",
            "1234-5678-1",
            "주민",
            "900101-",
            "등록",
            "번호",
            "1234567",
            "성",
            "명",
            "인",
            "감",
            "주",
            "소",
            "서울특별시 강남구 테헤란로 123, 101동 101호 (역삼동, 테스트아파트)",
            "[]부동산 매수자[√]자동차매수자",
            "용도",
            "자동차 매도용",
            "매수자",
            "성명(법인명) : 더미모터스(주)",
            "주민(법인)등록번호 : 110111-1234567",
            "주소 : 서울특별시 영등포구 여의대로 108"
        ]
        result = OCRService.parse_document({"texts": texts, "elapsed_sec": 1.15})
        self.assertEqual(result["document_type"], "SEAL")
        fields = result["fields"]
        self.assertEqual(fields["resident_number"], "900101-1234567")
        # 검증: 신청인은 대리 발급 신청인이므로 차주 본인 성명으로 추출하지 않고 빈 값("")이어야 함
        self.assertEqual(fields["name"], "")
        # 실패 재현 대상 2: 주소가 공란이 아니라 '테헤란로 123'으로 추출되어야 함
        self.assertIn("테헤란로 123", fields["base_address"])
        self.assertIn("101동 101호", fields["detail_address"])

    def test_car_registration_split_car_name_label(self):
        """
        차와 명이 별도 라인으로 분절된 서식:
        "④차", "명", "스파크 1.0" 순서에서
        1자 라벨 파편 '명'이 아닌 '스파크 1.0'이 차명으로 정확히 추출되는지 검증
        """
        texts = [
            "자동차등록증",
            "①자동차등록번호",
            "123가4567",
            "②차종",
            "경형승용",
            "③용도",
            "자가용",
            "④차",
            "명",
            "스파크 1.0",
            "⑤형식 및 모델연도",
            "DC487",
            "2021",
            "⑥차대번호",
            "KMHET41BP0A000001",
            "⑧사용본거지",
            "서울특별시 서초구 반포대로 50",
            "소유자",
            "⑨성명(명칭)",
            "홍길동",
            "⑩주민(법인)등록번호",
            "900101-1234567",
            "⑪주소",
            "서울특별시 강남구 테헤란로 123, 101동 101호"
        ]
        result = OCRService.parse_document({"texts": texts, "elapsed_sec": 0.88})
        self.assertEqual(result["document_type"], "CAR")
        fields = result["fields"]
        self.assertEqual(fields["car_name"], "스파크 1.0")
        self.assertEqual(fields["car_number"], "123가4567")
        self.assertEqual(fields["vin"], "KMHET41BP0A000001")
        self.assertEqual(fields["owner_name"], "홍길동")
        self.assertEqual(fields["resident_number"], "900101-1234567")
        self.assertIn("테헤란로 123", fields["base_address"])

    def test_car_registration_coordinate_based_car_name(self):
        """
        boxes가 전달되는 환경에서도 boxes를 차명에 사용하지 않고,
        텍스트 순서 기반으로 차명이 '스파크 1.0'으로 확정 추출되는지 검증
        """
        raw_items = [
            ("자동차등록증", [[200, 50], [400, 50], [400, 80], [200, 80]]),
            ("①자동차등록번호", [[50, 100], [150, 100], [150, 130], [50, 130]]),
            ("123가4567", [[160, 100], [250, 100], [250, 130], [160, 130]]),
            ("④차명", [[100, 200], [150, 200], [150, 230], [100, 230]]),
            ("스파크 1.0", [[160, 200], [250, 200], [250, 230], [160, 230]]),
            ("⑤형식 및 모델연도", [[260, 200], [380, 200], [380, 230], [260, 230]]),
            ("DC487", [[390, 200], [450, 200], [450, 230], [390, 230]]),
            ("2021", [[460, 200], [500, 200], [500, 230], [460, 230]]),
            ("⑥차대번호", [[50, 250], [150, 250], [150, 280], [50, 280]]),
            ("KMHET41BP0A000001", [[160, 250], [350, 250], [350, 280], [160, 280]]),
            ("소유자", [[50, 300], [100, 300], [100, 330], [50, 330]]),
            ("⑨성명(명칭)", [[110, 300], [180, 300], [180, 330], [110, 330]]),
            ("홍길동", [[190, 300], [250, 300], [250, 330], [190, 330]]),
            ("⑩주민(법인)등록번호", [[50, 350], [180, 350], [180, 380], [50, 380]]),
            ("900101-1234567", [[190, 350], [320, 350], [320, 380], [190, 380]]),
            ("⑪주소", [[50, 400], [100, 400], [100, 430], [50, 430]]),
            ("서울특별시 강남구 테헤란로 123, 101동 101호", [[110, 400], [450, 400], [450, 430], [110, 430]]),
        ]
        texts = [item[0] for item in raw_items]
        boxes = [item[1] for item in raw_items]

        result = OCRService.parse_document({
            "texts": texts,
            "boxes": boxes,
            "elapsed_sec": 0.5
        })

        self.assertEqual(result["document_type"], "CAR")
        fields = result["fields"]
        self.assertEqual(fields["car_name"], "스파크 1.0")
        self.assertEqual(fields["car_number"], "123가4567")
        self.assertEqual(fields["vin"], "KMHET41BP0A000001")
        self.assertEqual(fields["owner_name"], "홍길동")
        self.assertEqual(fields["resident_number"], "900101-1234567")
        self.assertIn("테헤란로 123", fields["base_address"])

    def test_car_registration_order_based_car_name_cases(self):
        """
        차명-형식 라벨 사이 토큰 순서 기반 추출 검증:
        (a) ["④차명","스파크","1.0","⑤형식","DC487"] → "스파크 1.0"
        (b) ["차명","아반떼","형식","MD"] → "아반떼"
        (c) ["④차명 스파크 1.0","⑤형식 DC487"] → "스파크 1.0"
        (d) ["④차명","⑤형식","DC487"] → 공란 (DC487 채택 금지)
        (e) ["③용도", "스파크 1.0", "④차", "명", "DC487", "2021", "⑤형식 및 모델연도", "⑥차대번호", "KLYDC487DMC214608"] → "스파크 1.0"
        (f) ["④차명", "G80", "⑤형식 및 모델연도", "⑥차대번호", "KLYDC487DMC214608"] → "G80"
        (g) ["④차", "스파크1.0", "명", "DC487", "2021", "⑤형식및 모델연도"] → "스파크 1.0" / "스파크1.0"
        (h) ["④차", "명", "DC487", "2021", "⑤형식및 모델연도", "⑥차대번호", "KLYDC487DMC214608"] → 공란
        """
        # (a) 다중 토큰 결합
        res_a = OCRService.parse_car_registration(["④차명", "스파크", "1.0", "⑤형식", "DC487"])
        self.assertEqual(res_a["fields"]["car_name"], "스파크 1.0")

        # (b) 원문자 없는 차명/형식 라벨
        res_b = OCRService.parse_car_registration(["차명", "아반떼", "형식", "MD"])
        self.assertEqual(res_b["fields"]["car_name"], "아반떼")

        # (c) 라벨에 값이 붙어 있는 inline 케이스
        res_c = OCRService.parse_car_registration(["④차명 스파크 1.0", "⑤형식 DC487"])
        self.assertEqual(res_c["fields"]["car_name"], "스파크 1.0")

        # (d) 차명 칸이 비어있고 형식 코드가 바로 이어지는 경우 (DC487 채택 절대 금지, 공란)
        res_d = OCRService.parse_car_registration(["④차명", "⑤형식", "DC487"])
        self.assertEqual(res_d["fields"]["car_name"], "")

        # (e) 라벨 직전 차명 위치 (위치 2: ③용도 뒤, ④차 직전)
        res_e = OCRService.parse_car_registration(["③용도", "스파크 1.0", "④차", "명", "DC487", "2021", "⑤형식 및 모델연도", "⑥차대번호", "KLYDC487DMC214608"])
        self.assertEqual(res_e["fields"]["car_name"], "스파크 1.0")

        # (f) 영숫자 단일 차명 보호 (G80: VIN 필터에 의해 제거되지 않음)
        res_f = OCRService.parse_car_registration(["④차명", "G80", "⑤형식 및 모델연도", "⑥차대번호", "KLYDC487DMC214608"])
        self.assertEqual(res_f["fields"]["car_name"], "G80")

        # (g) 라벨 조각 사이 차명 (위치 1: ④차와 명 사이, DC487 배제)
        res_g = OCRService.parse_car_registration(["④차", "스파크1.0", "명", "DC487", "2021", "⑤형식및 모델연도"])
        self.assertIn(res_g["fields"]["car_name"], ("스파크 1.0", "스파크1.0"))

        # (h) 차명 없이 형식 코드만 존재하는 분절 라벨 (DC487 채택 차단, 공란)
        res_h = OCRService.parse_car_registration(["④차", "명", "DC487", "2021", "⑤형식및 모델연도", "⑥차대번호", "KLYDC487DMC214608"])
        self.assertEqual(res_h["fields"]["car_name"], "")


if __name__ == "__main__":
    unittest.main()

