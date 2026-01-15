from fastapi import APIRouter, Depends, status
from controllers.post import get_posts_list, create_post
from models.post import CreatePostRequest
from dependencies import get_current_user # 로그인 체크기

router = APIRouter(prefix="/v1/posts")

@router.get("")
async def get_posts(offset: int = 0, limit: int = 10):
    return await get_posts_list(offset, limit)

# 게시물 작성은 로그인한 사람만 가능
@router.post("", status_code=201)
async def write_post(
    post_data: CreatePostRequest, 
    user: dict = Depends(get_current_user)
):
    return await create_post(post_data, user)