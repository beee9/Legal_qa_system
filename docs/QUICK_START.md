# Legal QA System - 快速启动

## ⚠️ 重要信息

**服务端口**: `8003` (不是 5001)  
**访问地址**: http://localhost:8003

---

## 🚀 启动步骤

### 1. 安装依赖（首次运行）
```bash
cd E:\陈杰\Legal_qa_system
pip install -r config\requirements.txt
```

### 2. 启动服务
```bash
python app.py
```

### 3. 访问界面
打开浏览器: http://localhost:8003

---

## ✅ 验收测试

### 测试 1: 健康检查
```bash
curl http://localhost:8003/health
```
预期: `{"status":"healthy"}`

### 测试 2: 简单问答
在浏览器中输入: "民法典第509条是什么"

预期: 返回法条内容

---

## 🐛 问题排查

### 问题: 网页打不开
1. 检查服务是否启动成功
2. 确认端口是 **8003** 不是 5001
3. 检查防火墙是否阻止

### 问题: ModuleNotFoundError
运行: `pip install -r config\requirements.txt`

### 问题: 依赖服务未运行
检查: `docker ps | findstr "mysql redis milvus"`

---

## 📝 常用命令

```bash
# 检查依赖服务
docker ps

# 检查端口占用
netstat -ano | findstr :8003

# 停止服务
按 Ctrl+C

# 重启服务
python app.py
```

---

**正确访问地址**: http://localhost:8003 ✅
