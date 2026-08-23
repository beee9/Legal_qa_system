#!/bin/bash
set -e

echo "========================================="
echo "等待依赖服务就绪..."
echo "========================================="

# 数据库名与密码从环境变量读取（默认与 config.ini / .env 一致）
MYSQL_PASSWORD="${MYSQL_PASSWORD:-12345678}"
MYSQL_DATABASE="${MYSQL_DATABASE:-legal_qa}"
REDIS_PASSWORD="${REDIS_PASSWORD:-1234}"

# 等待 MySQL 就绪
echo "等待 MySQL 启动..."
until python -c "import pymysql; pymysql.connect(host='mysql', port=3306, user='root', password='$MYSQL_PASSWORD', database='$MYSQL_DATABASE')" 2>/dev/null; do
  echo "MySQL 未就绪，等待中..."
  sleep 3
done
echo "✓ MySQL 已就绪"

# 等待 Redis 就绪
echo "等待 Redis 启动..."
until python -c "import redis; r = redis.Redis(host='redis', port=6379, password='$REDIS_PASSWORD'); r.ping()" 2>/dev/null; do
  echo "Redis 未就绪，等待中..."
  sleep 2
done
echo "✓ Redis 已就绪"

# 等待 Milvus 就绪
echo "等待 Milvus 启动..."
until python -c "from pymilvus import connections; connections.connect(host='milvus', port=19530)" 2>/dev/null; do
  echo "Milvus 未就绪，等待中..."
  sleep 5
done
echo "✓ Milvus 已就绪"

echo "========================================="
echo "所有依赖服务已就绪，启动应用..."
echo "========================================="

# 启动应用
exec python app.py
