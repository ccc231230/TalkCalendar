from fastapi import APIRouter
from pydantic import BaseModel
from services.parser import parse_voice_command


class ParseRequest(BaseModel):
    text: str


router = APIRouter()


@router.post("/parse")
async def parse_text(req: ParseRequest):
    """解析语音文字，返回结构化日历数据"""
    if not req.text.strip():
        return {
            "intent": "unknown",
            "params": {},
            "status": "empty",
        }
    result = parse_voice_command(req.text)
    result["status"] = "success"
    return result
