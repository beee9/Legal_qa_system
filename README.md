# 项目的介绍与部署

项目是黑马课程服务的问答系统，主要提供专业和通用知识的回答

## 环境安装

* 使用uv包管理或者原生的python虚拟环境，python的版本为3.12
* python原生的虚拟环境依赖包，[requirements.txt](requirements.txt)
* uv的依赖环境为[pyproject.toml](pyproject.toml)

安装虚拟环境，同步依赖包

```shell
uv sync
```

或者使用pip包管理

```shell
pip install -r requirements.txt
```

## 依赖服务

本项目需要使用下面的服务：

* mysql
* milvus
* redis

服务使用docker-compose.yml文件配置，配置文件在[docker-compose.yml](docker/milvus_redis/docker-compose.yml)
在当前的docker-compose.yml的配置文件目录下，执行下面命令启动：

```shell
docker compose up -d
```

## 项目启动

### mysql问答系统

需要提前创建mysql数据库，数据库的名称为 `subjects_kg`
需要把高频问答数据写入mysql中，运行脚本[mysql_client.py](mysql_qa/db/mysql_client.py)
注意高频问答对数据一定不要重复写入。

### milvus问答系统

需要提前创建milvus 数据库，数据库的名称为 `itcast`
需要把离线文档写入向量数据库 运行脚本[vector_store.py](rag_qa/core/vector_store.py)

### 项目启动脚本

确保 mysql milvus redis 服务正常启动的情况下，运行主脚本启动服务

```shell
python app.py
```
