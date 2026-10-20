"""
services/ocr_worker.py
RapidOCR + OpenVINO 전용 독립 실행 워커 스크립트.
J-PRO 본체 가상환경의 의존성을 오염시키지 않기 위해 .venv_ocr_spike 환경에서 subprocess로 격리 실행됩니다.

주요 특징:
1. 상주 워커 모드(--serve): 프로세스 시작 시 모델을 1회만 로드하고 stdin/stdout JSON 통신으로 장당 0.1~0.3초대 즉각 처리
2. v2 최적화: 상단 60% 크롭 1차 추론 + 핵심 필드 누락 시 100% 전체 이미지 안전 폴백
3. 실측 확정 파라미터 (임의 변경 금지):
   - Global.use_cls = False (개별 텍스트 박스 180도 오회전 방지 - 대표자명 유실 원천 차단)
   - Det: EngineType.OPENVINO, PP-OCRv5 MOBILE, limit_side_len=960, limit_type="max", unclip_ratio=2.0, box_thresh=0.5
   - Rec: EngineType.OPENVINO, PP-OCRv5 MOBILE, lang_type="korean"
"""
import os
import sys
import re
import json
import time
import argparse
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageOps
import numpy as np

# RapidOCR 소스 체크 경고 억제
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

if sys.platform.startswith("win"):
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

_ENGINE = None

def get_engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr import RapidOCR, EngineType, ModelType, OCRVersion
        _ENGINE = RapidOCR(params={
            "Global.use_cls": False,
            "Det.engine_type": EngineType.OPENVINO,
            "Det.ocr_version": OCRVersion.PPOCRV5,
            "Det.model_type": ModelType.MOBILE,
            "Det.limit_side_len": 960,
            "Det.limit_type": "max",
            "Det.unclip_ratio": 2.0,
            "Det.box_thresh": 0.5,
            "Rec.engine_type": EngineType.OPENVINO,
            "Rec.ocr_version": OCRVersion.PPOCRV5,
            "Rec.model_type": ModelType.MOBILE,
            "Rec.lang_type": "korean"
        })
    return _ENGINE


def preprocess_image_orientation(img: Image.Image) -> Image.Image:
    """
    EXIF Orientation 태그를 기반으로 물리적 픽셀 방향을 바로잡습니다.
    스마트폰에서 90도 회전되어 저장된 사진을 정방향으로 복원합니다.
    """
    try:
        transposed = ImageOps.exif_transpose(img)
        return transposed if transposed is not None else img
    except Exception:
        return img


def _raw_infer(engine, img_pil: Image.Image):
    """엔진 직접 추론 후 texts, scores, boxes 반환"""
    img_np = np.array(img_pil)
    out = engine(img_np)
    texts = list(out.txts) if (out and out.txts is not None) else []
    scores = [float(s) for s in out.scores] if (out and out.scores is not None) else []
    boxes = [b.tolist() if hasattr(b, 'tolist') else b for b in out.boxes] if (out and out.boxes is not None) else []
    return texts, scores, boxes


def _check_essential_keys(texts: List[str]) -> bool:
    r"""
    서류 판별용 핵심 식별자 존재 여부 검사:
    - 사업자등록번호 (\d{3}-\d{2}-\d{5})
    - 주민등록번호 (13자리 또는 유효 생년월일 6자리)
    - 차대번호 (17자리 영숫자)
    - 차량번호 (\d{2,3}[가-힣]\d{4})
    """
    has_biz = any(re.search(r'\b\d{3}[ -]?\d{2}[ -]?\d{5}\b', t) for t in texts)
    has_resident = any(
        re.search(r'\b\d{6}[ -]?[1-4]\d{6}\b', t) or
        re.search(r'\b\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[ -]?$', t)
        for t in texts
    )
    has_vin = any(re.search(r'[A-HJ-NPR-Z0-9]{17}', t.replace(" ", "")) for t in texts)
    has_carnum = any(re.search(r'\b\d{2,3}[가-힣]\s*\d{4}\b', t) for t in texts)
    return bool(has_biz or has_resident or has_vin or has_carnum)


