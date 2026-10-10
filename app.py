from fastapi import FastAPI, WebSocket, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
import os
from pydantic import BaseModel
import asyncio
import json
import uuid
import threading
from typing import Optional, List, Dict, Any
import time
import re

# 导入现有的系统
from new_main import IntegratedQASystem
from base import logger
from mysql_qa import RedisClient

# 导入 AI-Native 智能体系统
try:
    from agentic.legal_agent_system import LegalAgentSystem
    AGENT_AVAILABLE = True
except ImportError as e:
    print(f"警告: AI-Native 智能体系统未安装: {e}")
    AGENT_AVAILABLE = False

# 创建应用实例
app = FastAPI(title="问答系统API", description="集成MySQL和RAG的智能问答系统")

# 配置CORS，允许前端访问（限制来源，不用通配符+凭据的组合）
# 默认允许本机同源（静态页面）与 vite 开发服务器；生产可用 ALLOWED_ORIGINS 覆盖
_DEFAULT_ORIGINS = [
    "http://localhost:8003",
    "http://127.0.0.1:8003",
    "http://localhost:5173",   # vite dev server
    "http://127.0.0.1:5173",
]
_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
_ALLOWED_ORIGINS = [o.strip() for o in _ALLOWED_ORIGINS if o.strip()] or _DEFAULT_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建静态文件目录
os.makedirs("static", exist_ok=True)

# 创建全局QA系统实例
qa_system = IntegratedQASystem()

# 创建 Redis 客户端（用于智能体状态存储）
redis_client = RedisClient()

# 创建 AI-Native 智能体系统实例
if AGENT_AVAILABLE:
    try:
        agent_system = LegalAgentSystem()
        print("✓ AI-Native 智能体系统已启动")
    except Exception as e:
        print(f"警告: AI-Native 智能体系统启动失败: {e}")
        AGENT_AVAILABLE = False
        agent_system = None
else:
    agent_system = None

# 定义日常问候用语模式和回复（法律场景文案）
GREETING_PATTERNS = [
    {
        "pattern": r"^(你好|您好|hi|hello)",
        "response": "你好！我是法律智能问答助手，为您提供民法典等常用法律的信息参考，很高兴为您服务！"
    },
    {
        "pattern": r"^(你是谁|您是谁|你叫什么|你的名字|who are you)",
        "response": "我是法律智能问答助手，基于《民法典》《劳动法》《公司法》等常用法律为您提供信息参考（不构成法律意见）。"
    },
    {
        "pattern": r"^(在吗|在不在|有人吗)",
        "response": "我在！我是法律智能问答助手，随时为您解答法律问题。"
    },
    {
        "pattern": r"^(干嘛呢|你在干嘛|做什么)",
        "response": "我正在待命，随时为您提供民法典等常用法律的信息参考。有什么可以帮您的？"
    }
]


# 定义请求模型
class QueryRequest(BaseModel):
    query: str
    source_filter: Optional[str] = None
    session_id: Optional[str] = None
    use_agent: Optional[bool] = False  # 新增：是否使用 AI-Native 模式


# 定义响应模型
class QueryResponse(BaseModel):
    answer: str
    is_streaming: bool
    session_id: str
    processing_time: float


# 添加静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")


# 根路径重定向到index.html
@app.get("/")
def read_root():
    return FileResponse("static/index.html")


# 创建新会话
@app.post("/api/create_session")
def create_session():
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}


# 查询历史消息
@app.get("/api/history/{session_id}")
def get_history(session_id: str):
    try:
        history = qa_system.get_session_history(session_id)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


# 清除历史消息
@app.delete("/api/history/{session_id}")
def clear_history(session_id: str):
    success = qa_system.clear_session_history(session_id)
    if success:
        return {"status": "success", "message": "历史记录已清除"}
    else:
        raise HTTPException(status_code=500, detail="清除历史记录失败")


# 检查是否为日常问候用语并返回模板回复
def check_greeting(query: str) -> Optional[str]:
    query_text = query.strip()
    for pattern_info in GREETING_PATTERNS:
        if re.match(pattern_info["pattern"], query_text, re.IGNORECASE):
            return pattern_info["response"]
    return None


