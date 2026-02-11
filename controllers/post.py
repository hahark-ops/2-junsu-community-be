from datetime import datetime
from database import get_db_connection
from utils import APIException

async def get_posts_list(offset: int, limit: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 게시글 목록 조회 (작성자 정보 포함)
        # 뷰 카운트, 좋아요 수, 댓글 수는 별도 쿼리나 조인으로 가져올 수 있음
        # 여기서는 간단하게 posts 테이블 정보만 가져옴 + 작성자 닉네임은 posts 테이블에 비정규화되어 있음
        
        # 게시글 + 좋아요 수 + 댓글 수 + 작성자 프로필 이미지
        sql = """
            SELECT p.*, u.profileimage as authorProfileImage,
            (SELECT COUNT(*) FROM likes WHERE postId = p.postId) as likeCount,
            (SELECT COUNT(*) FROM comments WHERE postId = p.postId) as commentCount
            FROM posts p
            LEFT JOIN users u ON p.writerEmail = u.email
            ORDER BY p.createdAt DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(sql, (limit, offset))
        posts = cursor.fetchall()
        
        cursor.execute("SELECT count(*) as total FROM posts")
        total_count = cursor.fetchone()["total"]
        
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
        # 게시글 확인
        cursor.execute("SELECT * FROM posts WHERE postId = %s", (post_id,))
        target_post = cursor.fetchone()
        
        if not target_post:
            raise APIException(code="POST_NOT_FOUND", message="수정할 게시글을 찾을 수 없습니다.", status_code=404)
        
        if target_post["writerEmail"] != current_user["email"]:
            raise APIException(code="NOT_THE_AUTHOR", message="본인이 작성한 글만 수정할 수 있습니다.", status_code=403)
        
        updates = []
        values = []
        
        if "title" in update_data:
            updates.append("title = %s")
            values.append(update_data["title"])
        if "content" in update_data:
            updates.append("content = %s")
            values.append(update_data["content"])
        if "fileUrl" in update_data:
            updates.append("fileUrl = %s")
            values.append(update_data["fileUrl"])
            
        if updates:
            values.append(post_id)
            sql = f"UPDATE posts SET {', '.join(updates)} WHERE postId = %s"
            cursor.execute(sql, tuple(values))
            conn.commit()
            
        updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        return {
            "code": "UPDATE_POST_SUCCESS",
            "message": "게시글이 성공적으로 수정되었습니다.",
            "data": {
                "postId": post_id,
                "updatedAt": updated_at
            }
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

async def create_post(post_data: dict, user: dict):
    if not post_data.get("title") or not post_data.get("content"):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="제목과 내용은 필수입니다.", status_code=400)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = "INSERT INTO posts (title, content, fileUrl, writer, writerEmail) VALUES (%s, %s, %s, %s, %s)"
        val = (post_data["title"], post_data["content"], post_data.get("fileUrl"), user["nickname"], user["email"])
        cursor.execute(sql, val)
        conn.commit()
        
        new_id = cursor.lastrowid
        
        return {"code": "POST_CREATED", "message": "게시물이 등록되었습니다.", "data": {"postId": new_id}}
    except Exception as e:
        conn.rollback()
        raise e
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
        # 게시글 + 작성자 프로필
        sql = """
            SELECT p.*, u.profileimage as authorProfileImage
            FROM posts p
            LEFT JOIN users u ON p.writerEmail = u.email
            WHERE p.postId = %s
        """
        cursor.execute(sql, (post_id,))
        target_post = cursor.fetchone()
        
        if not target_post:
             raise APIException(code="POST_NOT_FOUND", message="존재하지 않거나 삭제된 게시글입니다.", status_code=404)
        
        # 조회수 증가
        cursor.execute("UPDATE posts SET viewCount = viewCount + 1 WHERE postId = %s", (post_id,))
        conn.commit()
        
        # 좋아요 수
        cursor.execute("SELECT count(*) as count FROM likes WHERE postId = %s", (post_id,))
        like_count = cursor.fetchone()["count"]
        
        # 댓글 수
        cursor.execute("SELECT count(*) as count FROM comments WHERE postId = %s", (post_id,))
        comment_count = cursor.fetchone()["count"]
        
        # 좋아요 목록 (상세 정보 포함)
        sql_likes = """
            SELECT l.*, u.userId, u.nickname, u.email 
            FROM likes l
            JOIN users u ON l.userEmail = u.email
            WHERE l.postId = %s
        """
        cursor.execute(sql_likes, (post_id,))
        likes = cursor.fetchall()
        
        # 반환 데이터 구성 (기존 형식 유지)
        return {
            "code": "GET_POST_DETAIL_SUCCESS",
            "message": "게시글 정보를 성공적으로 불러왔습니다.",
            "data": {
                "postId": target_post["postId"],
                "title": target_post["title"],
                "content": target_post["content"],
                "fileUrl": target_post["fileUrl"],
                "writer": target_post["writer"],
                "writerEmail": target_post["writerEmail"],
                "viewCount": target_post["viewCount"] + 1, # 증가된 값 반영
                "createdAt": target_post["createdAt"],
                "authorProfileImage": target_post["authorProfileImage"],
                "likeCount": like_count,
                "commentCount": comment_count,
                "likes": likes,
                "userId": target_post["writerEmail"] # 프론트에서 비교용 (이메일이지만 userId 필드명 사용 중인 듯) -> 아니면 DB에서 ID 가져오기
                # Frontend post_detail.js:368 postAuthorId = String(currentPost.author.userId) or currentPost.authorId or currentPost.userId
                # 여기서는 writerEmail이 확실하므로, User Table 조인해서 ID를 주거나 해야함. 
                # 위 쿼리에서 u.userId를 가져왔으면 좋았을 것. 
            }
        }
        # 수정: 위 쿼리에서 userId도 가져오도록 수정
        # SELECT p.*, u.profileimage, u.userId as authorId ...
        
    finally:
        cursor.close()
        conn.close()

# get_post_detail 재작성 (userId 포함)
async def get_post_detail(post_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT p.*, u.profileimage as authorProfileImage, u.userId as authorId
            FROM posts p
            LEFT JOIN users u ON p.writerEmail = u.email
            WHERE p.postId = %s
        """
        cursor.execute(sql, (post_id,))
        target_post = cursor.fetchone()
        
        if not target_post:
             raise APIException(code="POST_NOT_FOUND", message="존재하지 않거나 삭제된 게시글입니다.", status_code=404)
        
        cursor.execute("UPDATE posts SET viewCount = viewCount + 1 WHERE postId = %s", (post_id,))
        conn.commit()
        
        cursor.execute("SELECT count(*) as count FROM likes WHERE postId = %s", (post_id,))
        like_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT count(*) as count FROM comments WHERE postId = %s", (post_id,))
        comment_count = cursor.fetchone()["count"]
        
        sql_likes = """
            SELECT l.*, u.userId, u.nickname, u.email 
            FROM likes l
            JOIN users u ON l.userEmail = u.email
            WHERE l.postId = %s
        """
        cursor.execute(sql_likes, (post_id,))
        likes = cursor.fetchall()

        return {
            "code": "GET_POST_DETAIL_SUCCESS",
            "message": "게시글 정보를 성공적으로 불러왔습니다.",
            "data": {
                "postId": target_post["postId"],
                "title": target_post["title"],
                "content": target_post["content"],
                "fileUrl": target_post["fileUrl"],
                "writer": target_post["writer"],
                "viewCount": target_post["viewCount"] + 1,
                "createdAt": target_post["createdAt"],
                "authorProfileImage": target_post["authorProfileImage"],
                "authorId": target_post["authorId"], # Frontend 호환성
                "userId": target_post["authorId"],   # Frontend 호환성
                "likeCount": like_count,
                "commentCount": comment_count,
                "likes": likes
            }
        }
    except Exception as e:
        raise e # 500 에러 처리됨
        
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
        cursor.execute("SELECT * FROM posts WHERE postId = %s", (post_id,))
        target_post = cursor.fetchone()
        
        if not target_post:
            raise APIException(code="POST_NOT_FOUND", message="삭제하려는 게시글을 찾을 수 없습니다.", status_code=404)
        
        if target_post["writerEmail"] != current_user["email"]:
            raise APIException(code="NOT_THE_AUTHOR", message="본인이 작성한 글만 삭제할 수 있습니다.", status_code=403)
        
        cursor.execute("DELETE FROM posts WHERE postId = %s", (post_id,))
        conn.commit()
        
        return {
            "code": "DELETE_POST_SUCCESS",
            "message": "게시글이 안전하게 삭제되었습니다.",
            "data": None
        }
    except Exception as e:
        conn.rollback()
        raise e
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
        # 게시글 존재 확인
        cursor.execute("SELECT count(*) as count FROM posts WHERE postId = %s", (post_id,))
        if cursor.fetchone()["count"] == 0:
            raise APIException(code="POST_NOT_FOUND", message="해당 게시글을 찾을 수 없습니다.", status_code=404)
        
        # 이미 좋아요 했는지 확인
        cursor.execute("SELECT count(*) as count FROM likes WHERE postId = %s AND userEmail = %s", (post_id, current_user["email"]))
        if cursor.fetchone()["count"] > 0:
            raise APIException(code="ALREADY_LIKED", message="이미 좋아요를 누른 게시글입니다.", status_code=409)
        
        cursor.execute("INSERT INTO likes (postId, userEmail) VALUES (%s, %s)", (post_id, current_user["email"]))
        conn.commit()
        
        cursor.execute("SELECT count(*) as count FROM likes WHERE postId = %s", (post_id,))
        like_count = cursor.fetchone()["count"]
        
        return {
            "code": "LIKE_SUCCESS",
            "message": "해당 게시글에 좋아요를 눌렀습니다.",
            "data": {"postId": post_id, "totalLikeCount": like_count, "isLiked": True}
        }
    except Exception as e:
        conn.rollback()
        raise e
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
        # 게시글 존재 확인
        cursor.execute("SELECT count(*) as count FROM posts WHERE postId = %s", (post_id,))
        if cursor.fetchone()["count"] == 0:
            raise APIException(code="POST_NOT_FOUND", message="해당 게시글을 찾을 수 없습니다.", status_code=404)
            
        cursor.execute("DELETE FROM likes WHERE postId = %s AND userEmail = %s", (post_id, current_user["email"]))
        conn.commit()
        
        cursor.execute("SELECT count(*) as count FROM likes WHERE postId = %s", (post_id,))
        like_count = cursor.fetchone()["count"]
        
        return {
            "code": "UNLIKE_SUCCESS",
            "message": "해당 게시글의 좋아요를 취소했습니다.",
            "data": {"postId": post_id, "totalLikeCount": like_count, "isLiked": False}
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
