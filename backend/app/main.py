"""
IT学习辅助系统 - FastAPI应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1 import documents as documents_router
from app.api.v1 import history as history_router
from app.api.v1 import websocket as websocket_router
from app.api.v1 import learning as learning_router
from app.api.v1 import streaming as streaming_router

# 配置日志
setup_logging()
logger = structlog.get_logger()

# 创建FastAPI应用
app = FastAPI(
    title="IT学习辅助系统",
    description="基于文档识别的智能学习辅助平台",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 注册路由（注意顺序：history要在documents之前，避免路由冲突）
app.include_router(history_router.router, prefix="/api/v1")
app.include_router(documents_router.router, prefix="/api/v1")
app.include_router(learning_router.router, prefix="/api/v1")
app.include_router(streaming_router.router, prefix="/api/v1")
app.include_router(websocket_router.router)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("应用启动", version="1.0.0")
    
    # 预热嵌入模型（在独立线程中执行，避免阻塞事件循环）
    try:
        from app.services.embedding_service import warmup_embedding_model
        import asyncio
        import concurrent.futures
        
        # 使用线程池执行模型预热，避免CPU密集型操作阻塞事件循环
        def run_warmup():
            """在线程中运行模型预热"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(warmup_embedding_model(timeout=30.0))
            finally:
                loop.close()
        
        # 在后台线程中执行，不阻塞主事件循环
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="model-warmup")
        executor.submit(run_warmup)
        logger.info("嵌入模型预热任务已启动（独立线程）")
    except Exception as e:
        logger.warning("启动嵌入模型预热任务失败", error=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("应用关闭")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "IT学习辅助系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