# 入参 出参
# 非流式查询接口（同步 def，FastAPI 放入线程池执行，避免阻塞事件循环）
@app.post("/api/query")
def query(request: QueryRequest):
    print("=" * 80)
    print("[查询请求] 收到新查询")
    print(f"问题: {request.query}")
    print("=" * 80)

    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())

    # 检查是否为日常问候
    greeting_response = check_greeting(request.query)
    if greeting_response:
        return {
            "answer": greeting_response,
            "is_streaming": False,
            "session_id": session_id,
            "processing_time": time.time() - start_time
        }

    # 判断是否需要流式处理
    # 对于长问题或复杂咨询，强制走 RAG 模式
    print(f"DEBUG - 问题长度: {len(request.query)}")
    print(f"DEBUG - 问题内容: {request.query[:100]}")
    if len(request.query) > 50 or any(word in request.query for word in ['怎么', '如何', '能不能', '是否', '请问', '帮我', '详细', '分析']):
        # 直接走 RAG
        need_rag = True
        answer = None
        print("DEBUG - 触发 RAG 模式")
    else:
        # 短问题先用 BM25 判断
        answer, need_rag = qa_system.bm25_search.search(request.query, threshold=12.0)
        print(f"DEBUG - BM25 模式, need_rag={need_rag}")

    if need_rag:
        # 需要 RAG 和 LLM 处理，返回流式响应提示
        return {
            "answer": "请使用WebSocket接口获取流式响应",
            "is_streaming": True,
            "session_id": session_id,
            "processing_time": time.time() - start_time
        }

    # 非流式查询，直接返回 BM25 检索的答案
    return {
        "answer": answer,
        "is_streaming": False,
        "session_id": session_id,
        "processing_time": time.time() - start_time
    }


# AI-Native 智能体查询接口
@app.post("/api/agent/query")
def agent_query(request: QueryRequest):
    """
    AI-Native 智能体模式查询接口
    支持多步推理、主动追问、工具调用
    """
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())
    
    # 检查 Agent 系统是否可用
    if not AGENT_AVAILABLE or agent_system is None:
        raise HTTPException(
            status_code=503, 
            detail="AI-Native 智能体系统未启动，请使用传统模式"
        )
    
    try:
        # 从 Redis 获取上一轮状态（如果存在）
        previous_state = None
        state_key = f"agent_state:{session_id}"
        try:
            state_json = redis_client.get_data(state_key)
            if state_json:
                previous_state = state_json
        except Exception as e:
            logger.warning(f"获取会话状态失败: {e}")

        # 调用 Agent 系统（传入上一轮状态）
        result = agent_system.run(request.query, previous_state)

        # 保存当前状态到 Redis（用于下一轮对话）
        try:
            redis_client.set_data(state_key, result, ttl=1800)  # 30分钟过期
        except Exception as e:
            logger.warning(f"保存会话状态失败: {e}")

        # 构建响应
        response = {
            "session_id": session_id,
            "intent": result.get('intent', ''),
            "need_clarify": result.get('need_clarify', False),
            "missing_info": result.get('missing_info', []),
            "tools_called": result.get('tools_called', []),
            "answer": result.get('final_answer') or result.get('draft_answer', ''),
            "processing_time": time.time() - start_time,
            "mode": "agent"
        }

        # 如果需要追问，返回特殊格式
        if result.get('need_clarify'):
            clarification_text = "为了更准确地回答您的问题，我需要了解以下信息：\n\n"
            for info in result['missing_info']:
                clarification_text += f"{info}\n"
            clarification_text += "\n请补充上述信息后，我将为您提供更详细的方案。"
            response['answer'] = clarification_text

        return response
        
    except Exception as e:
        import traceback
        error_detail = f"Agent 系统执行失败: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=str(e))


# 获取 Agent 系统状态
@app.get("/api/agent/status")
def agent_status():
    """查询 AI-Native 智能体系统状态"""
    return {
        "available": AGENT_AVAILABLE,
        "initialized": agent_system is not None,
        "tools_count": 11 if agent_system else 0,
        "message": "AI-Native 智能体系统运行正常" if AGENT_AVAILABLE else "智能体系统未启动"
    }


