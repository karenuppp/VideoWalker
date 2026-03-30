from typing import Dict, Optional
import httpx
from app.models.camera import Camera
from app.utils.logger import logger
from app.utils.exceptions import VideoStreamException
from app.config import settings
from app.utils.time import now


class VideoService:

    def __init__(self):
        self.timeout = 10
        self.client = httpx.AsyncClient(timeout=self.timeout)
        self.active_seconds = 72 * 24 * 60 * 60  # 72天

    async def get_stream_url(
        self,
        token: str,
        camera_id: str,
        db,
        active_second: int = 72 * 24 * 60 * 60,
        stream: Optional[str] = None,
        network: str = "LAN",
    ) -> Optional[Dict]:
        from sqlalchemy import select

        stmt = select(Camera).where(Camera.camera_id == camera_id)
        result = await db.execute(stmt)
        camera = result.scalar_one_or_none()

        # 检查是否需要重新获取RTSP地址
        need_fetch = True
        if camera and camera.stream_url and camera.stream_url_updated_at:
            elapsed = now() - camera.stream_url_updated_at
            if elapsed.total_seconds() < self.active_seconds:
                need_fetch = False
                logger.info(f"使用缓存的播放URL: {camera_id}, 已缓存 {elapsed.total_seconds() / 86400:.1f} 天")
                return {"stream_url": camera.stream_url}

        if need_fetch:
            logger.info(f"重新获取播放URL: {camera_id}")

        url = f"{settings.CMS_BASE_URL}/channels/{camera_id}/play"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {"active_second": active_second, "network": network}
        if stream:
            payload["stream"] = stream

        try:
            response = await self.client.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                result = response.json()

                # 更新数据库中的stream_url和获取时间
                stream_url = result.get("stream_url") or result.get("url", "")
                if camera and stream_url:
                    camera.stream_url = stream_url
                    camera.stream_url_updated_at = now()
                    await db.commit()
                    logger.info(f"已更新并缓存播放URL: {camera_id}")

                return result
            else:
                error_msg = f"获取播放URL失败: HTTP {response.status_code}"
                logger.error(error_msg)
                raise VideoStreamException(error_msg)

        except httpx.TimeoutException:
            logger.error(f"请求超时: {camera_id}")
            raise VideoStreamException(f"请求超时")
        except httpx.HTTPError as e:
            logger.error(f"HTTP错误: {e}")
            raise VideoStreamException(f"HTTP错误: {str(e)}")
        except Exception as e:
            logger.error(f"获取播放URL异常: {e}")
            raise VideoStreamException(f"请求异常: {str(e)}")

    async def close(self):
        await self.client.aclose()
