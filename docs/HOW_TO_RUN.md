# Legal QA System - 完整运行指南

> **项目名称**: AI-Native 法律问答系统  
> **项目路径**: `E:\陈杰\Legal_qa_system`  
> **更新时间**: 2026-08-25

---

## 🚀 快速开始（5分钟）

### 方式1：一键启动（推荐）

```bash
# 1. 进入项目目录
cd E:\陈杰\Legal_qa_system

# 2. 启动服务
python app.py

# 3. 打开浏览器访问
http://localhost:5001
```

就这么简单！🎉

---

## 📋 完整运行步骤（首次运行）

### 步骤1: 环境准备 ✅

#### 1.1 检查 Python 版本

```bash
python --version
```

**要求**: Python 3.8 或更高版本

**如果版本过低**:
- 下载安装: https://www.python.org/downloads/

#### 1.2 安装依赖

```bash
# 进入项目目录
cd E:\陈杰\Legal_qa_system

# 安装基础依赖
pip install -r requirements.txt

# 安装 AI-Native 依赖（可选，启用智能体模式需要）
pip install langgraph==0.0.50 langchain-core==0.1.40
```

**如果安装慢**，使用国内镜像：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 1.3 检查必需服务

**MySQL 数据库**:
```bash
# 检查 MySQL 是否运行
# Windows: 任务管理器 → 服务 → 查找 MySQL

# 或使用命令
mysql -u root -p
# 输入密码后如果能连接，说明正常
```

**Redis（可选）**:
```bash
# 检查 Redis 是否运行
redis-cli ping
# 如果返回 PONG，说明正常
```

**Milvus 向量数据库（可选）**:
```bash
# 检查 Milvus 是否运行
# 访问: http://localhost:19530/healthz
# 或检查进程
```

**如果某些服务未启动**:
- MySQL: 必须启动
- Redis: 可选，用于 BM25 缓存
- Milvus: 可选，用于向量检索

---

### 步骤2: 配置数据库 ✅

#### 2.1 修改数据库配置

编辑 `base/config.py`:

```python
# MySQL 配置
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "你的密码",  # 修改这里
    "database": "legal_qa",
    "charset": "utf8mb4"
}

# Redis 配置
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "password": None  # 如果有密码，修改这里
}

# Milvus 配置
MILVUS_CONFIG = {
    "host": "localhost",
    "port": "19530"
}
```

#### 2.2 初始化数据库

```bash
# 创建数据库
mysql -u root -p
CREATE DATABASE IF NOT EXISTS legal_qa CHARACTER SET utf8mb4;
USE legal_qa;

# 导入表结构
SOURCE E:\陈杰\Legal_qa_system\schema.sql;

# 退出
exit;
```

#### 2.3 导入数据（如果有）

```bash
# 如果有 SQL 数据文件
mysql -u root -p legal_qa < data.sql

# 或使用 Python 脚本导入
python data_tools/import_data.py
```

---

### 步骤3: 启动服务 🚀

#### 3.1 启动主服务

```bash
# 方式1: 直接启动（前台运行）
python app.py

# 方式2: 后台运行（Windows）
start python app.py

# 方式3: 使用 uvicorn 直接启动
uvicorn app:app --host 0.0.0.0 --port 5001
```

**成功启动的标志**:
```
INFO:     Uvicorn running on http://0.0.0.0:5001 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
✓ AI-Native 智能体系统已启动
```

#### 3.2 检查服务状态

```bash
# 新开一个终端，运行
curl http://localhost:5001/api/agent/status

# 或在浏览器访问
http://localhost:5001/api/agent/status
```

**预期返回**:
```json
{
  "available": true,
  "initialized": true,
  "tools_count": 11,
  "message": "AI-Native 智能体系统运行正常"
}
```

---

### 步骤4: 浏览器访问 🌐

#### 4.1 打开浏览器

```
地址: http://localhost:5001
```

#### 4.2 界面说明

```
┌────────────────────────────────────────────────────┐
│  Legal QA System - AI法律助手                       │
├────────────────────────────────────────────────────┤
│                                                    │
│  [对话区域]                                         │
│  显示问答历史                                        │
│                                                    │
├────────────────────────────────────────────────────┤
│  □ AI智能体模式 (AI会主动追问、调用工具...)  ← 新增  │
│  ┌──────────────────────────────────────┐        │
│  │ 输入法律问题...                [发送]  │        │
│  └──────────────────────────────────────┘        │
│  Enter 发送 · Shift+Enter 换行                     │
└────────────────────────────────────────────────────┘
```

---

### 步骤5: 测试功能 ✅

#### 5.1 传统模式测试

```
1. 不勾选 "AI智能体模式"
2. 输入: "民法典第509条是什么"
3. 点击发送
4. 查看响应（1-2秒）
```

