from fastapi import FastAPI
from src.handlers.twilio import router as twilio_router
from src.handlers.nomba import router as nomba_router

app = FastAPI(title="Hustaq")
app.include_router(twilio_router, prefix="/api/webhooks")
app.include_router(nomba_router, prefix="/api/webhooks")

@app.get("/api/health")
async def health():
    return {"status": "ok"}
