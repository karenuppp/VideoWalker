# VideoWalker 技术文档

## 1. 概述

VideoWalker 是一套面向 RTSP 摄像头的视频巡检系统，核心能力为“抽帧 + 识别 + 告警”。系统由后端服务（FastAPI + 异步任务调度 + MySQL）和前端管理台/用户端（Vue3）组成。后端负责摄像头管理、识别场景配置、定时抽帧、模型推理与告警落库；前端提供管理与告警查看能力。

## 2. 架构与模块

```
[RTSP 摄像头] -> [Backend 抽帧/识别] -> [MySQL] -> [告警 WebSocket/REST]
                                  ^               |
                                  |               v
                         [管理台: 摄像头/识别场景]  [用户端: 告警列表]
```

- 前端：`frontend/`，Vue3 + Element Plus。
- 后端：`backend/`，FastAPI + SQLAlchemy Async + APScheduler。
- 存储：MySQL（任务、帧、结果、告警等），帧图片落盘（`FRAME_STORAGE_PATH`）。
- 识别：通过 HTTP 调用模型 API（YOLO 兼容接口）。

## 3. 后端架构

### 3.1 入口与生命周期

- 入口文件：`backend/app/main.py`
- 启动流程：
  1. 初始化数据库连接（`init_db`）并自动建表（`Base.metadata.create_all`）。
  2. 启动调度器 `FrameScheduler`，按 `FRAME_INTERVAL` 触发任务入队。
  3. 挂载 API 路由、WebSocket 与帧文件静态访问 `/storage`。

### 3.2 数据模型（关键表）

- `cameras`：摄像头信息（编号、名称、RTSP、状态等）。
- `scene_templates` / `scene_versions`：识别场景模板与版本。
- `camera_scene_bindings`：摄像头与场景绑定（启停、抽帧频率、模型名覆盖等）。
- `detection_tasks`：待执行任务队列。
- `frames`：抽帧记录。
- `detection_results`：识别结果结构化存储。
- `alerts` / `alert_events` / `notification_logs`：告警与事件日志。

### 3.3 调度与执行逻辑

文件：`backend/app/tasks/scheduler.py`

1. `FrameScheduler.start(interval)` 启动定时入队任务。
2. 定时任务 `_enqueue_due_tasks`：
   - 查询启用中的 `camera_scene_bindings`，根据 `frame_interval_seconds` 或默认 `FRAME_INTERVAL` 判断是否到期。
   - 对每个到期绑定生成 `detection_tasks`（状态 `pending`）。
3. worker 线程池轮询 `pending` 任务，执行 `_execute_task`：
   - 获取摄像头 RTSP 地址（优先使用 `camera.stream_url`，否则走 CMS 播放地址）。
   - 调用 `FrameService` 抽帧，生成本地图片文件。
   - 调用 `AIService.detect_scene` 发送图片至模型 API。
   - 写入 `frames`、`detection_results`，若命中则通过 `AlertService` 创建告警并推送 WebSocket。

### 3.4 抽帧服务

文件：`backend/app/services/frame_service.py`

- 使用 `ffmpeg` 抽取单帧：
  - 传输协议由 `RTSP_TRANSPORT` 控制。
  - 使用 `-stimeout` 设置连接超时，默认偏好 TCP。
- 抽帧成功写入本地目录，路径由 `FRAME_STORAGE_PATH` 控制。

### 3.5 模型服务

文件：`backend/app/services/ai_service.py`

- 通过 HTTP POST 调用 `detect_api`：上传 JPEG 图片。
- 兼容 YOLO 推理服务，响应解析为统一结构：
  - `detected / confidence / description / details`。
- API 地址默认 `YOLO_API_URL`，可按场景覆盖（`scene_templates.detect_api`）。
- 识别使用的模型名来自 `camera_scene_bindings.model_name`（存在时覆盖），否则使用 `scene_versions.model_name`。

### 3.6 告警与 WebSocket

文件：`backend/app/services/alert_service.py` + `backend/app/services/websocket_service.py`

- 告警去重：在 `ALERT_DEDUP_SECONDS` 窗口内相同摄像头与场景命中会合并更新。
- 新告警写入 `alerts` 后推送到 `/ws/alerts` WebSocket。

### 3.7 API 概览

- 管理端：
  - `POST /api/v1/admin/cameras` 新增摄像头
  - `GET /api/v1/admin/cameras` 列表
  - `DELETE /api/v1/admin/cameras/{id}` 删除
  - `GET /api/v1/admin/scenes` 识别场景列表（绑定视图）
  - `POST /api/v1/admin/scenes` 新增识别场景（含摄像头、抽帧频率、识别 API）
  - `PATCH /api/v1/admin/scenes/{id}` 启停/更新抽帧频率
  - `DELETE /api/v1/admin/scenes/{id}` 删除识别场景

- 运行监控：
  - `GET /api/v1/system/status` 系统状态统计
  - `POST /api/v1/system/snapshot` 手动触发抽帧

- 用户告警：
  - `GET /api/v1/user/alerts` 告警列表
  - `GET /api/v1/alerts/{id}` 告警详情

## 4. 前端架构

### 4.1 入口与路由

- `frontend/src/main.ts`：Vue 应用入口。
- `frontend/src/router/index.ts`：
  - `/admin/dashboard` 管理台
  - `/user/alerts` 用户告警

### 4.2 管理台

- `AdminDashboardView.vue`：
  - 摄像头管理：新增/删除，展示状态与 RTSP 地址。
  - 识别场景管理：选择摄像头、设置抽帧频率、配置模型 API，新增/停用/删除。

### 4.3 用户告警

- `UserAlertsView.vue`：
  - 展示告警列表与详情。
  - 结合 WebSocket 实时更新。

## 5. 配置与环境变量

配置文件：`backend/app/config.py`，环境变量默认从 `backend/.env` 读取。

关键配置：

- 数据库
  - `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_CHARSET`
- 识别
  - `YOLO_API_URL`, `YOLO_API_KEY`, `YOLO_TIMEOUT`
- 抽帧
  - `FRAME_INTERVAL`, `FRAME_STORAGE_PATH`, `RTSP_TRANSPORT`, `RTSP_TIMEOUT`
- 调度
  - `QUEUE_WORKER_COUNT`, `TASK_POLL_INTERVAL_SECONDS`, `TASK_MAX_RETRIES`
- CMS 播放地址
  - `CMS_BASE_URL`, `CMS_TOKEN`

## 6. 数据流总结

1. 管理端创建摄像头与识别场景绑定。
2. 调度器按频率入队检测任务。
3. worker 拉取任务 -> 抽帧 -> 模型推理。
4. 结果落库 -> 告警去重 -> WebSocket 推送。
5. 用户端/管理端可实时查看告警与系统状态。
