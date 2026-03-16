"""Detection result model."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class DetectionResult(Base):
    """Structured AI detection result."""

    __tablename__ = "detection_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    frame_id = Column(Integer, ForeignKey("frames.id", ondelete="SET NULL"), nullable=True, index=True)
    binding_id = Column(Integer, ForeignKey("camera_scene_bindings.id", ondelete="SET NULL"), nullable=True, index=True)
    scene_version_id = Column(Integer, ForeignKey("scene_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    scene_key = Column(String(64), nullable=False, index=True)
    detected = Column(Boolean, nullable=False, default=False, index=True)
    confidence = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    details = Column(JSON, default=dict, comment="Structured result details")
    image_path = Column(String(255), nullable=False)
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    camera = relationship("Camera", backref="detection_results")
    frame = relationship("Frame", backref="detection_results")
