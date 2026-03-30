# Frontend (Vue3)

前端包含两个入口视图：

- 管理端：`/admin/dashboard`
- 用户端：`/user/alerts`

技术栈：Vue3 + Vue Router + Pinia + Element Plus。
视觉规范：管理台与用户端统一采用蓝白控制台风格（毛玻璃导航、分区卡片、统一空状态插图与提示文案）。

## 页面功能

### 管理台（`/admin/dashboard`）

| 标签页 | 功能 |
|--------|------|
| 摄像头管理 | 新增摄像头（编号、名称、RTSP）、删除 |
| 识别场景管理 | 新增场景（绑定摄像头 + 抽帧频率 + 模型 + 识别API）、启用/停用、删除、配置目标数量告警阈值 |

### 用户端（`/user/alerts`）

接收并处置实时 WebSocket 告警推送，支持未读/已读/已处理状态流转。

## 运行

```bash
cd frontend
npm install
npm run dev
```

## 构建

```bash
npm run type-check
npm run build
```

## API 代理

前端开发服务器代理 `/api` 请求到后端（`localhost:9002`），生产环境通过 Nginx 反向代理配置。
