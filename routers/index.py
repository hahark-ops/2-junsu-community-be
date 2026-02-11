from routers.file import router as file_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(post_router)
router.include_router(comment_router)
router.include_router(file_router)