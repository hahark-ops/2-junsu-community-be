from fastapi import APIRouter, Depends, Body
from controllers.comment import create_comment, get_comments
from dependencies import get_current_user

router = APIRouter(prefix="/v1/posts")

# 댓글 조회 (누구나 가능)
@router.get("/{post_id}/comments")
async def read_comments(post_id: int):
    return await get_comments(post_id)

# 댓글 작성 (로그인 필수)
@router.post("/{post_id}/comments", status_code=201)
async def create_comment_endpoint(
    post_id: int, 
    comment_data: dict = Body(...), 
    user: dict = Depends(get_current_user)
):
    return await create_comment(post_id, comment_data, user)

# TODO: 댓글 수정 (PATCH /v1/posts/{post_id}/comments/{comment_id})
# TODO: 댓글 삭제 (DELETE /v1/posts/{post_id}/comments/{comment_id})