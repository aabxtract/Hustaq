import os
import boto3

_cache: dict[str, str] = {}


def get_secret(key: str) -> str:
    if key in _cache:
        return _cache[key]

    # Convert path to env var: hustaq/twilio/auth_token -> HUSTAQ_TWILIO_AUTH_TOKEN
    env_key = key.replace('/', '_').replace('-', '_').upper()
    val = os.environ.get(env_key)
    if val:
        _cache[key] = val
        return val

    client = boto3.client('secretsmanager', region_name=os.environ.get('AWS_REGION', 'eu-west-1'))
    resp = client.get_secret_value(SecretId=key)
    _cache[key] = resp['SecretString']
    return _cache[key]
