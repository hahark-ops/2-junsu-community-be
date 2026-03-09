import os
import uuid
from typing import Optional
from urllib.parse import urlparse

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from dependencies import get_current_user

router = APIRouter(
    prefix="/v1/files",
    tags=["files"]
)

def _resolve_upload_dir() -> str:
    upload_dir = os.getenv("UPLOAD_DIR", "uploads").strip() or "uploads"
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME") and not os.path.isabs(upload_dir):
        return os.path.join("/tmp", upload_dir)
    return upload_dir


UPLOAD_DIR = _resolve_upload_dir()
UPLOAD_PROVIDER = os.getenv("UPLOAD_PROVIDER", "s3").strip().lower()
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "").strip()
S3_REGION = os.getenv("AWS_REGION", "").strip()
S3_OBJECT_PREFIX = os.getenv("S3_OBJECT_PREFIX", "uploads").strip().strip("/")
S3_BASE_URL = os.getenv("S3_BASE_URL", "").strip().rstrip("/")
UPLOAD_LAMBDA_API_URL = os.getenv("UPLOAD_LAMBDA_API_URL", "").strip()
UPLOAD_INTERNAL_TOKEN = os.getenv("UPLOAD_INTERNAL_TOKEN", "").strip()

# 업로드 디렉토리가 없으면 생성 (앱 시작 시에도 체크하지만 여기서도 안전하게)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
try:
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(15 * 1024 * 1024)))
except ValueError:
    MAX_UPLOAD_SIZE = 15 * 1024 * 1024

try:
    MAX_PROFILE_UPLOAD_SIZE = int(os.getenv("MAX_PROFILE_UPLOAD_SIZE_BYTES", str(MAX_UPLOAD_SIZE)))
except ValueError:
    MAX_PROFILE_UPLOAD_SIZE = MAX_UPLOAD_SIZE

try:
    MAX_POST_UPLOAD_SIZE = int(os.getenv("MAX_POST_UPLOAD_SIZE_BYTES", str(20 * 1024 * 1024)))
except ValueError:
    MAX_POST_UPLOAD_SIZE = 20 * 1024 * 1024


def _get_upload_limit(upload_type: str) -> int:
    normalized = (upload_type or "post").strip().lower()
    if normalized == "profile":
        return MAX_PROFILE_UPLOAD_SIZE
    if normalized == "post":
        return MAX_POST_UPLOAD_SIZE
    return MAX_UPLOAD_SIZE


def _format_limit_mb(size_bytes: int) -> str:
    return f"{size_bytes / (1024 * 1024):.1f}MB"


def _s3_client():
    kwargs = {}
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    session_token = os.getenv("AWS_SESSION_TOKEN", "").strip()

    if S3_REGION:
        kwargs["region_name"] = S3_REGION
    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key
        if session_token:
            kwargs["aws_session_token"] = session_token

    return boto3.client("s3", **kwargs)


def _build_s3_key(upload_type: str, filename: str) -> str:
    safe_type = (upload_type or "post").strip().lower()
    if safe_type not in {"post", "profile"}:
        safe_type = "post"
    return f"{S3_OBJECT_PREFIX}/{safe_type}/{filename}" if S3_OBJECT_PREFIX else f"{safe_type}/{filename}"


def _build_s3_file_url(object_key: str) -> str:
    if S3_BASE_URL:
        return f"{S3_BASE_URL}/{object_key}"

    # 기본 S3 public URL
    if S3_REGION and S3_REGION != "us-east-1":
        return f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{object_key}"
    return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{object_key}"


def _lambda_internal_headers() -> dict:
    if not UPLOAD_INTERNAL_TOKEN:
        raise HTTPException(status_code=500, detail="UPLOAD_INTERNAL_TOKEN 환경변수가 설정되지 않았습니다.")
    return {"X-Upload-Internal-Token": UPLOAD_INTERNAL_TOKEN}


