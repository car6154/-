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

    def test_latest_reset_session(self):
        """[새 건 시작] POST /api/ocr/latest/reset 호출 시 메타데이터 및 보관 파일 초기화 검증"""
        os.makedirs(LATEST_OCR_DIR, exist_ok=True)
        temp_img = os.path.join(LATEST_OCR_DIR, "latest_biz.jpg")
        with open(temp_img, "wb") as f:
            f.write(b"SAMPLE")

        # 1. 초기화 엔드포인트 호출
        res = client.post("/api/ocr/latest/reset")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))

        # 2. GET /api/ocr/latest 확인
        get_res = client.get("/api/ocr/latest")
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.json()
        self.assertFalse(get_data.get("has_data"))
        self.assertEqual(get_data.get("files"), {})

    def test_latest_save_account_only(self):
        """[계좌만 저장] POST /api/ocr/latest/account 사진 없이 계좌 텍스트 단독 전송 및 파싱 검증"""
        payload = {"account_text": "국민은행 123456-78-901234 홍길동"}
        res = client.post("/api/ocr/latest/account", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        acc = data.get("account", {})
        self.assertEqual(acc.get("bank_name"), "국민은행")
        self.assertEqual(acc.get("bank_code"), "004")
        self.assertEqual(acc.get("account_no"), "123456-78-901234")
        self.assertEqual(acc.get("holder"), "홍길동")

        # GET /api/ocr/latest 에서도 조회되는지 확인
        get_res = client.get("/api/ocr/latest")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json().get("account"), acc)

    def test_latest_file_type_update_to_fact(self):
        """[서류 종류 변경] PATCH /api/ocr/latest/file-type 으로 비사업용사실확인서(FACT) 변경 검증"""
        os.makedirs(LATEST_OCR_DIR, exist_ok=True)
        src_img = os.path.join(LATEST_OCR_DIR, "source_unknown.jpg")
        with open(src_img, "wb") as f:
            f.write(b"FACT_DOCUMENT_IMAGE_CONTENT")

        # 초기 UNKNOWN 보관
        _save_latest_result(
            task_id="task-unknown",
            doc_type="UNKNOWN",
            parsed={"document_type": "UNKNOWN", "fields": {}},
            file_path=src_img,
            orig_name="my_fact.jpg"
        )

        # 서류 종류 FACT로 갱신 요청
        patch_res = client.patch(
            "/api/ocr/latest/file-type",
            json={"old_doc_type": "UNKNOWN", "new_doc_type": "FACT"}
        )
        self.assertEqual(patch_res.status_code, 200)
        patch_data = patch_res.json()
        self.assertTrue(patch_data.get("success"))
        files = patch_data.get("files", {})
        self.assertNotIn("UNKNOWN", files)
        self.assertIn("FACT", files)
        self.assertTrue(files["FACT"]["has_file"])

        # 다운로드 검증
        dl_res = client.get("/api/ocr/latest/file?doc_type=FACT")
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.content, b"FACT_DOCUMENT_IMAGE_CONTENT")

    def test_main_document_priority_by_registration_type(self):
        """[주 서류 고정] 등록 기준에 따른 주 서류 우선순위 불변 검증"""
        os.makedirs(LATEST_OCR_DIR, exist_ok=True)
        seal_img = os.path.join(LATEST_OCR_DIR, "temp_seal.jpg")
        biz_img = os.path.join(LATEST_OCR_DIR, "temp_biz.jpg")
        with open(seal_img, "wb") as f:
            f.write(b"SEAL_IMG")
        with open(biz_img, "wb") as f:
            f.write(b"BIZ_IMG")

        seal_parsed = {
            "document_type": "SEAL",
            "vendor_type": "individual",
            "fields": {"name": "홍개인", "resident_number": "900101-1234567"}
        }
        biz_parsed = {
            "document_type": "BIZ",
            "vendor_type": "business",
            "fields": {"company_name": "(주)사업자상사", "business_number": "111-22-33333"}
        }

        # 시나리오 1: [개인 등록 기준] - 인감(SEAL) 분석 후 사업자(BIZ)가 나중에 들어와도 주 서류는 개인 정보 유지
        _save_latest_result(
            task_id="t1",
            doc_type="SEAL",
            parsed=seal_parsed,
            file_path=seal_img,
            orig_name="seal.jpg",
            registration_type="individual"
        )
        # BIZ가 나중에 완료됨
        _save_latest_result(
            task_id="t2",
            doc_type="BIZ",
            parsed=biz_parsed,
            file_path=biz_img,
            orig_name="biz.jpg",
            registration_type="individual"
        )

        res1 = client.get("/api/ocr/latest")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        # 주 서류 필드는 개인(인감증명서) 정보 유지!
        self.assertEqual(data1.get("document_type"), "SEAL")
        self.assertEqual(data1.get("vendor_type"), "individual")
        self.assertEqual(data1.get("data")["fields"]["name"], "홍개인")
        # 하지만 파일 맵에는 BIZ와 SEAL이 모두 보관되어 매입등록 첨부 가능!
        self.assertIn("SEAL", data1.get("files", {}))
        self.assertIn("BIZ", data1.get("files", {}))

        # 시나리오 2: [사업자 등록 기준] - 사업자(BIZ) 분석 후 등록증(CAR)이 나중에 들어와도 주 서류는 사업자 정보 유지
        # 새 건 시작
        client.post("/api/ocr/latest/reset")
        _save_latest_result(
            task_id="t3",
            doc_type="BIZ",
            parsed=biz_parsed,
            file_path=biz_img,
            orig_name="biz.jpg",
            registration_type="business"
        )
        # CAR가 나중에 완료됨
        car_parsed = {
            "document_type": "CAR",
            "vendor_type": "individual",
            "fields": {"car_number": "12가3456", "name": "차소유자"}
        }
        _save_latest_result(
            task_id="t4",
            doc_type="CAR",
            parsed=car_parsed,
            file_path=seal_img,
            orig_name="car.jpg",
            registration_type="business"
        )

        res2 = client.get("/api/ocr/latest")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        # 주 서류 필드는 사업자(BIZ) 정보 유지!
        self.assertEqual(data2.get("document_type"), "BIZ")
        self.assertEqual(data2.get("vendor_type"), "business")
        self.assertEqual(data2.get("data")["fields"]["company_name"], "(주)사업자상사")
        # 파일 맵에는 BIZ와 CAR 모두 보관됨
        self.assertIn("BIZ", data2.get("files", {}))
        self.assertIn("CAR", data2.get("files", {}))


if __name__ == "__main__":
    unittest.main()