**预期结果**: 直接返回法条内容

#### 5.2 AI-Native 模式测试

```
1. 勾选 "AI智能体模式"
2. 输入: "老板拖欠我工资怎么办"
3. 点击发送
4. 查看 AI 是否主动追问
```

**预期结果**: 
- AI 识别缺失信息
- 追问 4 个关键问题

#### 5.3 完整流程测试

```
1. 保持 "AI智能体模式" 勾选
2. 输入: "老板拖欠我两个月工资，月薪8000，未签合同，工作11个月，公司在北京，有转账记录"
3. 点击发送
4. 等待 3-5 秒
```

**预期结果**:
- ✅ 法律分析
- ✅ 自动计算: 104,000元
- ✅ 维权步骤
- ✅ 胜诉概率: 85%
- ✅ 时效提醒
- ✅ 劳动仲裁申请书

---

## 🧪 运行测试脚本

### 自动化测试

```bash
# 确保服务正在运行（app.py）

# 新开终端，运行测试
python test_integration.py
```

**测试内容**:
1. ✅ 智能体系统状态检查
2. ✅ 传统模式查询
3. ✅ AI-Native 追问模式
4. ✅ AI-Native 完整信息模式

**预期输出**:
```
✓ 通过  智能体状态检查
✓ 通过  传统模式查询
✓ 通过  AI-Native 追问模式
✓ 通过  AI-Native 完整信息模式

总计: 4/4 测试通过
🎉 所有测试通过！AI-Native 集成成功！
```

---

## 🔧 常见问题排查

### 问题1: 端口被占用

**症状**: 
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 5001)
```

**解决方法**:
```bash
# 查找占用 5001 端口的进程
netstat -ano | findstr :5001

# 记下 PID（最后一列）

# 结束进程
taskkill /PID <PID> /F

# 重新启动服务
python app.py
```

### 问题2: 无法连接 MySQL

**症状**:
```
ERROR: Can't connect to MySQL server on 'localhost'
```

**解决方法**:
```bash
# 1. 检查 MySQL 服务是否启动
services.msc  # 查找 MySQL 服务

# 2. 检查配置文件中的密码
# 编辑 base/config.py

# 3. 测试连接
mysql -u root -p -h localhost
```

### 问题3: AI智能体模式不可用

**症状**: 开关显示 "智能体系统未启动"

**解决方法**:
```bash
# 1. 安装 LangGraph
pip install langgraph==0.0.50 langchain-core==0.1.40

# 2. 检查导入
python -c "from agentic.legal_agent_system import LegalAgentSystem; print('OK')"

# 3. 重启服务
# Ctrl+C 停止服务
python app.py
```

### 问题4: 向量检索不可用

**症状**: RAG 模式报错

**解决方法**:
```bash
# 1. 检查 Milvus 是否运行
# 访问: http://localhost:19530/healthz

# 2. 如果 Milvus 未运行，启动它
# 或者禁用向量检索，只使用 BM25

# 3. 修改配置（可选）
# 编辑 new_main.py，设置 use_vector = False
```

### 问题5: 依赖安装失败

**症状**: `pip install` 报错

**解决方法**:
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或单独安装关键依赖
pip install fastapi uvicorn pymysql redis pymilvus -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 📂 项目结构说明

```
E:\陈杰\Legal_qa_system/
├── app.py                          # 主应用入口（FastAPI服务）⭐
├── new_main.py                     # 核心问答系统
├── requirements.txt                # Python依赖列表
│
├── base/                           # 基础模块
│   ├── config.py                   # 配置文件 ⚙️
│   ├── logger.py                   # 日志模块
│   └── law_database.py             # 数据库访问
│
├── mysql_qa/                       # MySQL检索模块
│   ├── bm25_search.py              # BM25精确检索
│   ├── mysql_client.py             # MySQL客户端
│   └── data/                       # 数据文件
│       ├── legal_qa_full.csv       # 原始数据
│       └── legal_qa_full_enhanced.csv  # 增强数据 ✨
│
├── rag_qa/                         # RAG检索模块
│   ├── core/
│   │   ├── vector_store.py         # 向量存储
│   │   └── llm_client.py           # LLM客户端
│   └── config.py                   # RAG配置
│
├── agentic/                        # AI-Native 智能体系统 ✨
│   ├── legal_agent_system.py       # 智能体核心
│   ├── legal_tools.py              # 11个工具
│   ├── demo.py                     # 演示脚本
│   └── README.md                   # 技术文档
│
├── static/                         # 前端资源
│   └── index.html                  # 主页面 ⭐
│
├── scripts/                        # 脚本工具
│   └── roadmap_executor.py         # 自动执行助手
│
├── test_integration.py             # 集成测试脚本 🧪
│
├── docs/                           # 文档目录
│   ├── AI_NATIVE_ROADMAP.md        # 完整路线图
│   ├── DAILY_CHECKLIST.md          # 每日清单
│   ├── PHASE1_COMPLETION_REPORT.md # 阶段报告
│   └── INTEGRATION_COMPLETE.md     # 集成报告
│
└── logs/                           # 日志目录
    └── app.log                     # 应用日志
