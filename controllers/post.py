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