def _request_presigned_url_via_lambda(
    upload_type: str,
    original_filename: str,
    content_type: str,
    size_bytes: int | None = None,
) -> Optional[tuple[str, str, str, str, int | None]]:
    if not UPLOAD_LAMBDA_API_URL:
        raise HTTPException(status_code=500, detail="UPLOAD_LAMBDA_API_URL 환경변수가 설정되지 않았습니다.")

    try:
        payload = {
            "type": upload_type,
            "filename": original_filename,
            "contentType": content_type,
        }
        if size_bytes is not None:
            payload["sizeBytes"] = int(size_bytes)

        presign_resp = requests.post(
            UPLOAD_LAMBDA_API_URL,
            json=payload,
            headers=_lambda_internal_headers(),
            timeout=15,
        )
    except requests.RequestException as e:
        print(f"Lambda presign request error: {str(e)}")
        return None

    if not presign_resp.ok:
        print(
            f"Lambda presign request failed: status={presign_resp.status_code}, body={presign_resp.text[:300]}"
        )
        return None

    try:
        body = presign_resp.json()
    except ValueError:
        raise HTTPException(status_code=500, detail="Lambda presign 응답 파싱에 실패했습니다.")

    data = body.get("data") or {}
    upload_url = data.get("uploadUrl") or body.get("uploadUrl")
    file_url = (
        data.get("fileUrl")
        or data.get("filePath")
        or data.get("url")
        or body.get("fileUrl")
        or body.get("filePath")
        or body.get("file_url")
    )
    object_key = data.get("objectKey") or body.get("objectKey")
    filename = data.get("filename") or body.get("filename") or ""
    content_length = data.get("contentLength") or body.get("contentLength")

    if upload_url:
        if not object_key and file_url:
            object_key = urlparse(file_url).path.lstrip("/")
        if not file_url and object_key:
            file_url = _build_s3_file_url(object_key)
        if not file_url:
            raise HTTPException(status_code=500, detail="업로드 URL 생성 결과가 올바르지 않습니다.")

        return (
            upload_url,
            file_url,
            object_key or urlparse(file_url).path.lstrip("/"),
            filename,
            int(content_length) if content_length is not None else None,
        )

    raise HTTPException(status_code=500, detail="업로드 URL 생성 결과가 올바르지 않습니다.")


