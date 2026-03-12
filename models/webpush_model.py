import hashlib

from models.common import get_cursor


def _endpoint_hash(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def upsert_subscription(
    user_email: str,
    endpoint: str,
    p256dh: str,
    auth: str,
):
    sql = """
        INSERT INTO web_push_subscriptions (
            userEmail,
            endpoint,
            endpointHash,
            p256dh,
            auth,
            isActive,
            lastUsedAt,
            createdAt,
            updatedAt
        )
        VALUES (%s, %s, %s, %s, %s, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON DUPLICATE KEY UPDATE
            userEmail = VALUES(userEmail),
            endpoint = VALUES(endpoint),
            p256dh = VALUES(p256dh),
            auth = VALUES(auth),
            isActive = 1,
            lastUsedAt = CURRENT_TIMESTAMP,
            updatedAt = CURRENT_TIMESTAMP
    """
    endpoint_hash = _endpoint_hash(endpoint)
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(sql, (user_email, endpoint, endpoint_hash, p256dh, auth))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def deactivate_subscription(user_email: str, endpoint: str):
    sql = """
        UPDATE web_push_subscriptions
        SET isActive = 0,
            updatedAt = CURRENT_TIMESTAMP
        WHERE userEmail = %s AND endpointHash = %s
    """
    endpoint_hash = _endpoint_hash(endpoint)
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(sql, (user_email, endpoint_hash))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise


def deactivate_endpoint(endpoint: str):
    sql = """
        UPDATE web_push_subscriptions
        SET isActive = 0,
            updatedAt = CURRENT_TIMESTAMP
        WHERE endpointHash = %s
    """
    endpoint_hash = _endpoint_hash(endpoint)
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(sql, (endpoint_hash,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def list_active_subscriptions(user_email: str):
    sql = """
        SELECT
            subscriptionId,
            userEmail,
            endpoint,
            p256dh,
            auth,
            isActive,
            lastUsedAt,
            createdAt,
            updatedAt
        FROM web_push_subscriptions
        WHERE userEmail = %s AND isActive = 1
        ORDER BY updatedAt DESC, subscriptionId DESC
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (user_email,))
        return cursor.fetchall()


def count_active_subscriptions(user_email: str) -> int:
    sql = """
        SELECT COUNT(*) AS count
        FROM web_push_subscriptions
        WHERE userEmail = %s AND isActive = 1
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (user_email,))
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"])


def touch_subscription(subscription_id: int):
    sql = """
        UPDATE web_push_subscriptions
        SET lastUsedAt = CURRENT_TIMESTAMP,
            updatedAt = CURRENT_TIMESTAMP
        WHERE subscriptionId = %s
    """
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(sql, (subscription_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