```

**关键文件**:
- ⭐ `app.py` - 启动这个文件
- ⭐ `static/index.html` - 前端界面
- ⚙️ `base/config.py` - 数据库配置
- ✨ `agentic/` - AI-Native 核心代码
- 🧪 `test_integration.py` - 测试脚本

---

## ⚙️ 配置文件位置

### 必须配置
1. **数据库配置**: `base/config.py`
   - MySQL 连接信息
   - Redis 连接信息
   - Milvus 连接信息

### 可选配置
2. **LLM 配置**: `rag_qa/config.py`
   - API Key
   - 模型名称
   - 温度参数

3. **日志配置**: `base/logger.py`
   - 日志级别
   - 日志路径

---

## 🎯 不同场景的运行方式

### 场景1: 只用传统模式（最简单）

**需要**:
- MySQL 数据库
- 数据已导入

**启动**:
```bash
python app.py
```

**使用**:
- 不勾选 "AI智能体模式"
- 响应速度快（1-2秒）

### 场景2: 使用 AI-Native 模式（推荐）

**需要**:
- MySQL 数据库
- 已安装 LangGraph

**启动**:
```bash
# 确保安装了 LangGraph
pip install langgraph==0.0.50 langchain-core==0.1.40

# 启动服务
python app.py
```

**使用**:
- 勾选 "AI智能体模式"
- 体验主动追问、工具调用

### 场景3: 完整功能（包含向量检索）

**需要**:
- MySQL 数据库
- Milvus 向量数据库
- 已安装 LangGraph
- LLM API Key

**启动**:
```bash
# 1. 启动 Milvus
# 2. 配置 LLM API Key
# 3. 启动服务
python app.py
```

**使用**:
- 所有功能可用
- 包含向量检索和语义理解

---

## 🔐 安全建议

### 生产环境部署

1. **修改默认端口**:
   ```python
   # app.py
   uvicorn.run(app, host="0.0.0.0", port=8000)  # 改为其他端口
   ```

2. **使用 HTTPS**:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 443 --ssl-keyfile key.pem --ssl-certfile cert.pem
   ```

3. **限制访问 IP**:
   ```python
   # app.py 添加中间件
   from fastapi.middleware.trustedhost import TrustedHostMiddleware
   app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com"])
   ```

4. **环境变量管理敏感信息**:
   ```bash
   # 不要在代码中硬编码密码
   export MYSQL_PASSWORD="your_password"
   export LLM_API_KEY="your_api_key"
   ```

---

## 📝 日常运行检查清单

### 每天启动前检查

- [ ] MySQL 服务是否运行
- [ ] Redis 服务是否运行（可选）
- [ ] Milvus 服务是否运行（可选）
- [ ] 磁盘空间是否充足
- [ ] 端口 5001 是否可用

### 每天关闭前

- [ ] 检查日志是否有异常
- [ ] 备份重要数据（可选）
- [ ] 优雅停止服务（Ctrl+C）

---

## 📞 获取帮助

### 文档
- 完整路线图: `AI_NATIVE_ROADMAP.md`
- 集成报告: `INTEGRATION_COMPLETE.md`
- 技术文档: `agentic/README.md`

### 测试
- 运行测试: `python test_integration.py`
- 演示脚本: `python agentic/demo.py`

### 日志
- 应用日志: `logs/app.log`
- 查看实时日志: `tail -f logs/app.log`（Linux/Mac）
- 或用记事本打开（Windows）

---

## ✅ 快速检查清单

运行前确认：

- [ ] Python 3.8+ 已安装
- [ ] 依赖已安装（`pip install -r requirements.txt`）
- [ ] MySQL 服务运行中
- [ ] 数据库配置正确（`base/config.py`）
- [ ] 数据已导入
- [ ] 端口 5001 未被占用

运行：

- [ ] `python app.py` 成功启动
- [ ] 浏览器能访问 `http://localhost:5001`
- [ ] 传统模式查询正常
- [ ] AI智能体模式可用（如已安装 LangGraph）

---

## 🎉 开始使用

```bash
# 就这三步！
cd E:\陈杰\Legal_qa_system
python app.py
# 浏览器打开 http://localhost:5001
```

祝使用愉快！ 🚀
