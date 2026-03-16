"""Detection task queue model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class DetectionTask(Base):
    """Queued detection task for worker execution."""

    __tablename__ = "detection_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    binding_id = Column(Integer, ForeignKey("camera_scene_bindings.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_version_id = Column(Integer, ForeignKey("scene_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True, comment="pending/running/success/failed")
    retries = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    frame_id = Column(Integer, ForeignKey("frames.id", ondelete="SET NULL"), nullable=True, index=True)
    detection_result_id = Column(Integer, ForeignKey("detection_results.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    camera = relationship("Camera", backref="detection_tasks")
    binding = relationship("CameraSceneBinding", backref="detection_tasks")
    scene_version = relationship("SceneVersion", backref="detection_tasks")
