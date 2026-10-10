# -*- coding: utf-8 -*-
"""Phase 1-3: 6 部法律切块 -> embedding(bge-m3) -> 入库 Milvus 集合 legal_rag。

可移植：路径/连接信息全部从 base.config.Config（config.ini/.env）读取，
不再硬编码本机绝对路径。默认非破坏（集合已存在则追加），用 --force 删除重建。
"""
import time
import re
import sys
import os
import warnings
import argparse
import numpy as np
warnings.filterwarnings("ignore")

from pathlib import Path

# 让脚本无论从哪个目录运行都能导入项目包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base import Config  # noqa: E402
from FlagEmbedding import BGEM3FlagModel  # noqa: E402
from pymilvus import MilvusClient, DataType  # noqa: E402

conf = Config()
PROJECT = Path(conf._PROJECT_ROOT)
DATA_DIR = PROJECT / "legal_data"
M3_PATH = os.path.join(conf.models_dir, "bge-m3")
MILVUS_URI = f"http://{conf.MILVUS_HOST}:{conf.MILVUS_PORT}"
COLLECTION = conf.MILVUS_COLLECTION_NAME
DENSE_DIM = 1024

LAWS = [
    ("民法典.txt", "民法典"), ("劳动法.txt", "劳动法"), ("劳动合同法.txt", "劳动合同法"),
    ("公司法.txt", "公司法"), ("刑法.txt", "刑法"), ("民事诉讼法.txt", "民事诉讼法"),
]

ART_RE = re.compile(r"(?:^|[\r\n])\s*(第[一二三四五六七八九十百千零〇]+条)", re.MULTILINE)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def extract_articles(text):
    matches = list(ART_RE.finditer(text))
    arts = []
    for i, m in enumerate(matches):
        num = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = re.sub(r"[　\t\r\n]+", " ", text[start:end]).strip()
        arts.append((num, body))
    return arts


def main():
    parser = argparse.ArgumentParser(description="法律条文切块 -> bge-m3 -> 入库 Milvus")
    parser.add_argument("--force", action="store_true",
                        help="集合已存在时删除重建（默认追加，不覆盖现有数据）")
    args = parser.parse_args()

    # 1. 加载模型（与查询端 vector_store 一致：FlagEmbedding + float32）
    log(f"加载 bge-m3 模型...")
    t0 = time.time()
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    emb = BGEM3FlagModel(M3_PATH, use_fp16=(device == "cuda"))
    log(f"模型加载完成, 设备={device}, 耗时 {time.time()-t0:.0f}s")

    # 2. 连接 Milvus & 建集合（默认不破坏现有数据）
    log("连接 Milvus...")
    client = MilvusClient(uri=MILVUS_URI)
    if client.has_collection(COLLECTION):
        if args.force:
            log(f"集合 {COLLECTION} 已存在, --force 删除重建")
            client.drop_collection(COLLECTION)
        else:
            log(f"集合 {COLLECTION} 已存在，跳过建集合（追加入库；如需重建请加 --force）")
    if not client.has_collection(COLLECTION):
        schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("subject", DataType.VARCHAR, max_length=50)
        schema.add_field("text", DataType.VARCHAR, max_length=4000)
        schema.add_field("parent_id", DataType.INT64)  # 添加父文档ID字段
        schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=DENSE_DIM)
        schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)  # 添加稀疏向量字段
        index_params = client.prepare_index_params()
        index_params.add_index("dense_vector", index_type="IVF_FLAT", metric_type="IP", params={"nlist": 128})
        index_params.add_index("sparse_vector", index_type="SPARSE_INVERTED_INDEX", metric_type="IP")
        client.create_collection(collection_name=COLLECTION, schema=schema, index_params=index_params)
        log(f"集合 {COLLECTION} 已创建 (dense {DENSE_DIM} 维 + sparse + parent_id)")

    # 3. 逐部法律切块 + 分批 embedding 入库
    total_ins = 0
    for fname, subject in LAWS:
        with open(DATA_DIR / fname, "r", encoding="utf-8") as f:
            text = f.read()
        arts = extract_articles(text)
        log(f"== {subject}: {len(arts)} 条条文 ==")
        BATCH = 24
        n_ins = 0
        for i in range(0, len(arts), BATCH):
            chunk = arts[i:i + BATCH]
            texts = [f"{num} {body}" for num, body in chunk]
            try:
                # 同时生成 dense 和 sparse 向量
                out = emb.encode(list(texts), return_dense=True, return_sparse=True)
                dense = np.asarray(out["dense_vecs"], dtype="float32").tolist()
                sparse = out["lexical_weights"]  # 稀疏向量
                rows = []
                for j, (num, body) in enumerate(chunk):
                    rows.append({
                        "subject": subject,
                        "text": f"{num} {body}",
                        "dense_vector": dense[j],
                        "sparse_vector": sparse[j],  # 添加稀疏向量
                        "parent_id": 0,  # 当前是父文档，parent_id 设为 0
                    })
                client.insert(COLLECTION, data=rows)
                n_ins += len(rows)
                if (i // BATCH) % 5 == 0:
                    log(f"  {subject} 已入库 {n_ins}/{len(arts)}")
            except Exception as e:
                log(f"  批次 {i} 失败: {e}")
        total_ins += n_ins
        log(f"== {subject} 入库完成: {n_ins} 条 ==")

    # 4. 验证
    stats = client.get_collection_stats(COLLECTION)
    log(f"全部完成! 本批入库 {total_ins} 条, Milvus 集合 entity 数: {stats['row_count']}")


if __name__ == "__main__":
    main()
