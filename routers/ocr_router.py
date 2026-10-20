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
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse

from services.ocr_service import OCRService, TEMP_OCR_DIR
from services.account_parser import parse_account_text

router = APIRouter(prefix="/api/ocr", tags=["OCR"])

# 최신 OCR 결과 및 전 서류 보관 디렉터리
LATEST_OCR_DIR = os.path.join(os.path.dirname(TEMP_OCR_DIR), "ocr_latest")
LATEST_META_FILE = os.path.join(LATEST_OCR_DIR, "latest_meta.json")

# 메모리 기반 태스크 저장소 (task_id -> task dict)
OCR_TASKS: Dict[str, Dict[str, Any]] = {}
TASK_LOCK = threading.Lock()


class AccountUpdateRequest(BaseModel):
    bank_name: Optional[str] = ""
    bank_code: Optional[str] = ""
    account_no: Optional[str] = ""
    holder: Optional[str] = ""


def _save_latest_result(task_id: str, doc_type: str, parsed: Dict[str, Any], file_path: str, orig_name: str, account: Optional[Dict[str, str]] = None):
    """최신 OCR 결과 JSON 및 전 서류(사업자/자동차등록증/인감) 원본 사진 보관"""
    try:
        os.makedirs(LATEST_OCR_DIR, exist_ok=True)
        ext = os.path.splitext(orig_name or file_path)[1].lower() or ".jpg"
        target_filename = f"latest_{doc_type.lower()}{ext}"
        target_path = os.path.join(LATEST_OCR_DIR, target_filename)

        if os.path.exists(file_path):
            shutil.copy2(file_path, target_path)

        # 기존 서류 종류별 파일 보관 상태 및 기존 계좌 정보 유지/갱신
        files_by_type = {}
        existing_account = {"bank_name": "", "bank_code": "", "account_no": "", "holder": ""}
        if os.path.exists(LATEST_META_FILE):
            try:
                with open(LATEST_META_FILE, "r", encoding="utf-8") as f:
                    old_meta = json.load(f)
                    files_by_type = old_meta.get("files", {})
                    if old_meta.get("account"):
                        existing_account = old_meta.get("account")
            except Exception:
                files_by_type = {}

        doc_key = doc_type.upper()
        files_by_type[doc_key] = {
            "has_file": True,
            "file_name": target_filename,
            "original_filename": orig_name,
            "download_url": f"/api/ocr/latest/file?doc_type={doc_key}",
            "updated_at": time.time()
        }

        # 전달받은 account가 유효하면 우선 반영, 없으면 parsed 내의 account 또는 기존 account 유지
        final_account = account or parsed.get("account") or existing_account
        parsed["account"] = final_account

        meta = {
            "has_data": True,
            "task_id": task_id,
            "document_type": doc_key,
            "vendor_type": parsed.get("vendor_type", "UNKNOWN"),
            "data": parsed,
            "account": final_account,
            "has_file": True,
            "file_name": target_filename,
            "original_filename": orig_name,
            "download_url": "/api/ocr/latest/file",
            "files": files_by_type,
            "completed_at": time.time()
        }

        with open(LATEST_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    except Exception as ex:
        print(f"[OCR Router] 최신 결과 보관 실패: {ex}", file=sys.stderr)


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


def _async_ocr_worker(task_id: str, file_path: str, account: Optional[Dict[str, str]] = None):
    """백그라운드 스레드에서 OCR subprocess를 실행하고 결과를 갱신합니다."""
    orig_name = ""
    with TASK_LOCK:
        if task_id in OCR_TASKS:
            OCR_TASKS[task_id]["status"] = "PROCESSING"
            orig_name = OCR_TASKS[task_id].get("original_filename", "")

    try:
        # 1. RapidOCR OpenVINO 서브프로세스 실행 (독립 가상환경)
        ocr_raw = OCRService.execute_ocr_subprocess(file_path)

        # 2. 문서 종류 및 필드 파싱
        parsed = OCRService.parse_document(ocr_raw)
        doc_type = parsed.get("document_type", "UNKNOWN")

        # 계좌 정보 탑재
        if account:
            parsed["account"] = account

        # 3. 최신 결과 보관 (전 서류 원본 보관 정책 + 계좌 정보)
        _save_latest_result(task_id, doc_type, parsed, file_path, orig_name, account=account)

        # 4. 개별 작업 상태 갱신
        download_url = f"/api/ocr/download/{task_id}"

        with TASK_LOCK:
            if task_id in OCR_TASKS:
                OCR_TASKS[task_id]["status"] = "COMPLETED"
                OCR_TASKS[task_id]["result"] = parsed
                OCR_TASKS[task_id]["download_url"] = download_url
                OCR_TASKS[task_id]["completed_at"] = time.time()

    except Exception as e:
        # 실패 시 파일 정리
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
async def upload_vendor_document(
    file: UploadFile = File(...),
    account_text: Optional[str] = Form(None)
):
    """
    거래처 서류(사업자등록증, 인감증명서, 자동차등록증) 사진 및 계좌 텍스트를 업로드하고 비동기 OCR 작업을 시작합니다.
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

    # 계좌 텍스트 파싱
    parsed_account = parse_account_text(account_text) if account_text else {"bank_name": "", "bank_code": "", "account_no": "", "holder": ""}

    with TASK_LOCK:
        OCR_TASKS[task_id] = {
            "task_id": task_id,
            "status": "PENDING",
            "created_at": time.time(),
            "file_path": saved_path,
            "original_filename": file.filename,
            "account": parsed_account,
            "result": None,
            "download_url": None,
            "error": None,
        }

    # 동기 블로킹 방지를 위해 백그라운드 스레드로 비동기 처리
    worker_thread = threading.Thread(
        target=_async_ocr_worker,
        args=(task_id, saved_path, parsed_account),
        daemon=True,
    )
    worker_thread.start()

    return {
        "success": True,
        "task_id": task_id,
        "status": "PENDING",
        "account": parsed_account,
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


@router.get("/latest")
async def get_latest_ocr_result():
    """
    가장 최근에 완료된 OCR 결과 JSON 및 전 서류 원본 파일 보관 현황을 조회합니다.
    """
    if not os.path.exists(LATEST_META_FILE):
        return {
            "has_data": False,
            "message": "최근 처리된 OCR 결과가 없습니다."
        }

    try:
        with open(LATEST_META_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["has_data"] = True
        return meta
    except Exception as e:
        return {
            "has_data": False,
            "error": f"최신 결과 로드 실패: {str(e)}"
        }


@router.patch("/latest")
async def update_latest_ocr_result(req: AccountUpdateRequest):
    """
    최신 OCR 결과에 계좌 정보(은행명, 은행코드, 계좌번호, 예금주) 수정 사항을 반영합니다.
    """
    if not os.path.exists(LATEST_META_FILE):
        raise HTTPException(status_code=404, detail="수정할 최신 OCR 결과가 없습니다.")

    try:
        with open(LATEST_META_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # 계좌 정보 갱신
        current_account = meta.get("account", {}) or {}
        
        # 은행명 전달 시 코드 자동 보정
        b_name = req.bank_name if req.bank_name is not None else current_account.get("bank_name", "")
        b_code = req.bank_code if req.bank_code is not None else current_account.get("bank_code", "")
        if b_name and not b_code:
            # 은행명으로 코드 역조회
            for code, name in BANK_CODE_MAP.items():
                if name == b_name or b_name in name:
                    b_code = code
                    break

        updated_account = {
            "bank_name": b_name,
            "bank_code": b_code,
            "account_no": req.account_no if req.account_no is not None else current_account.get("account_no", ""),
            "holder": req.holder if req.holder is not None else current_account.get("holder", "")
        }

        meta["account"] = updated_account
        if "data" in meta and isinstance(meta["data"], dict):
            meta["data"]["account"] = updated_account

        with open(LATEST_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        meta["has_data"] = True
        return {
            "success": True,
            "message": "최신 계좌 정보가 성공적으로 반영되었습니다.",
            "account": updated_account,
            "data": meta
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"계좌 정보 갱신 실패: {str(e)}")


@router.get("/latest/file")
async def download_latest_ocr_file(doc_type: Optional[str] = None):
    """
    최근 처리된 서류 원본 사진 파일을 다운로드합니다.
    doc_type 지정 시(BIZ, CAR, SEAL 등) 해당 서류를 반환하며, 미지정 시 가장 최근 서류를 반환합니다.
    """
    if not os.path.exists(LATEST_META_FILE):
        raise HTTPException(status_code=404, detail="최근 처리된 OCR 결과가 없습니다.")

    try:
        with open(LATEST_META_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="최신 메타데이터를 읽을 수 없습니다.")

    target_file_name = None
    orig_name = None

    if doc_type:
        doc_key = doc_type.upper()
        file_info = meta.get("files", {}).get(doc_key)
        if file_info and file_info.get("has_file"):
            target_file_name = file_info.get("file_name")
            orig_name = file_info.get("original_filename")
        else:
            raise HTTPException(status_code=404, detail=f"'{doc_key}' 종류의 보관된 서류 파일이 없습니다.")
    else:
        target_file_name = meta.get("file_name")
        orig_name = meta.get("original_filename")

    if not target_file_name:
        raise HTTPException(status_code=404, detail="보관된 서류 파일이 없습니다.")

    full_path = os.path.join(LATEST_OCR_DIR, target_file_name)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"서버에 파일이 존재하지 않습니다: {target_file_name}")

    return FileResponse(
        path=full_path,
        filename=orig_name or target_file_name,
        media_type="application/octet-stream"
    )
