import os

import mysql.connector


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": _int_env("DB_PORT", 3306),
    "user": os.getenv("DB_USER", "community_user"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "community_db"),
    "charset": "utf8mb4",
    "use_unicode": True,
    "get_warnings": True,
}

POOL_NAME = os.getenv("DB_POOL_NAME", "community_pool")
POOL_SIZE = _int_env("DB_POOL_SIZE", 5)
db_pool = None
db_pool_init_error = None


def _create_db_pool():
    return mysql.connector.pooling.MySQLConnectionPool(
        pool_name=POOL_NAME,
        pool_size=POOL_SIZE,
        **DB_CONFIG,
    )


def ensure_db_pool() -> bool:
    global db_pool, db_pool_init_error

    if db_pool is not None:
        return True

    try:
        db_pool = _create_db_pool()
        db_pool_init_error = None
        print("MySQL connection pool initialized")
        return True
    except Exception as exc:
        db_pool = None
        db_pool_init_error = exc
        print(f"MySQL pool initialization failed: {exc}")
        return False


ensure_db_pool()


def get_db_connection():
    if db_pool or ensure_db_pool():
        return db_pool.get_connection()
    return mysql.connector.connect(**DB_CONFIG)


def is_db_ready() -> bool:
    if not ensure_db_pool():
        print(f"MySQL readiness check failed: pool unavailable ({db_pool_init_error})")
        return False

    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True
    except Exception as exc:
        print(f"MySQL readiness check failed: {exc}")
        return False
