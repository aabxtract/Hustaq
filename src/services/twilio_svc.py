import os
import boto3
import httpx
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from src.lib.secrets import get_secret

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        auth_token = get_secret('hustaq/twilio/auth_token')
        _client = Client(os.environ['TWILIO_ACCOUNT_SID'], auth_token)
    return _client


async def send_message(to: str, body: str) -> None:
    # Set SKIP_TWILIO_SEND=true locally to log messages without real API calls
    if os.environ.get('SKIP_TWILIO_SEND', '').lower() == 'true':
        safe_body = body[:120].encode('ascii', errors='replace').decode('ascii')
        print(f'[MOCK SEND -> {to}]: {safe_body}')
        return
    client = get_client()
    from_number = os.environ['TWILIO_WHATSAPP_NUMBER']
    to_formatted = to if to.startswith('whatsapp:') else f'whatsapp:{to}'
    client.messages.create(from_=from_number, to=to_formatted, body=body)


def verify_twilio_signature(auth_token: str, signature: str, url: str, params: dict) -> bool:
    validator = RequestValidator(auth_token)
    return validator.validate(url, params, signature)


async def save_media_to_s3(media_url: str, seller_id: str) -> str:
    bucket = os.environ.get('S3_BUCKET', '')
    if not bucket:
        return media_url  # local dev — return Twilio URL as-is

    auth_token = get_secret('hustaq/twilio/auth_token')
    account_sid = os.environ['TWILIO_ACCOUNT_SID']

    async with httpx.AsyncClient() as client:
        resp = await client.get(media_url, auth=(account_sid, auth_token))

    s3 = boto3.client('s3')
    key = f'products/{seller_id}/{os.urandom(8).hex()}.jpg'
    s3.put_object(
        Bucket=bucket, Key=key,
        Body=resp.content,
        ContentType='image/jpeg',
        ACL='public-read',
    )
    return f'https://{bucket}.s3.amazonaws.com/{key}'
