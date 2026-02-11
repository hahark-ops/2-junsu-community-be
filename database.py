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

try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name=POOL_NAME,
        pool_size=POOL_SIZE,
        **DB_CONFIG,
    )
    print("MySQL connection pool initialized")
except Exception as e:
    print(f"MySQL pool initialization failed: {e}")
    db_pool = None


def get_db_connection():
    if db_pool:
        return db_pool.get_connection()
    return mysql.connector.connect(**DB_CONFIG)
