"""
Alert service.
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.alert_event import AlertEvent
from app.models.notification_log import NotificationLog
from sqlalchemy import delete
from app.models.camera import Camera
from app.models.scene_template import SceneTemplate
from app.config import settings
from app.utils.logger import logger
from app.utils.exceptions import DatabaseException
from app.services.websocket_service import WebSocketService


class  AlertService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_alert(
        self,
        camera_id: int,
        detection_result: Dict,
        image_path: str,
        detected_at: Optional[datetime] = None,
        alert_type: Optional[str] = None,
    ) -> Alert:
        try:
            if detected_at is None:
                detected_at = datetime.now(timezone(timedelta(hours=8)))

            alert_type_value = alert_type or detection_result.get("scene_type") or "other"
            dedup_cutoff = detected_at - timedelta(seconds=settings.ALERT_DEDUP_SECONDS)
            existing_query = (
                select(Alert)
                .where(
                    Alert.camera_id == camera_id,
                    Alert.alert_type == alert_type_value,
                    Alert.status.in_(["unread", "read"]),
                    Alert.detected_at >= dedup_cutoff,
                )
                .order_by(Alert.detected_at.desc())
                .limit(1)
            )
            existing_alert = (await self.db.execute(existing_query)).scalar_one_or_none()
            if existing_alert:
                previous_detected_at = existing_alert.detected_at
                existing_alert.confidence = detection_result.get(
                    "confidence", existing_alert.confidence
                )
                existing_alert.description = detection_result.get(
                    "description", existing_alert.description
                )
                existing_alert.image_path = image_path
                existing_alert.detected_at = detected_at
                self.db.add(
                    AlertEvent(
                        alert_id=existing_alert.id,
                        action="merged",
                        from_status=existing_alert.status,
                        to_status=existing_alert.status,
                        note=(
                            "Merged duplicate detection in dedup window "
                            f"({settings.ALERT_DEDUP_SECONDS}s), previous_detected_at={previous_detected_at}"
                        ),
                    )
                )
                await self.db.commit()
                await self.db.refresh(existing_alert)
                return existing_alert

            alert = Alert(
                camera_id=camera_id,
                alert_type=alert_type_value,
                confidence=detection_result.get("confidence", 0.0),
                description=detection_result.get("description", ""),
                image_path=image_path,
                status="unread",
                detected_at=detected_at,
            )

            self.db.add(alert)
            await self.db.commit()
            await self.db.refresh(alert)
            self.db.add(
                AlertEvent(
                    alert_id=alert.id,
                    action="created",
                    from_status=None,
                    to_status="unread",
                    note="Alert created by detection pipeline",
                )
            )
            await self.db.commit()

            try:
                scene = None
                if alert.alert_type:
                    scene = (
                        await self.db.execute(
                            select(SceneTemplate).where(SceneTemplate.scene_key == alert.alert_type)
                        )
                    ).scalar_one_or_none()
                camera = await self.db.get(Camera, camera_id)
                scene_name = scene.name if scene else None
                display_scene = scene_name or alert.alert_type
                websocket_service = WebSocketService()
                await websocket_service.broadcast_alert(
                    {
                        "id": alert.id,
                        "camera_id": alert.camera_id,
                        "alert_type": alert.alert_type,
                        "scene_name": scene_name,
                        "confidence": alert.confidence,
                        "description": f"检测到{display_scene}",
                        "image_path": alert.image_path,
                        "status": alert.status,
                        "detected_at": alert.detected_at.isoformat()
                        if alert.detected_at
                        else None,
                        "created_at": alert.created_at.isoformat() if alert.created_at else None,
                        "camera": {
                            "id": camera.id,
                            "camera_id": camera.camera_id,
                            "name": camera.name,
                            "location": camera.location,
                            "status": camera.status,
                            "last_frame_time": camera.last_frame_time.isoformat()
                            if camera.last_frame_time
                            else None,
                        }
                        if camera
                        else None,
                    }
                )
            except Exception as e:
                logger.warning(f"WebSocket broadcast failed: {e}")

            logger.info(
                f"Alert created: alert_id={alert.id}, camera_id={camera_id}"
            )
            return alert

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Create alert failed: {e}")
            raise DatabaseException(f"Create alert failed: {str(e)}")

    async def get_alerts(
        self,
        skip: int = 0,
        limit: int = 20,
        camera_id: Optional[str] = None,
        status: Optional[str] = None,
        alert_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Alert]:
        try:
            query = select(Alert)

            conditions = []
            if camera_id:
                camera_id_str = str(camera_id)
                if camera_id_str.isdigit():
                    conditions.append(Alert.camera_id == int(camera_id_str))
                else:
                    query = query.join(Camera)
                    conditions.append(Camera.camera_id == camera_id_str)

            if status:
                conditions.append(Alert.status == status.lower())
            if alert_type:
                conditions.append(Alert.alert_type == alert_type)
            if start_date is not None:
                conditions.append(Alert.detected_at >= start_date)
            if end_date is not None:
                conditions.append(Alert.detected_at <= end_date)

            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(Alert.detected_at.desc())
            query = query.offset(skip).limit(limit)

            result = await self.db.execute(query)
            alerts = result.scalars().all()

            logger.info(f"Get alerts success: count={len(alerts)}")
            return alerts

        except Exception as e:
            logger.error(f"Get alerts failed: {e}")
            raise DatabaseException(f"Get alerts failed: {str(e)}")

    async def get_alert_by_id(self, alert_id: int) -> Optional[Alert]:
        try:
            query = select(Alert).where(Alert.id == alert_id)
            result = await self.db.execute(query)
            alert = result.scalar_one_or_none()

            if alert:
                logger.info(f"Get alert success: alert_id={alert_id}")
            else:
                logger.warning(f"Alert not found: alert_id={alert_id}")

            return alert

        except Exception as e:
            logger.error(f"Get alert failed: {e}")
            raise DatabaseException(f"Get alert failed: {str(e)}")

    async def update_alert_status(self, alert_id: int, status: str) -> Alert:
        try:
            valid_statuses = ["unread", "read", "resolved"]
            status_value = status.lower()
            if status_value not in valid_statuses:
                raise ValueError(
                    f"Invalid status: {status}. Valid: {valid_statuses}"
                )

            alert = await self.get_alert_by_id(alert_id)
            if not alert:
                raise DatabaseException(f"Alert not found: alert_id={alert_id}")

            previous_status = alert.status
            alert.status = status_value
            self.db.add(
                AlertEvent(
                    alert_id=alert.id,
                    action="status_updated",
                    from_status=previous_status,
                    to_status=status_value,
                    note="Alert status updated",
                )
            )
            await self.db.commit()
            await self.db.refresh(alert)

            try:
                websocket_service = WebSocketService()
                await websocket_service.broadcast_alert_update(alert_id, status_value)
            except Exception as e:
                logger.warning(f"WebSocket broadcast failed: {e}")

            logger.info(
                f"Update alert status success: alert_id={alert_id}, status={status_value}"
            )
            return alert

        except ValueError as e:
            logger.error(f"Update alert status failed: {e}")
            raise DatabaseException(str(e))
        except DatabaseException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Update alert status failed: {e}")
            raise DatabaseException(f"Update alert status failed: {str(e)}")

    async def get_alert_stats(self) -> Dict:
        try:
            total_query = select(func.count(Alert.id))
            total_result = await self.db.execute(total_query)
            total = total_result.scalar()

            unread_query = select(func.count(Alert.id)).where(
                Alert.status == "unread"
            )
            unread_result = await self.db.execute(unread_query)
            unread = unread_result.scalar()

            read_query = select(func.count(Alert.id)).where(Alert.status == "read")
            read_result = await self.db.execute(read_query)
            read = read_result.scalar()

            resolved_query = select(func.count(Alert.id)).where(
                Alert.status == "resolved"
            )
            resolved_result = await self.db.execute(resolved_query)
            resolved = resolved_result.scalar()

            type_query = select(
                Alert.alert_type, func.count(Alert.id)
            ).group_by(Alert.alert_type)
            type_result = await self.db.execute(type_query)
            by_type = {row[0]: row[1] for row in type_result.all()}

            stats = {
                "total": total,
                "unread": unread,
                "read": read,
                "resolved": resolved,
                "by_type": by_type,
            }

            logger.info(f"Get alert stats success: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Get alert stats failed: {e}")
            raise DatabaseException(f"Get alert stats failed: {str(e)}")

    async def delete_alert(self, alert_id: int) -> bool:
        try:
            alert = await self.get_alert_by_id(alert_id)
            if not alert:
                logger.warning(f"Alert not found: alert_id={alert_id}")
                return False

            await self.db.execute(delete(AlertEvent).where(AlertEvent.alert_id == alert_id))
            await self.db.execute(delete(NotificationLog).where(NotificationLog.alert_id == alert_id))
            await self.db.delete(alert)
            await self.db.commit()

            logger.info(f"Delete alert success: alert_id={alert_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Delete alert failed: {e}")
            raise DatabaseException(f"Delete alert failed: {str(e)}")
