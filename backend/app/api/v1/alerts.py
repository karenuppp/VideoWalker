"""
Alert management API.
"""
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from sqlalchemy import select, and_

from app.database import get_db
from app.services.alert_service import AlertService
from app.utils.logger import logger
from app.models.alert import Alert
from app.models.camera import Camera
from app.models.scene_template import SceneTemplate


class CameraBrief(BaseModel):
    id: int
    camera_id: str
    name: str
    location: Optional[str]
    status: Optional[str]
    last_frame_time: Optional[datetime]

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    camera_id: int
    alert_type: str
    scene_name: Optional[str]
    confidence: Optional[float]
    description: Optional[str]
    image_path: str
    status: str
    detected_at: datetime
    created_at: datetime
    camera: Optional[CameraBrief]

    class Config:
        from_attributes = True


class AlertStatsResponse(BaseModel):
    total: int
    unread: int
    read: int
    resolved: int
    by_type: dict


class UpdateStatusRequest(BaseModel):
    status: str


router = APIRouter(prefix="/alerts", tags=["alerts"])


def _build_alert_view(alert: Alert, camera: Optional[Camera], scene_name: Optional[str]) -> AlertResponse:
    display_scene = scene_name or alert.alert_type
    description = f"检测到{display_scene}"
    return AlertResponse(
        id=alert.id,
        camera_id=alert.camera_id,
        alert_type=alert.alert_type,
        scene_name=scene_name,
        confidence=alert.confidence,
        description=description,
        image_path=alert.image_path,
        status=alert.status,
        detected_at=alert.detected_at,
        created_at=alert.created_at,
        camera=CameraBrief.from_orm(camera) if camera else None,
    )


async def _query_alerts(
    db: AsyncSession,
    skip: int,
    limit: int,
    camera_id: Optional[str],
    status: Optional[str],
    alert_type: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
):
    query = (
        select(Alert, Camera, SceneTemplate.name)
        .join(Camera, Camera.id == Alert.camera_id)
        .outerjoin(SceneTemplate, SceneTemplate.scene_key == Alert.alert_type)
    )

    conditions = []
    if camera_id:
        camera_id_str = str(camera_id)
        if camera_id_str.isdigit():
            conditions.append(Alert.camera_id == int(camera_id_str))
        else:
            conditions.append(Camera.camera_id == camera_id_str)

    if status:
        conditions.append(Alert.status == status.lower())
    if alert_type:
        conditions.append(Alert.alert_type == alert_type)
    if start_date is not None:
        conditions.append(Alert.detected_at >= start_date)
    if end_date is not None:
        conditions.append(Alert.detected_at <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(Alert.detected_at.desc()).offset(skip).limit(limit)
    return (await db.execute(query)).all()


@router.get("", response_model=List[AlertResponse])
async def get_alerts(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Records to return"),
    page: Optional[int] = Query(None, ge=1, description="Page number"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Page size"),
    current: Optional[int] = Query(None, alias="current", ge=1),
    pageSize: Optional[int] = Query(None, alias="pageSize", ge=1, le=100),
    camera_id: Optional[str] = Query(None, description="Camera id or code"),
    status: Optional[str] = Query(None, description="unread/read/resolved"),
    alert_type: Optional[str] = Query(None, description="Alert type filter"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db),
):
    try:
        if pageSize is not None:
            limit = pageSize
        if page_size is not None:
            limit = page_size

        page_index = current or page
        if page_index is not None:
            skip = max(0, (page_index - 1) * limit)

        rows = await _query_alerts(
            db=db,
            skip=skip,
            limit=limit,
            camera_id=camera_id,
            status=status,
            alert_type=alert_type,
            start_date=start_date,
            end_date=end_date,
        )
        return [_build_alert_view(row[0], row[1], row[2]) for row in rows]
    except Exception as e:
        logger.error(f"Get alerts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(db: AsyncSession = Depends(get_db)):
    try:
        alert_service = AlertService(db)
        stats = await alert_service.get_alert_stats()
        return stats
    except Exception as e:
        logger.error(f"Get alert stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    try:
        row = (
            await db.execute(
                select(Alert, Camera, SceneTemplate.name)
                .join(Camera, Camera.id == Alert.camera_id)
                .outerjoin(SceneTemplate, SceneTemplate.scene_key == Alert.alert_type)
                .where(Alert.id == alert_id)
            )
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")

        return _build_alert_view(row[0], row[1], row[2])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get alert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{alert_id}/status", response_model=AlertResponse)
async def update_alert_status(
    alert_id: int,
    request: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        alert_service = AlertService(db)
        await alert_service.update_alert_status(alert_id, request.status)
        row = (
            await db.execute(
                select(Alert, Camera, SceneTemplate.name)
                .join(Camera, Camera.id == Alert.camera_id)
                .outerjoin(SceneTemplate, SceneTemplate.scene_key == Alert.alert_type)
                .where(Alert.id == alert_id)
            )
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        return _build_alert_view(row[0], row[1], row[2])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Update alert status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    try:
        alert_service = AlertService(db)
        success = await alert_service.delete_alert(alert_id)

        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {"message": "Deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete alert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
