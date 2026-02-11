from contextlib import contextmanager

from database import get_db_connection


@contextmanager
def get_cursor(dictionary: bool = True):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()

