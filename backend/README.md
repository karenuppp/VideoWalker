# Backend (FastAPI)

主后端负责：配置管理、任务入队与消费、抽帧、告警、WebSocket 推送。

管理台当前对外的核心能力：

1. 摄像头管理（编号、名称、RTSP、删除）
2. 识别场景管理（选择摄像头、抽帧频率、识别API、停用/删除）

## 目录

- `app/main.py`：应用入口
- `app/api/v1`：API 路由
- `app/models`：SQLAlchemy 模型
- `app/tasks/scheduler.py`：队列调度与 worker 池
- `app/services`：视频、抽帧、YOLO调用、告警服务

## 运行

```bash
cd backend
uv venv .venv --python 3.12.8
source .venv/bin/activate
uv pip install -r requirements.txt
python -m app.main
```

默认端口：`9002`

## 识别执行模式

MVP 使用 MySQL 任务队列：

1. `task_enqueue` 定时任务按绑定策略写入 `detection_tasks`
2. worker 池并发领取并执行任务
3. 写入 `frames` / `detection_results` / `alerts`

## 关键配置

- `FRAME_INTERVAL`：入队扫描间隔（秒）
- `QUEUE_WORKER_COUNT`：worker 数量
- `TASK_MAX_RETRIES`：任务失败重试次数
- `TASK_POLL_INTERVAL_SECONDS`：worker 轮询间隔
- `YOLO_API_URL`：推理接口
- `ALERT_DEDUP_SECONDS`：告警去重窗口
