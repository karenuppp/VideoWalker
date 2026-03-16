"""Scene template model."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func

from app.database import Base


class SceneTemplate(Base):
    """Scene template table."""

    __tablename__ = "scene_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scene_key = Column(String(64), unique=True, nullable=False, index=True, comment="Scene key")
    name = Column(String(128), nullable=False, comment="Scene name")
    description = Column(Text, comment="Scene description")
    detect_api = Column(String(255), nullable=True, comment="Detection API endpoint for this scene")
    is_active = Column(Boolean, default=True, nullable=False, comment="Template active status")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Created time")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Updated time")
