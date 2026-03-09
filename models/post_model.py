from models.common import get_cursor

ALLOWED_POST_UPDATE_FIELDS = {
    "title",
    "content",
    "fileUrl",
}


def fetch_posts(offset: int, limit: int):
    sql = """
        SELECT
               p.postId,
               p.title,
               p.content,
               p.fileUrl,
               p.writer,
               p.viewCount,
               p.createdAt,
               p.updatedAt,
               u.userId as authorId,
               u.profileimage as authorProfileImage,
               (SELECT COUNT(*) FROM likes WHERE postId = p.postId) as likeCount,
               (SELECT COUNT(*) FROM comments WHERE postId = p.postId) as commentCount
        FROM posts p
        LEFT JOIN users u ON p.writerEmail = u.email
        ORDER BY p.createdAt DESC
        LIMIT %s OFFSET %s
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (limit, offset))
        return cursor.fetchall()


def count_posts() -> int:
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT count(*) as total FROM posts")
        row = cursor.fetchone() or {"total": 0}
        return int(row["total"])


def get_post_by_id(post_id: int):
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM posts WHERE postId = %s", (post_id,))
        return cursor.fetchone()


def get_post_detail(post_id: int):
    sql = """
        SELECT p.*, u.profileimage as authorProfileImage, u.userId as authorId
        FROM posts p
        LEFT JOIN users u ON p.writerEmail = u.email
        WHERE p.postId = %s
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (post_id,))
        return cursor.fetchone()


def increment_view_count(post_id: int):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("UPDATE posts SET viewCount = viewCount + 1 WHERE postId = %s", (post_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def count_likes(post_id: int) -> int:
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT count(*) as count FROM likes WHERE postId = %s", (post_id,))
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"])


def count_comments(post_id: int) -> int:
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT count(*) as count FROM comments WHERE postId = %s", (post_id,))
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"])


def fetch_likes(post_id: int):
    sql = """
        SELECT l.*, u.userId, u.nickname
        FROM likes l
        JOIN users u ON l.userEmail = u.email
        WHERE l.postId = %s
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (post_id,))
        return cursor.fetchall()


def create_post(title: str, content: str, file_url: str | None, writer: str, writer_email: str) -> int:
    sql = "INSERT INTO posts (title, content, fileUrl, writer, writerEmail) VALUES (%s, %s, %s, %s, %s)"
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(sql, (title, content, file_url, writer, writer_email))
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise


def _build_post_update_sql(post_id: int, fields: dict):
    invalid_fields = [key for key in fields if key not in ALLOWED_POST_UPDATE_FIELDS]
    if invalid_fields:
        raise ValueError("INVALID_UPDATE_FIELD")

    updates = []
    values = []
    for key, value in fields.items():
        updates.append(f"{key} = %s")
        values.append(value)
    values.append(post_id)

    sql = f"UPDATE posts SET {', '.join(updates)} WHERE postId = %s"
    return sql, tuple(values)


def update_post_fields(post_id: int, fields: dict):
    if not fields:
        return

    sql, values = _build_post_update_sql(post_id, fields)
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(sql, values)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def delete_post(post_id: int):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("DELETE FROM posts WHERE postId = %s", (post_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def exists_post(post_id: int) -> bool:
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT count(*) as count FROM posts WHERE postId = %s", (post_id,))
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"]) > 0


def has_user_liked(post_id: int, user_email: str) -> bool:
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT count(*) as count FROM likes WHERE postId = %s AND userEmail = %s", (post_id, user_email))
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"]) > 0


def add_like(post_id: int, user_email: str):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("INSERT INTO likes (postId, userEmail) VALUES (%s, %s)", (post_id, user_email))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def remove_like(post_id: int, user_email: str):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("DELETE FROM likes WHERE postId = %s AND userEmail = %s", (post_id, user_email))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
