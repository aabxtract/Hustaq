from src.lib.redis_client import get_redis
from src.handlers.nomba import verify_nomba_signature

r = get_redis()
print("nomba:processed:NOM-TEST-P2-001 =", r.get("nomba:processed:NOM-TEST-P2-001"))
print("nomba:processed:NOM-TEST-ACCT-REF =", r.get("nomba:processed:NOM-TEST-ACCT-REF"))
print("nomba:token =", r.get("nomba:token"))

# Also test signature verification
payload = {"event_type": "payment_success", "requestId": "x", "data": {"merchant": {"userId": ""}, "transaction": {"transactionId": "x", "type": "", "time": "", "responseCode": ""}}}
result = verify_nomba_signature(payload, "sig", "secret", "timestamp")
print("signature_verify=%s" % result)
