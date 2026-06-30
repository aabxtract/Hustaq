import os
import psycopg2
import psycopg2.extras

_conn = None


def get_db():
    global _conn
    if _conn is None or _conn.closed:
        _conn = _connect()
    else:
        # Detect stale connection from a previous Lambda warm invocation
        try:
            _conn.cursor().execute('SELECT 1')
        except Exception:
            _conn = _connect()
    return _conn


def _connect():
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ.get('DB_NAME', 'hustaq'),
        user=os.environ.get('DB_USER', 'hustaq'),
        password=os.environ.get('DB_PASS', 'hustaq_local'),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = True
    return conn


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description:
            return [dict(row) for row in cur.fetchall()]
        return []
