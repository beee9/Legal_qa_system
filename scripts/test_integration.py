# -*- coding: utf-8 -*-
"""Phase 4 集成测试：四类查询的完整检索链路（BM25 + 意图分类 + RAG 检索）
注：不依赖 LLM 生成（qwen3-max 调用另测），聚焦检索与分类链路正确性。"""
import sys
import logging
sys.path.insert(0, r"E:\陈杰\Legal_qa_system")
sys.path.insert(0, r"E:\陈杰\Legal_qa_system\mysql_qa")
sys.path.insert(0, r"E:\陈杰\Legal_qa_system\rag_qa\core")
logging.disable(logging.CRITICAL)

from base.config import Config
from mysql_qa.db.mysql_client import MySQLClient
from mysql_qa.retrieval.bm25_search import BM25Search
from mysql_qa.cache.redis_client import RedisClient
from query_classifier import QueryClassifier
from vector_store import VectorStore

conf = Config()

# 四类查询
CASES = [
    ("法条精确查询", "民法典第五百零九条是什么？"),
    ("概念解释", "什么是定金罚则？"),
    ("多实体对比", "定金和订金有什么区别？"),
    ("复杂场景咨询", "公司拖欠工资三个月，员工想维权，第一步该做什么？"),
]

print("=== Phase 4 集成测试 ===")
print(f"MySQL库: {conf.MYSQL_DATABASE} | Milvus集合: {conf.MILVUS_COLLECTION_NAME}")
print(f"意图模型: {conf.bert_intent_cls}\n")

# 初始化
mc = MySQLClient()
rc = RedisClient()
bm = BM25Search(rc, mc)
qc = QueryClassifier(conf.bert_intent_cls)
vs = VectorStore()

for cat, q in CASES:
    print(f"--- [{cat}] {q} ---")
    # 1. BM25 层
    answer, need_rag = bm.search(q, threshold=6.0)
    if answer:
        print(f"  ① BM25层: 命中MySQL (免RAG)")
        print(f"     答案: {answer[:55]}...")
    else:
        print(f"  ① BM25层: 未命中 -> 进入RAG")
        # 2. 意图分类
        cat2 = qc.predict_category(q)
        print(f"  ② 意图分类: {cat2}")
        # 3. RAG 检索
        docs = vs.hybrid_search_with_rerank(q)
        print(f"  ③ RAG检索 top1: [{docs[0].metadata.get('source')}] {docs[0].page_content[:45]}..." if docs else "  ③ RAG检索: 无结果")
    print()

print("=== 集成测试完成 ===")
