# -*- coding: utf-8 -*-
from fastapi import APIRouter
from pydantic import BaseModel
from services.scheduler import find_free_slots
from typing import Optional

router = APIRouter()


class SlotRequest(BaseModel):
    events: list[dict] = []
    date_start: str
    date_end: str
    duration_minutes: int
    prefer_morning: Optional[bool] = False
    top_k: Optional[int] = 5


@router.post("/find-slots")
async def find_slots(req: SlotRequest):
    if req.duration_minutes <= 0:
        return {"slots": [], "error": "时长必须大于0"}

    try:
        slots = find_free_slots(
            events=req.events,
            date_start=req.date_start,
            date_end=req.date_end,
            duration_minutes=req.duration_minutes,
            prefer_morning=req.prefer_morning or False,
            top_k=req.top_k or 5,
        )
        return {"slots": slots}
    except Exception as e:
        return {"slots": [], "error": str(e)}
