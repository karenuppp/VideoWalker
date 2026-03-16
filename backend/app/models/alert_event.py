"""Alert event model."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class AlertEvent(Base):
    """Alert status transition event."""

    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id = Column(Integer, nullable=True, index=True)
    action = Column(String(64), nullable=False, comment="Action type")
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    alert = relationship("Alert", backref="events")
