"""
集成 QA 系统 - Phase 3 最终版

完整功能：
- Phase 1: 意图分类（通用/法条/咨询）
- Phase 2: 检索策略选择（直接/子查询/HyDE/回溯）
- Phase 3: 上下文管理 + 对话摘要 + 优化 Prompt

三层架构：
- Layer 1: 意图分类 → 路由决策
- Layer 2: 策略选择 → 检索执行
- Layer 3: 上下文优化 → 答案生成
"""

from mysql_qa import MySQLClient, RedisClient, BM25Search
from rag_qa import VectorStore
from base import logger, Config
from openai import OpenAI
import time
import uuid
import pymysql
import os

# Phase 1: 意图分类器
try:
    from rag_qa.core.legal_query_classifier import LegalQueryClassifier
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    logger.warning("意图分类器未安装")

# Phase 2: 增强 RAG 系统
try:
    from rag_qa.core.retrieval_strategy_selector import RetrievalStrategySelector
    STRATEGY_SELECTOR_AVAILABLE = True
except ImportError:
    STRATEGY_SELECTOR_AVAILABLE = False
    logger.warning("检索策略选择器未安装")

# Phase 3: 最终增强版 RAG 系统
try:
    from rag_qa.core.ultimate_rag_system import UltimateRAGSystem
    ULTIMATE_RAG_AVAILABLE = True
except ImportError:
    ULTIMATE_RAG_AVAILABLE = False
    logger.warning("Phase 3 最终版 RAG 未安装")


