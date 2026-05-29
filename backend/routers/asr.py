from fastapi import APIRouter, UploadFile, File
from services.iflytek import recognize_audio

router = APIRouter()

@router.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    audio_data = await file.read()
    if not audio_data:
        return {"text": "", "status": "empty"}
    try:
        text, status = await recognize_audio(audio_data)
        if status == "mock":
            return {"text": "", "status": "mock"}
        elif status == "error":
            return {"text": "", "status": "error", "error": "识别失败"}
        return {"text": text, "status": "success"}
    except Exception as e:
        return {"text": "", "status": "error", "error": str(e)}