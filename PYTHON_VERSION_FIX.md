# Python 版本问题修复

## ❌ 问题

```
ERROR: Could not find a version that satisfies the requirement fastapi==0.136.3
```

**原因**: 你的 Python 版本 < 3.10，而 `fastapi==0.136.3` 需要 Python 3.10+

---

## ✅ 解决方案

### 方案 1: 降低 fastapi 版本（推荐，无需重装 Python）

已修复 `config/requirements.txt`，改为：
```
fastapi>=0.100.0  # 兼容 Python 3.8+
```

**现在重新安装**:
```bash
pip install -r config\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 方案 2: 升级 Python（可选）

如果想用最新版本：
1. 下载 Python 3.10+: https://www.python.org/downloads/
2. 安装后重新运行

---

## 🚀 快速启动（修复后）

```bash
# 1. 安装依赖（使用修复后的 requirements.txt）
cd E:\陈杰\Legal_qa_system
pip install -r config\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 启动服务
python app.py

# 3. 访问
http://localhost:8003
```

---

## 📋 版本兼容性

| Python 版本 | fastapi 版本 | 状态 |
|------------|-------------|------|
| 3.8, 3.9   | 0.100.0-0.128.x | ✅ 兼容 |
| 3.10+      | 所有版本 | ✅ 兼容 |
| < 3.8      | 需降级更多包 | ⚠️ 不推荐 |

---

**已修复**: `config/requirements.txt` 现在兼容 Python 3.8+
