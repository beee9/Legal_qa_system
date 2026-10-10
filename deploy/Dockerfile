# 使用 NVIDIA CUDA 12.1 基础镜像，保证 GPU 训练 BERT 模型
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# 设置环境变量，避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# 安装系统依赖（包括 Python 3.10）
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-dev \
    build-essential \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python 3.10 为默认 Python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# 升级 pip
RUN python -m pip install --upgrade pip

# 创建工作目录
WORKDIR /app

# ★★★ 关键优化：先只复制 requirements.txt ★★★
COPY requirements.txt .

# ★★★ 安装 Python 依赖（这一层会被缓存）★★★
# 使用清华源加速，PyTorch 使用 CUDA 12.1 官方源
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --extra-index-url https://download.pytorch.org/whl/cu121

# ★★★ 最后才复制项目代码 ★★★
COPY . .

# 把 config.ini 里的依赖服务地址改成 docker 服务名（与 docker-compose 服务名一致）
RUN sed -i '/\[mysql\]/,/host =/ s/host = localhost/host = mysql/' config.ini && \
    sed -i '/\[redis\]/,/host =/ s/host = localhost/host = redis/' config.ini && \
    sed -i '/\[milvus\]/,/host =/ s/host = localhost/host = milvus/' config.ini

# 暴露端口
EXPOSE 8003

# 启动命令
CMD ["python", "app.py"]