def _upload_to_s3(object_key: str, content: bytes, content_type: str):
    if not S3_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="S3_BUCKET_NAME 환경변수가 설정되지 않았습니다.")

    try:
        _s3_client().put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            Body=content,
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as e:
        print(f"S3 upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="S3 파일 업로드 중 오류가 발생했습니다.")


def _upload_via_lambda_api(upload_type: str, original_filename: str, content: bytes, content_type: str):
    # 1) Preferred path: get presigned URL from Lambda, then upload directly to S3.
    presigned = _request_presigned_url_via_lambda(
        upload_type=upload_type,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=len(content),
    )

    if presigned:
        upload_url, file_url, object_key, _filename, content_length = presigned
        if content_length is not None and int(content_length) != len(content):
            print(
                f"Presigned content length mismatch: expected={len(content)}, received={content_length}"
            )
            raise HTTPException(status_code=500, detail="업로드 URL 생성 결과가 올바르지 않습니다.")
        try:
            put_resp = requests.put(
                upload_url,
                data=content,
                headers={
                    "Content-Type": content_type,
                    "Content-Length": str(len(content)),
                },
                timeout=30,
            )
        except requests.RequestException as e:
            print(f"Presigned PUT request error: {str(e)}")
            raise HTTPException(status_code=500, detail="S3 Presigned 업로드 중 오류가 발생했습니다.")

        if put_resp.status_code not in {200, 201}:
            print(
                f"Presigned PUT failed: status={put_resp.status_code}, body={put_resp.text[:300]}"
            )
            raise HTTPException(status_code=500, detail="S3 Presigned 업로드에 실패했습니다.")

        return file_url, object_key

    # 2) Fallback path: legacy multipart relay through Lambda.
    try:
        lambda_resp = requests.post(
            UPLOAD_LAMBDA_API_URL,
            data={"type": upload_type},
            files={"file": (original_filename, content, content_type)},
            headers=_lambda_internal_headers(),
            timeout=20,
        )
    except requests.RequestException as e:
        print(f"Lambda upload request error: {str(e)}")
        raise HTTPException(status_code=500, detail="Lambda 업로드 요청 중 오류가 발생했습니다.")

    if not lambda_resp.ok:
        print(f"Lambda upload request failed: status={lambda_resp.status_code}, body={lambda_resp.text}")
        if lambda_resp.status_code == 401:
            raise HTTPException(status_code=500, detail="업로드 서비스 인증 설정 오류입니다.")
        if lambda_resp.status_code == 413:
            raise HTTPException(status_code=413, detail="파일 크기가 업로드 경로 제한을 초과했습니다.")
        raise HTTPException(status_code=500, detail="Lambda 업로드 요청에 실패했습니다.")

    try:
        body = lambda_resp.json()
    except ValueError:
        raise HTTPException(status_code=500, detail="Lambda 업로드 응답 파싱에 실패했습니다.")

    data = body.get("data") or {}
    file_url = (
        data.get("fileUrl")
        or data.get("filePath")
        or data.get("url")
        or body.get("fileUrl")
        or body.get("filePath")
        or body.get("file_url")
    )
    object_key = data.get("objectKey") or body.get("objectKey")

    if not file_url:
        raise HTTPException(status_code=500, detail="Lambda 업로드 응답 형식이 올바르지 않습니다.")

    if not object_key:
        parsed = urlparse(file_url)
        object_key = parsed.path.lstrip("/")

    return file_url, object_key


class UploadUrlRequest(BaseModel):
    type: str = "post"
    filename: str = "upload.png"
    contentType: str = "image/png"
    sizeBytes: int = 0


@router.post("/upload-url")
async def create_upload_url(
    payload: UploadUrlRequest,
    current_user: dict = Depends(get_current_user),
):
    _ = current_user

    if UPLOAD_PROVIDER != "lambda":
        raise HTTPException(status_code=400, detail="현재 업로드 provider는 presigned URL 발급을 지원하지 않습니다.")

    content_type = (payload.contentType or "image/png").strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

    filename = (payload.filename or "upload.png").strip() or "upload.png"
    file_extension = os.path.splitext(filename)[1].lower()
    if file_extension and file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="지원하지 않는 확장자입니다.")

    if payload.sizeBytes <= 0:
        raise HTTPException(status_code=400, detail="파일 크기 정보가 필요합니다.")

    upload_limit = _get_upload_limit(payload.type)
    if payload.sizeBytes > upload_limit:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 제한을 초과했습니다. (최대 {_format_limit_mb(upload_limit)})",
        )

    presigned = _request_presigned_url_via_lambda(
        upload_type=payload.type,
        original_filename=filename,
        content_type=content_type,
        size_bytes=payload.sizeBytes,
    )
    if not presigned:
        raise HTTPException(status_code=500, detail="업로드 URL 발급에 실패했습니다.")

    upload_url, file_url, object_key, saved_filename, content_length = presigned
    return {
        "uploadUrl": upload_url,
        "fileUrl": file_url,
        "objectKey": object_key,
        "filename": saved_filename or os.path.basename(object_key),
        "contentLength": content_length,
        "provider": "lambda-presigned",
    }


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    type: str = Form("post"),
    current_user: dict = Depends(get_current_user),
):
    try:
        # 인증된 사용자만 업로드 가능
        _ = current_user
        if not file.filename:
            raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")

        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

        # 파일 확장자 추출
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="지원하지 않는 확장자입니다.")

        upload_limit = _get_upload_limit(type)

        # 고유한 파일명 생성 (UUID)
        new_filename = f"{uuid.uuid4()}{file_extension}"

        # 파일 읽기(용량 제한 포함)
        total_size = 0
        chunks = []
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > upload_limit:
                raise HTTPException(
                    status_code=413,
                    detail=f"파일 크기가 제한을 초과했습니다. (최대 {_format_limit_mb(upload_limit)})",
                )
            chunks.append(chunk)

        file_bytes = b"".join(chunks)

        if UPLOAD_PROVIDER == "local":
            file_path = os.path.join(UPLOAD_DIR, new_filename)
            with open(file_path, "wb") as buffer:
                buffer.write(file_bytes)

            relative_url = f"/uploads/{new_filename}"
            return {
                "url": relative_url,
                "fileUrl": relative_url,
                "filename": new_filename,
            }

        if UPLOAD_PROVIDER == "lambda":
            file_url, object_key = _upload_via_lambda_api(
                upload_type=type,
                original_filename=file.filename,
                content=file_bytes,
                content_type=file.content_type or "application/octet-stream",
            )
            return {
                "url": file_url,
                "fileUrl": file_url,
                "filename": new_filename,
                "provider": "lambda",
                "objectKey": object_key,
            }

        if UPLOAD_PROVIDER != "s3":
            raise HTTPException(status_code=500, detail="UPLOAD_PROVIDER는 s3, local, lambda 중 하나여야 합니다.")

        object_key = _build_s3_key(type, new_filename)
        _upload_to_s3(object_key, file_bytes, file.content_type or "application/octet-stream")
        file_url = _build_s3_file_url(object_key)

        return {
            "url": file_url,
            "fileUrl": file_url,
            "filename": new_filename,
            "provider": "s3",
            "objectKey": object_key,
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="파일 업로드 중 오류가 발생했습니다.")
    finally:
        await file.close()
