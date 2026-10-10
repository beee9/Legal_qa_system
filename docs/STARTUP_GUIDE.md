# Legal QA System - 完整启动验收指南

**项目路径**: `E:\陈杰\Legal_qa_system`  
**更新时间**: 2026-08-26 19:35

---

## ✅ 启动前检查清单

### 1. 依赖服务状态
```bash
docker ps | grep -E "mysql|redis|milvus"
```

**应该看到**:
- ✅ `legal_qa_mysql` - MySQL (端口 3307)
- ✅ `legal_qa_redis` - Redis (端口 6380)
- ✅ `milvus-standalone` - Milvus (端口 19530)

### 2. 项目结构
```bash
cd E:\陈杰\Legal_qa_system
ls -la
```

**根目录应该只有 3 个文件**:
- `README.md`
- `app.py`
- `new_main.py`

---

## 🚀 启动步骤

### 方式一：直接启动（推荐用于验收）

```bash
# 1. 进入项目目录
cd E:\陈杰\Legal_qa_system

# 2. 检查配置（可选）
cat config/config.ini

# 3. 启动 Web 服务
python app.py
```

**预期输出**:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5001
```

### 方式二：CLI 交互模式

```bash
# 启动命令行交互
python new_main.py
```

**可以输入问题测试**，例如：
- "民法典第509条是什么"
- "公司不签劳动合同怎么办"
- "加班费怎么计算"

---

## 🧪 验收测试

### 测试 1：健康检查
```bash
curl http://localhost:5001/health
```

**预期返回**:
```json
{"status":"healthy"}
```

### 测试 2：Web 界面
1. 打开浏览器
2. 访问: `http://localhost:5001`
3. 应该看到法律问答界面

### 测试 3：简单问答
在 Web 界面输入：
```
民法典第509条是什么
```

**预期**:
- ✅ 返回法条内容
- ✅ 响应时间 < 3秒
- ✅ 引用法条编号

### 测试 4：复杂咨询（AI-Native 模式）
在 Web 界面输入：
```
我在公司工作3年，每月工资8000，公司一直没签劳动合同，
现在要辞退我，我能拿到什么赔偿？
```

**预期**:
- ✅ 系统主动追问细节
- ✅ 计算双倍工资
- ✅ 计算经济补偿金
- ✅ 生成仲裁申请书建议

---

## 🔍 验收要点

### ✅ 功能验收

| 功能 | 验收方法 | 预期结果 |
|------|---------|---------|
| 服务启动 | `python app.py` | 无报错，显示运行地址 |
| 健康检查 | `curl http://localhost:5001/health` | 返回 `{"status":"healthy"}` |
| Web 界面 | 浏览器访问 | 显示问答界面 |
| 法条查询 | 输入"民法典第509条" | 返回法条内容 |
| 智能问答 | 输入劳动纠纷问题 | 返回详细解答 |
| AI-Native | 复杂咨询 | 主动追问、工具调用 |

### ✅ 性能验收

| 指标 | 要求 | 验收方法 |
|------|------|---------|
| 启动时间 | < 30秒 | 计时启动过程 |
| 法条查询 | < 2秒 | 测试简单查询 |
| RAG 问答 | < 5秒 | 测试复杂问答 |
| 内存占用 | < 4GB | 任务管理器查看 |

### ✅ 数据验收

```bash
# 1. 检查 MySQL 数据
docker exec legal_qa_mysql mysql -uroot -p12345678 legal_qa -e "SELECT COUNT(*) FROM jpkb;"

# 预期: 2632 条数据
```

```bash
# 2. 检查 Milvus 数据
# 在 Python 中执行
from pymilvus import MilvusClient
client = MilvusClient(uri="http://localhost:19530")
client.get_collection_stats("legal_rag")

# 预期: 有数据存在
```

---

## 🐛 常见问题排查

### 问题 1: 启动报错 "ModuleNotFoundError"
**解决**:
```bash
pip install -r config/requirements.txt
```

### 问题 2: 连接数据库失败
**检查**:
```bash
# 检查 MySQL 是否运行
docker ps | grep mysql

# 检查配置
cat config/config.ini | grep mysql
```

### 问题 3: Milvus 连接失败
**检查**:
```bash
# 检查 Milvus 是否运行
docker ps | grep milvus

# 测试连接
curl http://localhost:19530/healthz
```

### 问题 4: 端口被占用
**检查端口**:
```bash
netstat -ano | findstr :5001
```

**更换端口**: 编辑 `app.py`，修改端口号

---

## 📊 验收报告模板

```
# Legal QA System 验收报告

验收时间: ________
验收人: ________

## 环境检查
- [ ] MySQL 运行正常
- [ ] Redis 运行正常  
- [ ] Milvus 运行正常
- [ ] Python 环境正常

## 功能验收
- [ ] 服务启动成功
- [ ] 健康检查通过
- [ ] Web 界面正常
- [ ] 法条查询正常
- [ ] 智能问答正常
- [ ] AI-Native 模式正常

## 性能验收
- [ ] 启动时间 < 30秒
- [ ] 法条查询 < 2秒
- [ ] RAG 问答 < 5秒
- [ ] 内存占用 < 4GB

## 数据验收
- [ ] MySQL 数据完整 (2632条)
- [ ] Milvus 数据正常

## 总体评价
- 验收结果: ☐ 通过 ☐ 不通过
- 问题记录: __________
- 备注: __________
```

---

## 🎯 快速验收命令

```bash
# 一键验收脚本
cd E:\陈杰\Legal_qa_system

echo "=== 1. 检查依赖服务 ==="
docker ps | grep -E "mysql|redis|milvus"

echo "=== 2. 检查项目结构 ==="
ls -la | grep -E "^-" | wc -l
echo "根目录文件数（应该是3）"

echo "=== 3. 启动服务 ==="
python app.py &
sleep 10

echo "=== 4. 健康检查 ==="
curl http://localhost:5001/health

echo "=== 5. 测试问答 ==="
echo "请手动打开浏览器测试: http://localhost:5001"
```

---

**验收联系人**: Claude Code  
**技术支持**: 查看 `docs/` 目录下的文档
