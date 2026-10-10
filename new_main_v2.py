"""
集成 QA 系统 - Phase 2 版本

新增功能：
1. 意图分类器（Phase 1）
2. 检索策略选择器（Phase 2）
3. 四种检索策略（直接/子查询/HyDE/回溯）

三层架构：
- Layer 1: 意图分类（通用/法条/咨询）
- Layer 2: 检索策略选择（直接/子查询/HyDE/回溯）
- Layer 3: 检索执行 + LLM 生成
"""

from mysql_qa import MySQLClient, RedisClient, BM25Search
from rag_qa import VectorStore
from base import logger, Config
from openai import OpenAI
import time
import uuid
import pymysql
import os

# 导入法律意图分类器（Phase 1）
try:
    from rag_qa.core.legal_query_classifier import LegalQueryClassifier
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    logger.warning("法律意图分类器未安装，将使用传统模式")

# 导入增强 RAG 系统（Phase 2）
try:
    from rag_qa.core.enhanced_rag_system import EnhancedRAGSystem
    from rag_qa.core.retrieval_strategy_selector import RetrievalStrategySelector
    ENHANCED_RAG_AVAILABLE = True
except ImportError:
    ENHANCED_RAG_AVAILABLE = False
    logger.warning("增强 RAG 系统未安装，将使用基础 RAG 模式")


