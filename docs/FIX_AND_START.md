# 🔧 问题修复和启动指南

## ⚠️ 发现的问题

1. **端口错误**: 应该访问 `http://localhost:8003` 而不是 5001
2. **缺少依赖**: 需要安装 Python 依赖包

---

## ✅ 完整解决方案

### 步骤 1: 安装依赖（必须）

```bash
# 打开命令行，进入项目目录
cd E:\陈杰\Legal_qa_system

# 安装所有依赖
pip install -r config\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**如果安装很慢或失败**，使用清华镜像源（已加在上面命令中）

**预计时间**: 5-10 分钟（首次安装）

### 步骤 2: 验证安装

```bash
# 检查 fastapi 是否安装成功
pip show fastapi

# 预期输出: 显示 fastapi 的版本信息
```

### 步骤 3: 启动服务

```bash
# 直接运行 Python 脚本
python app.py
```

**预期输出**:
```
2026-08-26 XX:XX:XX - INFO - Redis 连接成功
2026-08-26 XX:XX:XX - INFO - MySQL 连接成功
2026-08-26 XX:XX:XX - INFO - 使用设备：cpu (或 cuda)
INFO:     Started server process [xxxxx]
INFO:     Uvicorn running on http://0.0.0.0:8003
```

### 步骤 4: 访问界面

**打开浏览器，访问**: http://localhost:8003

---

## 🧪 快速测试

### 测试 1: 健康检查
```bash
curl http://localhost:8003/health
```

**预期返回**: `{"status":"healthy"}`

### 测试 2: Web 界面
在浏览器输入测试问题:
```
民法典第509条是什么
```

**预期**: 返回法条内容

---

## 🐛 常见问题

### Q1: "ModuleNotFoundError: No module named 'xxx'"
**原因**: 依赖未安装  
**解决**: 
```bash
pip install -r config\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: 网页显示"无法访问此网站"
**检查清单**:
1. 服务是否启动成功（查看命令行输出）
2. 端口是否正确（应该是 8003）
3. 防火墙是否阻止

### Q3: 启动显示乱码
**原因**: Windows 命令行编码问题  
**影响**: 仅显示乱码，不影响功能  
**忽略**: 继续等待服务启动即可

### Q4: 端口被占用
```bash
# 查找占用端口的进程
netstat -ano | findstr :8003

# 结束该进程（替换 PID）
taskkill /F /PID <PID>
```

### Q5: 依赖服务未运行
```bash
# 检查 MySQL, Redis, Milvus
docker ps | findstr "mysql redis milvus"

# 如果没有运行，启动它们
docker start legal_qa_mysql legal_qa_redis
```

---

## 📋 完整验收流程

```bash
# 1. 进入目录
cd E:\陈杰\Legal_qa_system

# 2. 安装依赖（首次）
pip install -r config\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 检查依赖服务
docker ps | findstr "mysql redis milvus"

# 4. 启动服务
python app.py

# 5. 新开一个命令行窗口，测试
curl http://localhost:8003/health

# 6. 打开浏览器
# 访问: http://localhost:8003
```

---

## 🎯 一键启动脚本（修复版）

如果你想用 `start.bat`，确保先手动安装依赖:

```bash
pip install -r config\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

然后双击 `start.bat` 即可。

---

## ✅ 验收标准

| 项目 | 检查方法 | 预期结果 |
|------|---------|---------|
| 依赖安装 | `pip show fastapi` | 显示版本信息 |
| 服务启动 | `python app.py` | 无报错，显示 "Uvicorn running" |
| 健康检查 | `curl localhost:8003/health` | `{"status":"healthy"}` |
| Web 界面 | 浏览器访问 localhost:8003 | 显示问答界面 |
| 功能测试 | 输入"民法典第509条" | 返回法条内容 |

---

## 📞 关键信息

- **正确端口**: 8003 ✅
- **错误端口**: 5001 ❌
- **访问地址**: http://localhost:8003
- **配置文件**: config/config.ini
- **依赖文件**: config/requirements.txt

---

**重要提示**: 
1. 必须先安装依赖: `pip install -r config\requirements.txt`
2. 访问地址是 8003 端口，不是 5001
3. 首次启动需要加载模型，可能需要 30-60 秒
