# 法律智能问答助手 - 测试指南

本文档为本项目提供系统化的测试流程与规范，涵盖功能、性能与质量评估。
推荐使用 **Apifox** 作为主要接口测试工具。

> ⚠️ 本项目的实际接口见下方「接口全景」表。测试时请以真实接口为准，
> 勿使用通用 RAG 模板的 `/qa`、`/upload`、`doc_id` 等（本项目无这些接口）。

---

## 0. 接口全景（本项目全部接口）

| 接口 | 方法 | 用途 | 请求体 | 成功返回 |
| :--- | :--- | :--- | :--- | :--- |
| `/health` | GET | 健康检查 | - | `{"status":"healthy"}` |
| `/api/create_session` | POST | 创建会话 | - | `{"session_id":"..."}` |
| `/api/query` | POST | 智能问答（BM25 精确 / 返回 is_streaming 判断走 RAG） | `{"query","source_filter","session_id"}` | `{"answer","is_streaming","session_id","processing_time"}` |
| `/api/sources` | GET | 获取法律领域列表 | - | `{"sources":["民法典",...]}` |
| `/api/history/{session_id}` | GET | 查会话历史 | - | `{"session_id","history":[{"question","answer"}]}` |
| `/api/history/{session_id}` | DELETE | 清空会话历史 | - | `{"status":"success","message":"..."}` |
| `/api/law` | GET | 法条原文精确查询 | 参数 `law`、`article` | `{"law","article","text"}`（未找到返回 404） |
| `/api/stream` | WebSocket | 流式问答（RAG + LLM 逐字输出） | 发送 `{"query","source_filter","session_id"}` | 消息 `{"type":"start/token/end/error",...}` |

---

## 1. 测试环境准备

确保被测服务已正常启动。

```bash
# 1. 本地直接运行（本项目最常用）
cd E:\陈杰\Legal_qa_system
./.venv-RAGtrain/Scripts/python.exe app.py

# 2. 验证服务健康状态
curl http://localhost:8003/health
```

> **预期结果**：返回 `{"status":"healthy"}`，表示服务已就绪。
> 前端页面：`http://localhost:8003`。

---

## 2. 功能测试（基于 Apifox）

### 2.1 创建测试项目与环境

1. 打开 Apifox，点击「新建项目」，选择 **"HTTP 项目"**。
2. 进入 **"环境管理"**，点击「新建环境」，命名 `开发环境`。
3. 添加环境变量：
   * **变量名**：`baseUrl`
   * **值**：`http://localhost:8003`
   * 再添加一个 `wsUrl`：`ws://localhost:8003`（供 WebSocket 接口用）
4. 接口 URL 中统一使用 `{{baseUrl}}`、`{{wsUrl}}`。

### 2.2 创建并测试各接口

在「接口」模块依次新建以下接口（均可加断言）。

#### A. 健康检查 `GET {{baseUrl}}/health`
- **断言**：HTTP 200；`$.status` `=` `healthy`

#### B. 创建会话 `POST {{baseUrl}}/api/create_session`
- **断言**：HTTP 200；`$.session_id` 非空（`!=` `null`）
- **数据传递**：在后置操作「提取变量」，用 `$.session_id` 存为 `sessionId`，供后续接口引用

#### C. 智能问答 `POST {{baseUrl}}/api/query`
- **Body（JSON）**：
  ```json
  {
    "query": "公司拖欠工资如何维权",
    "source_filter": "",
    "session_id": "{{sessionId}}"
  }
  ```
- **断言**：
  | 断言类型 | 表达式 | 操作符 | 期望值 |
  | :--- | :--- | :--- | :--- |
  | HTTP 状态码 | `response.responseCode` | `=` | `200` |
  | 返回答案 | `$.answer` | `!=` | `null` |
  | 流式标记 | `$.is_streaming` | 存在 | `true/false` 均可 |
- **说明**：`is_streaming=true` 表示该问题走了 RAG，需用 WebSocket 拿流式答案；`false` 则 `answer` 已含 BM25 精确答案。

#### D. 法律领域列表 `GET {{baseUrl}}/api/sources`
- **断言**：HTTP 200；`$.sources` 是数组且包含 `民法典`、`劳动法` 等

#### E. 会话历史 `GET {{baseUrl}}/api/history/{{sessionId}}`
- **断言**：HTTP 200；`$.history` 为数组（可为空）

#### F. 法条原文 `GET {{baseUrl}}/api/law?law=民法典&article=第1179条`
- **断言**：HTTP 200；`$.text` 非空；`$.law` `=` `民法典`
- **负例**：`law=不存在` → 期望 HTTP 404

