# controllers/user.py

from database import get_db_connection
from utils import APIException, validate_nickname, validate_nickname_length, validate_password

async def get_my_info(user: dict):
    """
    내 정보 조회 (세션 기반)
    user 인자는 dependencies.get_current_user에서 이미 DB 조회된 결과임
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
            "profileImage": user.get("profileImage")
        }
    }

async def get_user_by_id(user_id: int):
    """
    특정 사용자 정보 조회 (ID 기반)
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 3. 사용자 찾기 (is_deleted 여부 상관없이 조회하되, 로직상 거를지 결정)
        # 보통 userId 기반 조회는 프로필 보기 등이므로, 탈퇴회원도 "알 수 없음" 등으로 표시하거나 404
        
        query = "SELECT * FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        matched_user = cursor.fetchone()

        # 4. [404] 사용자 없음
        if matched_user is None:
            raise APIException(code="USER_NOT_FOUND", message="해당 사용자를 찾을 수 없습니다.", status_code=404)
        
        # 5. [403] 탈퇴한 회원 접근 금지 (선택 사항)
        if matched_user["is_deleted"]:
            raise APIException(code="FORBIDDEN", message="접근이 거부되었습니다.", status_code=403)

        # 프로필 이미지 가져오기
        img_query = """
            SELECT file_url FROM files 
            WHERE user_id = %s AND file_type = 'profile' AND deleted_at IS NULL
            ORDER BY created_at DESC LIMIT 1
        """
        cursor.execute(img_query, (user_id,))
        img = cursor.fetchone()
        
        profileimage = img["file_url"] if img else None

        # 6. 성공 응답
        return {
            "code": "GET_USER_SUCCESS",
            "message": "사용자 정보 조회 성공",
            "data": {
                "userId": matched_user["id"],
                "email": matched_user["email"],
                "nickname": matched_user["nickname"],
                "profileImage": profileimage
            }
        }
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 3. 회원정보 수정
# ==========================================
async def update_user(user_id: int, update_data: dict, current_user: dict):
    # 1. 권한 체크: 본인만 수정 가능
    if current_user["userId"] != user_id:
        raise APIException(code="PERMISSION_DENIED", message="본인의 정보만 수정할 수 있습니다.", status_code=403)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 3. 닉네임 수정 시 검증
        new_nickname = update_data.get("nickname")
        if new_nickname:
            # 3-1. 형식 검사
            if not validate_nickname(new_nickname):
                raise APIException(code="INVALID_NICKNAME_FORMAT", message="닉네임에 공백이나 특수문자를 포함할 수 없습니다.", status_code=400)
            # 3-2. 길이 검사
            if not validate_nickname_length(new_nickname):
                raise APIException(code="NICKNAME_TOO_LONG", message="닉네임은 최대 10자까지만 가능합니다.", status_code=400)
            
            # 3-3. 중복 검사 (자기 자신 제외)
            dup_query = "SELECT id FROM users WHERE nickname = %s AND id != %s"
            cursor.execute(dup_query, (new_nickname, user_id))
            if cursor.fetchone():
                raise APIException(code="ALREADY_EXIST_NICKNAME", message="이미 사용 중인 닉네임입니다.", status_code=409)
            
            update_query = "UPDATE users SET nickname = %s WHERE id = %s"
            cursor.execute(update_query, (new_nickname, user_id))
        
        # 4. 프로필 이미지 수정 (새 파일 insert)
        # file_url만 업데이트한다고 가정 (기존 파일 삭제 처리 등은 복잡하므로 단순 insert, 최신꺼 select)
        if "profileImage" in update_data and update_data["profileImage"]:
            # 기존 프로필 이미지들 soft delete 처리
            del_img_query = "UPDATE files SET deleted_at = NOW() WHERE user_id = %s AND file_type = 'profile'"
            cursor.execute(del_img_query, (user_id,))
            
            # 새 이미지 insert
            ins_img_query = """
                INSERT INTO files (file_type, user_id, file_url, file_name, file_size)
                VALUES ('profile', %s, %s, 'profile.jpg', 0)
            """
            cursor.execute(ins_img_query, (user_id, update_data["profileImage"]))

        conn.commit()
    
        return {
            "code": "UPDATE_USER_SUCCESS",
            "message": "회원 정보가 성공적으로 수정되었습니다.",
            "data": None
        }
    except Exception as e:
        conn.rollback()
        if isinstance(e, APIException):
            raise e
        print(f"Update User Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="회원 정보 수정 중 오류가 발생했습니다.", status_code=500)
    finally:
        cursor.close()
        conn.close()

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
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # DB에서 현재 비번 조회
        query = "SELECT password FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise APIException(code="USER_NOT_FOUND", message="사용자를 찾을 수 없습니다.", status_code=404)

        # 4. 현재 비밀번호 확인
        if user["password"] != current_pw:
            raise APIException(code="INVALID_CURRENT_PASSWORD", message="현재 사용 중인 비밀번호가 일치하지 않습니다.", status_code=401)
        
        # 5. 새 비밀번호 강도 검사
        if not validate_password(new_pw):
            raise APIException(code="WEAK_PASSWORD", message="비밀번호는 영문, 숫자, 특수문자를 포함하여 8~20자여야 합니다.", status_code=400)
        
        # 6. 비밀번호 변경
        update_pw_query = "UPDATE users SET password = %s WHERE id = %s"
        cursor.execute(update_pw_query, (new_pw, user_id))
        conn.commit()
        
        return {
            "code": "CHANGE_PASSWORD_SUCCESS",
            "message": "비밀번호가 성공적으로 변경되었습니다.",
            "data": None
        }
    except Exception as e:
        conn.rollback()
        if isinstance(e, APIException):
            raise e
        print(f"Change Password Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="비밀번호 변경 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 5. 회원 탈퇴 (Soft Delete)
# ==========================================
async def delete_user(current_user: dict):
    user_id = current_user["userId"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 2. Soft Delete 처리 (is_deleted = 1, deleted_at = NOW)
        # 닉네임 유니크를 어떡하지? 탈퇴해도 닉네임 유니크 유지가 필요하면 그대로 둠.
        # 여기선 is_deleted=True로 업데이트
        
        update_query = "UPDATE users SET is_deleted = TRUE, deleted_at = NOW() WHERE id = %s"
        cursor.execute(update_query, (user_id,))
        
        # 3. 해당 유저의 세션 모두 삭제
        del_session_query = "DELETE FROM sessions WHERE user_id = %s"
        cursor.execute(del_session_query, (user_id,))
        
        conn.commit()
        
        return {
            "code": "DELETE_USER_SUCCESS",
            "message": "회원 탈퇴가 안전하게 처리되었습니다. 그동안 이용해주셔서 감사합니다.",
            "data": None
        }
    except Exception as e:
        conn.rollback()
        print(f"Delete User Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="탈퇴 처리 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()