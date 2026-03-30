"""
日志管理工具
"""
import sys
from pathlib import Path
from loguru import logger
from app.config import settings


def setup_logger():
    """配置日志系统"""
    
    # 移除默认处理器
    logger.remove()
    
    # 控制台处理器
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    # 文件处理器
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        settings.LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )

    # 目标数量预警日志（仅记录count场景超阈值）
    count_log_path = Path(settings.COUNT_ALERT_LOG_FILE)
    count_log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        settings.COUNT_ALERT_LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: record["extra"].get("count_alert") is True,
    )
    
    return logger


# 初始化日志
logger = setup_logger()
