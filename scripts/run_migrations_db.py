#!/usr/bin/env python3
import os
import time
from pathlib import Path

import mysql.connector


ROOT_DIR = Path(__file__).resolve().parents[1]
MIGRATION_FILES = [
    ROOT_DIR / "schema.sql",
    ROOT_DIR / "scripts" / "migrations" / "20260226_add_session_expiry.sql",
    ROOT_DIR / "scripts" / "migrations" / "20260309_ensure_like_unique.sql",
    ROOT_DIR / "scripts" / "migrations" / "20260309_add_dm_tables.sql",
    ROOT_DIR / "scripts" / "migrations" / "20260309_add_dm_room_reads.sql",
    ROOT_DIR / "scripts" / "migrations" / "20260312_add_dm_client_message_id.sql",
    ROOT_DIR / "scripts" / "migrations" / "20260312_add_dm_realtime_published.sql",
]


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} 환경변수가 필요합니다.")
    return value


def connect():
    host = require_env("DB_HOST")
    port = int(os.environ.get("DB_PORT", "3306"))
    user = require_env("DB_USER")
    password = require_env("DB_PASSWORD")
    database = require_env("DB_NAME")

    last_error = None
    for _ in range(60):
        try:
            return mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                autocommit=False,
                use_pure=True,
            )
        except mysql.connector.Error as exc:
            last_error = exc
            time.sleep(2)

    raise RuntimeError(f"DB 연결 실패: {last_error}")


def split_sql_statements(sql: str) -> list[str]:
    statements = []
    buffer = []
    in_single = False
    in_double = False
    i = 0

    while i < len(sql):
        char = sql[i]
        next_char = sql[i + 1] if i + 1 < len(sql) else ""

        if not in_single and not in_double and char == "-" and next_char == "-":
            while i < len(sql) and sql[i] != "\n":
                i += 1
            continue

        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double

        if char == ";" and not in_single and not in_double:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
        else:
            buffer.append(char)

        i += 1

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)

    return statements


def apply_sql_file(connection, sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql)
    cursor = connection.cursor()
    try:
        for statement in statements:
            cursor.execute(statement)
            if cursor.with_rows:
                cursor.fetchall()
            while cursor.nextset():
                if cursor.with_rows:
                    cursor.fetchall()
                pass
    finally:
        try:
            cursor.close()
        except mysql.connector.Error:
            pass


def main() -> None:
    for migration_file in MIGRATION_FILES:
        if not migration_file.exists():
            raise RuntimeError(f"마이그레이션 파일이 없습니다: {migration_file}")

    connection = connect()
    try:
        for migration_file in MIGRATION_FILES:
            apply_sql_file(connection, migration_file)
            connection.commit()
            print(f"[PASS] applied {migration_file.name}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
