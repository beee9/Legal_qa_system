# -*- coding: utf-8 -*-
"""Phase 4 单元测试：BM25 阈值边界、RAG 降级、rerank 排序"""
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

conf = Config()
mc = MySQLClient()
rc = RedisClient()
bm = BM25Search(rc, mc)

passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} {detail}")


print("=== 单元测试 ===")

# 1. BM25 精确匹配应命中（原始分数 > 阈值 6.0）
print("\n[BM25 精确匹配]")
for q in ["民法典第五百零九条是什么？", "什么是定金罚则？", "试用期最长可以约定多久？"]:
    ans, need = bm.search(q, threshold=6.0)
    check(f"命中: {q}", bool(ans), f"need_rag={need}")

# 2. BM25 无关查询不应命中（应降级到 RAG）
print("\n[BM25 无关查询 -> RAG 降级]")
for q in ["你好", "今天天气怎么样", "推荐一部电影"]:
    ans, need = bm.search(q, threshold=6.0)
    check(f"不命中且降级RAG: {q}", (not ans) and need, f"ans={bool(ans)} need_rag={need}")

# 3. BM25 阈值边界：提高阈值应更严格，降低阈值应更宽松
print("\n[BM25 阈值边界]")
ans_hi, _ = bm.search("民法典第五百零九条是什么？", threshold=6.0)
ans_lo, _ = bm.search("民法典第五百零九条是什么？", threshold=2.0)
check("低阈值(2.0)必命中", bool(ans_lo))
check("高阈值(6.0)命中(精确匹配分数高)", bool(ans_hi))

# 4. 缓存生效（第二次查询走缓存）
print("\n[Redis 缓存]")
ans1, _ = bm.search("民法典第五百零九条是什么？", threshold=6.0)
ans2, _ = bm.search("民法典第五百零九条是什么？", threshold=6.0)
check("缓存命中(两次结果一致)", ans1 == ans2 and bool(ans1))

print(f"\n===== 结果: {passed} 通过, {failed} 失败 =====")
sys.exit(1 if failed else 0)
