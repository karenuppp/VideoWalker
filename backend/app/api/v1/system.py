"""
系统监控API
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.camera import Camera
from app.models.alert import Alert
from app.models.frame import Frame
from app.tasks.runtime import get_scheduler, get_scheduler_status
from app.utils.logger import logger
from app.utils.time import today_date
from pydantic import BaseModel
from datetime import datetime


# Pydantic模型
class SystemStatusResponse(BaseModel):
    """系统状态响应模型"""
    app_name: str
    app_version: str
    status: str
    scheduler: dict
    cameras: dict
    alerts: dict
    frames: dict


class CameraStatusResponse(BaseModel):
    """摄像头状态响应模型"""
    id: int
    camera_id: str
    name: str
    status: str
    location: Optional[str]
    last_frame_time: Optional[datetime]
    
    class Config:
        from_attributes = True


# 创建路由
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    db: AsyncSession = Depends(get_db)
):
    """
    获取系统状态
    """
    try:
        # 获取摄像头统计
        camera_total = await db.scalar(select(func.count(Camera.id)))
        camera_active = await db.scalar(
            select(func.count(Camera.id)).where(Camera.status == "active")
        )

        # 获取警告统计
        alert_total = await db.scalar(select(func.count(Alert.id)))
        alert_unread = await db.scalar(
            select(func.count(Alert.id)).where(Alert.status == "unread")
        )

        # 获取帧统计
        frame_total = await db.scalar(select(func.count(Frame.id)))
        frame_today = await db.scalar(
            select(func.count(Frame.id)).where(
                func.date(Frame.created_at) == today_date()
            )
        )

        # 获取调度器状态
        scheduler_status = get_scheduler_status()

        return {
            "app_name": "VideoWalker",
            "app_version": "1.0.0",
            "status": "running",
            "scheduler": scheduler_status,
            "cameras": {
                "total": camera_total or 0,
                "active": camera_active or 0
            },
            "alerts": {
                "total": alert_total or 0,
                "unread": alert_unread or 0
            },
            "frames": {
                "total": frame_total or 0,
                "today": frame_today or 0
            }
        }
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cameras", response_model=list[CameraStatusResponse])
async def get_all_cameras(
    status: Optional[str] = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有摄像头状态
    """
    try:
        query = select(Camera)
        if status:
            query = query.where(Camera.status == status)
        
        query = query.order_by(Camera.id)
        result = await db.execute(query)
        cameras = result.scalars().all()
        
        return cameras
    except Exception as e:
        logger.error(f"获取摄像头列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cameras/{camera_id}", response_model=CameraStatusResponse)
async def get_camera_status(camera_id: int, db: AsyncSession = Depends(get_db)):
    """
    获取指定摄像头状态
    """
    try:
        query = select(Camera).where(Camera.id == camera_id)
        result = await db.execute(query)
        camera = result.scalar_one_or_none()
        
        if not camera:
            raise HTTPException(status_code=404, detail="摄像头不存在")
        
        return camera
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取摄像头状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot")
async def trigger_snapshot():
    """
    手动触发抽帧任务
    """
    try:
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(status_code=503, detail="调度器未启动")
        await scheduler.trigger_now()
        return {"message": "任务已入队"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发抽帧任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
