# controllers/user.py

from database import get_db_connection
from utils import APIException, validate_nickname, validate_nickname_length, validate_password

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
            "profileimage": user.get("profileimage")
        }
    }

async def get_user_by_id(user_id: int):
    """
    특정 사용자 정보 조회 (ID 기반)
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE userId = %s", (user_id,))
        matched_user = cursor.fetchone()
        
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
                "profileimage": matched_user.get("profileimage")
            }
        }
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 3. 회원정보 수정
# ==========================================
async def update_user(user_id: int, update_data: dict, current_user: dict):
    if current_user["userId"] != user_id:
        raise APIException(code="PERMISSION_DENIED", message="본인의 정보만 수정할 수 있습니다.", status_code=403)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 사용자 존재 확인
        cursor.execute("SELECT * FROM users WHERE userId = %s", (user_id,))
        target_user = cursor.fetchone()
        
        if not target_user:
            raise APIException(code="USER_NOT_FOUND", message="사용자를 찾을 수 없습니다.", status_code=404)
        
        updates = []
        values = []
        
        # 닉네임 수정
        new_nickname = update_data.get("nickname")
        if new_nickname:
            if not validate_nickname(new_nickname):
                raise APIException(code="INVALID_NICKNAME_FORMAT", message="닉네임에 공백이나 특수문자를 포함할 수 없습니다.", status_code=400)
            if not validate_nickname_length(new_nickname):
                raise APIException(code="NICKNAME_TOO_LONG", message="닉네임은 최대 10자까지만 가능합니다.", status_code=400)
            
            # 중복 검사 (본인 제외)
            cursor.execute("SELECT count(*) as count FROM users WHERE nickname = %s AND userId != %s", (new_nickname, user_id))
            if cursor.fetchone()["count"] > 0:
                raise APIException(code="ALREADY_EXIST_NICKNAME", message="이미 사용 중인 닉네임입니다.", status_code=409)
            
            updates.append("nickname = %s")
            values.append(new_nickname)
            
            # (비정규화) 작성한 게시글/댓글의 닉네임 업데이트는 트리거로 하거나 여기서 같이 처리
            # 여기서는 간단하게 여기서 처리
            # posts 테이블 writer 업데이트
            cursor.execute("UPDATE posts SET writer = %s WHERE writerEmail = %s", (new_nickname, target_user["email"]))
            # comments 테이블 writer 업데이트
            cursor.execute("UPDATE comments SET writer = %s WHERE writerEmail = %s", (new_nickname, target_user["email"]))
        
        # 프로필 이미지 수정
        if "profileimage" in update_data:
            updates.append("profileimage = %s")
            values.append(update_data.get("profileimage"))
            
        if updates:
            sql = f"UPDATE users SET {', '.join(updates)} WHERE userId = %s"
            values.append(user_id)
            cursor.execute(sql, tuple(values))
            conn.commit()
            
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
    
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
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE userId = %s", (user_id,))
        target_user = cursor.fetchone()
        
        if not target_user:
            raise APIException(code="USER_NOT_FOUND", message="사용자를 찾을 수 없습니다.", status_code=404)
        
        if target_user["password"] != current_pw:
            raise APIException(code="INVALID_CURRENT_PASSWORD", message="현재 사용 중인 비밀번호가 일치하지 않습니다.", status_code=401)
        
        if not validate_password(new_pw):
            raise APIException(code="WEAK_PASSWORD", message="비밀번호는 영문, 숫자, 특수문자를 포함하여 8~20자여야 합니다.", status_code=400)
        
        cursor.execute("UPDATE users SET password = %s WHERE userId = %s", (new_pw, user_id))
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
    
    return {
        "code": "CHANGE_PASSWORD_SUCCESS",
        "message": "비밀번호가 성공적으로 변경되었습니다.",
        "data": None
    }

# ==========================================
# 5. 회원 탈퇴 (Soft Delete)
# ==========================================
async def delete_user(current_user: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Soft Delete
        cursor.execute("UPDATE users SET is_deleted = 1 WHERE userId = %s", (current_user["userId"],))
        
        # 세션 삭제
        cursor.execute("DELETE FROM sessions WHERE userEmail = %s", (current_user["email"],))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
    
    return {
        "code": "DELETE_USER_SUCCESS",
        "message": "회원 탈퇴가 안전하게 처리되었습니다. 그동안 이용해주셔서 감사합니다.",
        "data": None
    }
