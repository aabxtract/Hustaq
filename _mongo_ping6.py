import pymongo
try:
    uri = "mongodb+srv://hesedanu_db_user:MT7XVyKGSzrzAx9B@cluster0.dz7e9vn.mongodb.net/?appName=Cluster0&serverSelectionTimeoutMS=5000"
    print("creating sync client")
    c = pymongo.MongoClient(uri)
    print("created")
    print("server_info")
    info = c.server_info()
    print("pong", info.get("version"))
except Exception as e:
    print("error", type(e).__name__, e)
finally:
    try:
        c.close()
    except Exception:
        pass
