"""
tests/test_ocr_seal_isolation.py
인감증명서 대리 신청인 성명 혼선 방지 및 서류 연속 분석 시 필드 격리(Isolation) 회귀 테스트
(개인정보 보호를 위해 100% 가상 합성 텍스트만 사용)
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.ocr_service import OCRService


class TestOCRSealAndConsecutiveIsolation(unittest.TestCase):
    def test_seal_applicant_vs_owner_name_isolation(self):
        """
        인감증명서 대리 발급 케이스:
        상단에 대리 신청인 '문대리'가 있고 표 내에 본인 '허차주'가 있을 때,
        파서가 대리 신청인을 무시하고 본인 성명 '허차주'만 정확히 추출하는지 검증
        """
        raw_texts = [
            "인감증명법 시행령[별지 제14호서식]",
            "인감증명서 발급사실 확인용 번호",
            "신청인: 문대리(생년월일: 1995.05.12)",
            "담당자: 김공무(전화: 02-1234-5678)",
            "1234-5678-9012",
            "이 용지는 위조식별표시가 되어 있음",
            "주민등록번호",
            "880101-1234567",
            "인감증명서",
            "성",
            "명",
            "허차주",
            "(한 자)",
            "()",
            "주소",
            "서울특별시 송파구 올림픽로 300, 101동 202호 (신천동)",
            "용도",
            "자동차 매도용",
        ]

        result = OCRService.parse_document({"texts": raw_texts, "elapsed_sec": 0.8})
        self.assertEqual(result["document_type"], "SEAL")
        fields = result["fields"]

        # 본인 성명만 정확히 추출되고 대리 신청인은 유입되지 않아야 함
        self.assertEqual(fields["name"], "허차주")
        self.assertNotEqual(fields["name"], "문대리")
        self.assertNotEqual(fields["name"], "김공무")
        self.assertEqual(fields["resident_number"], "880101-1234567")
        self.assertIn("올림픽로 300", fields["base_address"])

    def test_seal_without_table_name_returns_empty_not_applicant(self):
        """
        표 내 본인 성명이 누락되거나 인식되지 않은 경우,
        대리 신청인을 본인 성명으로 잘못 채우지 않고 빈 값('')으로 안전하게 격리하는지 검증
        """
        raw_texts = [
            "인감증명법 시행령[별지 제14호서식]",
            "인감증명서 발급사실 확인용 번호",
            "신청인: 문대리(생년월일: 1995.05.12)",
            "주민등록번호",
            "880101-1234567",
            "인감증명서",
            "주소",
            "서울특별시 송파구 올림픽로 300",
        ]

        result = OCRService.parse_document({"texts": raw_texts, "elapsed_sec": 0.5})
        self.assertEqual(result["document_type"], "SEAL")
        # 신청인을 끌어오지 않고 반드시 빈 값('')이어야 함
        self.assertEqual(result["fields"]["name"], "")

    def test_consecutive_analysis_field_isolation(self):
        """
        연속 분석 시 1차 서류(BIZ)의 필드가 2차 서류(SEAL) 결과에 전혀 섞이지 않는지 검증
        """
        biz_texts = [
            "사업자등록증",
            "등록번호: 101-86-12345",
            "상호: 테스트상사(주)",
            "대표자: 김대표",
            "개업연월일: 2018년 03월 15일",
            "사업장소재지: 서울특별시 서초구 서초대로 100",
            "사업의종류: 업태 도매및소매업 종목 자동차부품",
        ]

        seal_texts = [
            "인감증명서",
            "성",
            "명",
            "박차주",
            "주민등록번호",
            "920202-1234567",
            "주소",
            "경기도 수원시 팔달구 매산로 50",
        ]

        # 1차 사업자등록증 분석
        biz_result = OCRService.parse_document({"texts": biz_texts, "elapsed_sec": 0.5})
        self.assertEqual(biz_result["document_type"], "BIZ")
        self.assertEqual(biz_result["fields"]["company_name"], "테스트상사(주)")
        self.assertEqual(biz_result["fields"]["representative_name"], "김대표")
        self.assertEqual(biz_result["fields"]["business_number"], "101-86-12345")

        # 2차 인감증명서 분석
        seal_result = OCRService.parse_document({"texts": seal_texts, "elapsed_sec": 0.5})
        self.assertEqual(seal_result["document_type"], "SEAL")
        seal_fields = seal_result["fields"]

        # 2차 결과 검증: 인감증명서의 본인 성명 및 주민번호
        self.assertEqual(seal_fields["name"], "박차주")
        self.assertEqual(seal_fields["resident_number"], "920202-1234567")

        # 1차 서류의 필드가 2차 결과에 전혀 존재하지 않거나 영향 주지 않아야 함
        self.assertNotIn("representative_name", seal_fields)
        self.assertNotIn("company_name", seal_fields)
        self.assertNotIn("business_number", seal_fields)
        self.assertNotIn("business_type", seal_fields)
        self.assertNotIn("business_item", seal_fields)

        # 역방향: 3차 사업자등록증 분석 시 2차 인감증명서 필드가 섞이지 않는지 검증
        biz_result_2 = OCRService.parse_document({"texts": biz_texts, "elapsed_sec": 0.5})
        self.assertEqual(biz_result_2["document_type"], "BIZ")
        self.assertNotIn("resident_number", biz_result_2["fields"])
        self.assertNotIn("name", biz_result_2["fields"])
        self.assertEqual(biz_result_2["fields"]["representative_name"], "김대표")


if __name__ == "__main__":
    unittest.main()
