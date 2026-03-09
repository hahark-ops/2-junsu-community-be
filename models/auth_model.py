from models.common import get_cursor


def count_users_by_email(email: str) -> int:
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT count(*) as count FROM users WHERE email = %s", (email,))
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"])


def count_users_by_nickname(nickname: str) -> int:
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT count(*) as count FROM users WHERE nickname = %s", (nickname,))
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"])


def create_user(email: str, password_hash: str, nickname: str, profile_image: str | None):
    with get_cursor() as (conn, cursor):
        try:
            sql = "INSERT INTO users (email, password, nickname, profileimage) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (email, password_hash, nickname, profile_image))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def get_user_by_email(email: str):
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM users WHERE email = %s AND is_deleted = 0", (email,))
        return cursor.fetchone()


def create_session(session_id: str, user_email: str):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(
                "INSERT INTO sessions (sessionId, userEmail, expiresAt) VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 7 DAY))",
                (session_id, user_email),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def delete_session(session_id: str):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("DELETE FROM sessions WHERE sessionId = %s", (session_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def purge_expired_sessions(limit: int = 500):
    safe_limit = max(1, min(int(limit), 5000))
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("DELETE FROM sessions WHERE expiresAt <= NOW() LIMIT %s", (safe_limit,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def get_user_email_by_session_id(session_id: str):
    try:
        purge_expired_sessions()
    except Exception as exc:
        print(f"Expired session purge failed: {exc}")

    with get_cursor() as (_, cursor):
        cursor.execute(
            "SELECT userEmail FROM sessions WHERE sessionId = %s AND expiresAt > NOW()",
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return row["userEmail"]
