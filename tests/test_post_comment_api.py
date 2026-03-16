from __future__ import annotations

import mysql.connector


def test_get_posts_list_success(client, monkeypatch):
    monkeypatch.setattr(
        "controllers.post.post_model.fetch_posts",
        lambda offset, limit: [
            {
                "postId": 3,
                "title": "제목",
                "content": "내용",
                "fileUrl": None,
                "writer": "tester",
                "viewCount": 1,
                "createdAt": "2026-03-16 10:00:00",
                "updatedAt": None,
                "authorId": 1,
                "authorProfileImage": None,
                "likeCount": 0,
                "commentCount": 0,
            }
        ],
    )
    monkeypatch.setattr("controllers.post.post_model.count_posts", lambda: 1)

    response = client.get("/v1/posts")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["totalCount"] == 1
    assert body["data"]["posts"][0]["postId"] == 3


def test_update_post_blank_title_returns_400(client, override_current_user, auth_user, monkeypatch):
    override_current_user(auth_user)
    monkeypatch.setattr(
        "controllers.post.post_model.get_post_by_id",
        lambda post_id: {"postId": post_id, "writerEmail": auth_user["email"]},
    )

    response = client.patch("/v1/posts/10", json={"title": "   "})

    assert response.status_code == 400
    assert response.json()["code"] == "REQUIRED_FIELDS_MISSING"


def test_like_post_duplicate_returns_409(client, override_current_user, auth_user, monkeypatch):
    override_current_user(auth_user)
    monkeypatch.setattr("controllers.post.post_model.exists_post", lambda post_id: True)

    def _raise_duplicate(post_id, email):
        exc = mysql.connector.IntegrityError(msg="duplicate")
        exc.errno = 1062
        raise exc

    monkeypatch.setattr("controllers.post.post_model.add_like", _raise_duplicate)

    response = client.post("/v1/posts/10/likes")

    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_LIKED"


def test_comment_update_blank_content_returns_400(client, override_current_user, auth_user, monkeypatch):
    override_current_user(auth_user)
    monkeypatch.setattr(
        "controllers.comment.comment_model.get_comment",
        lambda comment_id, post_id: {"commentId": comment_id, "postId": post_id, "writerEmail": auth_user["email"]},
    )

    response = client.patch("/v1/posts/3/comments/2", json={"content": "  "})

    assert response.status_code == 400
    assert response.json()["code"] == "REQUIRED_FIELDS_MISSING"
