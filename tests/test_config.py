# -*- coding: utf-8 -*-
"""Config 单元测试（纯逻辑，不依赖外部服务）"""
import os
import sys
import pytest

sys.path.insert(0, r"E:\陈杰\Legal_qa_system")


class TestConfig:
    def test_loads_legal_database(self):
        from base.config import Config
        c = Config()
        assert c.MYSQL_DATABASE == "legal_qa"

    def test_loads_legal_milvus_collection(self):
        from base.config import Config
        c = Config()
        assert c.MILVUS_COLLECTION_NAME == "legal_rag"

    def test_valid_sources_are_six_laws(self):
        from base.config import Config
        c = Config()
        assert len(c.VALID_SOURCES) == 6
        assert "民法典" in c.VALID_SOURCES

    def test_api_key_loaded_from_env(self):
        from base.config import Config
        c = Config()
        # 密钥应从 .env 加载，且非空
        assert c.DASHSCOPE_API_KEY, "DASHSCOPE_API_KEY 未从 .env 加载"
        assert c.DASHSCOPE_API_KEY.startswith("sk-")

    def test_project_root_exists(self):
        from base.config import Config
        assert os.path.exists(Config._PROJECT_ROOT)
        assert os.path.exists(os.path.join(Config._PROJECT_ROOT, "config.ini"))
