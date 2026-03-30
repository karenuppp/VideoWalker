import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from app.utils.logger import logger
from app.utils.exceptions import FrameCaptureException
from app.config import settings
from app.utils.time import now


class FrameService:

    def __init__(self, storage_path: Optional[str] = None, max_workers: int = 4):
        self.storage_path = Path(storage_path or settings.FRAME_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path = "ffmpeg"
        self.timeout = settings.RTSP_TIMEOUT
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"FrameService初始化完成，进程池大小: {max_workers}")

    def _generate_frame_path(self, camera_id: str, timestamp: datetime) -> str:
        date_path = self.storage_path / timestamp.strftime("%Y/%m/%d")
        date_path.mkdir(parents=True, exist_ok=True)
        filename = f"{camera_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        return str(date_path / filename)

    def _sync_capture_frame(
        self, stream_url: str, frame_path: str
    ) -> Tuple[int, str, str]:
        transport = settings.RTSP_TRANSPORT
        if transport not in {"tcp", "udp", "udp_multicast", "http", "https"}:
            logger.warning(f"非法RTSP_TRANSPORT配置: {transport}, 已回退为tcp")
            transport = "tcp"
        cmd = [
            self.ffmpeg_path,
            "-rtsp_transport",
            transport,
            "-rtsp_flags",
            "prefer_tcp",
            "-stimeout",
            str(int(self.timeout * 1000000)),
            "-i",
            stream_url,
        ]

        delay_seconds = float(settings.FRAME_GRAB_DELAY_SECONDS or 0.0)
        if delay_seconds > 0:
            cmd += ["-ss", f"{delay_seconds:.3f}"]

        grab_mode = (settings.FRAME_GRAB_MODE or "none").lower()
        if grab_mode == "iframe":
            cmd += [
                "-vf",
                "select=eq(pict_type\\,I)",
                "-vsync",
                "vfr",
            ]
        elif grab_mode == "skip":
            skip_frames = max(0, int(settings.FRAME_SKIP_FRAMES or 0))
            if skip_frames > 0:
                cmd += [
                    "-vf",
                    f"select=eq(n\\,{skip_frames})",
                    "-vsync",
                    "vfr",
                ]

        cmd += [
            "-vframes",
            "1",
            "-q:v",
            "2",
            "-y",
            frame_path,
        ]

        logger.info(f"执行FFmpeg命令: {' '.join(cmd)}")

        kwargs = {}
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                    
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs
        )

        try:
            stdout, stderr = process.communicate(timeout=self.timeout)
            stdout_text = stdout.decode("utf-8", errors="ignore")
            stderr_text = stderr.decode("utf-8", errors="ignore")

            # 提取关键错误信息
            if process.returncode != 0:
                # 只显示最后500个字符的错误信息
                if len(stderr_text) > 500:
                    stderr_text = "..." + stderr_text[-500:]
                logger.error(f"FFmpeg返回码: {process.returncode}, 错误: {stderr_text}")

            return (process.returncode, stdout_text, stderr_text)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            logger.error(f"FFmpeg命令超时 ({self.timeout}秒)")
            return (
                -1,
                stdout.decode("utf-8", errors="ignore"),
                stderr.decode("utf-8", errors="ignore"),
            )

    async def capture_frame(
        self,
        stream_url: str,
        camera_id: str,
        timestamp: Optional[datetime] = None,
    ) -> str:
        if timestamp is None:
            timestamp = now()

        frame_path = self._generate_frame_path(camera_id, timestamp)

        try:
            logger.info(f"开始抽帧 (rtsp): {stream_url} -> {frame_path}")

            loop = asyncio.get_event_loop()
            returncode, stdout, stderr = await loop.run_in_executor(
                self.executor,
                self._sync_capture_frame,
                stream_url,
                frame_path,
            )

            if returncode != 0:
                error_msg = stderr
                logger.error(f"抽帧失败: {error_msg}")
                raise FrameCaptureException(f"ffmpeg执行失败: {error_msg}")

            if not Path(frame_path).exists():
                raise FrameCaptureException("帧文件未创建")

            logger.info(f"抽帧成功: {frame_path}")
            return frame_path

        except FrameCaptureException:
            raise
        except Exception as e:
            logger.error(f"抽帧异常: {e}")
            raise FrameCaptureException(f"抽帧异常: {str(e)}")

    async def batch_capture_frames(
        self, stream_urls: List[tuple], max_concurrent: int = 5
    ) -> List[str]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def capture_with_semaphore(stream_url: str, camera_id: str):
            async with semaphore:
                return await self.capture_frame(stream_url, camera_id)

        tasks = [
            capture_with_semaphore(stream_url, camera_id)
            for stream_url, camera_id in stream_urls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        frame_paths = []
        for result in results:
            if isinstance(result, str):
                frame_paths.append(result)
            elif isinstance(result, Exception):
                logger.error(f"批量抽帧失败: {result}")

        return frame_paths

    async def shutdown(self):
        self.executor.shutdown(wait=True)
        logger.info("FrameService进程池已关闭")
