"""Admin APIs for camera-scene bindings."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.camera import Camera
from app.models.camera_scene_binding import CameraSceneBinding
from app.models.scene_version import SceneVersion
from app.models.scene_template import SceneTemplate
from app.utils.logger import logger


router = APIRouter(prefix="/admin/policies", tags=["admin-policies"])


class BindingCreateRequest(BaseModel):
    camera_id: int
    scene_version_id: int
    enabled: bool = True
    frame_interval_seconds: Optional[int] = Field(default=None, ge=1)
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    model_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    time_window_start: Optional[str] = Field(default=None, pattern=r"^([01]\\d|2[0-3]):[0-5]\\d$")
    time_window_end: Optional[str] = Field(default=None, pattern=r"^([01]\\d|2[0-3]):[0-5]\\d$")


class BindingUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    frame_interval_seconds: Optional[int] = Field(default=None, ge=1)
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    model_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    time_window_start: Optional[str] = Field(default=None, pattern=r"^([01]\\d|2[0-3]):[0-5]\\d$")
    time_window_end: Optional[str] = Field(default=None, pattern=r"^([01]\\d|2[0-3]):[0-5]\\d$")


class BindingResponse(BaseModel):
    id: int
    camera_id: int
    scene_version_id: int
    enabled: bool
    frame_interval_seconds: Optional[int]
    confidence_threshold: Optional[float]
    model_name: Optional[str]
    time_window_start: Optional[str]
    time_window_end: Optional[str]

    class Config:
        from_attributes = True


class BindingView(BaseModel):
    id: int
    camera_id: int
    camera_name: str
    scene_version_id: int
    scene_key: str
    scene_name: str
    scene_version: str
    scene_model_name: str
    enabled: bool
    frame_interval_seconds: Optional[int]
    confidence_threshold: Optional[float]
    model_name: Optional[str]


@router.get("/bindings", response_model=list[BindingView])
async def list_bindings(
    camera_id: Optional[int] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            CameraSceneBinding.id,
            CameraSceneBinding.camera_id,
            Camera.name,
            CameraSceneBinding.scene_version_id,
            SceneTemplate.scene_key,
            SceneTemplate.name,
            SceneVersion.version,
            SceneVersion.model_name,
            CameraSceneBinding.enabled,
            CameraSceneBinding.frame_interval_seconds,
            CameraSceneBinding.confidence_threshold,
            CameraSceneBinding.model_name,
        )
        .join(Camera, Camera.id == CameraSceneBinding.camera_id)
        .join(SceneVersion, SceneVersion.id == CameraSceneBinding.scene_version_id)
        .join(SceneTemplate, SceneTemplate.id == SceneVersion.scene_template_id)
        .order_by(CameraSceneBinding.id.desc())
    )

    if camera_id is not None:
        query = query.where(CameraSceneBinding.camera_id == camera_id)
    if enabled is not None:
        query = query.where(CameraSceneBinding.enabled.is_(enabled))

    rows = (await db.execute(query)).all()
    return [
        BindingView(
            id=row[0],
            camera_id=row[1],
            camera_name=row[2],
            scene_version_id=row[3],
            scene_key=row[4],
            scene_name=row[5],
            scene_version=row[6],
            scene_model_name=row[7],
            enabled=row[8],
            frame_interval_seconds=row[9],
            confidence_threshold=row[10],
            model_name=row[11],
        )
        for row in rows
    ]


@router.post("/bindings", response_model=BindingResponse)
async def create_binding(
    payload: BindingCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    camera = await db.get(Camera, payload.camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")

    scene_version = await db.get(SceneVersion, payload.scene_version_id)
    if not scene_version:
        raise HTTPException(status_code=404, detail="scene_version not found")

    exists = await db.execute(
        select(CameraSceneBinding).where(
            CameraSceneBinding.camera_id == payload.camera_id,
            CameraSceneBinding.scene_version_id == payload.scene_version_id,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="binding already exists")

    binding = CameraSceneBinding(**payload.model_dump())
    db.add(binding)
    await db.commit()
    await db.refresh(binding)
    return binding


@router.patch("/bindings/{binding_id}", response_model=BindingResponse)
async def update_binding(
    binding_id: int,
    payload: BindingUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    binding = await db.get(CameraSceneBinding, binding_id)
    if not binding:
        raise HTTPException(status_code=404, detail="binding not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return binding

    for key, value in updates.items():
        setattr(binding, key, value)

    try:
        await db.commit()
        await db.refresh(binding)
        return binding
    except Exception as e:
        await db.rollback()
        logger.error(f"Update binding failed: {e}")
        raise HTTPException(status_code=500, detail="update failed")


@router.delete("/bindings/{binding_id}")
async def delete_binding(
    binding_id: int,
    db: AsyncSession = Depends(get_db),
):
    binding = await db.get(CameraSceneBinding, binding_id)
    if not binding:
        raise HTTPException(status_code=404, detail="binding not found")

    await db.delete(binding)
    await db.commit()
    return {"message": "Deleted"}
