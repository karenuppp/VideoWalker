# Frontend (Vue3)

前端包含两个入口视图：

- 管理端：`/admin/dashboard`
- 用户端：`/user/alerts`

技术栈：Vue3 + Vue Router + Pinia + Element Plus。
视觉规范：管理端与用户端统一采用蓝白控制台风格（毛玻璃导航、分区卡片、统一空状态插图与提示文案）。

管理台功能逻辑当前仅保留两个标签页：

1. 摄像头管理（新增/删除）
2. 识别场景管理（选择摄像头、抽帧频率、识别API、停用/删除）

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

## 说明

- 主题为蓝白控制台风格。
- 管理端按摄像头创建识别场景并配置抽帧频率与模型 API。
- 用户端可接收并处置实时告警。
