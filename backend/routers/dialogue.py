# -*- coding: utf-8 -*-
from fastapi import APIRouter
from pydantic import BaseModel
from services.dialogue import process_message, mock_reply, get_client, rule_query, rule_delete
from services.scheduler import find_free_slots
from typing import Optional
import os

router = APIRouter()

LLM_KEY = os.getenv("LLM_API_KEY", "")


class MessageRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    events: Optional[list[dict]] = None


@router.post("/message")
async def dialogue_message(req: MessageRequest):
    if not req.text.strip():
        return {"session_id": req.session_id, "reply": "请说点什么吧~", "action": None}

    # Rule-based fast path: handle query/delete locally without LLM
    events = req.events or []
    result = rule_query(events, req.text)
    if result is not None:
        result["session_id"] = req.session_id or result.get("session_id")
        return result
    result = rule_delete(events, req.text)
    if result is not None:
        result["session_id"] = req.session_id or result.get("session_id")
        return result

    # If no LLM key configured, use mock mode
    if not LLM_KEY:
        return mock_reply(req.text)

    try:
        result = await process_message(
            text=req.text,
            session_id=req.session_id,
            events_json=req.events,
        )
        return result
    except Exception as e:
        return {
            "session_id": req.session_id,
            "reply": f"抱歉，出了点问题：{str(e)[:100]}",
            "action": None,
        }


@router.post("/reset")
async def dialogue_reset(req: MessageRequest):
    """重置会话"""
    from services.dialogue import _sessions
    if req.session_id and req.session_id in _sessions:
        del _sessions[req.session_id]
    return {"status": "ok"}
