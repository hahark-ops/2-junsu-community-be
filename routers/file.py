import os
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from dependencies import get_current_user

router = APIRouter(
    prefix="/v1/files",
    tags=["files"]
)

UPLOAD_DIR = "uploads"
UPLOAD_PROVIDER = os.getenv("UPLOAD_PROVIDER", "s3").strip().lower()
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "").strip()
S3_REGION = os.getenv("AWS_REGION", "").strip()
S3_OBJECT_PREFIX = os.getenv("S3_OBJECT_PREFIX", "uploads").strip().strip("/")
S3_BASE_URL = os.getenv("S3_BASE_URL", "").strip().rstrip("/")

# 업로드 디렉토리가 없으면 생성 (앱 시작 시에도 체크하지만 여기서도 안전하게)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
try:
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024)))
except ValueError:
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024


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
            if total_size > MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail="파일 크기가 제한을 초과했습니다.")
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

        if UPLOAD_PROVIDER != "s3":
            raise HTTPException(status_code=500, detail="UPLOAD_PROVIDER는 s3 또는 local 이어야 합니다.")

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
