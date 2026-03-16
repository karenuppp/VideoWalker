"""
警告数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Alert(Base):
    """警告模型"""
    
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True, comment="摄像头ID")
    alert_type = Column(String(50), nullable=False, index=True, comment="警告类型/场景：banner/lying_down")
    confidence = Column(Float, comment="AI识别置信度（0.0-1.0）")
    description = Column(Text, comment="详细描述")
    image_path = Column(String(255), nullable=False, comment="图片路径")
    status = Column(String(20), default="unread", index=True, comment="状态：unread/read/resolved")
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True, comment="检测时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    camera = relationship("Camera", backref="alerts")
    
    def __repr__(self):
        return f"<Alert(id={self.id}, camera_id={self.camera_id}, alert_type={self.alert_type}, status={self.status})>"
