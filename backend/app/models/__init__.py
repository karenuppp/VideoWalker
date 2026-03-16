"""
数据库模型
"""
from app.models.camera import Camera
from app.models.alert import Alert
from app.models.frame import Frame
from app.models.scene_template import SceneTemplate
from app.models.scene_version import SceneVersion
from app.models.camera_scene_binding import CameraSceneBinding
from app.models.detection_result import DetectionResult
from app.models.alert_event import AlertEvent
from app.models.notification_log import NotificationLog
from app.models.detection_task import DetectionTask

__all__ = [
    "Camera",
    "Alert",
    "Frame",
    "SceneTemplate",
    "SceneVersion",
    "CameraSceneBinding",
    "DetectionResult",
    "AlertEvent",
    "NotificationLog",
    "DetectionTask",
]
