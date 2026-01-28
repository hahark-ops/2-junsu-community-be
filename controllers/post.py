# controllers/post.py

from datetime import datetime
from database import get_db_connection
from utils import APIException

async def get_posts_list(offset: int, limit: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 게시글 목록 조회 + 작성자 닉네임 + 좋아요 수 + 댓글 수
        # users 테이블과 조인하여 작성자 닉네임/이메일 가져오기
        # post_likes, comments 테이블에서 count 계산 (서브쿼리)
        # deleted_at이 NULL인 게시글만 조회
        
        query = """
            SELECT 
                p.id as postId, 
                p.title, 
                p.content, 
                p.view_count as viewCount, 
                p.created_at as createdAt,
                u.id as authorId,
                u.nickname as writer,
                u.email as writerEmail,
                u.email as writerEmail,
                (SELECT file_url FROM files WHERE post_id = p.id AND file_type = 'post' AND deleted_at IS NULL LIMIT 1) as fileUrl,
                (SELECT file_url FROM files WHERE user_id = u.id AND file_type = 'profile' AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1) as authorProfileImage,
                (SELECT COUNT(*) FROM post_likes WHERE post_id = p.id) as likeCount,
                (SELECT COUNT(*) FROM comments WHERE post_id = p.id AND deleted_at IS NULL) as commentCount
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.deleted_at IS NULL
            ORDER BY p.created_at DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (limit, offset))
        posts = cursor.fetchall()
        
        # 전체 게시글 수 (페이지네이션용)
        count_query = "SELECT COUNT(*) as total FROM posts WHERE deleted_at IS NULL"
        cursor.execute(count_query)
        total_count = cursor.fetchone()["total"]
        
        # Datetime 객체를 문자열로 변환
        for post in posts:
            if isinstance(post["createdAt"], datetime):
                post["createdAt"] = post["createdAt"].isoformat()

        return {
            "code": "SUCCESS",
            "message": "게시물 목록 조회 성공",
            "data": {
                "posts": posts,
                "totalCount": total_count
            }
        }
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 4. 게시글 수정
# ==========================================
async def update_post(post_id: int, update_data: dict, current_user: dict):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. 게시글 찾기
        query = "SELECT * FROM posts WHERE id = %s AND deleted_at IS NULL"
        cursor.execute(query, (post_id,))
        target_post = cursor.fetchone()
        
        # 2. [404] 게시글 없음
        if not target_post:
            raise APIException(code="POST_NOT_FOUND", message="수정할 게시글을 찾을 수 없습니다.", status_code=404)
        
        # 3. [403] 작성자 확인
        if target_post["user_id"] != current_user["userId"]:
            raise APIException(code="NOT_THE_AUTHOR", message="본인이 작성한 글만 수정할 수 있습니다.", status_code=403)
        
        # 4. 수정
        # 동적 쿼리 생성
        fields = []
        values = []
        
        if "title" in update_data:
            fields.append("title = %s")
            values.append(update_data["title"])
        if "content" in update_data:
            fields.append("content = %s")
            values.append(update_data["content"])
        
        # 이미지 URL 업데이트 (files 테이블)
        if "fileUrl" in update_data:
            # 기존 이미지 삭제 처리 (혹은 덮어쓰기 정책)
            del_file_query = "UPDATE files SET deleted_at = NOW() WHERE post_id = %s AND file_type = 'post'"
            cursor.execute(del_file_query, (post_id,))
            
            if update_data["fileUrl"]:
                # 기존 업로드된 파일의 post_id 연결
                update_file_query = "UPDATE files SET post_id = %s, file_type = 'post' WHERE file_url = %s"
                cursor.execute(update_file_query, (post_id, update_data["fileUrl"]))
        
        if fields:
            query = f"UPDATE posts SET {', '.join(fields)} WHERE id = %s"
            values.append(post_id)
            cursor.execute(query, tuple(values))
            conn.commit()
            
            updated_at = datetime.now().isoformat()
            
            return {
                "code": "UPDATE_POST_SUCCESS",
                "message": "게시글이 성공적으로 수정되었습니다.",
                "data": {
                    "postId": post_id,
                    "updatedAt": updated_at
                }
            }
        else:
            # 변경사항 없음
             return {
                "code": "UPDATE_POST_SUCCESS",
                "message": "변경 사항이 없습니다.",
                "data": {"postId": post_id}
            }

    except Exception as e:
        conn.rollback()
        if isinstance(e, APIException):
            raise e
        print(f"Update Post Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="게시글 수정 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()

async def create_post(post_data: dict, user: dict):
    # 필수값 체크
    if not post_data.get("title") or not post_data.get("content"):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="제목과 내용은 필수입니다.", status_code=400)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = "INSERT INTO posts (user_id, title, content) VALUES (%s, %s, %s)"
        cursor.execute(query, (user["userId"], post_data["title"], post_data["content"]))
        new_post_id = cursor.lastrowid
        
        # 파일 연결 (fileUrl이 있는 경우)
        if post_data.get("fileUrl"):
             # INSERT가 아니라 UPDATE로 기존 파일에 post_id 매핑
             file_query = "UPDATE files SET post_id = %s, file_type = 'post' WHERE file_url = %s"
             cursor.execute(file_query, (new_post_id, post_data["fileUrl"]))
        
        conn.commit()
        
        return {"code": "POST_CREATED", "message": "게시물이 등록되었습니다.", "data": {"postId": new_post_id}}
    except Exception as e:
        conn.rollback()
        print(f"Create Post Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="게시글 작성 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 3. 게시글 상세 조회
# ==========================================
async def get_post_detail(post_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. 게시글 찾기 + 작성자 정보 + 조회수 증가
        # 트랜잭션 시작 (조회수 증가 때문)
        
        # 먼저 게시글 존재 확인
        query = """
            SELECT 
                p.id as postId, 
                p.title, 
                p.content, 
                p.view_count as viewCount, 
                p.created_at as createdAt,
                u.id as authorId, 
                u.id as authorId, 
                u.nickname as writer,
                (SELECT file_url FROM files WHERE user_id = u.id AND file_type = 'profile' AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1) as authorProfileImage,
                (SELECT file_url FROM files WHERE post_id = p.id AND file_type = 'post' AND deleted_at IS NULL LIMIT 1) as fileUrl
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = %s AND p.deleted_at IS NULL
        """
        cursor.execute(query, (post_id,))
        target_post = cursor.fetchone()
        
        # 2. [404] 게시글 없음
        if not target_post:
            raise APIException(code="POST_NOT_FOUND", message="존재하지 않거나 삭제된 게시글입니다.", status_code=404)
        
        # 3. 조회수 증가
        update_view_query = "UPDATE posts SET view_count = view_count + 1 WHERE id = %s"
        cursor.execute(update_view_query, (post_id,))
        conn.commit()
        
        # 조회수 메모리 상 증가 (반환값용)
        target_post["viewCount"] += 1
        
        # 4. 좋아요 수, 댓글 수 계산
        like_count_query = "SELECT COUNT(*) as count FROM post_likes WHERE post_id = %s"
        cursor.execute(like_count_query, (post_id,))
        like_count = cursor.fetchone()["count"]
        
        comment_count_query = "SELECT COUNT(*) as count FROM comments WHERE post_id = %s AND deleted_at IS NULL"
        cursor.execute(comment_count_query, (post_id,))
        comment_count = cursor.fetchone()["count"]
        
        # 날짜 포맷
        if isinstance(target_post["createdAt"], datetime):
            target_post["createdAt"] = target_post["createdAt"].isoformat()

        # 5. 성공 응답
        return {
            "code": "GET_POST_DETAIL_SUCCESS",
            "message": "게시글 정보를 성공적으로 불러왔습니다.",
            "data": {
                "postId": target_post["postId"],
                "title": target_post["title"],
                "content": target_post["content"],
                "fileUrl": target_post["fileUrl"],
                "writer": target_post["writer"],
                "authorProfileImage": target_post["authorProfileImage"],
                "authorId": target_post["authorId"],
                "viewCount": target_post["viewCount"],
                "likeCount": like_count,
                "commentCount": comment_count,
                "createdAt": target_post["createdAt"]
            }
        }
    except Exception as e:
        conn.rollback() # 조회수 증가 롤백
        if isinstance(e, APIException):
            raise e
        print(f"Get Post Detail Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="게시글 조회 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 5. 게시글 삭제
# ==========================================
async def delete_post(post_id: int, current_user: dict):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. 게시글 확인 (작성자 체크)
        query = "SELECT user_id FROM posts WHERE id = %s AND deleted_at IS NULL"
        cursor.execute(query, (post_id,))
        post = cursor.fetchone()
        
        # 2. [404] 게시글 없음
        if not post:
             raise APIException(code="POST_NOT_FOUND", message="삭제하려는 게시글을 찾을 수 없습니다.", status_code=404)

        # 3. [403] 작성자 확인
        if post["user_id"] != current_user["userId"]:
            raise APIException(code="NOT_THE_AUTHOR", message="본인이 작성한 글만 삭제할 수 있습니다.", status_code=403)
        
        # 4. 삭제 (Soft Delete)
        del_query = "UPDATE posts SET deleted_at = NOW() WHERE id = %s"
        cursor.execute(del_query, (post_id,))
        
        conn.commit()
    
        return {
            "code": "DELETE_POST_SUCCESS",
            "message": "게시글이 안전하게 삭제되었습니다.",
            "data": None
        }
    except Exception as e:
        conn.rollback()
        if isinstance(e, APIException):
            raise e
        print(f"Delete Post Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="게시글 삭제 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 6. 좋아요 추가
# ==========================================
async def like_post(post_id: int, current_user: dict):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. 게시글 존재 확인
        check_query = "SELECT id FROM posts WHERE id = %s AND deleted_at IS NULL"
        cursor.execute(check_query, (post_id,))
        if not cursor.fetchone():
             raise APIException(code="POST_NOT_FOUND", message="해당 게시글을 찾을 수 없습니다.", status_code=404)

        # 3. [409] 이미 좋아요 눌렀는지 확인 & 4. 추가
        # INSERT IGNORE 또는 try-except로 처리
        try:
            ins_query = "INSERT INTO post_likes (post_id, user_id) VALUES (%s, %s)"
            cursor.execute(ins_query, (post_id, current_user["userId"]))
            conn.commit()
        except mysql.connector.errors.IntegrityError:
            # Duplicate entry 에러
            raise APIException(code="ALREADY_LIKED", message="이미 좋아요를 누른 게시글입니다.", status_code=409)
        
        # 5. 좋아요 수 계산
        count_query = "SELECT COUNT(*) as count FROM post_likes WHERE post_id = %s"
        cursor.execute(count_query, (post_id,))
        like_count = cursor.fetchone()["count"]
        
        return {
            "code": "LIKE_SUCCESS",
            "message": "해당 게시글에 좋아요를 눌렀습니다.",
            "data": {"postId": post_id, "totalLikeCount": like_count, "isLiked": True}
        }
    except Exception as e:
        conn.rollback()
        if isinstance(e, APIException):
            raise e
        print(f"Like Post Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="좋아요 처리 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 7. 좋아요 취소
# ==========================================
async def unlike_post(post_id: int, current_user: dict):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. 게시글 존재 확인
        check_query = "SELECT id FROM posts WHERE id = %s AND deleted_at IS NULL"
        cursor.execute(check_query, (post_id,))
        if not cursor.fetchone():
             raise APIException(code="POST_NOT_FOUND", message="해당 게시글을 찾을 수 없습니다.", status_code=404)
        
        # 3. 좋아요 찾아서 삭제
        del_query = "DELETE FROM post_likes WHERE post_id = %s AND user_id = %s"
        cursor.execute(del_query, (post_id, current_user["userId"]))
        conn.commit()
        
        # 4. 좋아요 수 계산
        count_query = "SELECT COUNT(*) as count FROM post_likes WHERE post_id = %s"
        cursor.execute(count_query, (post_id,))
        like_count = cursor.fetchone()["count"]
        
        return {
            "code": "UNLIKE_SUCCESS",
            "message": "해당 게시글의 좋아요를 취소했습니다.",
            "data": {"postId": post_id, "totalLikeCount": like_count, "isLiked": False}
        }
    except Exception as e:
        conn.rollback()
        if isinstance(e, APIException):
            raise e
        print(f"Unlike Post Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="좋아요 취소 중 오류 발생", status_code=500)
    finally:
        cursor.close()
        conn.close()