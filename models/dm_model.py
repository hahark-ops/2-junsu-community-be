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
            ) AS lastMessageAt,
            (
                SELECT COUNT(*)
                FROM dm_messages um
                WHERE um.roomId = r.roomId
                  AND um.senderEmail <> %s
                  AND um.messageId > COALESCE(
                      (
                          SELECT rr.lastReadMessageId
                          FROM dm_room_reads rr
                          WHERE rr.roomId = r.roomId AND rr.userEmail = %s
                          LIMIT 1
                      ),
                      0
                  )
            ) AS unreadCount
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
        cursor.execute(sql, (user_email, user_email, user_email, user_email, user_email, user_email, user_email))
        return cursor.fetchall()


def list_messages(room_id: int, limit: int = 50, before_message_id: int | None = None):
    safe_limit = max(1, min(int(limit), 100))
    base_where = "roomId = %s"
    params: list[int] = [room_id]
    if before_message_id is not None:
        base_where += " AND messageId < %s"
        params.append(int(before_message_id))

    sql = f"""
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
            WHERE {base_where}
            ORDER BY messageId DESC
            LIMIT %s
        ) m
        JOIN users u ON u.email = m.senderEmail
        ORDER BY m.messageId ASC
    """

    has_more_sql = f"""
        SELECT 1
        FROM dm_messages
        WHERE {base_where}
        ORDER BY messageId DESC
        LIMIT %s, 1
    """

    with get_cursor() as (_, cursor):
        cursor.execute(sql, tuple(params + [safe_limit]))
        rows = cursor.fetchall()

        cursor.execute(has_more_sql, tuple(params + [safe_limit]))
        has_more = cursor.fetchone() is not None
        oldest_message_id = rows[0]["messageId"] if rows else None
        return rows, has_more, oldest_message_id


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


def get_room_last_message_id(room_id: int):
    sql = """
        SELECT messageId
        FROM dm_messages
        WHERE roomId = %s
        ORDER BY messageId DESC
        LIMIT 1
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (room_id,))
        row = cursor.fetchone()
        return row["messageId"] if row else None


def get_partner_last_read_message_id(room_id: int, user_email: str):
    sql = """
        SELECT lastReadMessageId
        FROM dm_room_reads
        WHERE roomId = %s AND userEmail <> %s
        ORDER BY lastReadAt DESC
        LIMIT 1
    """
    with get_cursor() as (_, cursor):
        cursor.execute(sql, (room_id, user_email))
        row = cursor.fetchone()
        return row["lastReadMessageId"] if row else None


def mark_room_as_read(room_id: int, user_email: str, message_id: int | None):
    if not message_id:
        return False

    select_sql = """
        SELECT lastReadMessageId
        FROM dm_room_reads
        WHERE roomId = %s AND userEmail = %s
    """
    insert_sql = """
        INSERT INTO dm_room_reads (roomId, userEmail, lastReadMessageId, lastReadAt)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
    """
    update_sql = """
        UPDATE dm_room_reads
        SET lastReadMessageId = %s, lastReadAt = CURRENT_TIMESTAMP
        WHERE roomId = %s AND userEmail = %s
    """

    with get_cursor() as (conn, cursor):
        try:
            cursor.execute(select_sql, (room_id, user_email))
            row = cursor.fetchone()

            if not row:
                cursor.execute(insert_sql, (room_id, user_email, message_id))
                conn.commit()
                return True

            last_read_message_id = row.get("lastReadMessageId")
            if last_read_message_id is not None and int(last_read_message_id) >= int(message_id):
                return False

            cursor.execute(update_sql, (message_id, room_id, user_email))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
