"""
routers/ocr_router.py
거래처 OCR 비즈니스 라우터.
사진 업로드 수신, 비동기 백그라운드 서브프로세스 OCR 처리, 상태 폴링 및 원본 다운로드 엔드포인트를 제공합니다.
"""
import os
import sys
import time
import uuid
import shutil
import threading
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse

from services.ocr_service import OCRService, TEMP_OCR_DIR

router = APIRouter(prefix="/api/ocr", tags=["OCR"])

# 메모리 기반 태스크 저장소 (task_id -> task dict)
OCR_TASKS: Dict[str, Dict[str, Any]] = {}
TASK_LOCK = threading.Lock()


def _cleanup_old_tasks():
    """1시간 이상 경과된 오래된 임시 파일 및 태스크 정리"""
    now = time.time()
    with TASK_LOCK:
        expired_ids = []
        for tid, tinfo in OCR_TASKS.items():
            if now - tinfo.get("created_at", 0) > 3600:  # 1시간
                fpath = tinfo.get("file_path")
                if fpath and os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
                expired_ids.append(tid)
        for tid in expired_ids:
            OCR_TASKS.pop(tid, None)


def _async_ocr_worker(task_id: str, file_path: str):
    """백그라운드 스레드에서 OCR subprocess를 실행하고 결과를 갱신합니다."""
    try:
        with TASK_LOCK:
            if task_id in OCR_TASKS:
                OCR_TASKS[task_id]["status"] = "PROCESSING"

        # 1. PaddleOCR 서브프로세스 실행 (독립 가상환경)
        ocr_raw = OCRService.execute_ocr_subprocess(file_path)

        # 2. 문서 종류 및 필드 파싱
        parsed = OCRService.parse_document(ocr_raw)
        doc_type = parsed.get("document_type", "UNKNOWN")

        download_url = None
        # 3. 파일 유지 및 삭제 정책:
        # - 사업자등록증(BIZ): 인트라넷 등록 시 파일 첨부가 필수이므로 다운로드 링크 제공 및 1시간 임시 보존
        # - 자동차등록증/인감증명서: 개인정보 보호를 위해 처리 완료 즉시 파일 영구 삭제
        if doc_type == "BIZ":
            download_url = f"/api/ocr/download/{task_id}"
        else:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

        with TASK_LOCK:
            if task_id in OCR_TASKS:
                OCR_TASKS[task_id]["status"] = "COMPLETED"
                OCR_TASKS[task_id]["result"] = parsed
                OCR_TASKS[task_id]["download_url"] = download_url
                OCR_TASKS[task_id]["completed_at"] = time.time()

    except Exception as e:
        # 실패 시 파일 삭제
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        with TASK_LOCK:
            if task_id in OCR_TASKS:
                OCR_TASKS[task_id]["status"] = "FAILED"
                OCR_TASKS[task_id]["error"] = str(e)
                OCR_TASKS[task_id]["completed_at"] = time.time()


@router.post("/vendor")
async def upload_vendor_document(file: UploadFile = File(...)):
    """
    거래처 서류(사업자등록증, 인감증명서, 자동차등록증) 사진을 업로드하고 비동기 OCR 작업을 시작합니다.
    """
    OCRService.ensure_temp_dir()
    _cleanup_old_tasks()

    if not file.filename:
        raise HTTPException(status_code=400, detail="업로드할 파일명이 없습니다.")

    task_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        ext = ".jpg"

    safe_filename = f"{task_id}{ext}"
    saved_path = os.path.join(TEMP_OCR_DIR, safe_filename)

    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")

    with TASK_LOCK:
        OCR_TASKS[task_id] = {
            "task_id": task_id,
            "status": "PENDING",
            "created_at": time.time(),
            "file_path": saved_path,
            "original_filename": file.filename,
            "result": None,
            "download_url": None,
            "error": None,
        }

    # 동기 블로킹 방지를 위해 백그라운드 스레드로 비동기 처리
    worker_thread = threading.Thread(
        target=_async_ocr_worker,
        args=(task_id, saved_path),
        daemon=True,
    )
    worker_thread.start()

    return {
        "success": True,
        "task_id": task_id,
        "status": "PENDING",
        "message": "서류 업로드 완료. OCR 분석 작업이 백그라운드에서 시작되었습니다."
    }


@router.get("/status/{task_id}")
async def get_ocr_task_status(task_id: str):
    """
    진행 중인 OCR 작업 상태 및 결과 데이터를 조회합니다.
    """
    with TASK_LOCK:
        task = OCR_TASKS.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="존재하지 않거나 만료된 작업 ID입니다.")

    return {
        "success": True,
        "task_id": task_id,
        "status": task.get("status"),
        "data": task.get("result"),
        "download_url": task.get("download_url"),
        "error": task.get("error"),
        "created_at": task.get("created_at"),
        "completed_at": task.get("completed_at"),
    }


@router.get("/download/{task_id}")
async def download_vendor_file(task_id: str):
    """
    사업자등록증 등 인트라넷 등록에 필요한 원본 서류 파일을 다운로드합니다.
    """
    with TASK_LOCK:
        task = OCR_TASKS.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="다운로드 대상 작업 정보를 찾을 수 없습니다.")

    file_path = task.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="서버에 파일이 존재하지 않거나 이미 삭제되었습니다.")

    orig_name = task.get("original_filename") or os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        filename=orig_name,
        media_type="application/octet-stream"
    )
