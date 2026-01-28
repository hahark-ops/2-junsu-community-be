from fastapi import APIRouter, UploadFile, File, Form, Depends, status
from controllers.file import upload_file
from dependencies import get_current_user, get_current_user_optional
from models.file import FileUploadResponse

router = APIRouter(prefix="/v1/files")

@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=FileUploadResponse)
async def upload_file_endpoint(
    file: UploadFile = File(...),
    type: str = Form(..., regex="^(post|profile)$"), # post 또는 profile만 허용
    user: dict = Depends(get_current_user_optional)
):
    """
    파일 업로드 API
    - type: 'post' 또는 'profile'
    - file: 이미지 파일
    """
    return await upload_file(file, type, user)
