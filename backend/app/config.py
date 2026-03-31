from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):

    APP_NAME: str = "VideoWalker"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_NAME: str = "videowalker"
    DB_CHARSET: str = "utf8mb4"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset={self.DB_CHARSET}"
        )

    YOLO_API_URL: str = "http://localhost:9001/infer"
    YOLO_API_KEY: str = ""
    YOLO_TIMEOUT: int = 20

    CMS_BASE_URL: Optional[str] = None
    CMS_USERNAME: Optional[str] = None
    CMS_PASSWORD: Optional[str] = None
    CMS_TOKEN: Optional[str] = None
    CMS_TIMEOUT: int = 30

    VIDEO_FRAME_INTERVAL: Optional[int] = None
    FRAME_INTERVAL: int = 30
    FRAME_STORAGE_PATH: str = "./storage/frames"
    FRAME_SKIP_FRAMES: int = 5
    FRAME_GRAB_MODE: str = "iframe"
    FRAME_GRAB_DELAY_SECONDS: float = 0.0
    RTSP_TRANSPORT: str = "tcp"
    RTSP_TIMEOUT: int = 10

    MAX_CONCURRENT_CAMERAS: int = 10
    MAX_CONCURRENT_DETECTIONS: int = 5
    ALERT_DEDUP_SECONDS: int = 300
    QUEUE_WORKER_COUNT: int = 3
    TASK_MAX_RETRIES: int = 0
    TASK_POLL_INTERVAL_SECONDS: float = 0.5
    ENQUEUE_TICK_SECONDS: float = 5.0

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/videowalker.log"
    COUNT_ALERT_LOG_FILE: str = "./logs/count_alerts.log"

    CORS_ORIGINS: list = [
        "http://localhost:80",
        "http://localhost:3000",
        "http://127.0.0.1:80",
        "http://127.0.0.1:3000",
    ]

    DEFAULT_SCENES: list[str] = ["banner", "lying_down"]

    @property
    def FRAME_INTERVAL_VALUE(self) -> int:
        return self.VIDEO_FRAME_INTERVAL or self.FRAME_INTERVAL

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        case_sensitive=True
    )


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
