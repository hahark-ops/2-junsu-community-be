from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import uuid
import os
from dependencies import get_current_user

router = APIRouter(
    prefix="/v1/files",
    tags=["files"]
)

UPLOAD_DIR = "uploads"

# 업로드 디렉토리가 없으면 생성 (앱 시작 시에도 체크하지만 여기서도 안전하게)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
try:
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024)))
except ValueError:
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    type: str = "post",
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
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        
        # 파일 저장(용량 제한 포함)
        total_size = 0
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE:
                    buffer.close()
                    os.remove(file_path)
                    raise HTTPException(status_code=413, detail="파일 크기가 제한을 초과했습니다.")
                buffer.write(chunk)
            
        # URL 반환 (서버 주소는 프론트엔드에서 조합하거나 상대경로로)
        # 여기서는 전체 URL을 반환하기보다 파일 경로를 반환하거나 전체 URL을 반환하도록 설정
        # main.py에서 /uploads를 정적 파일로 서빙하고 있음
        
        # 실제 운영 환경에서는 도메인이나 IP를 환경변수로 관리하는 것이 좋음
        # 현재는 클라이언트가 요청한 호스트를 기반으로 URL 생성하거나
        # 간단하게 /uploads/filename 포맷으로 리턴
        
        return {
            "url": f"/uploads/{new_filename}",
            "fileUrl": f"/uploads/{new_filename}", # 프록시(`host:3000/uploads/...`)를 통해 접근하도록 상대경로 사용
            "filename": new_filename
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="파일 업로드 중 오류가 발생했습니다.")
    finally:
        await file.close()
