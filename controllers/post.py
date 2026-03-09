from datetime import datetime

import mysql.connector

from models import post_model
from utils import APIException


def _serialize_likes(like_rows: list[dict]) -> list[dict]:
    serialized = []
    for row in like_rows or []:
        serialized.append(
            {
                "userId": row.get("userId"),
                "nickname": row.get("nickname"),
                "createdAt": row.get("createdAt"),
            }
        )
    return serialized


def _serialize_posts(posts: list[dict]) -> list[dict]:
    serialized = []
    for row in posts or []:
        serialized.append(
            {
                "postId": row.get("postId"),
                "title": row.get("title"),
                "content": row.get("content"),
                "fileUrl": row.get("fileUrl"),
                "writer": row.get("writer"),
                "viewCount": row.get("viewCount"),
                "createdAt": row.get("createdAt"),
                "updatedAt": row.get("updatedAt"),
                "authorProfileImage": row.get("authorProfileImage"),
                "likeCount": row.get("likeCount", 0),
                "commentCount": row.get("commentCount", 0),
            }
        )
    return serialized


async def get_posts_list(offset: int, limit: int):
    posts = _serialize_posts(post_model.fetch_posts(offset, limit))
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
        if not str(update_data["title"]).strip():
            raise APIException(code="REQUIRED_FIELDS_MISSING", message="제목과 내용은 필수입니다.", status_code=400)
        fields["title"] = update_data["title"]
    if "content" in update_data:
        if not str(update_data["content"]).strip():
            raise APIException(code="REQUIRED_FIELDS_MISSING", message="제목과 내용은 필수입니다.", status_code=400)
        fields["content"] = update_data["content"]
    if "fileUrl" in update_data:
        fields["fileUrl"] = update_data["fileUrl"]

    if fields:
        try:
            post_model.update_post_fields(post_id, fields)
        except ValueError as exc:
            if str(exc) == "INVALID_UPDATE_FIELD":
                raise APIException(
                    code="INVALID_UPDATE_FIELD",
                    message="허용되지 않은 수정 필드가 포함되어 있습니다.",
                    status_code=400,
                )
            raise

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


async def get_post_detail(post_id: int, increase_view: bool = True):
    target_post = post_model.get_post_detail(post_id)
    if not target_post:
        raise APIException(code="POST_NOT_FOUND", message="존재하지 않거나 삭제된 게시글입니다.", status_code=404)

    if increase_view:
        post_model.increment_view_count(post_id)
        refreshed_post = post_model.get_post_detail(post_id)
        if refreshed_post:
            target_post = refreshed_post

    like_count = post_model.count_likes(post_id)
    comment_count = post_model.count_comments(post_id)
    likes = _serialize_likes(post_model.fetch_likes(post_id))

    return {
        "code": "GET_POST_DETAIL_SUCCESS",
        "message": "게시글 정보를 성공적으로 불러왔습니다.",
        "data": {
            "postId": target_post["postId"],
            "title": target_post["title"],
            "content": target_post["content"],
            "fileUrl": target_post["fileUrl"],
            "writer": target_post["writer"],
            "viewCount": target_post["viewCount"],
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

    try:
        post_model.add_like(post_id, current_user["email"])
    except mysql.connector.IntegrityError as exc:
        if getattr(exc, "errno", None) == 1062:
            raise APIException(code="ALREADY_LIKED", message="이미 좋아요를 누른 게시글입니다.", status_code=409)
        raise
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
