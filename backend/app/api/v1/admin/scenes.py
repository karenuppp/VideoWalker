"""Admin APIs for scene management (camera-bound)."""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.camera import Camera
from app.models.camera_scene_binding import CameraSceneBinding
from app.models.detection_result import DetectionResult
from app.models.detection_task import DetectionTask
from app.models.scene_template import SceneTemplate
from app.models.scene_version import SceneVersion


router = APIRouter(prefix="/admin/scenes", tags=["admin-scenes"])


def _to_scene_key(name: str) -> str:
    key = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    return key or "scene"


class SceneCreateRequest(BaseModel):
    camera_id: int
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    detect_api: str = Field(..., min_length=1, max_length=255)
    frame_interval_seconds: Optional[int] = Field(default=None, ge=1)
    model_name: Optional[str] = Field(default=None, min_length=1, max_length=128)


class SceneUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    description: Optional[str] = None
    detect_api: Optional[str] = Field(default=None, min_length=1, max_length=255)
    enabled: Optional[bool] = None
    frame_interval_seconds: Optional[int] = Field(default=None, ge=1)
    model_name: Optional[str] = Field(default=None, min_length=1, max_length=128)


class SceneResponse(BaseModel):
    id: int
    camera_id: int
    camera_name: str
    scene_key: str
    name: str
    description: Optional[str]
    detect_api: Optional[str]
    enabled: bool
    frame_interval_seconds: Optional[int]
    model_name: Optional[str]


@router.get("", response_model=list[SceneResponse])
async def list_scenes(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(
                CameraSceneBinding.id,
                Camera.id,
                Camera.name,
                SceneTemplate.scene_key,
                SceneTemplate.name,
                SceneTemplate.description,
                SceneTemplate.detect_api,
                CameraSceneBinding.enabled,
                CameraSceneBinding.frame_interval_seconds,
                CameraSceneBinding.model_name,
                SceneVersion.model_name,
            )
            .join(Camera, Camera.id == CameraSceneBinding.camera_id)
            .join(SceneVersion, SceneVersion.id == CameraSceneBinding.scene_version_id)
            .join(SceneTemplate, SceneTemplate.id == SceneVersion.scene_template_id)
            .order_by(CameraSceneBinding.id.desc())
        )
    ).all()

    return [
        SceneResponse(
            id=row[0],
            camera_id=row[1],
            camera_name=row[2],
            scene_key=row[3],
            name=row[4],
            description=row[5],
            detect_api=row[6],
            enabled=row[7],
            frame_interval_seconds=row[8],
            model_name=row[9] or row[10],
        )
        for row in rows
    ]


@router.post("", response_model=SceneResponse)
async def create_scene(payload: SceneCreateRequest, db: AsyncSession = Depends(get_db)):
    camera = await db.get(Camera, payload.camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")

    scene_key_base = _to_scene_key(payload.name)
    scene_key = scene_key_base
    suffix = 1
    while True:
        exists = (
            await db.execute(select(SceneTemplate).where(SceneTemplate.scene_key == scene_key))
        ).scalar_one_or_none()
        if not exists:
            break
        suffix += 1
        scene_key = f"{scene_key_base}_{suffix}"

    template = SceneTemplate(
        scene_key=scene_key,
        name=payload.name,
        description=payload.description,
        detect_api=payload.detect_api,
        is_active=True,
    )
    db.add(template)
    await db.flush()

    model_name = payload.model_name or scene_key

    version = SceneVersion(
        scene_template_id=template.id,
        version="v1",
        detector_type="yolo",
        model_name=model_name,
        prompt=payload.description or payload.name,
        confidence_threshold=0.7,
        params={},
        is_published=True,
    )
    db.add(version)
    await db.flush()

    binding = CameraSceneBinding(
        camera_id=payload.camera_id,
        scene_version_id=version.id,
        enabled=True,
        frame_interval_seconds=payload.frame_interval_seconds,
        model_name=payload.model_name,
    )
    db.add(binding)

    await db.commit()
    await db.refresh(binding)
    await db.refresh(template)

    return SceneResponse(
        id=binding.id,
        camera_id=camera.id,
        camera_name=camera.name,
        scene_key=template.scene_key,
        name=template.name,
        description=template.description,
        detect_api=template.detect_api,
        enabled=binding.enabled,
        frame_interval_seconds=binding.frame_interval_seconds,
        model_name=binding.model_name or version.model_name,
    )


@router.put("/{scene_id}", response_model=SceneResponse)
@router.patch("/{scene_id}", response_model=SceneResponse)
async def update_scene(
    scene_id: int,
    payload: SceneUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    binding = await db.get(CameraSceneBinding, scene_id)
    if not binding:
        raise HTTPException(status_code=404, detail="scene not found")

    scene_version = await db.get(SceneVersion, binding.scene_version_id)
    template = await db.get(SceneTemplate, scene_version.scene_template_id) if scene_version else None
    if not scene_version or not template:
        raise HTTPException(status_code=404, detail="scene template not found")

    camera = await db.get(Camera, binding.camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"]:
        template.name = updates["name"]
    if "description" in updates:
        template.description = updates["description"]
    if "detect_api" in updates and updates["detect_api"]:
        template.detect_api = updates["detect_api"]
    if "enabled" in updates and updates["enabled"] is not None:
        binding.enabled = updates["enabled"]
    if "frame_interval_seconds" in updates:
        binding.frame_interval_seconds = updates["frame_interval_seconds"]
    if "model_name" in updates and updates["model_name"]:
        binding.model_name = updates["model_name"]
        scene_version.model_name = updates["model_name"]

    scene_version.prompt = template.description or template.name

    await db.commit()
    await db.refresh(binding)
    await db.refresh(template)

    return SceneResponse(
        id=binding.id,
        camera_id=camera.id,
        camera_name=camera.name,
        scene_key=template.scene_key,
        name=template.name,
        description=template.description,
        detect_api=template.detect_api,
        enabled=binding.enabled,
        frame_interval_seconds=binding.frame_interval_seconds,
        model_name=binding.model_name or scene_version.model_name,
    )


@router.delete("/{scene_id}")
async def delete_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    binding = await db.get(CameraSceneBinding, scene_id)
    if not binding:
        raise HTTPException(status_code=404, detail="scene not found")

    scene_version = await db.get(SceneVersion, binding.scene_version_id)
    template_id = scene_version.scene_template_id if scene_version else None

    await db.execute(delete(DetectionTask).where(DetectionTask.binding_id == binding.id))
    await db.execute(delete(DetectionResult).where(DetectionResult.binding_id == binding.id))
    await db.delete(binding)
    await db.flush()

    if scene_version:
        remaining = await db.scalar(
            select(func.count(CameraSceneBinding.id)).where(
                CameraSceneBinding.scene_version_id == scene_version.id
            )
        )
        if not remaining:
            await db.execute(
                delete(DetectionTask).where(DetectionTask.scene_version_id == scene_version.id)
            )
            await db.execute(
                delete(DetectionResult).where(DetectionResult.scene_version_id == scene_version.id)
            )
            other_versions = await db.scalar(
                select(func.count(SceneVersion.id)).where(
                    SceneVersion.scene_template_id == template_id,
                    SceneVersion.id != scene_version.id,
                )
            )
            await db.delete(scene_version)
            if template_id and (other_versions or 0) == 0:
                template = await db.get(SceneTemplate, template_id)
                if template:
                    await db.delete(template)

    await db.commit()
    return {"message": "Deleted"}
