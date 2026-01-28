# controllers/comment.py

from datetime import datetime
from database import get_db_connection
from utils import APIException

async def create_comment(post_id: int, comment_data: dict, user: dict):
    # 필수값 체크
    if not comment_data.get("content"):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="댓글 내용은 필수입니다.", status_code=400)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 게시글 존재 확인
        check_query = "SELECT id FROM posts WHERE id = %s AND deleted_at IS NULL"
        cursor.execute(check_query, (post_id,))
        if not cursor.fetchone():
             raise APIException(code="POST_NOT_FOUND", message="존재하지 않거나 삭제된 게시글입니다.", status_code=404)

        query = "INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)"
        cursor.execute(query, (post_id, user["userId"], comment_data["content"]))
        new_comment_id = cursor.lastrowid
        
        conn.commit()
        
        # 생성된 댓글 정보 반환 (작성자 정보 포함)
        created_at = datetime.now().isoformat()
        
        return {
            "code": "COMMENT_CREATED", 
            "message": "댓글 등록 완료", 
            "data": {
                "commentId": new_comment_id,
                "postId": post_id,
                "content": comment_data["content"],
                "writer": user["nickname"],
                "writerEmail": user["email"],
                "authorId": user["userId"],
                "createdAt": created_at
            }
        }
    except Exception as e:
        conn.rollback()
        if isinstance(e, APIException):
            raise e
        print(f"Create Comment Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="댓글 작성 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()

async def get_comments(post_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 댓글 조회 + 작성자 정보
        query = """
            SELECT 
                c.id as commentId,
                c.post_id as postId,
                c.content,
                c.created_at as createdAt,
                c.updated_at as updatedAt,
                u.id as authorId,
                u.nickname as writer,
                u.email as writerEmail,
                (SELECT file_url FROM files WHERE user_id = u.id AND file_type = 'profile' AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1) as authorProfileImage
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = %s AND c.deleted_at IS NULL
            ORDER BY c.created_at ASC
        """
        cursor.execute(query, (post_id,))
        comments = cursor.fetchall()
        
        # 날짜 포맷
        for comment in comments:
             if isinstance(comment["createdAt"], datetime):
                comment["createdAt"] = comment["createdAt"].isoformat()
             if isinstance(comment["updatedAt"], datetime):
                comment["updatedAt"] = comment["updatedAt"].isoformat()
        
        return {"code": "SUCCESS", "message": "댓글 목록 조회 성공", "data": comments}
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 3. 댓글 수정
# ==========================================
async def update_comment(post_id: int, comment_id: int, update_data: dict, current_user: dict):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. 댓글 찾기
        query = """
            SELECT c.*, u.email as writerEmail 
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = %s AND c.post_id = %s AND c.deleted_at IS NULL
        """
        cursor.execute(query, (comment_id, post_id))
        target_comment = cursor.fetchone()
        
        # 2. [404] 댓글 없음
        if not target_comment:
            raise APIException(code="COMMENT_NOT_FOUND", message="수정할 댓글을 찾을 수 없습니다.", status_code=404)
        
        # 3. [403] 작성자 확인
        if target_comment["user_id"] != current_user["userId"]:
            raise APIException(code="NOT_THE_COMMENT_AUTHOR", message="본인이 작성한 댓글만 수정할 수 있습니다.", status_code=403)
        
        # 4. 수정
        if "content" in update_data:
            update_query = "UPDATE comments SET content = %s WHERE id = %s"
            cursor.execute(update_query, (update_data["content"], comment_id))
            conn.commit()
            
            updated_at = datetime.now().isoformat()
            
            return {
                "code": "UPDATE_COMMENT_SUCCESS",
                "message": "댓글이 성공적으로 수정되었습니다.",
                "data": {"commentId": comment_id, "updatedAt": updated_at}
            }
        else:
            return {
                "code": "UPDATE_COMMENT_SUCCESS",
                "message": "변경 사항이 없습니다.",
                "data": {"commentId": comment_id}
            }

    except Exception as e:
        conn.rollback()
        if isinstance(e, APIException):
            raise e
        print(f"Update Comment Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="댓글 수정 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 4. 댓글 삭제
# ==========================================
async def delete_comment(post_id: int, comment_id: int, current_user: dict):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. 댓글 찾기
        query = "SELECT user_id FROM comments WHERE id = %s AND post_id = %s AND deleted_at IS NULL"
        cursor.execute(query, (comment_id, post_id))
        target_comment = cursor.fetchone()
        
        # 2. [404] 댓글 없음
        if not target_comment:
            raise APIException(code="COMMENT_NOT_FOUND", message="삭제할 댓글을 찾을 수 없습니다.", status_code=404)
        
        # 3. [403] 작성자 확인
        if target_comment["user_id"] != current_user["userId"]:
            raise APIException(code="NOT_THE_COMMENT_AUTHOR", message="본인이 작성한 댓글만 삭제할 수 있습니다.", status_code=403)
        
        # 4. 삭제 (Soft Delete)
        del_query = "UPDATE comments SET deleted_at = NOW() WHERE id = %s"
        cursor.execute(del_query, (comment_id,))
        conn.commit()
        
        return {
            "code": "DELETE_COMMENT_SUCCESS",
            "message": "댓글이 안전하게 삭제되었습니다.",
            "data": None
        }
    except Exception as e:
        conn.rollback()
        if isinstance(e, APIException):
            raise e
        print(f"Delete Comment Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="댓글 삭제 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()