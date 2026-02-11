from models import user_model
from utils import APIException, hash_password, validate_nickname, validate_nickname_length, validate_password, verify_password

async def get_my_info(user: dict):
    """
    내 정보 조회 (세션 기반)
    """
    if user.get("is_deleted"):
        raise APIException(code="FORBIDDEN", message="접근이 거부되었습니다.", status_code=403)

    return {
        "code": "GET_MY_INFO_SUCCESS",
        "message": "내 정보 조회 성공",
        "data": {
            "userId": user["userId"],
            "email": user["email"],
            "nickname": user["nickname"],
            "profileImage": user.get("profileimage")
        }
    }

async def get_user_by_id(user_id: int):
    """
    특정 사용자 정보 조회 (ID 기반)
    """
    matched_user = user_model.get_user_by_id(user_id)
    if not matched_user:
        raise APIException(code="USER_NOT_FOUND", message="해당 사용자를 찾을 수 없습니다.", status_code=404)
        
    if matched_user.get("is_deleted"):
        raise APIException(code="FORBIDDEN", message="접근이 거부되었습니다.", status_code=403)

    return {
        "code": "GET_USER_SUCCESS",
        "message": "사용자 정보 조회 성공",
        "data": {
            "userId": matched_user["userId"],
            "email": matched_user["email"],
            "nickname": matched_user["nickname"],
            "profileImage": matched_user.get("profileimage")
        }
    }

# ==========================================
# 3. 회원정보 수정
# ==========================================
async def update_user(user_id: int, update_data: dict, current_user: dict):
    if current_user["userId"] != user_id:
        raise APIException(code="PERMISSION_DENIED", message="본인의 정보만 수정할 수 있습니다.", status_code=403)
    
    target_user = user_model.get_user_by_id(user_id)
    if not target_user:
        raise APIException(code="USER_NOT_FOUND", message="사용자를 찾을 수 없습니다.", status_code=404)

    fields_to_update = {}
    
    new_nickname = update_data.get("nickname")
    if new_nickname:
        if not validate_nickname(new_nickname):
            raise APIException(code="INVALID_NICKNAME_FORMAT", message="닉네임에 공백이나 특수문자를 포함할 수 없습니다.", status_code=400)
        if not validate_nickname_length(new_nickname):
            raise APIException(code="NICKNAME_TOO_LONG", message="닉네임은 최대 10자까지만 가능합니다.", status_code=400)
        
        if user_model.count_users_by_nickname_excluding_user(new_nickname, user_id) > 0:
            raise APIException(code="ALREADY_EXIST_NICKNAME", message="이미 사용 중인 닉네임입니다.", status_code=409)
        
        fields_to_update["nickname"] = new_nickname
        user_model.update_writer_display_name(target_user["email"], new_nickname)

    if "profileImage" in update_data:
        fields_to_update["profileimage"] = update_data.get("profileImage")
    elif "profileimage" in update_data:
        fields_to_update["profileimage"] = update_data.get("profileimage")

    if fields_to_update:
        user_model.update_user_fields(user_id, fields_to_update)
    
    return {
        "code": "UPDATE_USER_SUCCESS",
        "message": "회원 정보가 성공적으로 수정되었습니다.",
        "data": None
    }

# ==========================================
# 4. 비밀번호 변경
# ==========================================
async def change_password(user_id: int, password_data: dict, current_user: dict):
    if current_user["userId"] != user_id:
        raise APIException(code="PERMISSION_DENIED", message="본인의 비밀번호만 변경할 수 있습니다.", status_code=403)
    
    current_pw = password_data.get("currentPassword")
    new_pw = password_data.get("newPassword")
    if not current_pw or not new_pw:
        raise APIException(code="MISSING_PASSWORD_FIELDS", message="현재 비밀번호와 새 비밀번호를 모두 입력해주세요.", status_code=400)
    
    target_user = user_model.get_user_by_id(user_id)
    if not target_user:
        raise APIException(code="USER_NOT_FOUND", message="사용자를 찾을 수 없습니다.", status_code=404)
    
    if not verify_password(current_pw, target_user.get("password")):
        raise APIException(code="INVALID_CURRENT_PASSWORD", message="현재 사용 중인 비밀번호가 일치하지 않습니다.", status_code=401)
    
    if not validate_password(new_pw):
        raise APIException(code="WEAK_PASSWORD", message="비밀번호는 영문, 숫자, 특수문자를 포함하여 8~20자여야 합니다.", status_code=400)
    
    user_model.update_user_password(user_id, hash_password(new_pw))
    
    return {
        "code": "CHANGE_PASSWORD_SUCCESS",
        "message": "비밀번호가 성공적으로 변경되었습니다.",
        "data": None
    }

# ==========================================
# 5. 회원 탈퇴 (Soft Delete)
# ==========================================
async def delete_user(current_user: dict):
    user_model.soft_delete_user_and_sessions(current_user["userId"], current_user["email"])
    
    return {
        "code": "DELETE_USER_SUCCESS",
        "message": "회원 탈퇴가 안전하게 처리되었습니다. 그동안 이용해주셔서 감사합니다.",
        "data": None
    }
