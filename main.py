from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routers.index import router as api_router 
from utils import APIException
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Community API - Task 2-1")

# 0. 미들웨어 설정 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. 명세에 정의된 에러 처리 (APIException)
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": exc.data,
        },
    )

# 2. 예상치 못한 서버 에러 처리 (500)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "code": "internal_server_error",
            "message": "서버 내부 오류가 발생했습니다.",
            "data": None,
        },
    )

# 통합 라우터 연결
app.include_router(api_router)

# 3. 정적 파일 서빙 (업로드된 이미지 접근 가능하도록)
# uploads 폴더가 없으면 생성
if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    return {"message": "Community Server is Running!"}