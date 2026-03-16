import asyncio
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, update

from app.config import settings
from app.models.camera import Camera
from app.models.camera_scene_binding import CameraSceneBinding
from app.models.detection_result import DetectionResult
from app.models.detection_task import DetectionTask
from app.models.frame import Frame
from app.models.scene_template import SceneTemplate
from app.models.scene_version import SceneVersion
from app.services.ai_service import AIService
from app.services.alert_service import AlertService
from app.services.frame_service import FrameService
from app.services.video_service import VideoService
from app.utils.logger import logger


class FrameScheduler:
    """Queue-based detection pipeline scheduler."""

    def __init__(self, db_factory):
        self.scheduler = AsyncIOScheduler()
        self.db_factory = db_factory
        self.video_service = VideoService()
        self.frame_service = FrameService()
        self.ai_service = AIService()
        self.is_running = False
        self._enqueue_lock = asyncio.Lock()
        self._workers: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    async def _has_active_task(self, db, binding_id: int) -> bool:
        query = select(DetectionTask.id).where(
            DetectionTask.binding_id == binding_id,
            DetectionTask.status.in_(["pending", "running"]),
        ).limit(1)
        row = (await db.execute(query)).first()
        return row is not None

    def _is_due(self, now: datetime, last_run_at: datetime | None, interval_seconds: int | None) -> bool:
        interval = interval_seconds or settings.FRAME_INTERVAL_VALUE
        if last_run_at is None:
            return True
        last_run = last_run_at
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
        return (now - last_run).total_seconds() >= interval

    async def _enqueue_due_tasks(self):
        if self._enqueue_lock.locked():
            logger.debug("enqueue lock busy, skip this tick")
            return

        async with self._enqueue_lock:
            now = datetime.now(timezone(timedelta(hours=8)))
            enqueued_count = 0

            async with self.db_factory() as db:
                query = (
                    select(
                        CameraSceneBinding,
                        SceneTemplate.scene_key,
                    )
                    .join(SceneVersion, SceneVersion.id == CameraSceneBinding.scene_version_id)
                    .join(SceneTemplate, SceneTemplate.id == SceneVersion.scene_template_id)
                    .join(Camera, Camera.id == CameraSceneBinding.camera_id)
                    .where(
                        CameraSceneBinding.enabled.is_(True),
                        Camera.status == "active",
                    )
                    .order_by(CameraSceneBinding.id.asc())
                )
                rows = (await db.execute(query)).all()

                for binding, scene_key in rows:
                    if not self._is_due(now, binding.last_run_at, binding.frame_interval_seconds):
                        continue

                    if await self._has_active_task(db, binding.id):
                        continue

                    task = DetectionTask(
                        camera_id=binding.camera_id,
                        binding_id=binding.id,
                        scene_version_id=binding.scene_version_id,
                        status="pending",
                        retries=0,
                        scheduled_for=now,
                    )
                    db.add(task)
                    enqueued_count += 1

                await db.commit()

            if enqueued_count:
                logger.info(f"Task enqueue tick complete: enqueued={enqueued_count}")

    async def _claim_task(self) -> int | None:
        now = datetime.now(timezone(timedelta(hours=8)))
        async with self.db_factory() as db:
            query = (
                select(DetectionTask.id)
                .where(
                    DetectionTask.status == "pending",
                    DetectionTask.scheduled_for <= now,
                )
                .order_by(DetectionTask.scheduled_for.asc(), DetectionTask.id.asc())
                .limit(1)
            )
            row = (await db.execute(query)).first()
            if not row:
                return None

            task_id = int(row[0])
            result = await db.execute(
                update(DetectionTask)
                .where(
                    DetectionTask.id == task_id,
                    DetectionTask.status == "pending",
                )
                .values(status="running", started_at=now, updated_at=now)
            )
            await db.commit()
            if result.rowcount == 0:
                return None
            return task_id

    async def _get_stream_url(self, camera: Camera) -> str:
        # MVP: direct RTSP stream preferred.
        if camera.stream_url and camera.stream_url.startswith("rtsp://"):
            return camera.stream_url

        async with self.db_factory() as db:
            result = await self.video_service.get_stream_url(
                token=settings.CMS_TOKEN or "",
                camera_id=camera.camera_id,
                db=db,
            )

        stream_url = None
        if isinstance(result, dict):
            stream_url = result.get("stream_url") or result.get("url")
        elif isinstance(result, str):
            stream_url = result

        if not stream_url:
            raise ValueError(f"Empty stream_url for camera_id={camera.camera_id}")
        return stream_url

    async def _execute_task(self, task_id: int, worker_name: str):
        now = datetime.now(timezone.utc)
        async with self.db_factory() as db:
            task = await db.get(DetectionTask, task_id)
            if not task:
                return

            camera = await db.get(Camera, task.camera_id)
            binding = await db.get(CameraSceneBinding, task.binding_id)
            scene_version = await db.get(SceneVersion, task.scene_version_id)
            if not camera or not binding or not scene_version:
                task.status = "failed"
                task.error_message = "task references missing camera/binding/scene_version"
                task.finished_at = now
                await db.commit()
                return

            scene_template = await db.get(SceneTemplate, scene_version.scene_template_id)
            if not scene_template:
                task.status = "failed"
                task.error_message = "scene template not found"
                task.finished_at = now
                await db.commit()
                return

        scene_key = scene_template.scene_key

        try:
            stream_url = await self._get_stream_url(camera)
            timestamp = datetime.now(timezone(timedelta(hours=8)))
            frame_path = await self.frame_service.capture_frame(stream_url, camera.camera_id, timestamp)

            detection = await self.ai_service.detect_scene(
                frame_path,
                scene_key,
                model_name=binding.model_name or scene_version.model_name,
                confidence_threshold=(
                    binding.confidence_threshold
                    if binding.confidence_threshold is not None
                    else scene_version.confidence_threshold
                ),
                detect_api=scene_template.detect_api,
            )

            async with self.db_factory() as db:
                frame = Frame(
                    camera_id=camera.id,
                    frame_path=frame_path,
                    frame_time=timestamp,
                    ai_processed=True,
                )
                db.add(frame)
                await db.flush()

                result = DetectionResult(
                    camera_id=camera.id,
                    frame_id=frame.id,
                    binding_id=binding.id,
                    scene_version_id=scene_version.id,
                    scene_key=scene_key,
                    detected=detection.get("detected", False),
                    confidence=detection.get("confidence", 0.0),
                    description=detection.get("description", ""),
                    details=detection.get("details", {}),
                    image_path=frame_path,
                    detected_at=timestamp,
                )
                db.add(result)
                await db.flush()

                threshold = (
                    binding.confidence_threshold
                    if binding.confidence_threshold is not None
                    else scene_version.confidence_threshold
                ) or 0.0
                confidence = float(detection.get("confidence", 0.0) or 0.0)
                if bool(detection.get("detected", False)) and confidence >= threshold:
                    alert_service = AlertService(db)
                    await alert_service.create_alert(
                        camera_id=camera.id,
                        detection_result=detection,
                        image_path=frame_path,
                        detected_at=timestamp,
                        alert_type=scene_key,
                    )

                db_camera = await db.get(Camera, camera.id)
                if db_camera:
                    db_camera.last_frame_time = timestamp

                db_binding = await db.get(CameraSceneBinding, binding.id)
                if db_binding:
                    db_binding.last_run_at = timestamp

                db_task = await db.get(DetectionTask, task_id)
                if db_task:
                    db_task.status = "success"
                    db_task.finished_at = timestamp
                    db_task.error_message = None
                    db_task.frame_id = frame.id
                    db_task.detection_result_id = result.id

                await db.commit()
                logger.info(
                    f"Task completed worker={worker_name} task_id={task_id} camera_id={camera.camera_id} scene={scene_key}"
                )

        except Exception as e:
            logger.error(f"Task failed worker={worker_name} task_id={task_id}: {e}")
            async with self.db_factory() as db:
                db_task = await db.get(DetectionTask, task_id)
                if not db_task:
                    return
                retries = db_task.retries + 1
                db_task.retries = retries
                db_task.error_message = str(e)
                db_task.finished_at = datetime.now(timezone(timedelta(hours=8)))

                if retries <= settings.TASK_MAX_RETRIES:
                    db_task.status = "pending"
                    db_task.started_at = None
                    db_task.scheduled_for = datetime.now(timezone(timedelta(hours=8))) + timedelta(seconds=2)
                else:
                    db_task.status = "failed"

                await db.commit()

    async def _worker_loop(self, index: int):
        worker_name = f"worker-{index}"
        logger.info(f"{worker_name} started")
        try:
            while not self._stop_event.is_set():
                task_id = await self._claim_task()
                if task_id is None:
                    await asyncio.sleep(settings.TASK_POLL_INTERVAL_SECONDS)
                    continue
                await self._execute_task(task_id, worker_name)
        except asyncio.CancelledError:
            logger.info(f"{worker_name} cancelled")
            raise
        except Exception as e:
            logger.error(f"{worker_name} crashed: {e}")
        finally:
            logger.info(f"{worker_name} stopped")

    def start(self, interval: int = None):
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        interval = interval or settings.FRAME_INTERVAL_VALUE

        self.scheduler.add_job(
            self._enqueue_due_tasks,
            "interval",
            seconds=interval,
            id="task_enqueue",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
        )

        self.scheduler.start()
        self._stop_event.clear()
        self._workers = [
            asyncio.create_task(self._worker_loop(i + 1), name=f"task-worker-{i+1}")
            for i in range(settings.QUEUE_WORKER_COUNT)
        ]

        self.is_running = True
        logger.info(
            f"Queue scheduler started, enqueue interval={interval}s, workers={settings.QUEUE_WORKER_COUNT}"
        )

    def stop(self):
        if not self.is_running:
            logger.warning("Scheduler not running")
            return

        self.scheduler.shutdown(wait=True)
        self._stop_event.set()

        for worker in self._workers:
            worker.cancel()
        self._workers = []

        self.is_running = False
        logger.info("Queue scheduler stopped")

    async def cleanup(self):
        if self.video_service:
            await self.video_service.close()
        if self.ai_service:
            await self.ai_service.close()
        if self.frame_service:
            await self.frame_service.shutdown()

    def pause(self):
        if not self.is_running:
            logger.warning("Scheduler not running")
            return

        self.scheduler.pause_job("task_enqueue")
        logger.info("Queue scheduler paused")

    def resume(self):
        if not self.is_running:
            logger.warning("Scheduler not running")
            return

        self.scheduler.resume_job("task_enqueue")
        logger.info("Queue scheduler resumed")

    def get_status(self) -> dict:
        job = self.scheduler.get_job("task_enqueue")
        active_workers = sum(1 for w in self._workers if not w.done())

        return {
            "running": self.is_running,
            "next_run_time": job.next_run_time.isoformat() if job else None,
            "enqueue_interval": settings.FRAME_INTERVAL_VALUE,
            "workers_total": settings.QUEUE_WORKER_COUNT,
            "workers_active": active_workers,
        }

    async def trigger_now(self):
        await self._enqueue_due_tasks()
