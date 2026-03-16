"""Scene version model."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class SceneVersion(Base):
    """Scene version table."""

    __tablename__ = "scene_versions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scene_template_id = Column(Integer, ForeignKey("scene_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(32), nullable=False, comment="Version label")
    detector_type = Column(String(20), nullable=False, default="yolo", comment="Detector type, e.g. yolo")
    model_name = Column(String(128), nullable=False, comment="Default model name for this scene version")
    prompt = Column(Text, nullable=False, comment="Prompt text")
    confidence_threshold = Column(Float, default=0.7, comment="Default confidence threshold")
    params = Column(JSON, default=dict, comment="Scene params")
    is_published = Column(Boolean, default=False, nullable=False, comment="Published status")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Created time")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Updated time")

    scene_template = relationship("SceneTemplate", backref="versions")
