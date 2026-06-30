import os
from dotenv import load_dotenv

load_dotenv()  # loads .env locally; no-op on Lambda

from fastapi import FastAPI
from mangum import Mangum
from src.handlers.twilio import router as twilio_router
from src.handlers.nomba import router as nomba_router

app = FastAPI(title='Hustaq')
app.include_router(twilio_router, prefix='/webhooks')
app.include_router(nomba_router, prefix='/webhooks')


@app.get('/health')
async def health():
    return {'status': 'ok'}


# Lambda entry point
handler = Mangum(app, lifespan='off')
