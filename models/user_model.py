from models.common import get_cursor


def get_user_by_id(user_id: int):
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM users WHERE userId = %s", (user_id,))
        return cursor.fetchone()


def get_user_by_email(email: str):
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        return cursor.fetchone()


def count_users_by_nickname_excluding_user(nickname: str, user_id: int) -> int:
    with get_cursor() as (_, cursor):
        cursor.execute(
            "SELECT count(*) as count FROM users WHERE nickname = %s AND userId != %s AND is_deleted = 0",
            (nickname, user_id),
        )
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"])


def update_writer_display_name(user_email: str, nickname: str):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("UPDATE posts SET writer = %s WHERE writerEmail = %s", (nickname, user_email))
            cursor.execute("UPDATE comments SET writer = %s WHERE writerEmail = %s", (nickname, user_email))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def update_user_fields(user_id: int, fields: dict):
    if not fields:
        return

    updates = []
    values = []
    for key, value in fields.items():
        updates.append(f"{key} = %s")
        values.append(value)

    values.append(user_id)
    sql = f"UPDATE users SET {', '.join(updates)} WHERE userId = %s"

    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(sql, tuple(values))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def update_user_password(user_id: int, password_hash: str):
    update_user_fields(user_id, {"password": password_hash})


def hard_delete_user(user_id: int):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            # users 삭제 시 FK ON DELETE CASCADE로 sessions/posts/comments/likes 연쇄 삭제
            cursor.execute("DELETE FROM users WHERE userId = %s", (user_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
