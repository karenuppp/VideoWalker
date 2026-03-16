"""
自定义异常类
"""
from fastapi import HTTPException, status


class VideoWalkerException(Exception):
    """基础异常类"""
    pass


class CameraNotFoundException(VideoWalkerException):
    """摄像头不存在异常"""
    pass


class VideoStreamException(VideoWalkerException):
    """视频流异常"""
    pass


class FrameCaptureException(VideoWalkerException):
    """抽帧异常"""
    pass


class AIServiceException(VideoWalkerException):
    """AI服务异常"""
    pass


class DatabaseException(VideoWalkerException):
    """数据库异常"""
    pass


class CMSException(VideoWalkerException):
    """CMS平台异常"""
    pass


def handle_exception(exc: VideoWalkerException) -> HTTPException:
    """
    异常转换为HTTP响应
    
    Args:
        exc: VideoWalkerException异常实例
        
    Returns:
        HTTPException: HTTP响应异常
    """
    error_map = {
        CameraNotFoundException: status.HTTP_404_NOT_FOUND,
        VideoStreamException: status.HTTP_503_SERVICE_UNAVAILABLE,
        FrameCaptureException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        AIServiceException: status.HTTP_503_SERVICE_UNAVAILABLE,
        DatabaseException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        CMSException: status.HTTP_503_SERVICE_UNAVAILABLE,
    }
    
    return HTTPException(
        status_code=error_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR),
        detail=str(exc)
    )