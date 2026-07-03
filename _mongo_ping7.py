import ssl
import pymongo
ctx = ssl.create_default_context()
ctx.minimum_version = ssl.TLSVersion.TLSv1_2
ctx.maximum_version = ssl.TLSVersion.TLSv1_3
ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
client = pymongo.MongoClient(
    "mongodb+srv://hesedanu_db_user:MT7XVyKGSzrzAx9B@cluster0.dz7e9vn.mongodb.net/?appName=Cluster0&serverSelectionTimeoutMS=5000&tls=true&tlsInsecure=true",
    tls=True,
    tlsInsecure=True,
    tlsAllowInvalidCertificates=True,
    connect=False,
)
print("created")
try:
    info = client.server_info()
    print("pong", info.get("version"))
except Exception as e:
    print("error", type(e).__name__, e)
finally:
    client.close()
