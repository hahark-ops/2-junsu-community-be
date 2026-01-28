# models/post.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ==========================================
# 요청 모델 (Request)
# ==========================================

class PostCreate(BaseModel):
    """게시글 작성 요청"""
    title: str
    content: str
    fileUrl: Optional[str] = None

class PostUpdate(BaseModel):
    """게시글 수정 요청"""
    title: Optional[str] = None
    content: Optional[str] = None
    fileUrl: Optional[str] = None

# ==========================================
# 응답 모델 (Response)
# ==========================================

class AuthorResponse(BaseModel):
    """작성자 정보"""
    userId: int
    nickname: str
    profileImageUrl: Optional[str] = None

class PostResponse(BaseModel):
    """게시글 정보 응답"""
    postId: int
    title: str
    content: Optional[str] = None
    fileUrl: Optional[str] = None
    writer: str
    authorId: Optional[int] = None
    viewCount: int = 0
    likeCount: int = 0
    commentCount: int = 0
    createdAt: str

class PostListResponse(BaseModel):
    """게시글 목록 응답"""
    postId: int
    title: str
    writer: str
    viewCount: int = 0
    likeCount: int = 0
    commentCount: int = 0
    createdAt: str

class LikeResponse(BaseModel):
    """좋아요 응답"""
    postId: int
    totalLikeCount: int
    isLiked: bool
