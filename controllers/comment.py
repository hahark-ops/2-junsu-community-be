from datetime import datetime
from database import fake_comments
from models.comment import CreateCommentRequest

async def create_comment(post_id: int, comment_data: CreateCommentRequest, user: dict):
    new_id = 1 if not fake_comments else fake_comments[-1]["commentId"] + 1
    new_comment = {
        "commentId": new_id,
        "postId": post_id,
        "content": comment_data.content,
        "writer": user["nickname"],
        "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }
    fake_comments.append(new_comment)
    return {"code": "COMMENT_CREATED", "message": "댓글 등록 완료", "data": new_comment}

async def get_comments(post_id: int):
    comments = [c for c in fake_comments if c["postId"] == post_id]
    return {"code": "SUCCESS", "data": comments}