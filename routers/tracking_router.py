# routers/tracking_router.py
import re
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from services.sold_out_tracker import SoldOutTracker

router = APIRouter(prefix="/api/tracking", tags=["Tracking"])


class TrackedCarCreateRequest(BaseModel):
    carid: str
    carName: Optional[str] = ""
    carNumber: Optional[str] = ""
    price: Optional[int] = 0
    source: Optional[str] = "cockpit"  # "cockpit" | "settlement"
    memo: Optional[str] = ""


@router.get("/cars")
def get_tracked_cars():
    """관심 추적 차량 전체 목록 조회"""
    try:
        data = SoldOutTracker.get_tracked_cars()
        items = list(data.values())
        # 최신 등록순 정렬
        items.sort(key=lambda x: x.get("addedAt", ""), reverse=True)
        return {"success": True, "total": len(items), "items": items}
    except Exception as e:
        return {"success": False, "error": str(e), "items": []}


@router.post("/cars")
def add_tracked_car(req: TrackedCarCreateRequest):
    """관심 추적 차량 등록/갱신"""
    cid = re.sub(r'\D', '', str(req.carid))
    if not cid or len(cid) < 5:
        raise HTTPException(status_code=400, detail="유효한 엔카 carid(숫자 5자리 이상)를 입력해주세요.")

    res = SoldOutTracker.add_tracked_car(
        car_id=cid,
        car_name=req.carName or "",
        car_number=req.carNumber or "",
        price=req.price or 0,
        source=req.source or "cockpit",
        memo=req.memo or ""
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "등록 실패"))
    return res


@router.delete("/cars/{carid}")
def remove_tracked_car(carid: str):
    """관심 추적 차량 등록 해제"""
    cid = re.sub(r'\D', '', str(carid))
    if not cid:
        raise HTTPException(status_code=400, detail="유효한 carid를 지정해주세요.")

    res = SoldOutTracker.remove_tracked_car(cid)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "차량을 찾을 수 없습니다."))
    return res


@router.post("/run")
def trigger_tracking_check(pacing_sec: float = 2.0):
    """관심 차량 전체 즉시 재확인 트리거 (페이싱 기본 2초 준수, 407 감지 시 즉시 중단)"""
    try:
        result = SoldOutTracker.check_all_tracked_cars(pacing_sec=max(0.5, pacing_sec))
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/status")
def get_tracking_status():
    """관심 차량 추적 상태 요약 통계"""
    try:
        data = SoldOutTracker.get_tracked_cars()
        items = list(data.values())
        active_count = sum(1 for i in items if i.get("status") == "판매중")
        estimated_sold_count = sum(1 for i in items if i.get("status") == "판매완료 추정")
        confirmed_sold_count = sum(1 for i in items if i.get("status") == "판매완료")
        unknown_count = sum(1 for i in items if i.get("status") == "확인불가")

        return {
            "success": True,
            "total": len(items),
            "activeCount": active_count,
            "estimatedSoldCount": estimated_sold_count,
            "confirmedSoldCount": confirmed_sold_count,
            "unknownCount": unknown_count
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
