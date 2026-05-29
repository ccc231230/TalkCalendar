from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import asr, nlp

app = FastAPI(title="TalkCalendar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(asr.router, prefix="/api/asr")
app.include_router(nlp.router, prefix="/api/nlp")

@app.get("/api/health")
async def health():
    return {"status": "ok"}
