"""Scene configuration definitions."""
from enum import Enum
from typing import Dict, Optional


class SceneType(str, Enum):
    """Supported scene types."""

    BANNER = "banner"
    LYING_DOWN = "lying_down"


class SceneConfig:
    """Scene config registry."""

    SCENES: Dict[SceneType, Dict] = {
        SceneType.BANNER: {
            "name": "拉横幅",
            "name_en": "Banner Detection",
            "description": "检测画面是否存在横幅、条幅、标语布条",
            "system_prompt": "YOLO model detection for banner scene.",
            "detector_type": "yolo",
            "default_model_name": "yolo-banner-v1",
            "color": "#1677ff",
            "icon": "🚩",
        },
        SceneType.LYING_DOWN: {
            "name": "躺地",
            "name_en": "Lying Down Detection",
            "description": "检测人员躺倒、卧地状态",
            "system_prompt": "YOLO model detection for lying-down scene.",
            "detector_type": "yolo",
            "default_model_name": "yolo-lying-v1",
            "color": "#4096ff",
            "icon": "🛌",
        },
    }

    @classmethod
    def get_scene_config(cls, scene_type: SceneType) -> Optional[Dict]:
        return cls.SCENES.get(scene_type)

    @classmethod
    def get_scene_name(cls, scene_type: SceneType) -> str:
        config = cls.get_scene_config(scene_type)
        return config["name"] if config else str(scene_type)
