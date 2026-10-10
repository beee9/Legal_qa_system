# 启动问题排查指南

> 如果遇到 `ERR_CONNECTION_REFUSED` 错误，按以下步骤排查

---

## 🔍 问题诊断

### 第1步：检查服务是否启动成功

打开 PowerShell 或命令提示符：

```bash
# 方式1：使用启动脚本（推荐）
E:\陈杰\Legal_qa_system\start.bat

# 方式2：手动启动
cd E:\陈杰\Legal_qa_system
python app.py
```

**成功启动的标志**：
```
INFO:     Uvicorn running on http://0.0.0.0:5001 (Press CTRL+C to quit)
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
✓ AI-Native 智能体系统已启动
```

如果看到以上信息，说明启动成功！

---

### 第2步：检查端口占用

**新开一个终端**（不要关闭运行 app.py 的终端）：

```bash
netstat -ano | findstr :5001
```

**预期输出**：
```
TCP    0.0.0.0:5001           0.0.0.0:0              LISTENING       12345
```

如果有输出，说明服务正在监听。

如果**没有输出**，说明服务启动失败，继续下一步。

---

### 第3步：查看启动错误信息

观察运行 `python app.py` 的终端，查找错误信息：

#### 常见错误1：端口被占用

```
ERROR: [Errno 10048] error while attempting to bind on address
```

**解决方法**：
```bash
# 查找占用端口的进程
netstat -ano | findstr :5001

# 结束进程（替换 <PID> 为实际进程ID）
taskkill /PID <PID> /F

# 或者修改端口
# 编辑 app.py 最后一行：
# uvicorn.run(app, host="0.0.0.0", port=5002)  # 改为 5002
```

#### 常见错误2：MySQL 连接失败

```
ERROR: Can't connect to MySQL server
或
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")
```

**解决方法**：

1. **检查 MySQL 服务是否运行**：
   - Windows：按 `Win+R`，输入 `services.msc`
   - 找到 MySQL 服务，确保状态为"正在运行"

2. **检查数据库配置**：
   ```bash
   # 编辑配置文件
   notepad E:\陈杰\Legal_qa_system\base\config.py
   
   # 确认以下信息正确：
   MYSQL_CONFIG = {
       "host": "localhost",
       "port": 3306,
       "user": "root",
       "password": "你的MySQL密码",  # 修改这里
       "database": "legal_qa"
   }
   ```

3. **测试 MySQL 连接**：
   ```bash
   mysql -u root -p
   # 输入密码
   
   # 成功连接后，检查数据库
   SHOW DATABASES;
   USE legal_qa;
   SHOW TABLES;
   ```

#### 常见错误3：Redis 连接失败

```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方法**：

Redis 是可选的（用于 BM25 缓存）。如果没有安装 Redis：

1. **临时解决**：注释掉 Redis 相关代码
   ```python
   # 编辑 mysql_qa/retrieval/bm25_search.py
   # 将 Redis 相关代码注释掉，或修改为不使用 Redis
   ```

2. **永久解决**：安装 Redis
   - 下载：https://github.com/tporadowski/redis/releases
   - 解压后运行 `redis-server.exe`

#### 常见错误4：依赖缺失

```
ModuleNotFoundError: No module named 'xxx'
```

**解决方法**：
```bash
# 安装缺失的依赖
pip install -r requirements.txt

# 或单独安装
pip install fastapi uvicorn pymysql redis pymilvus
```

#### 常见错误5：AI-Native 模块导入失败

```
ImportError: cannot import name 'LegalAgentSystem' from 'agentic.legal_agent_system'
```

**解决方法**：
```bash
# 安装 LangGraph
pip install langgraph==0.0.50 langchain-core==0.1.40

# 如果仍然失败，检查文件是否存在
dir E:\陈杰\Legal_qa_system\agentic\legal_agent_system.py
```

---

### 第4步：简化启动（最小配置）

如果上述步骤都失败，尝试最小配置启动：

1. **临时禁用 AI-Native 模式**：
   
   编辑 `app.py`，找到这几行：
   ```python
   try:
       from agentic.legal_agent_system import LegalAgentSystem
       AGENT_AVAILABLE = True
   except ImportError as e:
       print(f"警告: AI-Native 智能体系统未安装: {e}")
       AGENT_AVAILABLE = False
   ```
   
   改为直接设置：
   ```python
   AGENT_AVAILABLE = False  # 暂时禁用
   ```

2. **重新启动**：
   ```bash
   python app.py
   ```

3. **如果成功启动**，说明问题在 AI-Native 模块，稍后再安装 LangGraph。

---

### 第5步：检查防火墙

如果服务启动成功，但浏览器仍然无法访问：

```bash
# 检查是否是防火墙阻止
# Windows 防火墙 → 允许应用通过防火墙 → 添加 Python

