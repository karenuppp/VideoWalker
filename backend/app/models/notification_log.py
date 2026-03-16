"""Notification delivery log model."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class NotificationLog(Base):
    """Notification logs for alert delivery."""

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(32), nullable=False, comment="websocket/email/sms")
    recipient = Column(String(128), nullable=True)
    status = Column(String(20), nullable=False, default="sent")
    payload = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    alert = relationship("Alert", backref="notification_logs")
