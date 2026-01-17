from fastapi import APIRouter, Depends, Body
from controllers.post import get_posts_list, create_post as create_post_controller
from dependencies import get_current_user # 로그인 체크기

router = APIRouter(prefix="/v1/posts")

@router.get("")
async def get_posts(offset: int = 0, limit: int = 10):
    return await get_posts_list(offset, limit)

# 게시물 작성은 로그인한 사람만 가능
@router.post("", status_code=201)
async def create_post(
    post_data: dict = Body(...), 
    user: dict = Depends(get_current_user)
):
    return await create_post_controller(post_data, user)

# TODO: 게시글 상세 조회 (GET /v1/posts/{post_id})
# TODO: 게시글 수정 (PATCH /v1/posts/{post_id})
# TODO: 게시글 삭제 (DELETE /v1/posts/{post_id})
# TODO: 게시글 이미지 업로드 (POST /v1/posts/images)
# TODO: 게시글 좋아요 (POST /v1/posts/{post_id}/likes)
# TODO: 게시글 좋아요 취소 (DELETE /v1/posts/{post_id}/likes)