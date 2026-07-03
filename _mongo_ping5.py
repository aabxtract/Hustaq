import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
async def go():
    try:
        uri = (
            "mongodb+srv://hesedanu_db_user:MT7XVyKGSzrzAx9B@cluster0.dz7e9vn.mongodb.net/"
            "?appName=Cluster0"
            "&serverSelectionTimeoutMS=5000"
            "&tls=true"
            "&tlsInsecure=true"
        )
        print("creating client")
        c = AsyncIOMotorClient(uri)
        print("created client")
        print("calling server_info")
        info = await asyncio.wait_for(c.server_info(), timeout=8)
        print("pong", info.get("version"))
    except Exception as e:
        print("error", type(e).__name__, e)
    finally:
        try:
            c.close()
        except Exception:
            pass
asyncio.run(go())
