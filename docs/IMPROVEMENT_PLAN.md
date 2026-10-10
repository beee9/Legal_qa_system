# Legal QA System 改进方案

## 一、后端改进方案

### 1. 异步化改造（高优先级）

**问题：** 当前所有检索和推理都是同步阻塞，高并发下性能差

**方案：**
- 使用 `asyncio` + `run_in_executor` 将同步操作包装为异步
- 对 BM25、向量检索、BERT 分类进行异步包装
- 统一使用 `async def` 定义接口

```python
# 示例：异步包装同步操作
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=10)

async def async_bm25_search(query, threshold):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor, 
        qa_system.bm25_search.search, 
        query, 
        threshold
    )
```

### 2. 简化流式接口（高优先级）

**问题：** 当前需要先调 `/api/query` 判断，再开 WebSocket，两次请求

**方案：** 统一使用 WebSocket，自动判断是否需要流式

```python
@app.websocket("/api/query")
async def unified_query(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        query = data['query']
        
        # 先尝试 BM25
        answer, need_rag = await async_bm25_search(query, 6.0)
        
        if not need_rag:
            # 直接返回完整答案
            await websocket.send_json({
                "type": "complete",
                "answer": answer,
                "source": "bm25"
            })
        else:
            # 流式返回 RAG 答案
            await websocket.send_json({"type": "start"})
            async for token in async_rag_query(query):
                await websocket.send_json({
                    "type": "token",
                    "content": token
                })
            await websocket.send_json({"type": "end"})
    finally:
        await websocket.close()
```

### 3. 数据库连接池（中优先级）

**问题：** 当前使用单一 MySQL 连接，高并发下会有问题

**方案：** 使用 `aiomysql` 或 `asyncpg` 连接池

```python
from aiomysql import create_pool

# 在启动时创建连接池
@app.on_event("startup")
async def startup():
    app.state.db_pool = await create_pool(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DB,
        minsize=5,
        maxsize=20
    )

@app.on_event("shutdown")
async def shutdown():
    app.state.db_pool.close()
    await app.state.db_pool.wait_closed()
```

### 4. 统一错误处理（中优先级）

**问题：** 各接口错误处理不统一，日志记录不完整

**方案：** 添加全局异常处理器

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": exc.__class__.__name__
        }
    )
```

### 5. 接口优化建议

#### 5.1 合并重复逻辑
- 将 `/api/query` 和 `/api/stream` 合并为统一的 WebSocket 接口
- 移除 `force_rag` 参数，自动判断

#### 5.2 会话管理优化
- 在 Redis 中存储会话状态（避免频繁查 MySQL）
- 实现会话过期机制（24小时自动清理）

#### 5.3 添加缓存层
```python
# 对常见问题添加 Redis 缓存
async def get_answer_with_cache(query: str):
    cache_key = f"qa:{hashlib.md5(query.encode()).hexdigest()}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    answer = await query_system(query)
    await redis_client.setex(cache_key, 3600, json.dumps(answer))
    return answer
