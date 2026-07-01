from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    NOMBA_CLIENT_ID: str = ""
    NOMBA_CLIENT_SECRET: str = ""
    NOMBA_ENV: str = "sandbox"
    VERCEL_URL: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
