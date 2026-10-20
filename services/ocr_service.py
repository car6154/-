"""
services/ocr_service.py
J-PRO 거래처 OCR 비즈니스 서비스 및 문서 파서.
FastAPI 본체 환경에서 동작하며, RapidOCR + OpenVINO 상주 워커를 격리된 .venv_ocr_spike 가상환경에서 싱글턴으로 관리합니다.
"""
import os
import sys
import re
import json
import uuid
import queue
import threading
import subprocess
import shutil
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR_VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv_ocr_spike", "Scripts", "python.exe")
OCR_WORKER_SCRIPT = os.path.join(PROJECT_ROOT, "services", "ocr_worker.py")
TEMP_OCR_DIR = os.path.join(PROJECT_ROOT, "data", "temp_ocr")


class OCRService:
    # 상주 워커 싱글턴 상태 관리
    _worker_proc: Optional[subprocess.Popen] = None
    _worker_lock: threading.Lock = threading.Lock()
    _worker_queue: Optional[queue.Queue] = None
    _WORKER_TIMEOUT: float = 180.0

    @staticmethod
    def ensure_temp_dir():
        if not os.path.exists(TEMP_OCR_DIR):
            os.makedirs(TEMP_OCR_DIR, exist_ok=True)

    @classmethod
    def _get_python_exec(cls) -> str:
        python_exec = OCR_VENV_PYTHON
        if not os.path.exists(python_exec):
            alt_python = os.path.join(PROJECT_ROOT, ".venv_ocr_spike", "bin", "python")
            if os.path.exists(alt_python):
                python_exec = alt_python
            else:
                raise FileNotFoundError(
                    f"OCR 전용 가상환경 Python을 찾을 수 없습니다: {OCR_VENV_PYTHON}. "
                    "Phase 0 스파이크 가상환경(.venv_ocr_spike)이 생성되어 있는지 확인하세요."
                )
        return python_exec

    @classmethod
    def _kill_worker(cls):
        """기존 워커 프로세스를 안전하게 종료하고 리소스를 해제합니다."""
        if cls._worker_proc is not None:
            try:
                if cls._worker_proc.poll() is None:
                    cls._worker_proc.terminate()
                    cls._worker_proc.wait(timeout=3)
            except Exception:
                try:
                    cls._worker_proc.kill()
                except Exception:
                    pass
            finally:
                cls._worker_proc = None
                cls._worker_queue = None

    @classmethod
    def _ensure_worker_running(cls):
        """상주 워커 프로세스가 실행 중인지 확인하고, 미실행 또는 사망 시 새로 기동합니다."""
        if cls._worker_proc is not None and cls._worker_proc.poll() is None and cls._worker_queue is not None:
            return

        cls._kill_worker()
        python_exec = cls._get_python_exec()
        cmd = [python_exec, OCR_WORKER_SCRIPT, "--serve"]

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            encoding="utf-8",
            env=env,
        )

        out_queue: queue.Queue = queue.Queue()

        def _reader_thread(p: subprocess.Popen, q: queue.Queue):
            try:
                for line in iter(p.stdout.readline, ''):
                    if line:
                        q.put(line.strip())
            except Exception:
                pass
            finally:
                q.put(None)  # EOF 신호

        t = threading.Thread(target=_reader_thread, args=(proc, out_queue), daemon=True)
        t.start()

        # 기동 완료 신호({"status": "READY"}) 대기 (최대 180초)
        try:
            init_line = out_queue.get(timeout=cls._WORKER_TIMEOUT)
            if not init_line:
                raise RuntimeError("워커가 초기 신호 없이 종료되었습니다.")
            init_data = json.loads(init_line)
            if init_data.get("status") != "READY":
                raise RuntimeError(f"워커 준비 신호 불일치: {init_line}")
        except Exception as e:
            try:
                proc.kill()
            except Exception:
                pass
            raise RuntimeError(f"RapidOCR 상주 워커 기동 실패: {str(e)}")

        cls._worker_proc = proc
        cls._worker_queue = out_queue

    @classmethod
    def execute_ocr_subprocess(cls, image_path: str) -> Dict[str, Any]:
        """
        상주 워커 싱글턴 프로세스에 stdin JSON 라인으로 요청을 보내고 stdout 결과를 수신합니다.
        스레드 락으로 직렬화하며, 워커 사망 시 1회 자동 재기동합니다. (타임아웃 180초)
        """
        cls.ensure_temp_dir()

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"입력 이미지 파일이 존재하지 않습니다: {image_path}")

        abs_image_path = os.path.abspath(image_path)

        with cls._worker_lock:
            # 최대 2회 시도 (1차 실패 시 워커 재기동 후 2차 재시도)
            last_err = None
            for attempt in range(2):
                try:
                    cls._ensure_worker_running()
                    assert cls._worker_proc is not None and cls._worker_queue is not None

                    req_id = str(uuid.uuid4())
                    req = {
                        "req_id": req_id,
                        "image_path": abs_image_path,
                    }

                    # 요청 전송
                    cls._worker_proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
                    cls._worker_proc.stdin.flush()

                    # 응답 수신 (180초 타임아웃)
                    resp_line = cls._worker_queue.get(timeout=cls._WORKER_TIMEOUT)
                    if resp_line is None:
                        raise RuntimeError("워커 프로세스가 응답 중 예기치 않게 종료되었습니다 (EOF).")

                    worker_result = json.loads(resp_line)
                    if not worker_result.get("success"):
                        err_msg = worker_result.get("error", "Unknown worker error")
                        raise RuntimeError(f"OCR 처리 실패: {err_msg}")

                    return worker_result

                except queue.Empty:
                    cls._kill_worker()
                    raise TimeoutError(f"OCR 워커 처리 시간 초과 ({cls._WORKER_TIMEOUT}초)")
                except Exception as e:
                    last_err = e
                    cls._kill_worker()
                    if attempt == 1:
                        raise RuntimeError(f"OCR 워커 실행 최종 실패: {str(last_err)}")

            raise RuntimeError(f"OCR 워커 실행 실패: {str(last_err)}")

    @classmethod
    def classify_document_type(cls, texts: List[str]) -> str:
        """
        텍스트 목록을 기반으로 문서 종류(BIZ: 사업자등록증, CAR: 자동차등록증, SEAL: 인감증명서)를 자동 판별합니다.
        """
        full_text = " ".join(texts)

        # 1. 제목 및 핵심 서식 키워드 우선 검사
        if "사업자등록증" in full_text or "일반과세자" in full_text or "간이과세자" in full_text:
            return "BIZ"
        if "인감증명서" in full_text or "인감증명법" in full_text:
            return "SEAL"
        if "자동차등록증" in full_text or "자동차관리법" in full_text:
            return "CAR"

        # 2. 보조 키워드 매칭
        biz_score = sum(1 for kw in ["등록번호", "상호", "대표자", "사업장", "업태", "종목"] if kw in full_text)
        car_score = sum(1 for kw in ["차대번호", "원동기형식", "자동차등록번호", "차명", "검사유효기간"] if kw in full_text)
        seal_score = sum(1 for kw in ["인감", "위조식별", "발급사실", "부동산 매수자", "자동차매수자"] if kw in full_text)

        if biz_score >= 3 and biz_score > car_score and biz_score > seal_score:
            return "BIZ"
        if car_score >= 3 and car_score > biz_score and car_score > seal_score:
            return "CAR"
        if seal_score >= 2 and seal_score > biz_score and seal_score > car_score:
            return "SEAL"

        return "UNKNOWN"

    @classmethod
    def split_korean_address(cls, raw_addr: str) -> Tuple[str, str]:
        """
        주소를 기본주소(시/도 + 시/군/구 + 도로명/지번 및 건물번호까지)와 상세주소(동/호/층 등)로 분리합니다.
        분리 실패 시 전체를 기본주소에 할당하고 상세주소는 빈 문자열로 반환합니다.
        """
        cleaned = raw_addr.strip()
        if not cleaned:
            return "", ""

        # 주소 앞단 레이블 제거 (예: "사 업 장 소 재 지: ", "주소 : " 등)
        cleaned = re.sub(r'^(사\s*업\s*장\s*소\s*재\s*지|주\s*소)\s*[:\s]*', '', cleaned).strip()

        # 도로명 주소 패턴: "도로명 + 건물번호" (예: "인하로 295-1", "승학로 198")
        # 건물번호 뒤에 점(.), 쉼표(,), 괄호, 공백, 동/호/층이 나오는 지점을 경계로 분할
        pattern = r'^([가-힣\s\d]+?[로|길|읍|면|동|리]\s*\d+(?:-\d+)?)[,\s\.]+(.*)$'
        m = re.match(pattern, cleaned)
        if m:
            base = m.group(1).strip()
            detail = (m.group(2) or "").strip()
            return base, detail

        # 지번 주소 또는 단순 쉼표 기준 분리 시도
        if "," in cleaned:
            parts = cleaned.split(",", 1)
            return parts[0].strip(), parts[1].strip()

        return cleaned, ""

    @classmethod
    def extract_resident_number(cls, texts: List[str]) -> str:
        r"""
        주민등록번호 13자리 추출.
        - 일반: \d{6}-\d{7} 패턴
        - 인감증명서 실측 대응: 상단 본인 블록에서 앞 6자리(\d{6}-)와 뒤 7자리(\d{7})가 분리 검출된 경우 우선 병합
        """
        # 1. 인감증명서/본인 블록 분리 검출 병합 우선 탐색 (매수자 법인등록번호보다 본인 주민번호 우선)
        for i, t in enumerate(texts):
            # 매수자/법인 영역 도달 시 본인 탐색 중단
            if "매수자" in t or "법인등록번호" in t:
                break
            m_front = re.search(r'(\d{6})[ -]?$', t)
            if m_front:
                front_val = m_front.group(1)
                for j in range(i + 1, min(i + 8, len(texts))):
                    m_back = re.search(r'^([1-4]\d{6})\b', texts[j].strip())
                    if m_back:
                        return f"{front_val}-{m_back.group(1)}"

        # 2. 매수자 블록 이전 단일 블록 내 13자리 검색
        for t in texts:
            if "매수자" in t or "법인" in t or "부동산등기" in t:
                break
            m = re.search(r'(\d{6})[ -]?([1-4]\d{6})', t)
            if m:
                return f"{m.group(1)}-{m.group(2)}"

        # 3. 전체 텍스트 fallback 탐색
        for t in texts:
            m = re.search(r'\b(\d{6})[ -]?([1-4]\d{6})\b', t)
            if m:
                return f"{m.group(1)}-{m.group(2)}"

        return ""

    @classmethod
    def extract_business_number(cls, texts: List[str]) -> str:
        r"""
        사업자등록번호 10자리 (\d{3}-\d{2}-\d{5}) 추출.
        """
        for t in texts:
            m = re.search(r'(\d{3})[ -]?(\d{2})[ -]?(\d{5})', t)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return ""

    @classmethod
    def parse_biz_registration(cls, texts: List[str]) -> Dict[str, Any]:
        """
        사업자등록증 필드 추출:
        상호, 대표자명, 사업자등록번호, 업태, 종목, 주소(기본주소, 상세주소)
        """
        company_name = ""
        rep_name = ""
        biz_num = cls.extract_business_number(texts)
        biz_type = ""
        biz_item = ""
        raw_address = ""

        for i, t in enumerate(texts):
            t_clean = t.strip()

            # 상호명: "호 :테스트상호" 또는 "상호 :"
            if not company_name:
                if re.search(r'^(?:상\s*호|호)\s*[:\s]+(.+)', t_clean):
                    company_name = re.search(r'^(?:상\s*호|호)\s*[:\s]+(.+)', t_clean).group(1).strip()
                elif t_clean in ("상호", "성 호", "상 호") and i + 1 < len(texts):
                    company_name = texts[i + 1].strip()

            # 대표자명: "명: 홍길동" 또는 "성명 : 홍길동"
            if not rep_name:
                m_rep = re.search(r'^(?:대\s*표\s*자|성\s*명|명)\s*[:\s]+([가-힣]{2,5})', t_clean)
                if m_rep:
                    rep_name = m_rep.group(1).strip()
                elif t_clean in ("대표자", "성명", "성 명") and i + 1 < len(texts):
                    m_next = re.search(r'^[ :]*([가-힣]{2,5})', texts[i + 1].strip())
                    if m_next:
                        rep_name = m_next.group(1).strip()

            # 주소 (사업장 소재지)
            if not raw_address:
                m_addr = re.search(r'^(?:사\s*업\s*장\s*소\s*재\s*지|소\s*재\s*지)\s*[:\s]+(.+)', t_clean)
                if m_addr:
                    raw_address = m_addr.group(1).strip()
                elif "소재지" in t_clean and i + 1 < len(texts):
                    raw_address = texts[i + 1].strip()

            # 업태 및 종목
            if "업태" in t_clean:
                m_type = re.search(r'업\s*태\s*[:\s]*([가-힣A-Za-z0-9\s]+?)(?=\s*종\s*목|\s*종\s*록|$)', t_clean)
                if m_type:
                    biz_type = m_type.group(1).strip()
            if "종목" in t_clean or "종록" in t_clean:
                m_item = re.search(r'(?:종\s*목|종\s*록)\s*[:\s]*([가-힣A-Za-z0-9\s]+)', t_clean)
                if m_item:
                    biz_item = m_item.group(1).strip()

        base_addr, detail_addr = cls.split_korean_address(raw_address)

        return {
            "document_type": "BIZ",
            "document_label": "사업자등록증",
            "vendor_type": "business",  # 사업자
            "fields": {
                "business_number": biz_num,
                "company_name": company_name,
                "representative_name": rep_name,
                "business_type": biz_type,
                "business_item": biz_item,
                "address": raw_address,
                "base_address": base_addr,
                "detail_address": detail_addr,
            }
        }

    @classmethod
    def parse_seal_certificate(cls, texts: List[str]) -> Dict[str, Any]:
        """
        인감증명서 필드 추출:
        성명, 주민등록번호, 주소

        본인 영역 가드:
        성명·주민등록번호·주소 후보 탐색을 "매수자"·"용도"·"매도용" 중 하나라도 포함된 첫 라인의 이전까지로 제한합니다.
        그 이후 라인은 본인 필드 추출에 절대 쓰지 않습니다.
        """
        # 본인 영역 가드: "매수자", "용도", "매도용" 중 하나라도 포함된 첫 라인 이전까지만 탐색
        cutoff_idx = len(texts)
        for i, t in enumerate(texts):
            if any(guard_word in t for guard_word in ("매수자", "용도", "매도용")):
                cutoff_idx = i
                break

        owner_texts = texts[:cutoff_idx]

        name = ""
        resident_num = cls.extract_resident_number(owner_texts)
        raw_address = ""

        for i, t in enumerate(owner_texts):
            t_clean = t.strip()

            # 성명: "성 명" 레이블 다음 블록에 이름 위치
            if not name:
                if t_clean in ("성 명", "성명", "성  명"):
                    if i + 1 < len(owner_texts):
                        m_name = re.search(r'^([가-힣]{2,5})\b', owner_texts[i + 1].strip())
                        if m_name:
                            name = m_name.group(1).strip()
                elif re.search(r'^성\s*명\s*[:\s]+([가-힣]{2,5})', t_clean):
                    name = re.search(r'^성\s*명\s*[:\s]+([가-힣]{2,5})', t_clean).group(1).strip()

            # 주소: "주소" 레이블 다음 블록의 시/도 주소
            if not raw_address:
                if t_clean == "주소" and i + 1 < len(owner_texts):
                    candidate = owner_texts[i + 1].strip()
                    if any(city in candidate for city in ["시", "도", "구", "군", "로", "길"]):
                        raw_address = candidate
                elif re.search(r'^주\s*소\s*[:\s]+(.+)', t_clean):
                    raw_address = re.search(r'^주\s*소\s*[:\s]+(.+)', t_clean).group(1).strip()

        base_addr, detail_addr = cls.split_korean_address(raw_address)

        return {
            "document_type": "SEAL",
            "document_label": "인감증명서",
            "vendor_type": "individual",  # 개인
            "fields": {
                "name": name,
                "resident_number": resident_num,
                "address": raw_address,
                "base_address": base_addr,
                "detail_address": detail_addr,
            }
        }

    @classmethod
    def parse_car_registration(cls, texts: List[str]) -> Dict[str, Any]:
        """
        자동차등록증 필드 추출:
        소유자 성명, 주민등록번호, 주소 (소유자 주소 기준), 자동차등록번호, 차명, 차대번호
        """
        owner_name = ""
        resident_num = cls.extract_resident_number(texts)
        owner_address = ""
        car_number = ""
        car_name = ""
        vin = ""

        # 1. 차량 번호 (224버2800 형식)
        for t in texts:
            m_car = re.search(r'\b(\d{2,3}[가-힣]\s*\d{4})\b', t)
            if m_car:
                car_number = m_car.group(1).replace(" ", "")
                break

        # 2. 차대번호 (17자리 영숫자, I, O, Q 제외 규격이나 OCR 특성상 포함될 수 있으므로 허용)
        for t in texts:
            m_vin = re.search(r'\b([A-HJ-NPR-Z0-9]{17})\b', t)
            if m_vin:
                vin = m_vin.group(1)
                break

        # 3. 차명
        for i, t in enumerate(texts):
            if re.search(r'^[④\d\s]*차\s*명', t) or t.strip() in ("차명", "④차", "명"):
                if i + 1 < len(texts):
                    candidate = texts[i + 1].strip()
                    # 모델연도나 잡음이 아닌 차명
                    if not candidate.startswith("20") and len(candidate) >= 2:
                        car_name = candidate
                        break
            elif re.search(r'차\s*명\s*[:\s]+([가-힣A-Za-z0-9\.\s]+)', t):
                car_name = re.search(r'차\s*명\s*[:\s]+([가-힣A-Za-z0-9\.\s]+)', t).group(1).strip()
                break

        # 4. 소유자 정보 (성명 및 소유자 주소 - ⑧사용본거지와 혼동 방지)
        # 소유자 블록(소유자, ⑨ 성명, 주민등록번호) 주변 탐색
        owner_idx = -1
        for i, t in enumerate(texts):
            if "소유자" in t or "⑨ 성명" in t or "성명(명칭)" in t:
                owner_idx = i
                break

        if owner_idx != -1:
            # 소유자 블록 근처(±5블록)에서 성명 탐색
            for offset in range(-2, 6):
                idx = owner_idx + offset
                if 0 <= idx < len(texts):
                    candidate = texts[idx].strip()
                    if re.match(r'^[가-힣]{2,5}$', candidate) and candidate not in ("소유자", "성명", "명칭", "자가용", "경형승용"):
                        owner_name = candidate
                        break

        # 소유자 주소 탐색 (자동차등록증에서 "주 소" 레이블 다음 주소)
        for i, t in enumerate(texts):
            if re.search(r'^[①\d\s]*주\s*소', t) or t.strip() in ("주소", "① 주", "소"):
                # 소유자 주소는 대개 주민등록번호 직후에 위치
                if i + 1 < len(texts):
                    cand = texts[i + 1].strip()
                    if any(city in cand for city in ["시", "도", "구", "군", "로", "길"]):
                        owner_address = cand
                        break

        # 만약 소유자 주소를 못 찾았으면 사용본거지라도 fallback 탐색
        if not owner_address:
            for i, t in enumerate(texts):
                if "사용본거지" in t and i + 1 < len(texts):
                    owner_address = texts[i + 1].strip()
                    break

        base_addr, detail_addr = cls.split_korean_address(owner_address)

        return {
            "document_type": "CAR",
            "document_label": "자동차등록증",
            "vendor_type": "individual",  # 개인
            "fields": {
                "owner_name": owner_name,
                "resident_number": resident_num,
                "address": owner_address,
                "base_address": base_addr,
                "detail_address": detail_addr,
                "car_number": car_number,
                "car_name": car_name,
                "vin": vin,
            }
        }

    @classmethod
    def parse_document(cls, ocr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        OCR 원문 텍스트 목록을 받아 문서 종류를 판별하고 규격화된 필드를 추출합니다.
        """
        texts = ocr_data.get("texts", [])
        doc_type = cls.classify_document_type(texts)

        if doc_type == "BIZ":
            parsed = cls.parse_biz_registration(texts)
        elif doc_type == "SEAL":
            parsed = cls.parse_seal_certificate(texts)
        elif doc_type == "CAR":
            parsed = cls.parse_car_registration(texts)
        else:
            # 알 수 없는 문서
            parsed = {
                "document_type": "UNKNOWN",
                "document_label": "기타/미분류 서류",
                "vendor_type": "individual",
                "fields": {
                    "resident_number": cls.extract_resident_number(texts),
                    "business_number": cls.extract_business_number(texts),
                }
            }

        parsed["elapsed_sec"] = ocr_data.get("elapsed_sec", 0.0)
        parsed["raw_texts"] = texts
        return parsed
