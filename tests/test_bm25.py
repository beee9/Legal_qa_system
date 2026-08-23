# -*- coding: utf-8 -*-
"""BM25 检索层测试（依赖 MySQL/Redis 服务，需先启动 Docker）"""
import logging
import sys
import pytest

sys.path.insert(0, r"E:\陈杰\Legal_qa_system")
sys.path.insert(0, r"E:\陈杰\Legal_qa_system\mysql_qa")
logging.disable(logging.CRITICAL)


@pytest.fixture(scope="module")
def bm25():
    from mysql_qa.db.mysql_client import MySQLClient
    from mysql_qa.retrieval.bm25_search import BM25Search
    from mysql_qa.cache.redis_client import RedisClient
    mc = MySQLClient()
    rc = RedisClient()
    return BM25Search(rc, mc)


class TestBM25:
    def test_exact_article_hit(self, bm25):
        ans, need = bm25.search("民法典第五百零九条是什么？", threshold=6.0)
        assert ans, "精确法条查询应命中 MySQL"

    def test_concept_hit(self, bm25):
        ans, need = bm25.search("什么是定金罚则？", threshold=6.0)
        assert ans

    def test_irrelevant_should_use_rag(self, bm25):
        ans, need = bm25.search("你好", threshold=6.0)
        assert not ans, "无关查询不应命中"
        assert need, "无关查询应降级到 RAG"

    def test_low_threshold_still_hits(self, bm25):
        ans, _ = bm25.search("民法典第五百零九条是什么？", threshold=2.0)
        assert ans

    def test_redis_cache(self, bm25):
        a1, _ = bm25.search("民法典第五百零九条是什么？", threshold=6.0)
        a2, _ = bm25.search("民法典第五百零九条是什么？", threshold=6.0)
        assert a1 == a2 and bool(a1)

    def test_mis_hit_should_downgrade_to_rag(self, bm25):
        """方案B：BM25 高分但语义不相关（靠通用词碰上）应降级走 RAG。
        例：拖欠工资问题误命中公司法"公司僵局"，校验应拦住。"""
        ans, need = bm25.search("员工离职时公司拖欠工资，请问法律上如何维权？", threshold=6.0)
        assert not ans, "误命中条目不应返回"
        assert need, "语义不相关应降级到 RAG"

    def test_relevant_hit_stays(self, bm25):
        """方案B：语义真正相关的查询仍应命中，不被误伤。"""
        ans, need = bm25.search("离职时公司扣工资不发怎么办", threshold=6.0)
        assert ans, "相关查询应保持命中"