class IntegratedQASystemV3:
    """集成 QA 系统 V3 - Phase 1 + Phase 2 + Phase 3"""

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

        # 初始化 RAG 系统
        self._init_rag_system()

        # 初始化对话历史表
        self.init_conversation_table()

        # 初始化意图分类器（Phase 1）
        self._init_intent_classifier()

        # 初始化检索策略选择器（Phase 2）
        self._init_strategy_selector()

        # 系统信息
        self._log_system_info()

    def _init_rag_system(self):
        """初始化 RAG 系统（Phase 3 最终版）"""
        try:
            self.vector_store = VectorStore()

            # 优先使用 Phase 3 最终版
            if ULTIMATE_RAG_AVAILABLE:
                self.rag_system = UltimateRAGSystem(
                    vector_store=self.vector_store,
                    llm_callable=self.call_dashscope
                )
                self.rag_available = True
                self.rag_version = "Phase 3"
                self.logger.info("✓ Phase 3 最终版 RAG 系统已启动")
            elif STRATEGY_SELECTOR_AVAILABLE:
                # 回退到 Phase 2
                from rag_qa.core.enhanced_rag_system import EnhancedRAGSystem
                self.rag_system = EnhancedRAGSystem(
                    vector_store=self.vector_store,
                    llm_callable=self.call_dashscope
                )
                self.rag_available = True
                self.rag_version = "Phase 2"
                self.logger.info("✓ Phase 2 增强版 RAG 系统已启动")
            else:
                # 回退到基础版
                from rag_qa import RAGSystem
                self.rag_system = RAGSystem(self.vector_store, self.call_dashscope)
                self.rag_available = True
                self.rag_version = "Phase 1"
                self.logger.info("✓ 基础 RAG 系统已启动")

        except Exception as e:
            self.logger.warning(f"RAG 系统初始化失败: {e}")
            self.logger.warning("将使用 BM25 精确检索模式")
            self.vector_store = None
            self.rag_system = None
            self.rag_available = False
            self.rag_version = None

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
                self.logger.info("✓ Phase 1: 意图分类器已启动")
            except Exception as e:
                self.logger.warning(f"意图分类器加载失败: {e}")
                self.query_classifier = None
                self.classifier_enabled = False
        else:
            self.query_classifier = None
            self.classifier_enabled = False

    def _init_strategy_selector(self):
        """初始化检索策略选择器（Phase 2）"""
        if STRATEGY_SELECTOR_AVAILABLE and self.rag_available:
            try:
                self.strategy_selector = RetrievalStrategySelector()
                self.strategy_selector_enabled = True
                self.logger.info("✓ Phase 2: 检索策略选择器已启动")
            except Exception as e:
                self.logger.warning(f"检索策略选择器加载失败: {e}")
                self.strategy_selector = None
                self.strategy_selector_enabled = False
        else:
            self.strategy_selector = None
            self.strategy_selector_enabled = False

    def _log_system_info(self):
        """记录系统信息"""
        self.logger.info("=" * 80)
        self.logger.info("系统初始化完成")
        self.logger.info(f"  - RAG 版本: {self.rag_version or '不可用'}")
        self.logger.info(f"  - 意图分类器: {'启用' if self.classifier_enabled else '禁用'}")
        self.logger.info(f"  - 策略选择器: {'启用' if self.strategy_selector_enabled else '禁用'}")
        self.logger.info(f"  - 对话摘要: {'启用' if self.rag_version == 'Phase 3' else '禁用'}")
        self.logger.info(f"  - 上下文管理: {'启用' if self.rag_version == 'Phase 3' else '禁用'}")
        self.logger.info("=" * 80)

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
                    INDEX idx_session_id (session_id),
                    INDEX idx_timestamp (timestamp)
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

    def get_conversation_history(self, session_id: str, limit: int = 10) -> list:
        """获取对话历史"""
        try:
            self.mysql_client.cursor.execute("""
                SELECT question, answer FROM conversations
                WHERE session_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (session_id, limit))

            history = [
                {"question": row[0], "answer": row[1]}
                for row in self.mysql_client.cursor.fetchall()
            ]
            return history[::-1]  # 反转为时间正序
        except pymysql.MySQLError as e:
            self.logger.error(f"获取对话历史失败: {e}")
            return []

    def query(self, query_text: str, session_id: str = None, use_history: bool = True):
        """
        完整查询流程（Phase 1 + Phase 2 + Phase 3）

        Args:
            query_text: 用户查询
            session_id: 会话ID
            use_history: 是否使用对话历史（Phase 3 特性）

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
            self.logger.info(f"[Phase 1] 意图分类: {intent}")

        # 获取对话历史（Phase 3）
        conversation_history = None
        if use_history and self.rag_version == "Phase 3":
            conversation_history = self.get_conversation_history(session_id)
            self.logger.info(f"[Phase 3] 对话历史: {len(conversation_history)} 轮")

        # 路由决策
        strategy = None
        answer_generator = None

        if intent == "通用问题":
            # 直连 LLM
            self.logger.info("[路由] 通用问题 → 直连 LLM")
            prompt = f"用户问题：{query_text}\n\n请简洁回答。"
            answer_generator = self.call_dashscope(prompt)

        elif intent == "法条查询":
            # BM25 精确检索
            self.logger.info("[路由] 法条查询 → BM25 检索")
            bm25_results = self.bm25_search.search(query_text, top_k=3)

            if bm25_results:
                context = "\n\n".join([doc['text'] for doc in bm25_results])
                prompt = f"根据以下法律条文回答问题：\n\n{context}\n\n问题：{query_text}\n\n回答："
                answer_generator = self.call_dashscope(prompt)
            else:
                # 回退到 RAG
                self.logger.info("[路由] BM25 未命中 → 回退到 RAG")
                if self.rag_available:
                    answer_generator = self._rag_query(
                        query_text,
                        strategy="直接检索",
                        conversation_history=conversation_history
                    )
                else:
                    prompt = f"问题：{query_text}\n\n请回答："
                    answer_generator = self.call_dashscope(prompt)

        else:  # 法律咨询
            # Phase 2 + Phase 3: RAG 检索
            self.logger.info("[路由] 法律咨询 → RAG 向量检索")

            if self.rag_available:
                # Phase 2: 选择检索策略
                if self.strategy_selector_enabled:
                    strategy = self.strategy_selector.select_strategy(query_text)
                    self.logger.info(f"[Phase 2] 检索策略: {strategy}")

                # Phase 3: 使用对话历史
                answer_generator = self._rag_query(
                    query_text,
                    strategy=strategy,
                    conversation_history=conversation_history
                )
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

        # 保存到历史
        try:
            self._save_history(session_id, query_text, full_answer, intent, strategy)
        except Exception as e:
            self.logger.error(f"保存历史失败: {e}")

    def _rag_query(
        self,
        query_text: str,
        strategy: str = None,
        conversation_history: list = None
    ):
        """
        RAG 查询（支持 Phase 2 和 Phase 3）

        Args:
            query_text: 用户查询
            strategy: 检索策略
            conversation_history: 对话历史

        Yields:
            str: 流式答案片段
        """
        if self.rag_version == "Phase 3" and hasattr(self.rag_system, 'query_with_history'):
            # Phase 3: 支持对话历史
            return self.rag_system.query(
                query_text,
                strategy=strategy,
                stream=True,
                conversation_history=conversation_history
            )
        elif self.rag_version == "Phase 2" and hasattr(self.rag_system, 'query'):
            # Phase 2: 支持策略选择
            return self.rag_system.query(query_text, strategy=strategy, stream=True)
        else:
            # Phase 1: 基础 RAG
            return self.rag_system.query(query_text, stream=True)

    def _save_history(
        self,
        session_id: str,
        question: str,
        answer: str,
        intent: str = None,
        strategy: str = None
    ):
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
    print("集成 QA 系统 V3 - Phase 1 + Phase 2 + Phase 3")
    print("=" * 80)
    print("\nPhase 1: 意图分类")
    print("  - 通用问题 → 直连 LLM")
    print("  - 法条查询 → BM25 精确检索")
    print("  - 法律咨询 → RAG 向量检索")
    print("\nPhase 2: 检索策略选择")
    print("  - 直接检索")
    print("  - 子查询检索")
    print("  - HyDE 检索")
    print("  - 回溯问题检索")
    print("\nPhase 3: Prompt 优化")
    print("  - 智能上下文管理")
    print("  - 对话历史摘要")
    print("  - 优化 Prompt 模板")
    print("=" * 80)

    try:
        system = IntegratedQASystemV3()
        print("\n✓ 系统初始化成功")
    except Exception as e:
        print(f"\n✗ 系统初始化失败: {e}")