# 流式查询WebSocket接口
def _pump_query(gen, queue, loop):
    """在后台线程运行阻塞生成器，把 (token, is_complete) 推进 asyncio 队列。

    BERT 意图分类 / BM25 / Milvus 检索 / rerank / LLM 流式全是同步阻塞调用，
    若直接在事件循环里迭代会卡死所有并发连接。这里放到后台线程 + 队列回传。
    """
    def push(item):
        try:
            loop.call_soon_threadsafe(queue.put_nowait, item)
        except RuntimeError:
            # 事件循环已关闭（客户端断开），停止生产
            try:
                gen.close()
            except Exception:
                pass

    try:
        for token, is_complete in gen:
            push(("token", token, is_complete, None))
    except Exception as e:
        push(("error", None, False, str(e)))
    finally:
        push(("end", None, True, None))


@app.websocket("/api/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()

    def connected():
        return websocket.client_state == websocket.client_state.CONNECTED

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            request_data = json.loads(data)

            query = request_data.get("query")
            source_filter = request_data.get("source_filter")
            session_id = request_data.get("session_id", str(uuid.uuid4()))

            start_time = time.time()

            # 检查是否为日常问候
            greeting_response = check_greeting(query)
            if greeting_response:
                if connected():
                    await websocket.send_json({
                        "type": "token",
                        "token": greeting_response,
                        "session_id": session_id
                    })
                    await websocket.send_json({
                        "type": "end",
                        "session_id": session_id,
                        "is_complete": True,
                        "processing_time": time.time() - start_time
                    })
                continue

            # 发送开始标志
            if connected():
                await websocket.send_json({
                    "type": "start",
                    "session_id": session_id
                })

            # 前端仅在 /api/query 判定需要 RAG 后才打开本连接，
            # 因此这里直接走 RAG（force_rag=True），不再重复跑 BM25。
            queue = asyncio.Queue()
            gen = qa_system.query(
                query, source_filter=source_filter,
                session_id=session_id, force_rag=True,
            )
            threading.Thread(target=_pump_query, args=(gen, queue, loop), daemon=True).start()

            while True:
                kind, token, is_complete, error = await queue.get()
                if kind == "error":
                    if connected():
                        await websocket.send_json({
                            "type": "error",
                            "error": error,
                            "session_id": session_id
                        })
                    break
                if kind == "end":
                    if connected():
                        await websocket.send_json({
                            "type": "end",
                            "session_id": session_id,
                            "is_complete": True,
                            "processing_time": time.time() - start_time
                        })
                    break
                if token and connected():
                    await websocket.send_json({
                        "type": "token",
                        "token": token,
                        "session_id": session_id
                    })

    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected: code={e.code}, reason={e.reason}")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        if connected():
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
    finally:
        try:
            if connected():
                await websocket.close()
        except Exception as e:
            print(f"Error closing WebSocket: {str(e)}")


# 健康检查端点 用户运维监控服务存活状态
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# 获取有效的学科类别
@app.get("/api/sources")
def get_sources():
    return {"sources": qa_system.config.VALID_SOURCES}


# 法条原文精确查询（直接读 legal_data/ 下的 txt，不经过 RAG）
@app.get("/api/law")
def get_law_article(law: str = Query(..., description="法律名，如 民法典 / 劳动法"),
                    article: str = Query(..., description="条号，如 1179 / 第一千一百七十九条 / 第1179条")):
    from base.law_reader import get_law_reader
    text = get_law_reader().lookup(law, article)
    if not text:
        raise HTTPException(status_code=404, detail=f"未找到《{law}》{article}条原文")
    return {"law": law, "article": article, "text": text}


if __name__ == "__main__":
    import uvicorn

    # 注意：必须传 app 对象而非字符串 "app:app"。
    # 若传 "app:app"，uvicorn 会按模块名重新 import 本文件，
    # 导致模块级 `qa_system = IntegratedQASystem()` 执行两遍、
    # bge-m3/reranker/BERT 三个大模型被加载两次，内存翻倍，
    # 在 Windows 上会触发 OSError 1455（页面文件太小）。
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=False)