def _infer_and_check(engine, img: Image.Image) -> Tuple[List[str], List[float], List[Any], bool, bool]:
    """
    단일 이미지 방향에 대해:
    1. 상단 60% 크롭 1차 추론
    2. 필수 키 검사
    3. 누락 시 100% 전체 이미지 폴백 추론
    반환: (texts, scores, boxes, used_fallback, has_essential)
    """
    w, h = img.size

    # 1. 상단 60% 크롭 1차 추론
    top60_img = img.crop((0, 0, w, int(h * 0.6)))
    texts, scores, boxes = _raw_infer(engine, top60_img)
    has_essential = _check_essential_keys(texts)

    # 2. 누락 시 전체 이미지 폴백 추론
    used_fallback = False
    if not has_essential:
        used_fallback = True
        texts, scores, boxes = _raw_infer(engine, img)
        has_essential = _check_essential_keys(texts)

    return texts, scores, boxes, used_fallback, has_essential


def process_image(image_path: str) -> Dict[str, Any]:
    """
    사진 방향 자동 보정 및 v2 최적화 파이프라인:
    1. EXIF exif_transpose 적용으로 스마트폰 회전 복원
    2. 상단 60% 크롭 1차 추론 + 전체 이미지 폴백 (정상 각도 0도)
    3. 보험 장치: 필수 키 미검출 시 90도 / 270도 회전 재추론
    """
    engine = get_engine()
    t0 = time.perf_counter()

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"입력 이미지 파일을 찾을 수 없습니다: {image_path}")

    with Image.open(image_path) as raw_img:
        # 1. EXIF 회전 전처리
        full_img = preprocess_image_orientation(raw_img.convert("RGB"))

        # 2. 0도 기본 방향 추론
        texts, scores, boxes, used_fallback, has_essential = _infer_and_check(engine, full_img)
        applied_rotation = 0

        # 3. 보험 장치: 필수 키가 전혀 안 잡힌 경우에 한해 90도 / 270도 회전 재시도
        if not has_essential:
            for deg in (90, 270):
                rot_img = full_img.rotate(deg, expand=True)
                r_texts, r_scores, r_boxes, r_fallback, r_essential = _infer_and_check(engine, rot_img)
                if r_essential:
                    texts, scores, boxes, used_fallback = r_texts, r_scores, r_boxes, r_fallback
                    applied_rotation = deg
                    break

        t1 = time.perf_counter()

        return {
            "success": True,
            "elapsed_sec": round(t1 - t0, 3),
            "used_fallback": used_fallback,
            "applied_rotation": applied_rotation,
            "texts": [str(t) for t in texts],
            "scores": [float(s) for s in scores],
            "boxes": boxes,
        }


def run_standalone(image_path: str, output_path: str):
    """하위 호환 단발성 CLI 모드"""
    try:
        res = process_image(image_path)
    except Exception as e:
        res = {
            "success": False,
            "error": str(e),
            "texts": [],
            "scores": [],
            "boxes": [],
            "applied_rotation": 0,
        }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)


def run_server():
    """
    상주 워커 모드:
    FastAPI 프로세스와 stdin/stdout JSON 통신으로 메모리에 모델 상주 유지
    """
    engine = get_engine()
    # 첫 1회 내부 엔진 워밍업 (JIT 컴파일 및 캐시 준비)
    try:
        dummy = np.ones((100, 100, 3), dtype=np.uint8) * 255
        engine(dummy)
    except Exception:
        pass

    # 기동 완료 신호 출력
    print(json.dumps({"status": "READY"}), flush=True)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break  # 부모 프로세스 종료 시 자동 종료

            line = line.strip()
            if not line:
                continue

            req = json.loads(line)
            req_id = req.get("req_id")
            image_path = req.get("image_path")

            res = process_image(image_path)
            res["req_id"] = req_id
            print(json.dumps(res, ensure_ascii=False), flush=True)
        except Exception as e:
            err_res = {
                "success": False,
                "error": str(e),
                "texts": [],
                "scores": [],
                "boxes": [],
                "applied_rotation": 0,
            }
            print(json.dumps(err_res, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description="J-PRO RapidOCR OpenVINO Isolated Worker")
    parser.add_argument("--serve", action="store_true", help="Run in resident daemon mode communicating via stdin/stdout")
    parser.add_argument("--input", help="Input image file path")
    parser.add_argument("--output", help="Output JSON file path")
    args = parser.parse_args()

    if args.serve:
        run_server()
    elif args.input and args.output:
        run_standalone(args.input, args.output)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
