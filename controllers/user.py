# controllers/user.py

from database import fake_users, fake_sessions
from utils import APIException, validate_nickname, validate_nickname_length, validate_password

async def get_my_info(user: dict):
    """
    내 정보 조회 (세션 기반)
    """
    # 5. [403] 탈퇴한 회원 접근 금지 (get_current_user에서 처리되지 않았다면)
    if user.get("is_deleted") == True:
        raise APIException(code="FORBIDDEN", message="접근이 거부되었습니다.", status_code=403)

    return {
        "code": "GET_MY_INFO_SUCCESS",
        "message": "내 정보 조회 성공",
        "data": {
            "userId": user["userId"],
            "email": user["email"],
            "nickname": user["nickname"],
            "profileimage": user.get("profileimage")
        }
    }

async def get_user_by_id(user_id: int):
    """
    특정 사용자 정보 조회 (ID 기반)
    """
    # 3. 사용자 찾기
    matched_user = None
    for user in fake_users:
        if user["userId"] == user_id:
            matched_user = user
            break
    
    # 4. [404] 사용자 없음 (설계도: USER_NOT_FOUND)
    if matched_user is None:
        raise APIException(code="USER_NOT_FOUND", message="해당 사용자를 찾을 수 없습니다.", status_code=404)
        
    # (참고) 5. [403] 탈퇴한 회원 접근 금지
    if matched_user.get("is_deleted") == True:
        raise APIException(code="FORBIDDEN", message="접근이 거부되었습니다.", status_code=403)

    # 6. 성공 응답
    return {
        "code": "GET_USER_SUCCESS",
        "message": "사용자 정보 조회 성공",
        "data": {
            "userId": matched_user["userId"],
            "email": matched_user["email"],
            "nickname": matched_user["nickname"],
            "profileimage": matched_user.get("profileimage")
        }
    }

# ==========================================
# 3. 회원정보 수정
# ==========================================
async def update_user(user_id: int, update_data: dict, current_user: dict):
    # 1. 권한 체크: 본인만 수정 가능
    if current_user["userId"] != user_id:
        raise APIException(code="PERMISSION_DENIED", message="본인의 정보만 수정할 수 있습니다.", status_code=403)
    
    # 2. 사용자 찾기
    target_user = None
    for user in fake_users:
        if user["userId"] == user_id:
            target_user = user
            break
    
    if target_user is None:
        raise APIException(code="USER_NOT_FOUND", message="사용자를 찾을 수 없습니다.", status_code=404)
    
    # 3. 닉네임 수정 시 검증
    new_nickname = update_data.get("nickname")
    if new_nickname:
        # 3-1. 형식 검사
        if not validate_nickname(new_nickname):
            raise APIException(code="INVALID_NICKNAME_FORMAT", message="닉네임에 공백이나 특수문자를 포함할 수 없습니다.", status_code=400)
        # 3-2. 길이 검사
        if not validate_nickname_length(new_nickname):
            raise APIException(code="NICKNAME_TOO_LONG", message="닉네임은 최대 10자까지만 가능합니다.", status_code=400)
        # 3-3. 중복 검사
        for user in fake_users:
            if user["nickname"] == new_nickname and user["userId"] != user_id:
                raise APIException(code="ALREADY_EXIST_NICKNAME", message="이미 사용 중인 닉네임입니다.", status_code=409)
        target_user["nickname"] = new_nickname
    
    # 4. 프로필 이미지 수정
    if "profileimage" in update_data:
        target_user["profileimage"] = update_data["profileimage"]
    
    return {
        "code": "UPDATE_USER_SUCCESS",
        "message": "회원 정보가 성공적으로 수정되었습니다.",
        "data": None
    }

# ==========================================
# 4. 비밀번호 변경
# ==========================================
async def change_password(user_id: int, password_data: dict, current_user: dict):
    # 1. 권한 체크
    if current_user["userId"] != user_id:
        raise APIException(code="PERMISSION_DENIED", message="본인의 비밀번호만 변경할 수 있습니다.", status_code=403)
    
    # 2. 필수값 체크
    current_pw = password_data.get("currentPassword")
    new_pw = password_data.get("newPassword")
    if not current_pw or not new_pw:
        raise APIException(code="MISSING_PASSWORD_FIELDS", message="현재 비밀번호와 새 비밀번호를 모두 입력해주세요.", status_code=400)
    
    # 3. 사용자 찾기
    target_user = None
    for user in fake_users:
        if user["userId"] == user_id:
            target_user = user
            break
    
    if target_user is None:
        raise APIException(code="USER_NOT_FOUND", message="사용자를 찾을 수 없습니다.", status_code=404)
    
    # 4. 현재 비밀번호 확인
    if target_user["password"] != current_pw:
        raise APIException(code="INVALID_CURRENT_PASSWORD", message="현재 사용 중인 비밀번호가 일치하지 않습니다.", status_code=401)
    
    # 5. 새 비밀번호 강도 검사
    if not validate_password(new_pw):
        raise APIException(code="WEAK_PASSWORD", message="비밀번호는 영문, 숫자, 특수문자를 포함하여 8~20자여야 합니다.", status_code=400)
    
    # 6. 비밀번호 변경
    target_user["password"] = new_pw
    
    return {
        "code": "CHANGE_PASSWORD_SUCCESS",
        "message": "비밀번호가 성공적으로 변경되었습니다.",
        "data": None
    }

# ==========================================
# 5. 회원 탈퇴 (Soft Delete)
# ==========================================
async def delete_user(current_user: dict):
    # 1. 사용자 찾기
    target_user = None
    for user in fake_users:
        if user["userId"] == current_user["userId"]:
            target_user = user
            break
    
    if target_user is None:
        raise APIException(code="USER_NOT_FOUND", message="이미 존재하지 않거나 탈퇴 처리된 계정입니다.", status_code=404)
    
    # 2. Soft Delete 처리
    target_user["is_deleted"] = True
    
    # 3. 해당 유저의 세션 모두 삭제
    sessions_to_delete = [sid for sid, email in fake_sessions.items() if email == target_user["email"]]
    for sid in sessions_to_delete:
        del fake_sessions[sid]
    
    return {
        "code": "DELETE_USER_SUCCESS",
        "message": "회원 탈퇴가 안전하게 처리되었습니다. 그동안 이용해주셔서 감사합니다.",
        "data": None
    }