#### G. 流式问答 `WebSocket {{wsUrl}}/api/stream`
- 连接后发送：`{"query":"食物中毒可以要求哪些赔偿","source_filter":"","session_id":"{{sessionId}}"}`
- 预期收到消息序列：`type=start` → 多个 `type=token`（含 `token` 字段）→ `type=end`
- **断言**：最终收到 `type=end` 且 `is_complete=true`

### 2.3 保存多场景测试用例

为边界情况保存独立用例（修改 `query` 值）：

| 用例名称 | `query` 值 | 测试目标 |
| :--- | :--- | :--- |
| 正常-劳动仲裁 | `劳动合同纠纷如何申请仲裁` | 验证正常业务流程 |
| 正常-民法典 | `买到过期食品能索赔吗` | 验证 RAG/法条检索 |
| 边界-空问题 | `""` | 验证空输入处理 |
| 边界-超长问题 | （粘贴 500+ 字文本） | 验证超长输入处理 |
| 否定-非法律 | `今天天气怎么样` | 验证非法律问题处理 |

---

## 3. 场景集成测试（端到端流程）

本项目**没有**文档上传接口，因此端到端流程围绕「会话生命周期」：

1. 在 **"自动化测试"** 新建场景「问答会话全流程」。
2. 按顺序添加步骤：
   1. `POST /api/create_session` → 后置提取 `sessionId`
   2. `POST /api/query`（用 `{{sessionId}}`，问题如劳动仲裁）→ 断言 `$.answer` 非空
   3. 若 `is_streaming=true`，加 WebSocket 步骤 `{{wsUrl}}/api/stream` 验证流式结束
   4. `GET /api/history/{{sessionId}}` → 断言历史里出现了刚才的问题
   5. `DELETE /api/history/{{sessionId}}` → 清理
   6. 再次 `GET /api/history/{{sessionId}}` → 断言历史为空
3. 运行并查看报告。

---

## 4. 测试数据管理（数据驱动）

1. 准备 `questions.csv`，两列：`id`、`question`（每行一个测试问题）。
2. 在自动化测试场景中，点击「测试数据」上传该 CSV。
3. 请求 Body 中把 `query` 的值替换为 `{{question}}`。
4. 运行时会自动遍历每一行，用 N 个不同问题覆盖更多场景。
   > 注意：每个用例需自行 `create_session` 或用独立 `session_id`，避免串扰。

---

## 5. 性能测试（基线摸底）

* **工具**：Apifox「性能测试」或 JMeter。
* **场景**：对 `POST /api/query` 模拟 5 / 10 / 20 并发用户，持续 2-3 分钟。
* **核心指标**：P95/P99 响应时间、吞吐量（RPS）、错误率。
* **注意**：`/api/query` 若 `is_streaming=true` 只返回路由判断（很快）；真正耗时在 WebSocket `/api/stream`。压测流式请对 WebSocket 施压。
* **资源监控**：`docker stats` 或本地任务管理器，观察内存（加载了 bge-m3 / reranker / BERT 三个模型，内存占用较高）。

---

## 6. 测试报告模板

| 测试类别 | 接口/用例 | 预期结果 | 实际结果 | 状态 | 备注 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 功能 | `GET /health` | 200, status=healthy | | ✅/❌ | |
| 功能 | `POST /api/create_session` | 200, 返回 session_id | | ✅/❌ | |
| 功能 | `POST /api/query`(劳动仲裁) | 200, answer 非空 | | ✅/❌ | |
| 功能 | `GET /api/law?law=民法典&article=第1179条` | 200, text 非空 | | ✅/❌ | |
| 功能 | `GET /api/law`(无效法) | 404 | | ✅/❌ | |
| 功能 | `WS /api/stream` | start→token…→end | | ✅/❌ | |
| 边界 | `POST /api/query`(空问题) | 4xx 或空答案 | | ✅/❌ | |
| 场景 | 会话全流程 | 建→问→查→清→空 | | ✅/❌ | |
| 性能 | 10 并发 3min | P95 < 3s | | ✅/❌ | |

---

## 附：常见问题

- **用浏览器打开页面**：用 `http://localhost:8003`，**不要用** `http://0.0.0.0:8003`（会报 `ERR_ADDRESS_INVALID`）。
- **启动依赖**：本地需 MySQL / Redis / Milvus 运行（见项目记忆/文档）。Milvus 未启动时，RAG 相关查询会失败。
- **WebSocket 断连**：前端已实现自动重连；Apifox 测试时若断连属正常，重点看是否最终收到 `end`。
