"""
Camera model.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class Camera(Base):
    """Camera table."""

    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(String(50), unique=True, nullable=False, index=True, comment="Camera ID")
    name = Column(String(100), nullable=False, comment="Camera name")
    cms_url = Column(String(255), nullable=False, comment="CMS base URL")
    username = Column(String(50), nullable=False, comment="Camera username")
    password = Column(String(255), nullable=False, comment="Camera password (encrypted)")
    location = Column(String(100), comment="Camera location")
    stream_protocol = Column(String(20), default="rtsp", comment="Stream protocol, e.g. rtsp")
    scenes = Column(JSON, default=list, comment="Legacy scene list fallback, e.g. ['banner']")
    status = Column(String(20), default="active", comment="Status: active/inactive/error")
    last_frame_time = Column(DateTime(timezone=True), comment="Last frame time")
    stream_url = Column(Text, comment="Cached stream URL")
    stream_url_updated_at = Column(DateTime(timezone=True), comment="Stream URL updated time")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Created time")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Updated time")

    def __repr__(self):
        return f"<Camera(id={self.id}, camera_id={self.camera_id}, name={self.name}, scenes={self.scenes})>"
