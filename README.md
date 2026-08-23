# 法律智能问答系统 (Legal_QA)

> 基于 `Itcast_qa_system`（教育咨询问答系统）架构迁移的**民法典等常用法律法条问答系统**。
> 覆盖《民法典》《劳动法》《劳动合同法》《公司法》《刑法》《民事诉讼法》6 部常用法律。

## 核心能力

- **两级检索路由**：BM25 精确层（法条精确查询，快）→ 未命中降级 RAG 向量检索（开放式法律咨询）
- **意图分类**：BERT 三分类（法条查询 / 法律咨询 / 通用问题），准确率 100%
- **混合向量检索**：bge-m3（dense 1024 维）+ bge-reranker-v2-m3 重排序
- **法律合规**：prompt 强制引用法条编号 + 免责声明（不构成法律意见）

## 技术架构

```
用户查询
  │
  ├─ BM25 精确层 (MySQL jpkb + Redis 缓存)
  │    └─ 命中 → 直接返回标准答案
  │
  └─ 未命中 → RAG 层
       ├─ QueryClassifier (BERT 三分类：法条查询/法律咨询/通用问题)
       ├─ 策略选择 (LLM：直接/HyDE/子查询/回溯)
       ├─ Milvus 向量检索 (legal_rag 集合, bge-m3)
       └─ Rerank 重排序 → LLM 生成答案（引用法条编号 + 免责声明）
```

## 快速开始

### 1. 环境准备

- Python 3.9+，推荐使用 uv 或原生虚拟环境
- 运行依赖：`requirements.txt`

```shell
pip install -r requirements.txt
```

### 2. 依赖服务（MySQL / Milvus / Redis）

服务使用 Docker 部署：

```shell
cd docker/milvus_redis
docker compose up -d
```

### 3. 配置

- `config.ini`：业务配置（数据库、集合、模型等）
- `.env`：**API 密钥**（已 gitignore，勿提交）

### 4. 启动

```shell
# CLI 交互式问答
python new_main.py

# Web 服务 (FastAPI, WebSocket/SSE)
python app.py
```

## 测试

```shell
# 单元测试（config + BM25）
python -m pytest tests/ -v

# 集成测试（需服务运行 + 模型加载）
python scripts/test_integration.py
```

## 数据说明

| 数据 | 位置 | 内容 |
|---|---|---|
| 结构化问答 | MySQL `legal_qa.jpkb` | 2632 条（精确查询 2489 + 概念解释 144） |
| 向量数据 | Milvus `legal_rag` | 2542 条文（dense-only） |
| 法条原文 | `legal_data/` | 6 部法律 UTF-8 txt |
| 训练语料 | `rag_qa/classify_data/` | 593 条三分类语料 |
| 完整备份 | `mysql_qa/data/legal_qa_full.csv` | 2632 条问答对 CSV |

数据来源：国家法律法规数据库（flk.npc.gov.cn）等权威公开源。

## 目录结构

```
├── app.py / new_main.py       # 入口（Web / CLI）
├── config.ini / .env          # 配置（密钥在 .env）
├── base/                      # 基础模块（配置、日志）
├── mysql_qa/                  # BM25 精确检索层
├── rag_qa/                    # RAG 向量检索层
├── legal_data/                # 法条数据
├── static/                    # 前端静态页
├── scripts/                   # 工具脚本（入库/测试）
├── tests/                     # pytest 单元测试
└── docs/                      # 文档（复盘日志/演示用例）
```

## 相关文档

- [接口文档](docs/接口文档.md)
- [演示用例与面试话术](docs/演示用例与面试话术.md)
- [项目问题复盘日志](docs/项目问题复盘日志.md)
