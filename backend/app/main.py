from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.database import init_db, close_db
from app.tasks.scheduler import FrameScheduler
from app.tasks.runtime import set_scheduler
from app.api.v1 import alerts, system
from app.api.v1.admin import (
    cameras as admin_cameras,
    scenes as admin_scenes,
    policies as admin_policies,
    models as admin_models,
)
from app.api.v1.user import alerts as user_alerts
from app.api.v1.internal import system as internal_system
from app.services.websocket_service import manager
from app.utils.logger import logger
# 导入模型以确保它们被注册
from app.models import (
    Camera,
    Alert,
    Frame,
    SceneTemplate,
    SceneVersion,
    CameraSceneBinding,
    DetectionResult,
    AlertEvent,
    NotificationLog,
    DetectionTask,
)

scheduler: FrameScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler

    logger.info("=" * 50)
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 50)

    try:
        await init_db()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

    try:
        from app.database import AsyncSessionLocal
        scheduler = FrameScheduler(AsyncSessionLocal)
        scheduler.start(interval=settings.FRAME_INTERVAL_VALUE)
        set_scheduler(scheduler)
        logger.info(f"任务调度器已启动，抽帧间隔: {settings.FRAME_INTERVAL_VALUE}秒")
    except Exception as e:
        logger.error(f"任务调度器启动失败: {e}")
        raise

    yield

    logger.info("=" * 50)
    logger.info("关闭应用...")
    logger.info("=" * 50)

    if scheduler:
        scheduler.stop()
        set_scheduler(None)
        logger.info("任务调度器已停止")

    try:
        await close_db()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI视频巡查系统 - 实时监控摄像头，识别异常情况",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(admin_cameras.router, prefix="/api/v1")
app.include_router(admin_scenes.router, prefix="/api/v1")
app.include_router(admin_policies.router, prefix="/api/v1")
app.include_router(admin_models.router, prefix="/api/v1")
app.include_router(user_alerts.router, prefix="/api/v1/user")
app.include_router(internal_system.router, prefix="/api/v1")


@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(websocket)

storage_path = Path(settings.FRAME_STORAGE_PATH)
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "api": "/api/v1"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9002,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
