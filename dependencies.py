from fastapi import Request

from models import auth_model, user_model
from utils import APIException


def resolve_user_by_session_id(session_id: str | None):
    if not session_id:
        raise APIException(
            code="LOGIN_REQUIRED",
            message="로그인이 필요한 기능입니다.",
            status_code=401,
        )

    user_email = auth_model.get_user_email_by_session_id(session_id)
    if not user_email:
        raise APIException(
            code="LOGIN_REQUIRED",
            message="유효하지 않은 세션입니다. 다시 로그인해주세요.",
            status_code=401,
        )

    user = user_model.get_user_by_email(user_email)
    if not user:
        try:
            auth_model.delete_session(session_id)
        except Exception:
            pass
        raise APIException(
            code="LOGIN_REQUIRED",
            message="유효하지 않은 세션입니다. 다시 로그인해주세요.",
            status_code=401,
        )

    return user


async def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    return resolve_user_by_session_id(session_id)
