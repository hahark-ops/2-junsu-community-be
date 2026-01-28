import os
import uuid
import shutil
from fastapi import UploadFile
from database import get_db_connection
from utils import APIException
from datetime import datetime

UPLOAD_DIR = "uploads"
BASE_URL = "http://localhost:8000" # 실제 배포 시에는 환경변수로 관리 필요

# 업로드 디렉토리 확인 및 생성
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

async def upload_file(file: UploadFile, file_type: str, user: dict | None):
    # 1. 파일 검증 (확장자, 크기 등)
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise APIException(code="INVALID_FILE_TYPE", message="이미지 파일만 업로드 가능합니다.", status_code=400)
    
    # 2. 고유 파일명 생성
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # 3. 파일 저장
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        print(f"File Save Error: {e}")
        raise APIException(code="FILE_SAVE_ERROR", message="파일 저장 중 오류가 발생했습니다.", status_code=500)
    
    # 4. 파일 크기 확인
    file_size = os.path.getsize(file_path)
    file_url = f"{BASE_URL}/{UPLOAD_DIR}/{unique_filename}"
    
    # 5. DB 저장 (files 테이블)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # post_id는 아직 모름(NULL), user_id는 로그인한 유저
        query = """
            INSERT INTO files (file_type, user_id, file_url, file_name, file_size)
            VALUES (%s, %s, %s, %s, %s)
        """
        user_id = user["userId"] if user else None
        cursor.execute(query, (file_type, user_id, file_url, file.filename, file_size))
        new_file_id = cursor.lastrowid
        conn.commit()
        
        created_at_query = "SELECT created_at FROM files WHERE id = %s"
        cursor.execute(created_at_query, (new_file_id,))
        created_at = cursor.fetchone()["created_at"]
        
        return {
            "fileId": new_file_id,
            "fileUrl": file_url,
            "fileName": file.filename,
            "fileSize": file_size,
            "fileType": file_type,
            "createdAt": created_at
        }
    except Exception as e:
        conn.rollback()
        # DB 저장 실패 시 저장된 파일도 삭제하는 것이 좋음
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"DB Insert Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="파일 정보 저장 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()
