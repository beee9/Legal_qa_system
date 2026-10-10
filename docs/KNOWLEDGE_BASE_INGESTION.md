# 多格式离线知识库导入

导入命令会递归扫描目录中的 `.md`、`.markdown`、`.pdf`、`.txt`、`.docx` 文件，切分后写入当前 `config.ini` 配置的 Milvus 集合。

## 准备

```powershell
pip install -r config\requirements.txt
```

确认 Milvus 已启动，并且 `config.ini` 中的 `[milvus]` 配置可连接。

## 导入

```powershell
python scripts\ingest_documents.py E:\knowledge_base --source 法律资料
```

重复导入同一目录时，原文件保持相同的稳定 ID。文件内容减少或切块数变少时，使用 `--replace` 清除本次成功加载文件的旧切块：

```powershell
python scripts\ingest_documents.py E:\knowledge_base --source 法律资料 --replace
```

## 旧集合 schema 不兼容

旧版 `legal_rag` 集合缺少文档来源、父块和稀疏向量字段时，导入会停止并提示缺失字段。可选择新建一个集合，避免影响旧数据：

```powershell
python scripts\ingest_documents.py E:\knowledge_base --collection legal_rag_documents --source 法律资料
```

要让应用查询新集合，将 `config.ini` 的 `collection_name` 改为 `legal_rag_documents` 后重启服务。

`--recreate` 会删除目标集合并重建，只应在已备份且确认不需要其中旧数据时使用。
