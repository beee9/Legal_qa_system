# -*- coding: utf-8 -*-
"""Phase 1-3: 6 部法律切块 -> embedding(bge-m3) -> 入库 Milvus 集合 legal_rag"""
import time
import re
import warnings
import sys
import numpy as np
warnings.filterwarnings("ignore")

from pathlib import Path
from milvus_model.hybrid import BGEM3EmbeddingFunction
from pymilvus import MilvusClient, DataType

PROJECT = Path(r"E:\陈杰\Legal_qa_system")
DATA_DIR = PROJECT / "legal_data"
M3_PATH = r"E:\陈杰\Itcast_qa_system\rag_qa\models\bge-m3"
MILVUS_URI = "http://localhost:19530"
COLLECTION = "legal_rag"
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
    # 1. 加载模型
    log(f"加载 bge-m3 模型...")
    t0 = time.time()
    emb = BGEM3EmbeddingFunction(model_name_or_path=M3_PATH, device="cpu")
    log(f"模型加载完成, 耗时 {time.time()-t0:.0f}s")

    # 2. 连接 Milvus & 建集合（pymilvus 3.0 Schema 方式）
    log("连接 Milvus...")
    client = MilvusClient(uri=MILVUS_URI)
    if client.has_collection(COLLECTION):
        log(f"集合 {COLLECTION} 已存在, 删除重建")
        client.drop_collection(COLLECTION)
    schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field("subject", DataType.VARCHAR, max_length=50)
    schema.add_field("text", DataType.VARCHAR, max_length=4000)
    schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=DENSE_DIM)
    index_params = client.prepare_index_params()
    index_params.add_index("dense_vector", index_type="IVF_FLAT", metric_type="IP", params={"nlist": 128})
    client.create_collection(collection_name=COLLECTION, schema=schema, index_params=index_params)
    log(f"集合 {COLLECTION} 已创建 (dense 1024 + sparse)")

    # 3. 逐部法律切块 + 分批 embedding 入库
    total_ins = 0
    for fname, subject in LAWS:
        with open(DATA_DIR / fname, "r", encoding="utf-8") as f:
            text = f.read()
        arts = extract_articles(text)
        log(f"== {subject}: {len(arts)} 条条文 ==")
        # 分批
        BATCH = 24
        n_ins = 0
        for i in range(0, len(arts), BATCH):
            chunk = arts[i:i + BATCH]
            texts = [f"{num} {body}" for num, body in chunk]
            try:
                out = emb(texts)
                dense = np.asarray(out["dense"]).tolist()
                rows = []
                for j, (num, body) in enumerate(chunk):
                    rows.append({
                        "subject": subject,
                        "text": f"{num} {body}",
                        "dense_vector": dense[j],
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
    log(f"全部完成! 总入库 {total_ins} 条, Milvus 集合 entity 数: {stats['row_count']}")


if __name__ == "__main__":
    main()
