from twilio.rest import Client
from twilio.request_validator import RequestValidator
from src.lib.config import settings

_client: Client | None = None

def get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client

async def send_message(to: str, body: str) -> None:
    client = get_client()
    from_number = settings.TWILIO_WHATSAPP_NUMBER
    to_formatted = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    client.messages.create(from_=from_number, to=to_formatted, body=body)

def verify_twilio_signature(
    auth_token: str, signature: str, url: str, params: dict
) -> bool:
    validator = RequestValidator(auth_token)
    return validator.validate(url, params, signature)
