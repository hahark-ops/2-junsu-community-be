from models.common import get_cursor

ALLOWED_USER_UPDATE_FIELDS = {
    "nickname",
    "profileimage",
    "password",
}


def get_user_by_id(user_id: int):
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM users WHERE userId = %s AND is_deleted = 0", (user_id,))
        return cursor.fetchone()


def get_user_by_email(email: str):
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM users WHERE email = %s AND is_deleted = 0", (email,))
        return cursor.fetchone()


def count_users_by_nickname_excluding_user(nickname: str, user_id: int) -> int:
    with get_cursor() as (_, cursor):
        cursor.execute(
            "SELECT count(*) as count FROM users WHERE nickname = %s AND userId != %s",
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


def _build_user_update_sql(user_id: int, fields: dict):
    invalid_fields = [key for key in fields if key not in ALLOWED_USER_UPDATE_FIELDS]
    if invalid_fields:
        raise ValueError("INVALID_UPDATE_FIELD")

    updates = []
    values = []
    for key, value in fields.items():
        updates.append(f"{key} = %s")
        values.append(value)
    values.append(user_id)
    sql = f"UPDATE users SET {', '.join(updates)} WHERE userId = %s"
    return sql, tuple(values)


def update_user_fields(user_id: int, fields: dict):
    if not fields:
        return

    sql, values = _build_user_update_sql(user_id, fields)

    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(sql, values)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def update_user_profile_with_writer_sync(user_id: int, user_email: str, fields: dict):
    if not fields:
        return

    sql, values = _build_user_update_sql(user_id, fields)

    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            if "nickname" in fields:
                new_nickname = fields["nickname"]
                cursor.execute("UPDATE posts SET writer = %s WHERE writerEmail = %s", (new_nickname, user_email))
                cursor.execute("UPDATE comments SET writer = %s WHERE writerEmail = %s", (new_nickname, user_email))

            cursor.execute(sql, values)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def update_user_password(user_id: int, password_hash: str):
    update_user_fields(user_id, {"password": password_hash})


def soft_delete_user(user_id: int, user_email: str):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("UPDATE users SET is_deleted = 1 WHERE userId = %s", (user_id,))
            cursor.execute("DELETE FROM sessions WHERE userEmail = %s", (user_email,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
