# VideoWalker

实时视频流智能监控平台。摄像头绑定识别场景，定时抽帧后送 YOLO 推理，超阈值推送前端告警。

---

## 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                      VideoWalker2                             │
├────────────────────────┬─────────────────────────────────────┤
│   Frontend (Vue3)      │   Backend (FastAPI)                  │
│   管理台 + 用户端       │   API + 调度 + 抽帧 + 告警           │
│   localhost:3000       │   localhost:9002                     │
└────────┬───────────────┴─────────────┬───────────────────────┘
         │                              │
         │  WebSocket                   │  RTSP
         │◄─────────────────────────────┼────────────────────►
         │                              │
    ┌────▼────┐              ┌─────────▼──────────┐
    │ 前端告警 │              │   YOLO Service      │
    │ 实时推送 │              │   localhost:9001     │
    └─────────┘              └─────────────────────┘
```

**核心流程**：

1. 管理台配置摄像头 + 识别场景（绑定模型、抽帧频率、告警阈值）
2. `FrameScheduler` 定时扫描到期场景，写入 `DetectionTask` 队列
3. Worker 领取任务 → `FrameService` FFmpeg 抽帧 → `AIService` 调用 YOLO 推理
4. 检测结果按规则评估，`AlertService` 判断是否告警
5. WebSocket 实时推送告警到前端

---

## 目录结构

```
VideoWalker2/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI 路由
│   │   │   ├── admin/       # 管理台 API（场景、摄像头、策略）
│   │   │   ├── alerts.py    # 告警查询 API
│   │   │   └── system.py    # 系统状态 API
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── services/        # 核心服务
│   │   │   ├── ai_service.py        # YOLO 推理调用
│   │   │   ├── alert_service.py     # 告警创建 + WebSocket 推送
│   │   │   ├── frame_service.py     # FFmpeg 抽帧
│   │   │   └── video_service.py     # CMS API 获取 RTSP
│   │   ├── tasks/
│   │   │   └── scheduler.py # 队列调度器（enqueue + worker pool）
│   │   ├── utils/
│   │   │   ├── logger.py    # 日志
│   │   │   ├── time.py      # 时区工具（UTC+8）
│   │   │   └── exceptions.py
│   │   └── config.py        # 配置中心
│   ├── yolo_service/        # YOLO 推理服务（独立进程）
│   │   ├── app.py           # 通用多模型推理服务
│   │   ├── banner_service.py # 横幅检测专用（单模型）
│   │   └── people_count_service.py # 人员计数专用
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/             # 前端 API 调用层（axios）
│       ├── types/           # TypeScript 类型定义
│       ├── views/           # 页面组件
│       │   ├── AdminDashboardView.vue  # 管理台
│       │   └── UserAlertsView.vue     # 用户端告警
│       └── router/
└── storage/frames/          # 抽帧图片存储目录
```

---

## 快速启动

### 1. 后端

```bash
cd backend
uv venv .venv --python 3.12.8
source .venv/bin/activate
uv pip install -r requirements.txt
python -m app.main
# API 服务 → http://localhost:9002
```

### 2. YOLO 推理服务（独立进程）

```bash
# 通用多模型服务
cd backend/yolo_service
uv pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 9001 --reload

# 或专用服务（二选一）
uvicorn banner_service:app --host 0.0.0.0 --port 9001
uvicorn people_count_service:app --host 0.0.0.0 --port 9002
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
# 前端 → http://localhost:3000
```

### 4. 配置

在 `backend/.env` 中配置：

```env
# 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=videowalker

# YOLO 推理服务地址
YOLO_API_URL=http://localhost:9001/infer

# CMS（获取 RTSP 流地址，可选）
CMS_BASE_URL=http://your-cms-api
CMS_TOKEN=your-token

# 抽帧
FRAME_INTERVAL=30
FRAME_STORAGE_PATH=./storage/frames
RTSP_TRANSPORT=tcp
RTSP_TIMEOUT=10

