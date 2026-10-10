# Legal QA System - 完整部署指南

## 📋 目录

- [系统架构](#系统架构)
- [环境要求](#环境要求)
- [快速启动](#快速启动)
- [详细部署步骤](#详细部署步骤)
- [配置说明](#配置说明)
- [数据导入](#数据导入)
- [服务管理](#服务管理)
- [常见问题](#常见问题)
- [性能优化](#性能优化)
- [监控与维护](#监控与维护)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   用户查询 (Web/API)                      │
└────────────────────┬────────────────────────────────────┘
                     ↓
        ┌────────────────────────┐
        │   意图分类器 (BERT)     │  ← 44ms 分类耗时
        │  法条/咨询/通用问题      │
        └────────┬───────────────┘
                 ↓
    ┌────────────┼────────────┐
    ↓            ↓             ↓
┌───────┐  ┌─────────┐  ┌──────────┐
│通用问题│  │法条查询 │  │法律咨询   │
│直连LLM│  │BM25检索 │  │RAG检索   │
└───────┘  └─────────┘  └──────────┘
                              ↓
                    ┌──────────────────┐
                    │  Milvus 向量库   │
                    │  2542 条法律文档  │
                    └──────────────────┘
```

### 核心组件

| 组件 | 作用 | 端口 | 状态 |
|------|------|------|------|
| FastAPI | Web 服务 | 8003 | ✅ |
| MySQL | 数据存储 | 3307 | ✅ |
| Redis | 缓存 | 6380 | ✅ |
| Milvus | 向量检索 | 19530 | ✅ |
| 意图分类器 | 查询路由 | - | ✅ |

---

## 环境要求

### 硬件要求

**最低配置**：
- CPU: 4 核
- 内存: 8GB
- 磁盘: 20GB
- GPU: 可选（建议 NVIDIA GPU 4GB+ 显存）

**推荐配置**：
- CPU: 8 核+
- 内存: 16GB+
- 磁盘: 50GB SSD
- GPU: NVIDIA GPU 8GB+ 显存（用于加速向量检索和意图分类）

### 软件要求

| 软件 | 版本 | 说明 |
|------|------|------|
| Python | 3.9.x | 必需（3.8 有兼容性问题） |
| Docker | 20.10+ | 用于运行 MySQL/Redis/Milvus |
| CUDA | 11.8+ | 可选（GPU 加速） |
| Git | 2.30+ | 代码管理 |

### 系统依赖

**Windows**：
- Docker Desktop
- Git Bash / WSL2

**Linux**：
- Docker Engine
- docker-compose

---

## 快速启动

### 一键启动（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd Legal_qa_system

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key

# 3. 启动所有服务
docker start legal_qa_mysql legal_qa_redis milvus-standalone

# 4. 启动应用（使用虚拟环境）
.venv-RAGtrain\Scripts\python.exe app.py

# 5. 访问系统
# http://localhost:8003
```

### 验证启动

```bash
# 检查服务状态
docker ps | grep -E "legal_qa|milvus"

# 检查端口
netstat -ano | findstr "8003 3307 6380 19530"

# 测试 API
curl http://localhost:8003/api/health
```

---

## 详细部署步骤

### Step 1: 克隆项目

```bash
git clone <repository-url>
cd Legal_qa_system
```

### Step 2: 安装 Python 依赖

**选项 A：使用现有虚拟环境（推荐）**

```bash
# 项目已包含配置好的虚拟环境
.venv-RAGtrain\Scripts\activate  # Windows
# 或
source .venv-RAGtrain/bin/activate  # Linux/Mac
```

**选项 B：创建新虚拟环境**

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装额外依赖
pip install pymilvus[model] FlagEmbedding torch transformers
```

### Step 3: 配置环境变量

创建 `.env` 文件：

```bash
# DashScope API（阿里云通义千问）
DASHSCOPE_API_KEY=sk-your-api-key-here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# MySQL 配置
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=legal_qa

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_PASSWORD=

# Milvus 配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=legal_rag
```

### Step 4: 启动 Docker 服务

**检查现有容器**：

```bash
docker ps -a | grep -E "legal_qa|milvus"
```

**启动服务**：

```bash
# MySQL
docker start legal_qa_mysql

# Redis
docker start legal_qa_redis

# Milvus
docker start milvus-standalone
docker start milvus-etcd
docker start milvus-minio
```

**如果容器不存在，创建新容器**：

```bash
# MySQL
docker run -d \
  --name legal_qa_mysql \
  -p 3307:3306 \
  -e MYSQL_ROOT_PASSWORD=12345678 \
  -e MYSQL_DATABASE=legal_qa \
  -v mysql_data:/var/lib/mysql \
  mysql:8.0.43

# Redis
docker run -d \
  --name legal_qa_redis \
  -p 6380:6379 \
  redis:7.2

# Milvus（使用 docker-compose）
# 下载 milvus docker-compose.yml
wget https://github.com/milvus-io/milvus/releases/download/v2.4.4/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d
```

### Step 5: 导入法律数据到 Milvus

```bash
# 使用虚拟环境运行导入脚本
.venv-RAGtrain\Scripts\python.exe scripts/ingest_milvus.py --force

# 预期输出：
# [20:39:39] 模型加载完成, 设备=cuda, 耗时 4s
# [20:39:42] 集合 legal_rag 已创建
# [20:40:12] 全部完成! 本批入库 2542 条

# 验证导入
python -c "
from pymilvus import connections, Collection
connections.connect(host='localhost', port='19530')
coll = Collection('legal_rag')
coll.flush()
print(f'文档数量: {coll.num_entities}')
"
# 应该输出: 文档数量: 2542
```

### Step 6: 启动应用

```bash
# 使用虚拟环境启动
.venv-RAGtrain\Scripts\python.exe app.py

# 或者后台运行
nohup .venv-RAGtrain\Scripts\python.exe app.py > app.log 2>&1 &
```

### Step 7: 验证系统

```bash
# 检查服务状态
curl http://localhost:8003/api/health

# 测试查询
curl -X POST http://localhost:8003/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "民法典第509条是什么"}'

# 访问 Web 界面
# http://localhost:8003
```

---

## 配置说明

### config.ini

```ini
[mysql]
host = 127.0.0.1
port = 3307
user = root
password = 12345678
database = legal_qa

[redis]
host = localhost
port = 6380
password =
db = 0

[milvus]
host = localhost
port = 19530
collection_name = legal_rag

[model]
# 模型目录（bge-m3, reranker 等）
models_dir = rag_qa/models

[intent_classifier]
# 意图分类器模型路径
model_path = rag_qa/core/legal_intent_classifier/final_model
```

### 意图分类器配置

意图分类器使用 BERT 模型，三分类：

| 意图类型 | 路由策略 | 平均耗时 |
|---------|---------|---------|
| 通用问题 | 直连 LLM | 544ms |
| 法条查询 | BM25 检索 | 244ms |
| 法律咨询 | RAG 向量检索 | 2044ms |

**禁用意图分类器**（回退到传统模式）：

在 `new_main.py` 中设置：

```python
CLASSIFIER_AVAILABLE = False
```

---

## 数据导入

### 法律数据来源

项目包含 6 部法律文档：

```
legal_data/
├── 民法典.txt (1260 条)
├── 劳动法.txt (107 条)
├── 劳动合同法.txt (98 条)
├── 公司法.txt (266 条)
├── 刑法.txt (505 条)
└── 民事诉讼法.txt (306 条)
```

### 导入脚本说明

```bash
# 查看帮助
python scripts/ingest_milvus.py --help

# 强制重建集合（删除旧数据）
python scripts/ingest_milvus.py --force

# 追加模式（保留旧数据）
python scripts/ingest_milvus.py
```

### 自定义数据导入

添加新的法律文档：

1. 将文档放入 `legal_data/` 目录
2. 格式：每条法律条文以 "第X条" 开头
3. 修改 `scripts/ingest_milvus.py` 中的 `LAWS` 列表
4. 运行导入脚本

示例：

```python
LAWS = [
    ("民法典.txt", "民法典"),
    ("你的新法律.txt", "新法律名称"),
    # ...
]
```

---

## 服务管理

### 启动服务

```bash
# 启动 Docker 服务
docker start legal_qa_mysql legal_qa_redis milvus-standalone

# 启动应用
.venv-RAGtrain\Scripts\python.exe app.py
```

### 停止服务

```bash
# 停止应用
ps aux | grep "python.exe app.py" | awk '{print $2}' | xargs kill

# 或使用 PID
kill <PID>

# 停止 Docker 服务
docker stop legal_qa_mysql legal_qa_redis milvus-standalone
```

### 重启服务

```bash
# 重启 Docker 服务
docker restart legal_qa_mysql legal_qa_redis milvus-standalone

# 重启应用
kill <PID>
.venv-RAGtrain\Scripts\python.exe app.py
```

### 查看日志

```bash
# 应用日志
tail -f app.log

# Docker 日志
docker logs -f legal_qa_mysql
docker logs -f legal_qa_redis
docker logs -f milvus-standalone
```

### 健康检查

```bash
# 检查所有服务状态
curl http://localhost:8003/api/health

# 检查 MySQL
docker exec legal_qa_mysql mysqladmin -uroot -p12345678 ping

# 检查 Redis
docker exec legal_qa_redis redis-cli ping

# 检查 Milvus
curl http://localhost:9091/healthz
```

---

## 常见问题

### Q1: 端口被占用

**问题**：`error while attempting to bind on address ('0.0.0.0', 8003)`

**解决方案**：

```bash
# 查找占用端口的进程
netstat -ano | findstr 8003

# 停止进程
taskkill /F /PID <PID>
```

### Q2: MySQL 连接失败

**问题**：`Can't connect to MySQL server on '127.0.0.1'`

**解决方案**：

```bash
# 检查 MySQL 容器状态
docker ps | grep legal_qa_mysql

# 启动容器
docker start legal_qa_mysql

# 检查端口映射
docker port legal_qa_mysql
```

### Q3: Milvus 集合不存在

**问题**：`Milvus 连接不可用: collection 'legal_rag' not found`

**解决方案**：

```bash
# 运行数据导入脚本
.venv-RAGtrain\Scripts\python.exe scripts/ingest_milvus.py --force

# 验证导入
python -c "
from pymilvus import connections, Collection
connections.connect(host='localhost', port='19530')
coll = Collection('legal_rag')
coll.flush()
print(f'文档数量: {coll.num_entities}')
"
```

### Q4: 意图分类器加载失败

**问题**：`法律意图分类器未安装`

**解决方案**：

检查模型文件是否存在：

```bash
ls -la rag_qa/core/legal_intent_classifier/final_model/
```

如果不存在，需要重新训练或从备份恢复。

### Q5: GPU 不可用

**问题**：`使用设备: cpu`（期望使用 GPU）

**解决方案**：

```bash
# 检查 CUDA 是否可用
python -c "import torch; print(torch.cuda.is_available())"

# 安装 CUDA 版本的 PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Q6: API Key 无效

**问题**：`DashScope API 调用失败`

**解决方案**：

1. 检查 `.env` 文件中的 `DASHSCOPE_API_KEY`
2. 访问 https://dashscope.console.aliyun.com/ 获取新的 API Key
3. 确认 API Key 有足够的额度

### Q7: 编码错误

**问题**：`'gbk' codec can't encode character`

**解决方案**：

修改 `app.py`，移除所有 emoji 字符：

```python
# 错误示例
print("🔥🔥🔥 收到查询请求！")

# 正确示例
print("[查询请求] 收到新查询")
```

---

## 性能优化

### 1. GPU 加速

**启用 CUDA**：

```python
# 在 config.ini 或代码中设置
device = "cuda" if torch.cuda.is_available() else "cpu"
```

**预期提升**：
- 向量检索速度：2-3 倍
- 意图分类速度：3-5 倍

### 2. 缓存优化

**Redis 缓存策略**：

```python
# 缓存常见查询结果（TTL 1 小时）
redis_client.setex(f"query:{query_hash}", 3600, result)
```

**预期提升**：
- 重复查询响应时间：10-50ms

### 3. 批量处理

**批量向量检索**：

```python
# 一次处理多个查询
results = vector_store.batch_search(queries, top_k=5)
```

**预期提升**：
- 批量查询吞吐量：5-10 倍

### 4. 模型量化

**量化意图分类器**：

```bash
# 使用 ONNX 量化（体积减少 75%）
python -m transformers.convert_graph_to_onnx \
  --model_path rag_qa/core/legal_intent_classifier/final_model \
  --output_path rag_qa/core/legal_intent_classifier/model.onnx
```

**预期提升**：
- 模型加载速度：2-3 倍
- 推理速度：1.5-2 倍

### 5. 连接池优化

**MySQL 连接池**：

```python
# 在 config.ini 中调整
[mysql]
pool_size = 10
max_overflow = 20
```

**预期提升**：
- 并发查询吞吐量：3-5 倍

---

## 监控与维护

### 日志管理

**日志位置**：

```
Legal_qa_system/
├── app.log              # 应用主日志
├── app_rag.log          # RAG 系统日志
└── logs/                # 其他日志
```

**日志级别**：

```python
# 在 base/config.py 中设置
logging.basicConfig(level=logging.INFO)  # INFO/DEBUG/WARNING/ERROR
```

### 性能监控

**关键指标**：

| 指标 | 正常范围 | 监控方式 |
|------|---------|---------|
| 响应时间 | < 3s | 应用日志 |
| 意图分类耗时 | < 100ms | 日志 + 统计 |
| 向量检索耗时 | < 2s | 日志 + 统计 |
| 内存使用 | < 8GB | `docker stats` |
| CPU 使用 | < 80% | `top` / `htop` |

**监控脚本**：

```bash
# 实时监控容器资源
docker stats legal_qa_mysql legal_qa_redis milvus-standalone

# 监控应用日志
tail -f app.log | grep -E "耗时|错误|Exception"
```

### 数据备份

**MySQL 备份**：

```bash
# 导出数据库
docker exec legal_qa_mysql mysqldump -uroot -p12345678 legal_qa > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker exec -i legal_qa_mysql mysql -uroot -p12345678 legal_qa < backup_20260908.sql
```

**Milvus 备份**：

```bash
# 导出集合数据
python scripts/export_milvus_data.py --collection legal_rag --output backup/

# 恢复集合数据
python scripts/ingest_milvus.py --force
```

### 定期维护

**每日检查**：
- [ ] 检查服务状态（`docker ps`）
- [ ] 查看错误日志（`grep ERROR app.log`）
- [ ] 监控磁盘空间（`df -h`）

**每周维护**：
- [ ] 备份 MySQL 数据库
- [ ] 清理旧日志文件
- [ ] 检查 API 额度使用情况

**每月维护**：
- [ ] 更新依赖包（`pip list --outdated`）
- [ ] 优化数据库索引
- [ ] 性能测试与调优

---

## 生产部署建议

### 1. 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. 使用 Supervisor 管理进程

```ini
[program:legal_qa]
command=/path/to/.venv-RAGtrain/Scripts/python.exe app.py
directory=/path/to/Legal_qa_system
autostart=true
autorestart=true
stderr_logfile=/var/log/legal_qa.err.log
stdout_logfile=/var/log/legal_qa.out.log
```

### 3. 配置 HTTPS

```bash
# 使用 Let's Encrypt
certbot --nginx -d your-domain.com
```

### 4. 设置防火墙

```bash
# 仅开放必要端口
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 5. 配置自动重启

**Windows**：

创建 Windows 服务或使用任务计划程序

**Linux**：

```bash
# 使用 systemd
sudo systemctl enable legal_qa
sudo systemctl start legal_qa
```

---

## 附录

### A. 完整依赖列表

主要依赖：

```
fastapi==0.115.5
uvicorn==0.32.1
pymilvus==3.0.0
pymysql==1.1.1
redis==5.2.0
torch==2.4.1
transformers==4.46.3
FlagEmbedding==1.2.11
jieba==0.42.1
rank-bm25==0.2.2
openai==1.54.5
```

### B. 目录结构

```
Legal_qa_system/
├── app.py                      # Web 服务入口
├── new_main.py                 # 集成 QA 系统（含意图分类器）
├── config.ini                  # 配置文件
├── .env                        # 环境变量（API Keys）
├── base/                       # 基础模块
│   ├── config.py
│   └── __init__.py
├── mysql_qa/                   # MySQL + BM25 检索
│   ├── db/
│   └── retrieval/
├── rag_qa/                     # RAG 向量检索
│   ├── core/
│   │   ├── vector_store.py
│   │   ├── legal_intent_classifier/  # 意图分类器模型
│   │   └── legal_query_classifier.py
│   └── models/                 # BGE-M3 等模型
├── scripts/                    # 工具脚本
│   ├── ingest_milvus.py        # 数据导入脚本
│   └── ...
├── legal_data/                 # 法律文档
│   ├── 民法典.txt
│   └── ...
├── static/                     # 前端静态文件
│   └── index.html
└── docs/                       # 文档
    ├── DEPLOYMENT_GUIDE.md     # 本文档
    └── ...
```

### C. API 接口文档

**查询接口**：

```http
POST /api/query
Content-Type: application/json

{
  "query": "民法典第509条是什么",
  "session_id": "optional-session-id"
}
```

**响应**：

```json
{
  "answer": "第五百零九条 当事人应当按照约定全面履行自己的义务...",
  "session_id": "uuid-xxx",
  "processing_time": 0.244,
  "is_streaming": false
}
```

**健康检查**：

```http
GET /api/health
```

**响应**：

```json
{
  "status": "ok",
  "services": {
    "mysql": "connected",
    "redis": "connected",
    "milvus": "connected",
    "classifier": "loaded"
  }
}
```

### D. 联系方式

- 项目仓库：[GitHub/GitLab URL]
- 技术支持：[邮箱/Issue Tracker]
- 文档更新：2026-09-08

---

**部署完成后，记得测试以下场景**：

1. ✅ 通用问题测试："今天天气怎么样"
2. ✅ 法条查询测试："民法典第509条"
3. ✅ 法律咨询测试："老板拖欠工资怎么办"
4. ✅ 并发压力测试（使用 Apache Bench 或 Locust）
5. ✅ 长时间稳定性测试（24 小时+）

祝部署顺利！🚀