```

---

## 二、前端改进方案

### 1. 组件化拆分（高优先级）

**问题：** 所有代码都在 `App.jsx` 中，维护困难

**方案：** 拆分为多个组件

```
frontend/src/
├── components/
│   ├── ChatMessage.jsx      # 单条消息组件
│   ├── ChatInput.jsx         # 输入框组件
│   ├── ChatHistory.jsx       # 历史记录侧边栏
│   ├── SourceFilter.jsx      # 法律来源筛选
│   └── AgentModeToggle.jsx   # AI模式切换
├── hooks/
│   ├── useWebSocket.js       # WebSocket 连接管理
│   ├── useChat.js            # 聊天状态管理
│   └── useSession.js         # 会话管理
├── services/
│   └── api.js                # API 调用封装
├── utils/
│   └── constants.js          # 常量定义
└── App.jsx
```

### 2. 统一 API 调用（高优先级）

**问题：** 先 fetch 再 WebSocket，逻辑复杂

**方案：** 统一使用 WebSocket

```javascript
// hooks/useWebSocket.js
export function useWebSocket(url) {
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const socket = new WebSocket(url);
    
    socket.onopen = () => {
      console.log('WebSocket 连接成功');
      setConnected(true);
    };
    
    socket.onclose = () => {
      console.log('WebSocket 断开');
      setConnected(false);
    };
    
    setWs(socket);
    
    return () => socket.close();
  }, [url]);

  const sendMessage = (data) => {
    if (ws && connected) {
      ws.send(JSON.stringify(data));
    }
  };

  return { ws, connected, sendMessage };
}
```

```javascript
// hooks/useChat.js
export function useChat(sessionId) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const { ws, connected, sendMessage } = useWebSocket('ws://localhost:8003/api/query');

  useEffect(() => {
    if (!ws) return;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'start':
          setLoading(true);
          setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }]);
          break;
        
        case 'token':
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last.streaming) {
              return [...prev.slice(0, -1), { ...last, content: last.content + data.content }];
            }
            return prev;
          });
          break;
        
        case 'complete':
          setMessages(prev => [...prev, { role: 'assistant', content: data.answer, streaming: false }]);
          setLoading(false);
          break;
        
        case 'end':
          setMessages(prev => {
            const last = prev[prev.length - 1];
            return [...prev.slice(0, -1), { ...last, streaming: false }];
          });
          setLoading(false);
          break;
      }
    };
  }, [ws]);

  const sendQuery = (query, sourceFilter) => {
    setMessages(prev => [...prev, { role: 'user', content: query }]);
    sendMessage({ query, source_filter: sourceFilter, session_id: sessionId });
  };

  return { messages, loading, sendQuery, connected };
}
```

### 3. 状态管理优化（中优先级）

**方案：** 使用 Context API 或 Zustand

```javascript
// store/chatStore.js (使用 Zustand)
import create from 'zustand';

