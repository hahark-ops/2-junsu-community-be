# database.py
import mysql.connector
from typing import Generator

# 1. MySQL 연결 설정
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "community_db",
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "autocommit": True  # 자동 커밋 활성화
}

def get_db_connection():
    """DB 연결 객체 반환"""
    return mysql.connector.connect(**DB_CONFIG)

def get_db_cursor(dictionary=True):
    """
    커서 생성 헬퍼
    dictionary=True: 결과를 딕셔너리로 반환 (ex: {"id": 1, "email": "..."})
    """
    conn = get_db_connection()
    return conn, conn.cursor(dictionary=dictionary)

# ==========================================
# 기존 Fake 데이터 (주석 처리 또는 백업)
# ==========================================

# fake_users = [...]
# fake_posts = []
# fake_comments = []
# fake_sessions = {}
# fake_likes = []