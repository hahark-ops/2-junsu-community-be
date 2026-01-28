# models/comment.py
from pydantic import BaseModel
from typing import Optional

# ==========================================
# 요청 모델 (Request)
# ==========================================

class CommentCreate(BaseModel):
    """댓글 작성 요청"""
    content: str

class CommentUpdate(BaseModel):
    """댓글 수정 요청"""
    content: str

# ==========================================
# 응답 모델 (Response)
# ==========================================

class CommentResponse(BaseModel):
    """댓글 정보 응답"""
    commentId: int
    postId: int
    content: str
    writer: str
    authorId: Optional[int] = None
    createdAt: str
    updatedAt: Optional[str] = None
