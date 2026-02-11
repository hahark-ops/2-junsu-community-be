from datetime import datetime
from database import fake_posts
from utils import APIException

async def get_posts_list(offset: int, limit: int):
    return {
        "code": "SUCCESS",
        "message": "게시물 목록 조회 성공",
        "data": {
            "posts": fake_posts[offset : offset + limit],
            "totalCount": len(fake_posts)
        }
    }

# ==========================================
# 4. 게시글 수정
# ==========================================
async def update_post(post_id: int, update_data: dict, current_user: dict):
    # 1. 게시글 찾기
    target_post = None
    for post in fake_posts:
        if post["postId"] == post_id:
            target_post = post
            break
    
    # 2. [404] 게시글 없음
    if target_post is None:
        raise APIException(code="POST_NOT_FOUND", message="수정할 게시글을 찾을 수 없습니다.", status_code=404)
    
    # 3. [403] 작성자 확인
    if target_post["writerEmail"] != current_user["email"]:
        raise APIException(code="NOT_THE_AUTHOR", message="본인이 작성한 글만 수정할 수 있습니다.", status_code=403)
    
    # 4. 수정
    if "title" in update_data:
        target_post["title"] = update_data["title"]
    if "content" in update_data:
        target_post["content"] = update_data["content"]
    if "fileUrl" in update_data:
        target_post["fileUrl"] = update_data["fileUrl"]
    
    updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    target_post["updatedAt"] = updated_at
    
    return {
        "code": "UPDATE_POST_SUCCESS",
        "message": "게시글이 성공적으로 수정되었습니다.",
        "data": {
            "postId": target_post["postId"],
            "updatedAt": updated_at
        }
    }

async def create_post(post_data: dict, user: dict):
    # 필수값 체크
    if not post_data.get("title") or not post_data.get("content"):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="제목과 내용은 필수입니다.", status_code=400)
    
    new_id = 1 if not fake_posts else fake_posts[-1]["postId"] + 1
    new_post = {
        "postId": new_id,
        "title": post_data["title"],
        "content": post_data["content"],
        "fileUrl": post_data.get("fileUrl"),
        "writer": user["nickname"],
        "writerEmail": user["email"],
        "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "viewCount": 0
    }
    fake_posts.append(new_post)
    return {"code": "POST_CREATED", "message": "게시물이 등록되었습니다.", "data": {"postId": new_id}}

# ==========================================
# 3. 게시글 상세 조회
# ==========================================
async def get_post_detail(post_id: int):
    # 1. 게시글 찾기
    target_post = None
    for post in fake_posts:
        if post["postId"] == post_id:
            target_post = post
            break
    
    # 2. [404] 게시글 없음
    if target_post is None:
        raise APIException(code="POST_NOT_FOUND", message="존재하지 않거나 삭제된 게시글입니다.", status_code=404)
    
    # 3. 조회수 증가
    target_post["viewCount"] = target_post.get("viewCount", 0) + 1
    
    # 4. 성공 응답
    return {
        "code": "GET_POST_DETAIL_SUCCESS",
        "message": "게시글 정보를 성공적으로 불러왔습니다.",
        "data": {
            "postId": target_post["postId"],
            "title": target_post["title"],
            "content": target_post["content"],
            "fileUrl": target_post.get("fileUrl"),
            "writer": target_post["writer"],
            "viewCount": target_post["viewCount"],
            "createdAt": target_post["createdAt"]
        }
    }

# ==========================================
# 5. 게시글 삭제
# ==========================================
async def delete_post(post_id: int, current_user: dict):
    # 1. 게시글 찾기
    target_post = None
    target_index = -1
    for i, post in enumerate(fake_posts):
        if post["postId"] == post_id:
            target_post = post
            target_index = i
            break
    
    # 2. [404] 게시글 없음
    if target_post is None:
        raise APIException(code="POST_NOT_FOUND", message="삭제하려는 게시글을 찾을 수 없습니다.", status_code=404)
    
    # 3. [403] 작성자 확인
    if target_post["writerEmail"] != current_user["email"]:
        raise APIException(code="NOT_THE_AUTHOR", message="본인이 작성한 글만 삭제할 수 있습니다.", status_code=403)
    
    # 4. 삭제
    fake_posts.pop(target_index)
    
    return {
        "code": "DELETE_POST_SUCCESS",
        "message": "게시글이 안전하게 삭제되었습니다.",
        "data": None
    }

# ==========================================
# 6. 좋아요 추가
# ==========================================
async def like_post(post_id: int, current_user: dict):
    from database import fake_likes
    
    # 1. 게시글 찾기
    target_post = None
    for post in fake_posts:
        if post["postId"] == post_id:
            target_post = post
            break
    
    # 2. [404] 게시글 없음
    if target_post is None:
        raise APIException(code="POST_NOT_FOUND", message="해당 게시글을 찾을 수 없습니다.", status_code=404)
    
    # 3. [409] 이미 좋아요 눌렀는지 확인
    for like in fake_likes:
        if like["postId"] == post_id and like["userEmail"] == current_user["email"]:
            raise APIException(code="ALREADY_LIKED", message="이미 좋아요를 누른 게시글입니다.", status_code=409)
    
    # 4. 좋아요 추가
    fake_likes.append({"postId": post_id, "userEmail": current_user["email"]})
    
    # 5. 좋아요 수 계산
    like_count = sum(1 for like in fake_likes if like["postId"] == post_id)
    
    return {
        "code": "LIKE_SUCCESS",
        "message": "해당 게시글에 좋아요를 눌렀습니다.",
        "data": {"postId": post_id, "totalLikeCount": like_count, "isLiked": True}
    }

# ==========================================
# 7. 좋아요 취소
# ==========================================
async def unlike_post(post_id: int, current_user: dict):
    from database import fake_likes
    
    # 1. 게시글 찾기
    target_post = None
    for post in fake_posts:
        if post["postId"] == post_id:
            target_post = post
            break
    
    # 2. [404] 게시글 없음
    if target_post is None:
        raise APIException(code="POST_NOT_FOUND", message="해당 게시글을 찾을 수 없습니다.", status_code=404)
    
    # 3. 좋아요 찾아서 삭제
    like_index = -1
    for i, like in enumerate(fake_likes):
        if like["postId"] == post_id and like["userEmail"] == current_user["email"]:
            like_index = i
            break
    
    if like_index != -1:
        fake_likes.pop(like_index)
    
    # 4. 좋아요 수 계산
    like_count = sum(1 for like in fake_likes if like["postId"] == post_id)
    
    return {
        "code": "UNLIKE_SUCCESS",
        "message": "해당 게시글의 좋아요를 취소했습니다.",
        "data": {"postId": post_id, "totalLikeCount": like_count, "isLiked": False}
    }