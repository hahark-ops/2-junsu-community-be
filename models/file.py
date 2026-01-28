from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FileUploadResponse(BaseModel):
    fileId: int
    fileUrl: str
    fileName: str
    fileSize: int
    fileType: str
    createdAt: datetime