export const useChatStore = create((set, get) => ({
  sessionId: null,
  messages: [],
  loading: false,
  sourceFilter: null,
  agentMode: false,

  setSessionId: (id) => set({ sessionId: id }),
  
  addMessage: (message) => set(state => ({
    messages: [...state.messages, message]
  })),
  
  updateLastMessage: (content) => set(state => {
    const messages = [...state.messages];
    const last = messages[messages.length - 1];
    messages[messages.length - 1] = { ...last, content: last.content + content };
    return { messages };
  }),
  
  setLoading: (loading) => set({ loading }),
  setSourceFilter: (filter) => set({ sourceFilter: filter }),
  toggleAgentMode: () => set(state => ({ agentMode: !state.agentMode })),
  
  clearMessages: () => set({ messages: [] })
}));
```

### 4. UI/UX 改进（中优先级）

#### 4.1 添加加载动画
```jsx
// components/TypingIndicator.jsx
export function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <span></span>
      <span></span>
      <span></span>
    </div>
  );
}
```

#### 4.2 错误提示
```jsx
// components/ErrorMessage.jsx
export function ErrorMessage({ error, onRetry }) {
  return (
    <div className="error-message">
      <p>⚠️ {error}</p>
      <button onClick={onRetry}>重试</button>
    </div>
  );
}
```

#### 4.3 消息时间戳
```jsx
// components/ChatMessage.jsx
export function ChatMessage({ message }) {
  return (
    <div className={`message ${message.role}`}>
      <div className="message-content">{message.content}</div>
      <div className="message-time">
        {new Date(message.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}
```

### 5. 性能优化（低优先级）

- 使用 `React.memo` 避免不必要的重渲染
- 虚拟滚动处理长对话历史
- 图片懒加载
- 代码分割（React.lazy）

---

## 三、架构优化建议

### 1. 目录结构重组

```
Legal_qa_system/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置管理
│   │   ├── dependencies.py      # 依赖注入
│   │   └── middleware.py        # 中间件
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── query.py         # 查询接口
│   │   │   ├── session.py       # 会话管理
│   │   │   └── agent.py         # AI Agent 接口
│   │   └── models/
│   │       ├── request.py       # 请求模型
│   │       └── response.py      # 响应模型
│   ├── services/
│   │   ├── qa_service.py        # 问答服务
│   │   ├── rag_service.py       # RAG 服务
│   │   └── agent_service.py     # Agent 服务
│   ├── repositories/
│   │   ├── mysql_repo.py        # MySQL 数据访问
│   │   └── redis_repo.py        # Redis 数据访问
│   └── utils/
│       ├── logger.py
│       └── errors.py
├── frontend/
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── services/
│       ├── store/
│       └── utils/
├── tests/
│   ├── backend/
│   └── frontend/
├── docker-compose.yml
└── README.md
```

### 2. 添加 Docker 支持

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8003:8003"
    environment:
      - MYSQL_HOST=mysql
      - REDIS_HOST=redis
      - MILVUS_HOST=milvus
    depends_on:
      - mysql
      - redis
      - milvus

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: legal_qa
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  milvus:
    image: milvusdb/milvus:latest
    volumes:
      - milvus_data:/var/lib/milvus

volumes:
  mysql_data:
  redis_data:
  milvus_data:
```

### 3. 添加测试

```python
# tests/backend/test_qa_service.py
import pytest
from app.services.qa_service import QAService

@pytest.mark.asyncio
async def test_bm25_search():
    service = QAService()
    answer, need_rag = await service.search("民法典第509条")
    assert answer is not None
    assert not need_rag

@pytest.mark.asyncio
async def test_rag_search():
    service = QAService()
    answer, need_rag = await service.search("合同违约怎么办")
    assert need_rag
```

---

## 四、实施优先级

### Phase 1: 紧急修复（1-2天）
1. ✅ 修复 `uvicorn.run` 重复加载问题（已在代码中修复）
2. 🔴 简化 API 调用逻辑（合并 `/api/query` 和 WebSocket）
3. 🔴 前端组件化拆分（至少拆分出 ChatMessage 和 ChatInput）

### Phase 2: 核心优化（3-5天）
1. 🟠 后端异步化改造
2. 🟠 添加数据库连接池
3. 🟠 统一错误处理
4. 🟠 前端状态管理优化

### Phase 3: 功能增强（1周）
1. 🟡 添加缓存层
2. 🟡 会话管理优化
3. 🟡 UI/UX 改进（加载动画、错误提示）
4. 🟡 添加单元测试

### Phase 4: 长期优化（可选）
1. ⚪ Docker 容器化
2. ⚪ 添加 CI/CD
3. ⚪ 性能监控和日志分析
4. ⚪ 文档完善

---

## 五、立即可执行的快速修复

### 1. 修复前端 API 调用（最简单）

在 `frontend/src/App.jsx` 中，删除先调 `/api/query` 的逻辑，直接使用 WebSocket：

```javascript
const handleSend = async () => {
  if (!inputValue.trim() || !ws || ws.readyState !== WebSocket.OPEN) return;

  const userMessage = {
    role: 'user',
    content: inputValue,
    timestamp: new Date().toISOString()
  };
  
  setMessages(prev => [...prev, userMessage]);
  setInputValue('');
  setIsLoading(true);

  // 直接通过 WebSocket 发送
  ws.send(JSON.stringify({
    query: inputValue,
    source_filter: sourceFilter,
    session_id: sessionId
  }));
};
```

### 2. 添加加载状态指示器

```jsx
{isLoading && (
  <div className="loading-indicator">
    <div className="typing-dots">
      <span>.</span><span>.</span><span>.</span>
    </div>
    <span>正在思考...</span>
  </div>
)}
```

### 3. 添加错误重试机制

```javascript
const [error, setError] = useState(null);

useEffect(() => {
  if (ws) {
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('连接失败，请检查网络或刷新页面重试');
    };
  }
}, [ws]);

// 重试按钮
{error && (
  <div className="error-banner">
    <span>{error}</span>
    <button onClick={() => window.location.reload()}>重新连接</button>
  </div>
)}
```

---

## 六、总结

**最关键的3个问题：**
1. 前后端流式通信逻辑过于复杂（两次请求）
2. 后端同步阻塞操作影响并发性能
3. 前端代码组织混乱，难以维护

**建议优先处理：**
1. 合并 API 接口，统一使用 WebSocket
2. 前端组件化拆分
3. 添加基础的错误处理和加载状态

这些改动投入产出比最高，可以快速提升系统的可用性和可维护性。
