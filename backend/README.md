# Backend (FastAPI)

主后端负责：配置管理、任务入队与消费、抽帧、告警、WebSocket 推送。

## 核心能力

1. **摄像头管理**（编号、名称、RTSP、删除）
2. **识别场景管理**（选择摄像头、抽帧频率、识别API、停用/删除、目标数量告警阈值）
3. **告警处理**（去重、WebSocket 推送、状态流转）
4. **系统监控**（状态总览、摄像头状态、手动抽帧触发）

## 目录

- `app/main.py`：应用入口
- `app/api/v1/`：API 路由
  - `admin/`：管理台 API（scenes、cameras、models、policies）
  - `alerts.py`：告警查询 API
  - `system.py`：系统状态 API
- `app/models/`：SQLAlchemy 模型
- `app/tasks/scheduler.py`：队列调度与 worker 池
- `app/services/`：核心服务
  - `ai_service.py`：YOLO 推理调用
  - `alert_service.py`：告警创建 + WebSocket 推送
  - `frame_service.py`：FFmpeg 抽帧
  - `video_service.py`：CMS API 获取 RTSP 流地址
- `yolo_service/`：YOLO 推理服务（独立进程）
  - `app.py`：通用多模型服务
  - `banner_service.py`：横幅检测专用
  - `people_count_service.py`：人员计数专用

## 运行

```bash
cd backend
uv venv .venv --python 3.12.8
source .venv/bin/activate
uv pip install -r requirements.txt
python -m app.main
```

默认端口：`9002`

YOLO 服务需单独启动（默认 `localhost:9001`）：

```bash
cd yolo_service
uv pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 9001 --reload
```

## 识别执行模式

MySQL 任务队列：

1. `task_enqueue` 定时任务扫描到期绑定策略，写入 `detection_tasks`
2. worker 池并发领取并执行任务
3. 任务流程：获取 RTSP → FFmpeg 抽帧 → YOLO 推理 → 规则评估 → 告警判定
4. 结果写入 `frames` / `detection_results` / `alerts`

## 关键配置（`.env`）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `YOLO_API_URL` | `http://localhost:9001/infer` | YOLO 推理接口 |
| `FRAME_INTERVAL` / `VIDEO_FRAME_INTERVAL` | `30` | 默认抽帧间隔（秒） |
| `QUEUE_WORKER_COUNT` | `3` | worker 数量 |
| `TASK_MAX_RETRIES` | `2` | 任务失败重试次数 |
| `ALERT_DEDUP_SECONDS` | `300` | 告警去重窗口（秒） |
| `ENQUEUE_TICK_SECONDS` | `5.0` | 入队扫描间隔（秒） |
| `RTSP_TRANSPORT` | `tcp` | RTSP 传输协议 |
| `RTSP_TIMEOUT` | `10` | RTSP 连接超时（秒） |
| `CMS_BASE_URL` / `CMS_TOKEN` | - | CMS API（获取 RTSP 地址） |

## WebSocket

告警实时推送端点：`ws://host:9002/ws/alerts`
