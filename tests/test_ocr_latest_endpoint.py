import os
import shutil
import unittest
from fastapi.testclient import TestClient
from api_server import app
from routers.ocr_router import LATEST_OCR_DIR, LATEST_META_FILE, _save_latest_result

client = TestClient(app)

class TestOCRLatestEndpoints(unittest.TestCase):
    def setUp(self):
        # 테스트 전 디렉터리 정리
        if os.path.exists(LATEST_OCR_DIR):
            shutil.rmtree(LATEST_OCR_DIR, ignore_errors=True)
            
    def tearDown(self):
        # 테스트 후 정리
        if os.path.exists(LATEST_OCR_DIR):
            shutil.rmtree(LATEST_OCR_DIR, ignore_errors=True)

    def test_latest_no_data(self):
        """데이터가 없을 때 GET /api/ocr/latest 정상 응답"""
        res = client.get("/api/ocr/latest")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data.get("has_data"))
        self.assertIn("최근 처리된 OCR 결과가 없습니다", data.get("message", ""))

    def test_latest_file_404_when_no_data(self):
        """데이터가 없을 때 GET /api/ocr/latest/file 404 응답"""
        res = client.get("/api/ocr/latest/file")
        self.assertEqual(res.status_code, 404)

    def test_latest_save_and_download(self):
        """최신 결과 보관 및 조회/다운로드 종단 검증"""
        # 1. 가짜 원본 이미지 파일 생성
        os.makedirs(LATEST_OCR_DIR, exist_ok=True)
        temp_img = os.path.join(LATEST_OCR_DIR, "temp_source.jpg")
        dummy_content = b"DUMMY_IMAGE_BINARY_DATA_FOR_TESTING_12345"
        with open(temp_img, "wb") as f:
            f.write(dummy_content)

        parsed_sample = {
            "document_type": "BIZ",
            "vendor_type": "business",
            "fields": {
                "company_name": "(주)테스트상사",
                "business_number": "123-45-67890"
            }
        }

        # 2. _save_latest_result 호출
        _save_latest_result(
            task_id="test-task-123",
            doc_type="BIZ",
            parsed=parsed_sample,
            file_path=temp_img,
            orig_name="business_license.jpg"
        )

        # 3. GET /api/ocr/latest 확인
        res = client.get("/api/ocr/latest")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("has_data"))
        self.assertEqual(data.get("document_type"), "BIZ")
        self.assertEqual(data.get("vendor_type"), "business")
        self.assertEqual(data.get("data")["fields"]["company_name"], "(주)테스트상사")
        self.assertTrue(data.get("has_file"))
        self.assertIn("BIZ", data.get("files", {}))
        self.assertTrue(data["files"]["BIZ"]["has_file"])

        # 4. GET /api/ocr/latest/file 다운로드 및 크기 일치 확인
        res_file = client.get("/api/ocr/latest/file")
        self.assertEqual(res_file.status_code, 200)
        self.assertEqual(res_file.content, dummy_content)
        self.assertEqual(len(res_file.content), len(dummy_content))

        # 5. 서류 종류 지정 다운로드 (doc_type=BIZ)
        res_biz = client.get("/api/ocr/latest/file?doc_type=BIZ")
        self.assertEqual(res_biz.status_code, 200)
        self.assertEqual(res_biz.content, dummy_content)

        # 6. 미등록 서류 종류 (doc_type=CAR) 404 확인
        res_car = client.get("/api/ocr/latest/file?doc_type=CAR")
        self.assertEqual(res_car.status_code, 404)

    def test_latest_account_and_patch(self):
        """계좌 정보 보관 및 PATCH /api/ocr/latest 수정 기능 검증"""
        os.makedirs(LATEST_OCR_DIR, exist_ok=True)
        temp_img = os.path.join(LATEST_OCR_DIR, "temp_source.jpg")
        with open(temp_img, "wb") as f:
            f.write(b"DUMMY_IMAGE")

        parsed_sample = {
            "document_type": "BIZ",
            "vendor_type": "business",
            "fields": {"company_name": "(주)계좌상사"}
        }
        init_account = {
            "bank_name": "국민은행",
            "bank_code": "004",
            "account_no": "123456-78-901234",
            "holder": "홍길동"
        }

        # 1. 초기 보관
        _save_latest_result(
            task_id="test-task-account",
            doc_type="BIZ",
            parsed=parsed_sample,
            file_path=temp_img,
            orig_name="account_test.jpg",
            account=init_account
        )

        # 2. GET /api/ocr/latest 확인
        res = client.get("/api/ocr/latest")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("account"), init_account)
        self.assertEqual(data.get("data")["account"], init_account)

        # 3. PATCH /api/ocr/latest 로 계좌 정보 직접 수정
        patch_payload = {
            "bank_name": "신한은행",
            "bank_code": "088",
            "account_no": "110-987-654321",
            "holder": "김제이"
        }
        patch_res = client.patch("/api/ocr/latest", json=patch_payload)
        self.assertEqual(patch_res.status_code, 200)
        patch_data = patch_res.json()
        self.assertTrue(patch_data.get("success"))
        self.assertEqual(patch_data.get("account"), patch_payload)

        # 4. 재조회하여 파일에 영구 반영되었는지 확인
        res_after = client.get("/api/ocr/latest")
        data_after = res_after.json()
        self.assertEqual(data_after.get("account"), patch_payload)
        self.assertEqual(data_after.get("data")["account"], patch_payload)

if __name__ == "__main__":
    unittest.main()
