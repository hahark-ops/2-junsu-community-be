from fastapi import Request
from database import get_db_connection
from utils import APIException

# 로그인한 사용자 찾기 (없으면 에러 401)
async def get_current_user(request: Request):
    # 1. 쿠키에서 세션 ID 가져오기
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        raise APIException(
            code="LOGIN_REQUIRED",
            message="로그인이 필요한 기능입니다.",
            status_code=401
        )

    # 2. DB 연결
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 3. 세션 테이블과 유저 테이블 조인 조회
        # 만료 시간 체크도 포함 (expires_at > NOW())
        query = """
            SELECT u.* 
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_id = %s 
            AND s.expires_at > NOW()
            AND u.is_deleted = FALSE
        """
        cursor.execute(query, (session_id,))
        user = cursor.fetchone()

        if not user:
             raise APIException(
                code="LOGIN_REQUIRED",
                message="로그인 세션이 만료되었거나 유효하지 않습니다.",
                status_code=401
            )
        
        # Pydantic 모델과 호환되도록 필드명 매핑 (user_id -> userId)
        # DB 컬럼이 id, nickname 등 소문자인데 백엔드 로직에서는 userId를 기대할 수 있음
        # 하지만 models/user.py를 보면 userId, email, nickname 등을 사용함.
        # DB의 id를 userId로 변환해주는 것이 안전함.
        
        user["userId"] = user["id"]
        # DB에서 profile_image_url 컬럼이 없음? 아 통합 파일 테이블인데..
        # 아까 스키마에서 users 테이블엔 profile_image 관련 컬럼이 없고 files 테이블에 있음.
        # 프로필 이미지도 같이 가져오려면?
        
        # 프로필 이미지 조회 (files 테이블)
        img_query = """
            SELECT file_url 
            FROM files 
            WHERE user_id = %s AND file_type = 'profile' AND deleted_at IS NULL
            ORDER BY created_at DESC 
            LIMIT 1
        """
        cursor.execute(img_query, (user["id"],))
        img = cursor.fetchone()
        
        user["profileimage"] = img["file_url"] if img else None
        
        return user

    finally:
        cursor.close()
        conn.close()