from fastapi import APIRouter, Depends, Body, status
from controllers.post import get_posts_list, create_post as create_post_controller, get_post_detail, update_post, delete_post, like_post, unlike_post
from dependencies import get_current_user # 로그인 체크기

router = APIRouter(prefix="/v1/posts")

@router.get("")
async def get_posts(offset: int = 0, limit: int = 10):
    return await get_posts_list(offset, limit)

@router.get("/{post_id}", status_code=status.HTTP_200_OK)
async def get_post(post_id: int):
    return await get_post_detail(post_id)

# 게시물 작성은 로그인한 사람만 가능
@router.post("", status_code=201)
async def create_post(
    post_data: dict = Body(...), 
    user: dict = Depends(get_current_user)
):
    return await create_post_controller(post_data, user)

@router.patch("/{post_id}", status_code=status.HTTP_200_OK)
async def update_post_endpoint(
    post_id: int,
    update_data: dict = Body(...),
    user: dict = Depends(get_current_user)
):
    return await update_post(post_id, update_data, user)

@router.delete("/{post_id}", status_code=status.HTTP_200_OK)
async def delete_post_endpoint(post_id: int, user: dict = Depends(get_current_user)):
    return await delete_post(post_id, user)

@router.post("/{post_id}/likes", status_code=status.HTTP_201_CREATED)
async def like_post_endpoint(post_id: int, user: dict = Depends(get_current_user)):
    return await like_post(post_id, user)

@router.delete("/{post_id}/likes", status_code=status.HTTP_200_OK)
async def unlike_post_endpoint(post_id: int, user: dict = Depends(get_current_user)):
    return await unlike_post(post_id, user)

# TODO: 게시글 이미지 업로드 (POST /v1/posts/images)