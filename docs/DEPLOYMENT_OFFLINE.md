# VideoWalker 离线生产部署文档

本文用于将项目迁移并部署到**离线生产环境**。建议采用“在线构建 + 离线部署”的方式，尽量减少离线侧依赖下载。

## 1. 目标拓扑（单机）

```
[Browser] --> [Nginx (静态前端 + 反向代理)] --> [FastAPI :9002] --> [MySQL]
                                   |-- /ws/alerts (WebSocket)
```

如需多机部署，可将 MySQL 与 FastAPI 分离，并通过内网访问。

## 2. 依赖与前置条件

离线环境需要提前准备以下依赖：

- 操作系统：Linux (推荐 Ubuntu 22.04 / CentOS 7+)
- Python：3.12.8
- Node.js：18+（仅在离线环境本地构建前端时需要）
- MySQL：8.0+（或 MariaDB 10.6+，需兼容）
- ffmpeg：支持 RTSP
- Nginx：用于部署前端与反向代理（可选但推荐）

## 3. 在线准备（有网络的构建机）

### 3.1 后端依赖离线包

在有网络的机器上下载 Python 依赖包：

```bash
cd backend
uv pip download -r requirements.txt -d ./packages
```

输出的 `backend/packages/` 目录请拷贝到离线环境。

### 3.2 YOLO 推理服务依赖离线包

在有网络的机器上下载 YOLO 服务依赖：

```bash
cd backend/yolo_service
uv pip download -r requirements.txt -d ./packages
```

输出的 `backend/yolo_service/packages/` 目录请拷贝到离线环境。

### 3.3 前端构建

推荐在有网络机器完成构建，离线环境只部署 `dist`：

```bash
cd frontend
npm ci
npm run build
```

将 `frontend/dist` 拷贝到离线环境的 Web 目录。

> 如果必须离线构建，需要提前准备 npm 缓存或私有 npm 仓库镜像。

## 4. 离线部署步骤

### 4.1 数据库初始化

在 MySQL 中创建数据库与账号：

```sql
CREATE DATABASE videowalker DEFAULT CHARSET utf8mb4;
CREATE USER 'videowalker'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON videowalker.* TO 'videowalker'@'%';
FLUSH PRIVILEGES;
```

执行初始化脚本：

```bash
mysql -u videowalker -p videowalker < database/init.sql
```

### 4.2 后端部署

1) 拷贝 `backend/` 到离线服务器
2) 创建虚拟环境（使用 uv + Python 3.12.8）

```bash
cd backend
uv venv .venv --python 3.12.8
source .venv/bin/activate
uv pip install --no-index --find-links ./packages -r requirements.txt
```

3) 编写 `backend/.env`（示例）

```ini
# DB
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=videowalker
DB_PASSWORD=your_password
DB_NAME=videowalker
DB_CHARSET=utf8mb4

# YOLO
YOLO_API_URL=http://127.0.0.1:9001/infer
YOLO_API_KEY=
YOLO_TIMEOUT=20

# CMS (如不使用可留空)
CMS_BASE_URL=
CMS_TOKEN=

# 抽帧
FRAME_INTERVAL=30
FRAME_STORAGE_PATH=./storage/frames
RTSP_TRANSPORT=tcp
RTSP_TIMEOUT=10

# 调度
QUEUE_WORKER_COUNT=3
TASK_POLL_INTERVAL_SECONDS=0.5
TASK_MAX_RETRIES=2

# 日志
LOG_LEVEL=INFO
LOG_FILE=./logs/videowalker.log
```

4) 启动后端

```bash
python -m app.main
```

### 4.3 YOLO 推理服务部署

1) 拷贝 `backend/yolo_service/` 到离线服务器（建议与后端同机）\n
2) 创建虚拟环境并安装依赖：

```bash
cd backend/yolo_service
uv venv .venv --python 3.12.8
source .venv/bin/activate
uv pip install --no-index --find-links ./packages -r requirements.txt
```

3) 准备模型文件\n
将 `.pt` 模型文件放入 `backend/yolo_service/models/`，或通过环境变量指定模型目录：

```bash
export YOLO_MODELS_DIR=/opt/videowalker/models
```

模型文件名需与场景配置的 `model_name` 对应（不含 `.pt` 后缀），例如：\n
`model_name=best` 对应模型文件 `best.pt`。

4) 启动 YOLO 服务（默认 9001 端口示例）\n
在离线环境中建议用 uvicorn 启动：

```bash
uvicorn app:app --host 0.0.0.0 --port 9001
```

> 后端 `YOLO_API_URL` 需指向该服务，例如 `http://127.0.0.1:9001/infer`。\n

### 4.4 systemd 托管（推荐）

为 YOLO 服务新增一个 systemd 文件，例如 `/etc/systemd/system/videowalker-yolo.service`：

```ini
[Unit]
Description=VideoWalker YOLO Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/videowalker/backend/yolo_service
Environment=PATH=/opt/videowalker/backend/yolo_service/.venv/bin
Environment=YOLO_MODELS_DIR=/opt/videowalker/models
Environment=YOLO_API_KEY=
ExecStart=/opt/videowalker/backend/yolo_service/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 9001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
systemctl daemon-reload
systemctl enable videowalker-yolo
systemctl start videowalker-yolo
```

### 4.5 systemd 托管（推荐）

创建 `/etc/systemd/system/videowalker.service`：

```ini
[Unit]
Description=VideoWalker Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/videowalker/backend
Environment=PATH=/opt/videowalker/backend/.venv/bin
ExecStart=/opt/videowalker/backend/.venv/bin/python -m app.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
systemctl daemon-reload
systemctl enable videowalker
systemctl start videowalker
```

### 4.6 前端部署

将 `frontend/dist` 拷贝到 Nginx Web 根目录，例如 `/var/www/videowalker`。

Nginx 示例配置：

```nginx
server {
    listen 80;
    server_name _;

    root /var/www/videowalker;
    index index.html;

    location / {
        try_files $uri /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:9002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:9002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

重启 Nginx：

```bash
systemctl restart nginx
```

## 5. 验证步骤

- 后端健康检查：`http://<host>:9002/health`
- YOLO 服务健康检查：`http://<host>:9001/health`
- 系统状态：`http://<host>:9002/api/v1/system/status`
- 管理台：`http://<host>/admin/dashboard`
- 用户端：`http://<host>/user/alerts`
- WebSocket：`ws://<host>/ws/alerts`

## 6. 常见问题排查

1) **RTSP 抽帧失败**
   - 确认离线服务器可访问 RTSP 地址。
   - 检查 `RTSP_TRANSPORT` 是否为 `tcp/udp`。
   - 确保 ffmpeg 安装并可执行。

2) **模型 API 不可达**
   - 检查 `YOLO_API_URL` 是否可达。
   - 离线环境需部署模型服务或使用内网地址。

3) **前端接口 404**
   - 确认 Nginx 反向代理 `/api/` 指向后端。

4) **WebSocket 无法连接**
   - Nginx 需开启 `Upgrade/Connection` 头代理配置。
