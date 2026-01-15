from datetime import datetime
from database import fake_posts
from models.post import CreatePostRequest, UpdatePostRequest

async def get_posts_list(offset: int, limit: int):
    return {
        "code": "SUCCESS",
        "data": {
            "posts": fake_posts[offset : offset + limit],
            "totalCount": len(fake_posts)
        }
    }

async def create_post(post_data: CreatePostRequest, user: dict):
    new_id = 1 if not fake_posts else fake_posts[-1]["postId"] + 1
    new_post = {
        "postId": new_id,
        "title": post_data.title,
        "content": post_data.content,
        "fileUrl": post_data.fileUrl,
        "writer": user["nickname"],      # 로그인한 유저 닉네임 사용
        "writerEmail": user["email"],    # 본인 확인용
        "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "viewCount": 0
    }
    fake_posts.append(new_post)
    return {"code": "POST_CREATED", "data": {"postId": new_id}}