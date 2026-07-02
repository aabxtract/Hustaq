from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://localhost:27017/hustaq"
    UPSTASH_REDIS_URL: str = "redis://localhost:6379"

    # ── Meta WhatsApp Cloud API (replaces Twilio) ──
    META_ACCESS_TOKEN: str = ""
    META_PHONE_NUMBER_ID: str = ""      # Hustaq bot's phone number ID
    META_BOT_NUMBER: str = ""           # Hustaq bot's display phone number (e.g. +14155238886)
    META_VERIFY_TOKEN: str = ""         # Random string for webhook verification
    META_API_VERSION: str = "v22.0"

    # ── Legacy Twilio (kept for reference during migration) ──
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""

    # ── Nomba Payments ──
    NOMBA_CLIENT_ID: str = ""
    NOMBA_CLIENT_SECRET: str = ""
    NOMBA_ENV: str = "sandbox"
    VERCEL_URL: str = ""

    class Config:
        env_file = ".env"

_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
