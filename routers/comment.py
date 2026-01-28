from fastapi import APIRouter, Depends, status
from controllers.comment import create_comment, get_comments, update_comment, delete_comment
from dependencies import get_current_user
from models.comment import CommentCreate, CommentUpdate

router = APIRouter(prefix="/v1/posts")

# 댓글 조회 (누구나 가능)
@router.get("/{post_id}/comments")
async def read_comments(post_id: int):
    return await get_comments(post_id)

# 댓글 작성 (로그인 필수)
@router.post("/{post_id}/comments", status_code=201)
async def create_comment_endpoint(
    post_id: int, 
    comment_data: CommentCreate, 
    user: dict = Depends(get_current_user)
):
    return await create_comment(post_id, comment_data.model_dump(), user)

@router.patch("/{post_id}/comments/{comment_id}", status_code=status.HTTP_200_OK)
async def update_comment_endpoint(
    post_id: int,
    comment_id: int,
    update_data: CommentUpdate,
    user: dict = Depends(get_current_user)
):
    return await update_comment(post_id, comment_id, update_data.model_dump(), user)

@router.delete("/{post_id}/comments/{comment_id}", status_code=status.HTTP_200_OK)
async def delete_comment_endpoint(
    post_id: int,
    comment_id: int,
    user: dict = Depends(get_current_user)
):
    return await delete_comment(post_id, comment_id, user)