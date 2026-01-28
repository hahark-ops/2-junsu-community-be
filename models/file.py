# models/file.py
from pydantic import BaseModel
from typing import Optional

# ==========================================
# 응답 모델 (Response)
# ==========================================

class FileResponse(BaseModel):
    """파일 업로드 응답"""
    imageUrl: str
    fileName: str
    size: Optional[int] = None