# 或临时关闭防火墙测试（不推荐生产环境）
```

---

## ✅ 成功启动的完整流程

### 标准启动流程

**终端1（启动服务）**：
```bash
cd E:\陈杰\Legal_qa_system
python app.py
```

等待看到：
```
INFO:     Uvicorn running on http://0.0.0.0:5001
✓ AI-Native 智能体系统已启动
```

**终端2（验证）**：
```bash
# 检查端口
netstat -ano | findstr :5001

# 运行测试
python test_integration.py
```

**浏览器**：
```
访问: http://localhost:5001
或: http://127.0.0.1:5001
```

---

## 🚀 使用启动脚本（最简单）

我已经为你创建了一个启动脚本，自动检查所有依赖：

```bash
# 双击运行或在命令行执行
E:\陈杰\Legal_qa_system\start.bat
```

这个脚本会：
1. ✅ 检查 Python 环境
2. ✅ 检查依赖安装
3. ✅ 检查 MySQL 连接
4. ✅ 自动启动服务

---

## 📞 仍然无法解决？

### 收集诊断信息

运行以下命令并记录输出：

```bash
# 1. Python 版本
python --version

# 2. 依赖检查
pip list | findstr "fastapi uvicorn pymysql"

# 3. 启动日志
python app.py 2>&1 | tee startup.log

# 4. 端口状态
netstat -ano | findstr :5001

# 5. 进程状态
tasklist | findstr python
```

### 查看详细日志

```bash
# 查看应用日志
type E:\陈杰\Legal_qa_system\logs\app.log
```

### 最后的办法：使用其他端口

编辑 `app.py` 最后一行：
```python
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # 改为 8000
```

然后访问：`http://localhost:8000`

---

## 🎯 快速诊断命令

```bash
# 一键诊断（复制粘贴运行）
echo ===== Python 版本 =====
python --version

echo ===== 端口检查 =====
netstat -ano | findstr :5001

echo ===== MySQL 连接测试 =====
python -c "import pymysql; pymysql.connect(host='localhost', user='root', password='', database='legal_qa'); print('MySQL 连接成功')"

echo ===== 依赖检查 =====
python -c "import fastapi, uvicorn, pymysql; print('核心依赖已安装')"

echo ===== AI-Native 模块检查 =====
python -c "from agentic.legal_agent_system import LegalAgentSystem; print('AI-Native 模块可用')"
```

---

## 📝 成功案例参考

### 案例1：MySQL 密码错误

**症状**：服务启动失败，显示 MySQL 连接错误

**解决**：
1. 编辑 `base/config.py`
2. 修改密码为正确的 MySQL 密码
3. 重新启动 `python app.py`

### 案例2：端口被占用

**症状**：`[Errno 10048] error while attempting to bind`

**解决**：
1. 找到占用端口的进程：`netstat -ano | findstr :5001`
2. 结束进程：`taskkill /PID <进程ID> /F`
3. 重新启动服务

### 案例3：AI-Native 模块未安装

**症状**：启动时显示 "AI-Native 智能体系统未安装"

**解决**：
1. 安装 LangGraph：`pip install langgraph langchain-core`
2. 重新启动服务
3. 如果不需要 AI-Native 功能，可以忽略此警告

---

## ✅ 验证服务正常运行

当服务成功启动后，进行以下验证：

### 1. 终端验证
```bash
# 新开终端
curl http://localhost:5001/api/agent/status
```

**预期输出**：
```json
{
  "available": true,
  "initialized": true,
  "tools_count": 11,
  "message": "AI-Native 智能体系统运行正常"
}
```

### 2. 浏览器验证

访问：`http://localhost:5001`

**预期看到**：
- Legal QA System 界面
- 输入框
- AI智能体模式开关（如果 LangGraph 已安装）

### 3. 功能验证

在界面输入：`"民法典第509条是什么"`

**预期结果**：1-2秒内返回法条内容

---

**记住**：如果一切正常，你应该在终端看到类似这样的输出：

```
2026-08-25 14:27:42 - INFO - Redis 连接成功
2026-08-25 14:27:42 - INFO - BM25 模型初始化完成
2026-08-25 14:27:42 - INFO - 使用设备：cpu
✓ AI-Native 智能体系统已启动
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5001 (Press CTRL+C to quit)
```

看到这些信息，就可以在浏览器访问 `http://localhost:5001` 了！🎉
