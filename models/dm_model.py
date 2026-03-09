from models.common import get_cursor


def normalize_room_participants(email_a: str, email_b: str) -> tuple[str, str]:
    return tuple(sorted((email_a, email_b)))


def get_room_by_id(room_id: int):
    sql = """
        SELECT roomId, userAEmail, userBEmail, createdAt, updatedAt
        FROM dm_rooms
        WHERE roomId = %s
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (room_id,))
        return cursor.fetchone()


def get_room_by_participants(email_a: str, email_b: str):
    normalized_a, normalized_b = normalize_room_participants(email_a, email_b)
    sql = """
        SELECT roomId, userAEmail, userBEmail, createdAt, updatedAt
        FROM dm_rooms
        WHERE userAEmail = %s AND userBEmail = %s
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (normalized_a, normalized_b))
        return cursor.fetchone()


def create_room(email_a: str, email_b: str) -> int:
    normalized_a, normalized_b = normalize_room_participants(email_a, email_b)
    sql = "INSERT INTO dm_rooms (userAEmail, userBEmail) VALUES (%s, %s)"
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(sql, (normalized_a, normalized_b))
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise


def list_rooms_for_user(user_email: str):
    sql = """
        SELECT
            r.roomId,
            r.createdAt,
            r.updatedAt,
            CASE
                WHEN r.userAEmail = %s THEN partner_b.userId
                ELSE partner_a.userId
            END AS partnerUserId,
            CASE
                WHEN r.userAEmail = %s THEN partner_b.nickname
                ELSE partner_a.nickname
            END AS partnerNickname,
            CASE
                WHEN r.userAEmail = %s THEN partner_b.profileimage
                ELSE partner_a.profileimage
            END AS partnerProfileImage,
            (
                SELECT m.content
                FROM dm_messages m
                WHERE m.roomId = r.roomId
                ORDER BY m.messageId DESC
                LIMIT 1
            ) AS lastMessage,
            (
                SELECT m.createdAt
                FROM dm_messages m
                WHERE m.roomId = r.roomId
                ORDER BY m.messageId DESC
                LIMIT 1
            ) AS lastMessageAt
        FROM dm_rooms r
        JOIN users partner_a ON partner_a.email = r.userAEmail
        JOIN users partner_b ON partner_b.email = r.userBEmail
        WHERE r.userAEmail = %s OR r.userBEmail = %s
        ORDER BY COALESCE(
            (
                SELECT m.createdAt
                FROM dm_messages m
                WHERE m.roomId = r.roomId
                ORDER BY m.messageId DESC
                LIMIT 1
            ),
            r.updatedAt
        ) DESC, r.roomId DESC
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (user_email, user_email, user_email, user_email, user_email))
        return cursor.fetchall()


def list_messages(room_id: int, limit: int = 50):
    safe_limit = max(1, min(int(limit), 100))
    sql = """
        SELECT
            m.messageId,
            m.roomId,
            m.content,
            m.createdAt,
            u.userId AS senderUserId,
            u.nickname AS senderNickname,
            u.profileimage AS senderProfileImage,
            u.email AS senderEmail
        FROM (
            SELECT *
            FROM dm_messages
            WHERE roomId = %s
            ORDER BY messageId DESC
            LIMIT %s
        ) m
        JOIN users u ON u.email = m.senderEmail
        ORDER BY m.messageId ASC
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (room_id, safe_limit))
        return cursor.fetchall()


def create_message(room_id: int, sender_email: str, content: str):
    insert_sql = "INSERT INTO dm_messages (roomId, senderEmail, content) VALUES (%s, %s, %s)"
    update_sql = "UPDATE dm_rooms SET updatedAt = CURRENT_TIMESTAMP WHERE roomId = %s"
    with get_cursor(dictionary=False) as (conn, cursor):
        try:
            cursor.execute(insert_sql, (room_id, sender_email, content))
            message_id = cursor.lastrowid
            cursor.execute(update_sql, (room_id,))
            conn.commit()
            return message_id
        except Exception:
            conn.rollback()
            raise


def get_message_by_id(message_id: int):
    sql = """
        SELECT
            m.messageId,
            m.roomId,
            m.content,
            m.createdAt,
            u.userId AS senderUserId,
            u.nickname AS senderNickname,
            u.profileimage AS senderProfileImage,
            u.email AS senderEmail
        FROM dm_messages m
        JOIN users u ON u.email = m.senderEmail
        WHERE m.messageId = %s
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (message_id,))
        return cursor.fetchone()


def is_room_participant(room_id: int, user_email: str) -> bool:
    sql = """
        SELECT COUNT(*) AS count
        FROM dm_rooms
        WHERE roomId = %s
          AND (userAEmail = %s OR userBEmail = %s)
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (room_id, user_email, user_email))
        row = cursor.fetchone() or {"count": 0}
        return int(row["count"]) > 0