class IntegratedQASystemV2:
    """集成 QA 系统 V2 - 包含 Phase 1 和 Phase 2 优化"""

    def __init__(self):
        self.logger = logger
        self.config = Config()

        # 初始化数据库和缓存
        self.mysql_client = MySQLClient()
        self.redis_client = RedisClient()
        self.bm25_search = BM25Search(self.redis_client, self.mysql_client)

        # 初始化 LLM 客户端
        try:
            self.client = OpenAI(
                api_key=self.config.DASHSCOPE_API_KEY,
                base_url=self.config.DASHSCOPE_BASE_URL
            )
        except Exception as e:
            self.logger.error(f"OpenAI 客户端初始化失败: {e}")
            raise

        # 初始化向量存储和 RAG 系统
        self._init_rag_system()

        # 初始化对话历史表
        self.init_conversation_table()

        # 初始化意图分类器（Phase 1）
        self._init_intent_classifier()

        # 初始化检索策略选择器（Phase 2）
        self._init_strategy_selector()

    def _init_rag_system(self):
        """初始化 RAG 系统（基础或增强版）"""
        try:
            self.vector_store = VectorStore()

            # 优先使用增强版 RAG（Phase 2）
            if ENHANCED_RAG_AVAILABLE:
                self.rag_system = EnhancedRAGSystem(
                    vector_store=self.vector_store,
                    llm_callable=self.call_dashscope
                )
                self.rag_available = True
                self.logger.info("✓ 增强版 RAG 系统已启动（支持 4 种检索策略）")
            else:
                # 回退到基础 RAG
                from rag_qa import RAGSystem
                self.rag_system = RAGSystem(self.vector_store, self.call_dashscope)
                self.rag_available = True
                self.logger.info("✓ 基础 RAG 系统已启动")

        except Exception as e:
            self.logger.warning(f"RAG 系统初始化失败: {e}")
            self.logger.warning("将使用 BM25 精确检索模式")
            self.vector_store = None
            self.rag_system = None
            self.rag_available = False

    def _init_intent_classifier(self):
        """初始化意图分类器（Phase 1）"""
        if CLASSIFIER_AVAILABLE:
            try:
                classifier_path = os.path.join(
                    os.path.dirname(__file__),
                    "rag_qa", "core", "legal_intent_classifier", "final_model"
                )
                self.query_classifier = LegalQueryClassifier(model_path=classifier_path)
                self.classifier_enabled = True
                self.logger.info("✓ 意图分类器已启动（三分类：法条查询/法律咨询/通用问题）")
            except Exception as e:
                self.logger.warning(f"意图分类器加载失败: {e}")
                self.query_classifier = None
                self.classifier_enabled = False
        else:
            self.query_classifier = None
            self.classifier_enabled = False

    def _init_strategy_selector(self):
        """初始化检索策略选择器（Phase 2）"""
        if ENHANCED_RAG_AVAILABLE and self.rag_available:
            try:
                self.strategy_selector = RetrievalStrategySelector()
                self.strategy_selector_enabled = True
                self.logger.info("✓ 检索策略选择器已启动（四策略：直接/子查询/HyDE/回溯）")
            except Exception as e:
                self.logger.warning(f"检索策略选择器加载失败: {e}")
                self.strategy_selector = None
                self.strategy_selector_enabled = False
        else:
            self.strategy_selector = None
            self.strategy_selector_enabled = False

    def init_conversation_table(self):
        """初始化对话历史表"""
        try:
            self.mysql_client.cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36) NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    intent VARCHAR(50),
                    strategy VARCHAR(50),
                    INDEX idx_session_id (session_id)
                )
            """)
            self.mysql_client.connection.commit()
            self.logger.info("对话历史表初始化成功")
        except pymysql.MySQLError as e:
            self.logger.error(f"初始化对话历史表失败: {e}")
            raise

    def call_dashscope(self, prompt):
        """调用 DashScope API（流式输出）"""
        try:
            completion = self.client.chat.completions.create(
                model=self.config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个专业的法律助手。"},
                    {"role": "user", "content": prompt},
                ],
                timeout=30,
                stream=True
            )

            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"LLM 调用失败: {e}")
            yield f"错误：LLM 调用失败 - {e}"

    def query(self, query_text: str, session_id: str = None):
        """
        完整查询流程（Phase 1 + Phase 2）

        流程：
        1. 意图分类（通用/法条/咨询）
        2. 根据意图选择路由
        3. 对于法律咨询，选择检索策略
        4. 执行检索并生成答案

        Args:
            query_text: 用户查询
            session_id: 会话ID

        Yields:
            str: 流式答案片段
        """
        start_time = time.time()
        session_id = session_id or str(uuid.uuid4())

        self.logger.info(f"[查询] '{query_text}' (session: {session_id})")

        # Phase 1: 意图分类
        intent = "法律咨询"  # 默认意图
        if self.classifier_enabled:
            intent = self.query_classifier.predict(query_text)
            self.logger.info(f"[意图分类] {intent}")

        # 路由决策
        strategy = None
        answer_generator = None

        if intent == "通用问题":
            # 直连 LLM，不检索
            self.logger.info("[路由] 通用问题 -> 直连 LLM")
            prompt = f"用户问题：{query_text}\n\n请简洁回答。"
            answer_generator = self.call_dashscope(prompt)

        elif intent == "法条查询":
            # BM25 精确检索
            self.logger.info("[路由] 法条查询 -> BM25 检索")
            bm25_results = self.bm25_search.search(query_text, top_k=3)

            if bm25_results:
                context = "\n\n".join([doc['text'] for doc in bm25_results])
                prompt = f"根据以下法律条文回答问题：\n\n{context}\n\n问题：{query_text}\n\n回答："
                answer_generator = self.call_dashscope(prompt)
            else:
                # BM25 未命中，回退到 RAG
                self.logger.info("[路由] BM25 未命中 -> 回退到 RAG")
                if self.rag_available:
                    answer_generator = self._rag_query(query_text, strategy="直接检索")
                else:
                    prompt = f"问题：{query_text}\n\n请回答："
                    answer_generator = self.call_dashscope(prompt)

        else:  # 法律咨询
            # Phase 2: 检索策略选择 + RAG
            self.logger.info("[路由] 法律咨询 -> RAG 向量检索")

            if self.rag_available:
                # 选择检索策略
                if self.strategy_selector_enabled:
                    strategy = self.strategy_selector.select_strategy(query_text)
                    self.logger.info(f"[检索策略] {strategy}")

                answer_generator = self._rag_query(query_text, strategy=strategy)
            else:
                # RAG 不可用，直接 LLM
                prompt = f"问题：{query_text}\n\n请提供法律建议："
                answer_generator = self.call_dashscope(prompt)

        # 流式输出答案
        full_answer = ""
        for chunk in answer_generator:
            full_answer += chunk
            yield chunk

        # 记录耗时和历史
        elapsed = time.time() - start_time
        self.logger.info(f"[查询完成] 耗时 {elapsed:.2f}s")

        # 保存到历史（异步，不影响返回）
        try:
            self._save_history(session_id, query_text, full_answer, intent, strategy)
        except Exception as e:
            self.logger.error(f"保存历史失败: {e}")

    def _rag_query(self, query_text: str, strategy: str = None):
        """
        RAG 查询（支持增强版和基础版）

        Args:
            query_text: 用户查询
            strategy: 检索策略（仅增强版支持）

        Yields:
            str: 流式答案片段
        """
        if ENHANCED_RAG_AVAILABLE and hasattr(self.rag_system, 'query'):
            # 增强版 RAG（Phase 2）
            return self.rag_system.query(query_text, strategy=strategy, stream=True)
        else:
            # 基础版 RAG（Phase 1）
            return self.rag_system.query(query_text, stream=True)

    def _save_history(self, session_id: str, question: str, answer: str,
                     intent: str = None, strategy: str = None):
        """保存对话历史到数据库"""
        try:
            self.mysql_client.cursor.execute("""
                INSERT INTO conversations
                (session_id, question, answer, timestamp, intent, strategy)
                VALUES (%s, %s, %s, NOW(), %s, %s)
            """, (session_id, question, answer, intent, strategy))
            self.mysql_client.connection.commit()
        except pymysql.MySQLError as e:
            self.logger.error(f"保存历史失败: {e}")


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("集成 QA 系统 V2 - Phase 1 + Phase 2")
    print("=" * 80)
    print("\nPhase 1 功能：")
    print("  - 意图分类器（通用/法条/咨询）")
    print("  - 智能路由（直连 LLM / BM25 / RAG）")
    print("\nPhase 2 功能：")
    print("  - 检索策略选择器")
    print("  - 四种检索策略：")
    print("    1. 直接检索")
    print("    2. 子查询检索")
    print("    3. HyDE 检索")
    print("    4. 回溯问题检索")
    print("=" * 80)

    # 初始化系统
    try:
        system = IntegratedQASystemV2()
        print("\n✓ 系统初始化成功")
    except Exception as e:
        print(f"\n✗ 系统初始化失败: {e}")
