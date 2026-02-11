from datetime import datetime
from database import fake_comments
from utils import APIException

async def create_comment(post_id: int, comment_data: dict, user: dict):
    # 필수값 체크
    if not comment_data.get("content"):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="댓글 내용은 필수입니다.", status_code=400)
    
    new_id = 1 if not fake_comments else fake_comments[-1]["commentId"] + 1
    new_comment = {
        "commentId": new_id,
        "postId": post_id,
        "content": comment_data["content"],
        "writer": user["nickname"],
        "writerEmail": user["email"],
        "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }
    fake_comments.append(new_comment)
    return {"code": "COMMENT_CREATED", "message": "댓글 등록 완료", "data": new_comment}

async def get_comments(post_id: int):
    comments = [c for c in fake_comments if c["postId"] == post_id]
    return {"code": "SUCCESS", "message": "댓글 목록 조회 성공", "data": comments}

# ==========================================
# 3. 댓글 수정
# ==========================================
async def update_comment(post_id: int, comment_id: int, update_data: dict, current_user: dict):
    # 1. 댓글 찾기
    target_comment = None
    for comment in fake_comments:
        if comment["commentId"] == comment_id and comment["postId"] == post_id:
            target_comment = comment
            break
    
    # 2. [404] 댓글 없음
    if target_comment is None:
        raise APIException(code="COMMENT_NOT_FOUND", message="수정할 댓글을 찾을 수 없습니다.", status_code=404)
    
    # 3. [403] 작성자 확인
    if target_comment.get("writerEmail") != current_user["email"]:
        raise APIException(code="NOT_THE_COMMENT_AUTHOR", message="본인이 작성한 댓글만 수정할 수 있습니다.", status_code=403)
    
    # 4. 수정
    if "content" in update_data:
        target_comment["content"] = update_data["content"]
    
    updated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    target_comment["updatedAt"] = updated_at
    
    return {
        "code": "UPDATE_COMMENT_SUCCESS",
        "message": "댓글이 성공적으로 수정되었습니다.",
        "data": {"commentId": comment_id, "updatedAt": updated_at}
    }

# ==========================================
# 4. 댓글 삭제
# ==========================================
async def delete_comment(post_id: int, comment_id: int, current_user: dict):
    # 1. 댓글 찾기
    target_comment = None
    target_index = -1
    for i, comment in enumerate(fake_comments):
        if comment["commentId"] == comment_id and comment["postId"] == post_id:
            target_comment = comment
            target_index = i
            break
    
    # 2. [404] 댓글 없음
    if target_comment is None:
        raise APIException(code="COMMENT_NOT_FOUND", message="삭제할 댓글을 찾을 수 없습니다.", status_code=404)
    
    # 3. [403] 작성자 확인
    if target_comment.get("writerEmail") != current_user["email"]:
        raise APIException(code="NOT_THE_COMMENT_AUTHOR", message="본인이 작성한 댓글만 삭제할 수 있습니다.", status_code=403)
    
    # 4. 삭제
    fake_comments.pop(target_index)
    
    return {
        "code": "DELETE_COMMENT_SUCCESS",
        "message": "댓글이 안전하게 삭제되었습니다.",
        "data": None
    }