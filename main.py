from fastapi import FastAPI
from routers.index import router as api_router 

app = FastAPI(title="Community API - Task 2-1")

# 통합 라우터 연결
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Community Server is Running!"}