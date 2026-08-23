# 法律智能问答系统 - 前端

基于 **React + Vite** 的独立前端工程，对接后端 FastAPI（REST + WebSocket 流式）。

## 技术栈
- React 18
- Vite 5
- 原生 WebSocket（流式对话，无需额外依赖）

## 快速开始

### 1. 先启动后端（依赖 MySQL/Milvus/Redis 服务）
```shell
cd E:\陈杰\Legal_qa_system
python app.py        # 后端运行在 http://localhost:8003
```

### 2. 安装前端依赖并启动开发服务器
```shell
cd frontend
npm install
npm run dev          # http://localhost:5173（/api 自动代理到后端 8003）
```

### 3. 生产构建
```shell
npm run build        # 生成 dist/
```

## 对接的接口
| 接口 | 用途 |
|---|---|
| `POST /api/create_session` | 创建会话 |
| `POST /api/query` | 查询（判断是否流式） |
| `WebSocket /api/stream` | 流式对话（RAG/LLM 生成） |

开发代理配置见 `vite.config.js`（`/api` → `localhost:8003`，含 WebSocket）。

## 法律化文案
- 页面标题：法律智能问答系统
- 欢迎语：法律智能问答助手
- 底部免责声明：本系统提供法律信息参考，不构成法律意见
