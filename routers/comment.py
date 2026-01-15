from fastapi import APIRouter, Depends, status
from controllers.comment import create_comment, get_comments
from models.comment import CreateCommentRequest
from dependencies import get_current_user

router = APIRouter(prefix="/v1/posts")

# 댓글 조회 (누구나 가능)
@router.get("/{post_id}/comments")
async def read_comments(post_id: int):
    return await get_comments(post_id)

# 댓글 작성 (로그인 필수)
@router.post("/{post_id}/comments", status_code=201)
async def write_comment(
    post_id: int, 
    comment_data: CreateCommentRequest, 
    user: dict = Depends(get_current_user)
):
    return await create_comment(post_id, comment_data, user)