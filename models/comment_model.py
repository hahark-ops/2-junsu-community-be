from models.common import get_cursor


def create_comment(post_id: int, content: str, writer: str, writer_email: str) -> int:
    sql = "INSERT INTO comments (postId, content, writer, writerEmail) VALUES (%s, %s, %s, %s)"
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(sql, (post_id, content, writer, writer_email))
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise


def fetch_comments(post_id: int):
    sql = """
        SELECT c.*, u.profileimage as authorProfileImage, u.userId as authorId,
               u.nickname as authorNickname, u.email as authorEmail
        FROM comments c
        LEFT JOIN users u ON c.writerEmail = u.email
        WHERE c.postId = %s
        ORDER BY c.createdAt ASC
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (post_id,))
        return cursor.fetchall()


def get_comment(comment_id: int, post_id: int):
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT * FROM comments WHERE commentId = %s AND postId = %s", (comment_id, post_id))
        return cursor.fetchone()


def update_comment_content(comment_id: int, content: str):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("UPDATE comments SET content = %s WHERE commentId = %s", (content, comment_id))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def delete_comment(comment_id: int):
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute("DELETE FROM comments WHERE commentId = %s", (comment_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise

