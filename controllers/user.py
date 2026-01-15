# controllers/user.py

from fastapi import status
from fastapi.responses import JSONResponse
from database import fake_users
from utils import validate_email # 유틸 도구 가져오기

async def get_user_info(email: str):
    """
    사용자 정보 조회 로직
    """
    
    # 1. [400] 필수값 누락 체크 (설계도: REQUIRED_FIELDS_MISSING)
    if not email:
        return JSONResponse(status_code=400, content={
            "code": "REQUIRED_FIELDS_MISSING",
            "message": "이메일 정보가 누락되었습니다.",
            "data": None
        })

    # 2. [400] 이메일 형식 검사 (설계도: INVALID_EMAIL_FORMAT)
    if not validate_email(email):
        return JSONResponse(status_code=400, content={
            "code": "INVALID_EMAIL_FORMAT",
            "message": "유효하지 않은 이메일 형식입니다.",
            "data": None
        })

    # 3. 사용자 찾기
    matched_user = None
    for user in fake_users:
        if user["email"] == email:
            matched_user = user
            break
    
    # 4. [404] 사용자 없음 (설계도: USER_NOT_FOUND)
    if matched_user is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "code": "USER_NOT_FOUND",
                "message": "해당 사용자를 찾을 수 없습니다.",
                "data": None
            }
        )
        
    # (참고) 5. [403] 탈퇴한 회원 접근 금지
    if matched_user.get("is_deleted") == True:
        return JSONResponse(status_code=403, content={"code": "FORBIDDEN", ...})

    # 6. 성공 응답
    return {
        "code": "GET_USER_SUCCESS",
        "message": "사용자 정보 조회 성공",
        "data": {
            "email": matched_user["email"],
            "nickname": matched_user["nickname"],
            "profileimage": matched_user.get("profileimage")
        }
    }