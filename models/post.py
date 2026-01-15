from pydantic import BaseModel
from typing import Optional

class CreatePostRequest(BaseModel):
    title: str
    content: str
    fileUrl: Optional[str] = None

class UpdatePostRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    fileUrl: Optional[str] = None