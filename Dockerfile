# Python 基础镜像
FROM --platform=amd64 python:3.12-slim-bullseye

# 设置工作目录
WORKDIR /Users/chan/projects/Itcast_qa_system

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
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

# 复制依赖文件
#COPY requirements.txt requirements.txt

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN pip install  -r  requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple


# 创建日志目录
RUN mkdir -p logs

# 修改配置文件中的服务地址为 Docker 服务名
RUN sed -i '/\[mysql\]/,/host =/ s/host = localhost/host = mysql/' config.ini && \
    sed -i '/\[redis\]/,/host =/ s/host = localhost/host = redis/' config.ini && \
    sed -i '/\[milvus\]/,/host =/ s/host = localhost/host = milvus/' config.ini && \
    sed -i 's|log_file = /Users/chan/projects/Itcast_qa_system/logs/app.log|log_file = /app/logs/app.log|g' config.ini

# 复制入口脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露端口
EXPOSE 8003

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# 使用入口脚本启动
ENTRYPOINT ["/entrypoint.sh"]
