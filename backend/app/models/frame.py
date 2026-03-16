"""
抽帧记录数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Frame(Base):
    """抽帧记录模型"""
    
    __tablename__ = "frames"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True, comment="摄像头ID")
    frame_path = Column(String(255), nullable=False, comment="帧存储路径")
    frame_time = Column(DateTime(timezone=True), nullable=False, index=True, comment="帧时间戳")
    ai_processed = Column(Boolean, default=False, comment="是否已AI处理")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    camera = relationship("Camera", backref="frames")
    
    def __repr__(self):
        return f"<Frame(id={self.id}, camera_id={self.camera_id}, frame_time={self.frame_time}, ai_processed={self.ai_processed})>"