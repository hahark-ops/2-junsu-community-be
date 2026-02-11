from datetime import datetime
from models import comment_model, post_model
from utils import APIException

async def create_comment(post_id: int, comment_data: dict, user: dict):
    # 필수값 체크
    if not comment_data.get("content"):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="댓글 내용은 필수입니다.", status_code=400)
    
    if not post_model.exists_post(post_id):
        raise APIException(code="POST_NOT_FOUND", message="해당 게시글을 찾을 수 없습니다.", status_code=404)
    
    new_id = comment_model.create_comment(
        post_id=post_id,
        content=comment_data["content"],
        writer=user["nickname"],
        writer_email=user["email"],
    )
    
    return {
        "code": "COMMENT_CREATED", 
        "message": "댓글 등록 완료", 
        "data": {
            "commentId": new_id,
            "postId": post_id,
            "content": comment_data["content"],
            "writer": user["nickname"],
            "writerEmail": user["email"],
            "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "authorProfileImage": user.get("profileimage")
        }
    }

async def get_comments(post_id: int):
    comments = comment_model.fetch_comments(post_id)
    
    formatted_comments = []
    for c in comments:
        formatted_comments.append({
            "commentId": c["commentId"],
            "postId": c["postId"],
            "content": c["content"],
            "writer": c["writer"],
            "writerEmail": c["writerEmail"],
            "createdAt": c["createdAt"],
            "updatedAt": c.get("updatedAt"),
            "authorProfileImage": c["authorProfileImage"],
            "userId": c["authorId"],
            "authorId": c["authorId"],
            "nickname": c["authorNickname"],
            "authorEmail": c["authorEmail"]
        })
    
    return {"code": "SUCCESS", "message": "댓글 목록 조회 성공", "data": formatted_comments}

# ==========================================
# 3. 댓글 수정
# ==========================================
async def update_comment(post_id: int, comment_id: int, update_data: dict, current_user: dict):
    target_comment = comment_model.get_comment(comment_id, post_id)
    if not target_comment:
        raise APIException(code="COMMENT_NOT_FOUND", message="수정할 댓글을 찾을 수 없습니다.", status_code=404)
    
    if target_comment["writerEmail"] != current_user["email"]:
        raise APIException(code="NOT_THE_COMMENT_AUTHOR", message="본인이 작성한 댓글만 수정할 수 있습니다.", status_code=403)
    
    if "content" in update_data:
        comment_model.update_comment_content(comment_id, update_data["content"])
    
    updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    return {
        "code": "UPDATE_COMMENT_SUCCESS",
        "message": "댓글이 성공적으로 수정되었습니다.",
        "data": {"commentId": comment_id, "updatedAt": updated_at}
    }

# ==========================================
# 4. 댓글 삭제
# ==========================================
async def delete_comment(post_id: int, comment_id: int, current_user: dict):
    target_comment = comment_model.get_comment(comment_id, post_id)
    if not target_comment:
        raise APIException(code="COMMENT_NOT_FOUND", message="삭제할 댓글을 찾을 수 없습니다.", status_code=404)
    
    if target_comment["writerEmail"] != current_user["email"]:
        raise APIException(code="NOT_THE_COMMENT_AUTHOR", message="본인이 작성한 댓글만 삭제할 수 있습니다.", status_code=403)
    
    comment_model.delete_comment(comment_id)

    return {
        "code": "DELETE_COMMENT_SUCCESS",
        "message": "댓글이 안전하게 삭제되었습니다.",
        "data": None
    }
