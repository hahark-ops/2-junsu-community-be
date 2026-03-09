import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from database import is_db_ready
from controllers.dm import handle_room_event
from realtime.redis_bus import is_redis_ready, start_room_event_subscriber, stop_room_event_subscriber
from routers.index import router as api_router
from utils import APIException

app = FastAPI(title="Community API - Task 2-1")
logger = logging.getLogger("community.api")

def _cors_origins():
    raw = os.getenv("CORS_ALLOW_ORIGINS")
    if raw:
        origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
        if origins:
            return origins

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

# 0. 미들웨어 설정 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
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
    client_host = request.client.host if request.client else "unknown"
    logger.exception(
        "Unhandled exception method=%s path=%s query=%s client=%s",
        request.method,
        request.url.path,
        request.url.query,
        client_host,
    )
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


@app.on_event("startup")
async def startup_event():
    await start_room_event_subscriber(handle_room_event)


@app.on_event("shutdown")
async def shutdown_event():
    await stop_room_event_subscriber()

def _resolve_upload_dir() -> str:
    upload_dir = os.getenv("UPLOAD_DIR", "uploads").strip() or "uploads"
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME") and not os.path.isabs(upload_dir):
        return os.path.join("/tmp", upload_dir)
    return upload_dir


# 정적 파일 서빙 (이미지 업로드)
UPLOAD_DIR = _resolve_upload_dir()
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
async def root():
    if not is_db_ready():
        return JSONResponse(
            status_code=503,
            content={"message": "Community Server is Running, but database is unavailable."},
        )
    if not is_redis_ready():
        return JSONResponse(
            status_code=503,
            content={"message": "Community Server is Running, but realtime broker is unavailable."},
        )
    return {"message": "Community Server is Running!"}


@app.get("/healthz/ready")
async def readiness():
    if not is_db_ready():
        return JSONResponse(
            status_code=503,
            content={"status": "unready", "database": "unavailable"},
        )
    if not is_redis_ready():
        return JSONResponse(
            status_code=503,
            content={"status": "unready", "database": "ok", "redis": "unavailable"},
        )
    return {"status": "ready", "database": "ok", "redis": "ok"}
