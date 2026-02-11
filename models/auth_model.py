from models.common import get_cursor


def count_users_by_email(email: str) -> int:
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT count(*) as count FROM users WHERE email = %s AND is_deleted = 0", (email,))
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"])


def count_users_by_nickname(nickname: str) -> int:
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT count(*) as count FROM users WHERE nickname = %s AND is_deleted = 0", (nickname,))
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"])


def purge_deleted_users_for_signup(email: str, nickname: str):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(
                "SELECT userId FROM users WHERE is_deleted = 1 AND (email = %s OR nickname = %s)",
                (email, nickname),
            )
            rows = cursor.fetchall()
            user_ids = [row[0] for row in rows]
            if user_ids:
                placeholders = ", ".join(["%s"] * len(user_ids))
                cursor.execute(
                    f"DELETE FROM users WHERE is_deleted = 1 AND userId IN ({placeholders})",
                    tuple(user_ids),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


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
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        return cursor.fetchone()


def create_session(session_id: str, user_email: str):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("INSERT INTO sessions (sessionId, userEmail) VALUES (%s, %s)", (session_id, user_email))
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


def get_user_email_by_session_id(session_id: str):
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT userEmail FROM sessions WHERE sessionId = %s", (session_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return row["userEmail"]
