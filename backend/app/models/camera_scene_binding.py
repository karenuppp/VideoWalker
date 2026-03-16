"""Camera scene binding model."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class CameraSceneBinding(Base):
    """Binding table for camera and scene version."""

    __tablename__ = "camera_scene_bindings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_version_id = Column(Integer, ForeignKey("scene_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    frame_interval_seconds = Column(Integer, nullable=True, comment="Optional override interval")
    confidence_threshold = Column(Float, nullable=True, comment="Optional override threshold")
    model_name = Column(String(128), nullable=True, comment="Optional model override for binding")
    last_run_at = Column(DateTime(timezone=True), nullable=True, comment="Last executed time for interval control")
    time_window_start = Column(String(5), nullable=True, comment="Start HH:MM")
    time_window_end = Column(String(5), nullable=True, comment="End HH:MM")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Created time")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Updated time")

    camera = relationship("Camera", backref="scene_bindings")
    scene_version = relationship("SceneVersion", backref="camera_bindings")
