import mysql.connector
from mysql.connector import pooling
import os

# 데이터베이스 설정
# 실제 배포 시에는 환경변수나 보안 파일로 관리하는 것이 좋습니다.
DB_CONFIG = {
    "host": "localhost",          # EC2 내부 MySQL
    "user": "community_user",     # 전용 DB 사용자
    "password": "CommunityUser123!", # 전용 DB 비밀번호
    "database": "community_db",   # 데이터베이스 이름
    "charset": "utf8mb4",
    "use_unicode": True,
    "get_warnings": True,
}

# 커넥션 풀 생성 (성능 향상)
try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="mypool",
        pool_size=5,
        **DB_CONFIG
    )
    print("MySQL 커넥션 풀 생성 완료")
except Exception as e:
    print(f"MySQL 연결 실패: {e}")
    db_pool = None

def get_db_connection():
    try:
        if db_pool:
            return db_pool.get_connection()
        else:
            # 풀 생성이 안 됐을 경우 직접 연결 시도
            return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        print(f"DB 커넥션 가져오기 실패: {e}")
        raise e