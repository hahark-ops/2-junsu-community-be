from datetime import datetime

from models import post_model
from utils import APIException


async def get_posts_list(offset: int, limit: int):
    posts = post_model.fetch_posts(offset, limit)
    total_count = post_model.count_posts()
    return {
        "code": "SUCCESS",
        "message": "게시물 목록 조회 성공",
        "data": {
            "posts": posts,
            "totalCount": total_count,
        },
    }


async def update_post(post_id: int, update_data: dict, current_user: dict):
    target_post = post_model.get_post_by_id(post_id)
    if not target_post:
        raise APIException(code="POST_NOT_FOUND", message="수정할 게시글을 찾을 수 없습니다.", status_code=404)

    if target_post["writerEmail"] != current_user["email"]:
        raise APIException(code="NOT_THE_AUTHOR", message="본인이 작성한 글만 수정할 수 있습니다.", status_code=403)

    fields = {}
    if "title" in update_data:
        fields["title"] = update_data["title"]
    if "content" in update_data:
        fields["content"] = update_data["content"]
    if "fileUrl" in update_data:
        fields["fileUrl"] = update_data["fileUrl"]

    if fields:
        post_model.update_post_fields(post_id, fields)

    return {
        "code": "UPDATE_POST_SUCCESS",
        "message": "게시글이 성공적으로 수정되었습니다.",
        "data": {
            "postId": post_id,
            "updatedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        },
    }


async def create_post(post_data: dict, user: dict):
    if not post_data.get("title") or not post_data.get("content"):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="제목과 내용은 필수입니다.", status_code=400)

    new_id = post_model.create_post(
        title=post_data["title"],
        content=post_data["content"],
        file_url=post_data.get("fileUrl"),
        writer=user["nickname"],
        writer_email=user["email"],
    )
    return {"code": "POST_CREATED", "message": "게시물이 등록되었습니다.", "data": {"postId": new_id}}


async def get_post_detail(post_id: int):
    target_post = post_model.get_post_detail(post_id)
    if not target_post:
        raise APIException(code="POST_NOT_FOUND", message="존재하지 않거나 삭제된 게시글입니다.", status_code=404)

    post_model.increment_view_count(post_id)
    like_count = post_model.count_likes(post_id)
    comment_count = post_model.count_comments(post_id)
    likes = post_model.fetch_likes(post_id)

    return {
        "code": "GET_POST_DETAIL_SUCCESS",
        "message": "게시글 정보를 성공적으로 불러왔습니다.",
        "data": {
            "postId": target_post["postId"],
            "title": target_post["title"],
            "content": target_post["content"],
            "fileUrl": target_post["fileUrl"],
            "writer": target_post["writer"],
            "writerEmail": target_post["writerEmail"],
            "viewCount": target_post["viewCount"] + 1,
            "createdAt": target_post["createdAt"],
            "authorProfileImage": target_post["authorProfileImage"],
            "authorId": target_post["authorId"],
            "userId": target_post["authorId"],
            "likeCount": like_count,
            "commentCount": comment_count,
            "likes": likes,
        },
    }


async def delete_post(post_id: int, current_user: dict):
    target_post = post_model.get_post_by_id(post_id)
    if not target_post:
        raise APIException(code="POST_NOT_FOUND", message="삭제하려는 게시글을 찾을 수 없습니다.", status_code=404)

    if target_post["writerEmail"] != current_user["email"]:
        raise APIException(code="NOT_THE_AUTHOR", message="본인이 작성한 글만 삭제할 수 있습니다.", status_code=403)

    post_model.delete_post(post_id)
    return {
        "code": "DELETE_POST_SUCCESS",
        "message": "게시글이 안전하게 삭제되었습니다.",
        "data": None,
    }


async def like_post(post_id: int, current_user: dict):
    if not post_model.exists_post(post_id):
        raise APIException(code="POST_NOT_FOUND", message="해당 게시글을 찾을 수 없습니다.", status_code=404)

    if post_model.has_user_liked(post_id, current_user["email"]):
        raise APIException(code="ALREADY_LIKED", message="이미 좋아요를 누른 게시글입니다.", status_code=409)

    post_model.add_like(post_id, current_user["email"])
    like_count = post_model.count_likes(post_id)
    return {
        "code": "LIKE_SUCCESS",
        "message": "해당 게시글에 좋아요를 눌렀습니다.",
        "data": {"postId": post_id, "totalLikeCount": like_count, "isLiked": True},
    }


async def unlike_post(post_id: int, current_user: dict):
    if not post_model.exists_post(post_id):
        raise APIException(code="POST_NOT_FOUND", message="해당 게시글을 찾을 수 없습니다.", status_code=404)

    post_model.remove_like(post_id, current_user["email"])
    like_count = post_model.count_likes(post_id)
    return {
        "code": "UNLIKE_SUCCESS",
        "message": "해당 게시글의 좋아요를 취소했습니다.",
        "data": {"postId": post_id, "totalLikeCount": like_count, "isLiked": False},
    }
