from fastapi import FastAPI
from src.handlers.whatsapp import router as whatsapp_router
from src.handlers.nomba import router as nomba_router

app = FastAPI(title="Hustaq")

app.include_router(whatsapp_router, prefix="/api/webhooks")
app.include_router(nomba_router, prefix="/api/webhooks")

# Also mount at /webhooks for backward compatibility
app.include_router(whatsapp_router, prefix="/webhooks")
app.include_router(nomba_router, prefix="/webhooks")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health")
async def api_health():
    return {"status": "ok"}
