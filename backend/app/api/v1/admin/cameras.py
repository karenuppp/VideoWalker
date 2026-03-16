"""Admin camera management APIs (MVP)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import Alert
from app.models.alert_event import AlertEvent
from app.models.camera import Camera
from app.models.camera_scene_binding import CameraSceneBinding
from app.models.detection_result import DetectionResult
from app.models.detection_task import DetectionTask
from app.models.frame import Frame
from app.models.notification_log import NotificationLog
from app.models.scene_template import SceneTemplate
from app.models.scene_version import SceneVersion


router = APIRouter(prefix="/admin/cameras", tags=["admin-cameras"])


class CameraCreateRequest(BaseModel):
    camera_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    rtsp_url: str = Field(..., min_length=1, max_length=500)
    enabled: bool = True


class CameraUpdateRequest(BaseModel):
    camera_id: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    rtsp_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    enabled: Optional[bool] = None


class CameraResponse(BaseModel):
    id: int
    camera_id: str
    name: str
    rtsp_url: Optional[str]
    enabled: bool


class CameraSceneAssignRequest(BaseModel):
    scene_id: int
    frame_interval_seconds: Optional[int] = Field(default=30, ge=1, le=3600)


class CameraSceneBindingView(BaseModel):
    binding_id: int
    scene_id: int
    scene_name: str
    scene_key: str
    enabled: bool
    frame_interval_seconds: Optional[int]


@router.get("", response_model=list[CameraResponse])
async def list_cameras(
    enabled: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Camera).order_by(Camera.id.desc())
    if enabled is not None:
        query = query.where(Camera.status == ("active" if enabled else "inactive"))
    rows = (await db.execute(query)).scalars().all()
    return [
        CameraResponse(
            id=row.id,
            camera_id=row.camera_id,
            name=row.name,
            rtsp_url=row.stream_url,
            enabled=row.status == "active",
        )
        for row in rows
    ]


@router.post("", response_model=CameraResponse)
async def create_camera(
    payload: CameraCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    exists = (await db.execute(select(Camera).where(Camera.camera_id == payload.camera_id))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="camera_id already exists")

    camera = Camera(
        camera_id=payload.camera_id,
        name=payload.name,
        cms_url=payload.rtsp_url,
        username="",
        password="",
        location=None,
        stream_protocol="rtsp",
        scenes=[],
        status="active" if payload.enabled else "inactive",
        stream_url=payload.rtsp_url,
    )
    db.add(camera)
    await db.commit()
    await db.refresh(camera)

    return CameraResponse(
        id=camera.id,
        camera_id=camera.camera_id,
        name=camera.name,
        rtsp_url=camera.stream_url,
        enabled=camera.status == "active",
    )


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    payload: CameraUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")

    updates = payload.model_dump(exclude_unset=True)
    if "camera_id" in updates and updates["camera_id"]:
        camera.camera_id = updates["camera_id"]
    if "name" in updates and updates["name"]:
        camera.name = updates["name"]
    if "rtsp_url" in updates and updates["rtsp_url"]:
        camera.stream_url = updates["rtsp_url"]
        camera.cms_url = updates["rtsp_url"]
    if "enabled" in updates and updates["enabled"] is not None:
        camera.status = "active" if updates["enabled"] else "inactive"

    await db.commit()
    await db.refresh(camera)
    return CameraResponse(
        id=camera.id,
        camera_id=camera.camera_id,
        name=camera.name,
        rtsp_url=camera.stream_url,
        enabled=camera.status == "active",
    )


@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")

    alert_ids = (
        await db.execute(select(Alert.id).where(Alert.camera_id == camera_id))
    ).scalars().all()
    if alert_ids:
        await db.execute(delete(AlertEvent).where(AlertEvent.alert_id.in_(alert_ids)))
        await db.execute(delete(NotificationLog).where(NotificationLog.alert_id.in_(alert_ids)))

    await db.execute(delete(DetectionResult).where(DetectionResult.camera_id == camera_id))
    await db.execute(delete(DetectionTask).where(DetectionTask.camera_id == camera_id))
    await db.execute(delete(Frame).where(Frame.camera_id == camera_id))
    await db.execute(delete(CameraSceneBinding).where(CameraSceneBinding.camera_id == camera_id))
    await db.execute(delete(Alert).where(Alert.camera_id == camera_id))

    await db.delete(camera)
    await db.commit()
    return {"message": "Deleted"}


@router.get("/{camera_id}/scenes", response_model=list[CameraSceneBindingView])
async def list_camera_scenes(camera_id: int, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")

    query = (
        select(
            CameraSceneBinding.id,
            SceneTemplate.id,
            SceneTemplate.name,
            SceneTemplate.scene_key,
            CameraSceneBinding.enabled,
            CameraSceneBinding.frame_interval_seconds,
        )
        .join(SceneVersion, SceneVersion.id == CameraSceneBinding.scene_version_id)
        .join(SceneTemplate, SceneTemplate.id == SceneVersion.scene_template_id)
        .where(CameraSceneBinding.camera_id == camera_id)
        .order_by(CameraSceneBinding.id.desc())
    )
    rows = (await db.execute(query)).all()
    return [
        CameraSceneBindingView(
            binding_id=row[0],
            scene_id=row[1],
            scene_name=row[2],
            scene_key=row[3],
            enabled=row[4],
            frame_interval_seconds=row[5],
        )
        for row in rows
    ]


@router.post("/{camera_id}/scenes")
async def assign_scene_to_camera(
    camera_id: int,
    payload: CameraSceneAssignRequest,
    db: AsyncSession = Depends(get_db),
):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")
    if camera.status != "active":
        raise HTTPException(status_code=400, detail="only enabled camera can assign scenes")

    template = await db.get(SceneTemplate, payload.scene_id)
    if not template:
        raise HTTPException(status_code=404, detail="scene not found")

    version = (
        await db.execute(
            select(SceneVersion)
            .where(SceneVersion.scene_template_id == template.id)
            .order_by(SceneVersion.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=400, detail="scene has no available version")

    exists = (
        await db.execute(
            select(CameraSceneBinding).where(
                CameraSceneBinding.camera_id == camera_id,
                CameraSceneBinding.scene_version_id == version.id,
            )
        )
    ).scalar_one_or_none()
    if exists:
        exists.enabled = True
        exists.frame_interval_seconds = payload.frame_interval_seconds
        await db.commit()
        return {"message": "updated", "binding_id": exists.id}

    binding = CameraSceneBinding(
        camera_id=camera_id,
        scene_version_id=version.id,
        enabled=True,
        frame_interval_seconds=payload.frame_interval_seconds,
        confidence_threshold=None,
        model_name=None,
    )
    db.add(binding)
    await db.commit()
    await db.refresh(binding)
    return {"message": "created", "binding_id": binding.id}


@router.delete("/{camera_id}/scenes/{binding_id}")
async def unassign_scene_from_camera(
    camera_id: int,
    binding_id: int,
    db: AsyncSession = Depends(get_db),
):
    binding = await db.get(CameraSceneBinding, binding_id)
    if not binding or binding.camera_id != camera_id:
        raise HTTPException(status_code=404, detail="binding not found")
    await db.delete(binding)
    await db.commit()
    return {"message": "Deleted"}