# 调度
QUEUE_WORKER_COUNT=3
ENQUEUE_TICK_SECONDS=5.0
TASK_MAX_RETRIES=2
ALERT_DEDUP_SECONDS=300
```

---

## 功能模块

### 管理台（`/admin/dashboard`）

| 功能 | 说明 |
|------|------|
| 摄像头管理 | 新增 / 删除摄像头（编号、名称、RTSP 直接填入） |
| 识别场景管理 | 绑定摄像头 + 选择模型 + 配置抽帧频率 + 目标数量告警阈值 |
| 启用/停用场景 | 动态开关场景，不删配置 |
| 规则配置 | `presence`（目标存在即告警）或 `count`（目标数量超阈值告警） |

### 用户端（`/user/alerts`）

| 功能 | 说明 |
|------|------|
| 实时告警列表 | WebSocket 推送，列表展示 |
| 告警状态 | 未读 → 已读 → 已处理 |
| 告警去重 | 5 分钟内同一摄像头同一场景合并 |

---

## API 概览

### 管理台 API（`/api/v1/admin`）

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/cameras` | 摄像头列表 |
| POST | `/cameras` | 新增摄像头 |
| PATCH | `/cameras/:id` | 更新摄像头 |
| DELETE | `/cameras/:id` | 删除摄像头 |
| GET | `/scenes` | 场景列表（含 rule 详情） |
| POST | `/scenes` | 创建场景 |
| PATCH | `/scenes/:id` | 更新场景（含 rule） |
| DELETE | `/scenes/:id` | 删除场景 |
| GET | `/models?detect_api=` | 从 YOLO 服务查询可用模型 |

### 告警 API（`/api/v1/alerts`）

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/alerts` | 告警列表（分页、过滤） |
| PATCH | `/alerts/:id/status` | 更新状态 |
| DELETE | `/alerts/:id` | 删除告警 |
| GET | `/alerts/stats` | 统计聚合 |

### 系统 API（`/api/v1/system`）

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/system/status` | 系统整体状态 |
| GET | `/system/cameras` | 摄像头状态列表 |
| POST | `/system/snapshot` | 手动触发一次抽帧任务 |

---

## 数据模型

### 核心关系

```
Camera (摄像头)
  └── CameraSceneBinding (场景绑定)
        ├── SceneVersion (场景版本)
        │     └── SceneTemplate (场景模板)
        └── DetectionTask (调度任务)
              └── DetectionResult (检测结果)
                    └── Alert (告警)
```

### 关键表

| 表名 | 说明 |
|------|------|
| `cameras` | 摄像头信息（编号、名称、RTSP） |
| `scene_templates` | 场景模板（scene_key、detect_api） |
| `scene_versions` | 版本（含 model_name、confidence_threshold、rule params） |
| `camera_scene_bindings` | 绑定关系 + frame_interval_seconds + last_run_at |
| `detection_tasks` | 任务队列（pending / running / success / failed） |
| `detection_results` | 检测结果（detected、confidence、class_counts） |
| `alerts` | 告警记录（含去重逻辑） |
| `alert_events` | 告警状态变更事件 |

---

## 规则评估逻辑

两种规则类型（存在 `rule.type` 字段）：

- **`presence`**：检测到任意目标即告警（默认）
- **`count`**：目标数量满足 `op` + `threshold` 条件时告警

```python
# count 规则示例：任意目标 count >= 3
{
    "type": "count",
    "target": "any",
    "op": ">=",
    "threshold": 3
}
```

---

## WebSocket

告警实时推送：`ws://host:9002/ws/alerts`

推送消息格式：

```json
{
  "id": 1,
  "camera_id": 1,
  "alert_type": "banner",
  "scene_name": "拉横幅检测",
  "confidence": 0.95,
  "description": "检测到拉横幅检测",
  "image_path": "/storage/frames/2026/03/30/CAM001_xxx.jpg",
  "status": "unread",
  "detected_at": "2026-03-30T10:00:00+08:00",
  "camera": {
    "id": 1,
    "camera_id": "CAM001",
    "name": "东门球机",
    "location": "东门",
    "status": "active"
  }
}
```

---

## YOLO 服务接口

所有 YOLO 服务统一响应格式：

```json
{
  "detected": true,
  "confidence": 0.92,
  "description": "Detected 3 objects for scene=banner",
  "boxes": [{"cls": 0, "label": "banner", "confidence": 0.92, "xyxy": [x1,y1,x2,y2]}],
  "labels": ["banner"],
  "details": {
    "scene_key": "banner",
    "model_name": "banner",
    "count": 3,
    "total_count": 3,
    "class_counts": {"banner": 3}
  }
}
```

---

## 已知限制

- RTSP 直连模式：若 `Camera.stream_url` 以 `rtsp://` 开头则直接使用，跳过 CMS API
- 抽帧图片：默认保存在 `storage/frames/YYYY/MM/DD/`，需定期清理
- 人员计数服务 (`people_count_service`) 默认只识别 `person` class（class_id=0），可通过 `PEOPLE_TARGET_LABELS` 环境变量扩展
