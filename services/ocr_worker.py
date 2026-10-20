"""
services/ocr_worker.py
PaddleOCR 전용 독립 실행 워커 스크립트.
J-PRO 본체 가상환경의 의존성을 오염시키지 않기 위해 .venv_ocr_spike 환경에서 subprocess로 격리 실행됩니다.
"""
import os
import sys
import json
import argparse
import time

# PaddleOCR 소스 체크 경고/에러 방지
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

def run_worker(image_path: str, output_path: str):
    t0 = time.perf_counter()
    from paddleocr import PaddleOCR
    
    # 스파이크 실측 확정값 (변경 금지)
    # enable_mkldnn=False: oneDNN ConvertPirAttribute2RuntimeAttribute 에러 회피용 필수값
    ocr = PaddleOCR(
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="korean_PP-OCRv5_mobile_rec",
        use_doc_orientation_classify=True,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,
    )
    
    res = list(ocr.predict(input=image_path))
    t1 = time.perf_counter()
    
    texts = []
    scores = []
    boxes = []
    
    for r in res:
        if isinstance(r, dict):
            rec_texts = r.get('rec_texts', [])
            rec_scores = r.get('rec_scores', [])
            dt_polys = r.get('dt_polys', [])
            texts.extend(rec_texts)
            scores.extend(rec_scores)
            for poly in dt_polys:
                if hasattr(poly, 'tolist'):
                    boxes.append(poly.tolist())
                else:
                    boxes.append(poly)
        elif hasattr(r, 'rec_texts'):
            texts.extend(r.rec_texts)
            scores.extend(r.rec_scores)
            
    result_data = {
        "success": True,
        "elapsed_sec": round(t1 - t0, 3),
        "texts": [str(t) for t in texts],
        "scores": [float(s) for s in scores],
        "boxes": boxes,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(description="J-PRO PaddleOCR Isolated Worker")
    parser.add_argument("--input", required=True, help="Input image file path")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()
    
    try:
        run_worker(args.input, args.output)
    except Exception as e:
        err_res = {
            "success": False,
            "error": str(e),
            "texts": [],
            "scores": [],
            "boxes": []
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(err_res, f, ensure_ascii=False, indent=2)
        sys.exit(1)

if __name__ == "__main__":
    main()
