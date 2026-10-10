# 导入MySQL和Redis客户端，管理数据库和缓存
from mysql_qa import MySQLClient, RedisClient, BM25Search
# 导入RAG系统组件
from rag_qa import VectorStore, RAGSystem
# 导入配置和日志
from base import logger, Config
# 导入OpenAI客户端，用于DashScope API
from openai import OpenAI
# 导入时间库，记录处理时间
import time
# 导入UUID生成唯一会话ID
import uuid
# 导入pymysql错误处理
import pymysql
# 导入 os 用于路径处理
import os

# 导入法律意图分类器
try:
    from rag_qa.core.legal_query_classifier import LegalQueryClassifier
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    logger.warning("法律意图分类器未安装，将使用传统模式")


class IntegratedQASystem:
    def __init__(self):
        # 初始化日志
        self.logger = logger
        # 初始化配置
        self.config = Config()
        # 初始化MySQL客户端
        self.mysql_client = MySQLClient()
        # 初始化Redis客户端
        self.redis_client = RedisClient()
        # 初始化BM25搜索
        self.bm25_search = BM25Search(self.redis_client, self.mysql_client)
        try:
            # 初始化OpenAI客户端，连接DashScope API
            self.client = OpenAI(api_key=self.config.DASHSCOPE_API_KEY,
                                 base_url=self.config.DASHSCOPE_BASE_URL)
        except Exception as e:
            self.logger.error(f"OpenAI客户端初始化失败: {e}")
            raise
        # 初始化向量存储（可选，如果 Milvus 不可用则跳过）
        try:
            self.vector_store = VectorStore()
            self.rag_system = RAGSystem(self.vector_store, self.call_dashscope)
            self.rag_available = True
            self.logger.info("RAG 向量检索系统已启动")
        except Exception as e:
            self.logger.warning(f"RAG 向量检索系统初始化失败（Milvus 不可用）: {e}")
            self.logger.warning("将使用 BM25 精确检索模式")
            self.vector_store = None
            self.rag_system = None
            self.rag_available = False
        # 初始化对话历史表
        self.init_conversation_table()

        # 初始化法律意图分类器（可选）
        if CLASSIFIER_AVAILABLE:
            try:
                classifier_path = os.path.join(
                    os.path.dirname(__file__),
                    "rag_qa", "core", "legal_intent_classifier", "final_model"
                )
                self.query_classifier = LegalQueryClassifier(model_path=classifier_path)
                self.classifier_enabled = True
                self.logger.info("✓ 法律意图分类器已启动（三分类：法条查询/法律咨询/通用问题）")
            except Exception as e:
                self.logger.warning(f"法律意图分类器加载失败: {e}")
                self.query_classifier = None
                self.classifier_enabled = False
        else:
            self.query_classifier = None
            self.classifier_enabled = False

    def init_conversation_table(self):
        """初始化MySQL中的conversations表，用于存储对话历史"""
        try:
            self.mysql_client.cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36) NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    INDEX idx_session_id (session_id)
                )
            """)
            self.mysql_client.connection.commit()
            self.logger.info("对话历史表初始化成功")
        except pymysql.MySQLError as e:
            self.logger.error(f"初始化对话历史表失败: {e}")
            raise

    # 调用模型
    def call_dashscope(self, prompt):
        """调用DashScope API生成答案（流式输出，生成器）"""
        try:
            completion = self.client.chat.completions.create(
                model=self.config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个有用的助手。"},
                    {"role": "user", "content": prompt},
                ],
                timeout=30,
                stream=True  # 启用流式输出
            )

            # 逐个 yield 每个 chunk
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield content
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            yield f"错误：LLM调用失败 - {e}"

    def _fetch_recent_history(self, session_id: str) -> list:
        """获取最近 N 轮对话历史（N = config.HISTORY_LIMIT）"""
        try:
            self.mysql_client.cursor.execute("""
                SELECT question, answer
                FROM conversations
                WHERE session_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (session_id, self.config.HISTORY_LIMIT))
            history = [{"question": row[0], "answer": row[1]} for row in self.mysql_client.cursor.fetchall()]
            return history[::-1]
        except pymysql.MySQLError as e:
            self.logger.error(f"获取对话历史失败: {e}")
            return []

    def update_session_history(self, session_id: str, question: str, answer: str) -> list:
        """更新会话历史到MySQL，保留最近 N 轮对话"""
        try:
            self.mysql_client.cursor.execute("""
                INSERT INTO conversations (session_id, question, answer, timestamp)
                VALUES (%s, %s, %s, NOW())
            """, (session_id, question, answer))
            history = self._fetch_recent_history(session_id)
            self.mysql_client.cursor.execute("""
                DELETE FROM conversations
                WHERE session_id = %s AND id NOT IN (
                    SELECT id FROM (
                        SELECT id
                        FROM conversations
                        WHERE session_id = %s
                        ORDER BY timestamp DESC
                        LIMIT %s
                    ) AS sub
                )
            """, (session_id, session_id, self.config.HISTORY_LIMIT))
            self.mysql_client.connection.commit()
            self.logger.info(f"会话 {session_id} 历史更新成功")
            return history
        except pymysql.MySQLError as e:
            self.logger.error(f"更新会话历史失败: {e}")
            self.mysql_client.connection.rollback()
            raise
        except Exception as e:
            self.logger.error(f"更新会话历史意外错误: {e}")
            self.mysql_client.connection.rollback()
            raise

    def get_session_history(self, session_id: str) -> list:
        """从MySQL获取会话历史"""
        return self._fetch_recent_history(session_id)

    def clear_session_history(self, session_id: str) -> bool:
        """清除指定会话历史"""
        try:
            self.mysql_client.cursor.execute("""
                DELETE FROM conversations
                WHERE session_id = %s
            """, (session_id,))
            self.mysql_client.connection.commit()
            self.logger.info(f"会话 {session_id} 历史已清除")
            return True
        except pymysql.MySQLError as e:
            self.logger.error(f"清除会话历史失败: {e}")
            self.mysql_client.connection.rollback()
            return False

    # 修改 main.py 中的 query 方法
    def query(self, query, source_filter=None, session_id=None, force_rag=False):
        """查询集成系统，支持意图分类、对话历史和流式输出。

        force_rag: 调用方已知该查询需要走 RAG（例如 WebSocket 流式请求前
        已在 /api/query 中做过 BM25 判断），跳过重复的 BM25 精确检索。
        """
        start_time = time.time()
        self.logger.info(f"处理查询: '{query}' (会话ID: {session_id})")
        history = self.get_session_history(session_id) if session_id else []

        # ========== 意图分类逻辑（新增） ==========
        if self.classifier_enabled and self.query_classifier and not force_rag:
            intent = self.query_classifier.predict_category(query)
            self.logger.info(f"✓ 意图分类: {intent}")

            # 1. 通用问题 - 直连 LLM（不检索法律库）
            if intent == "通用问题":
                self.logger.info("→ 路由：直连 LLM（通用问题）")
                prompt = f"你是一个有用的助手。请回答以下问题：\n\n{query}"
                collected_answer = ""

                for token in self.call_dashscope(prompt):
                    collected_answer += token
                    yield token, False

                # 更新历史
                if session_id:
                    self.update_session_history(session_id, query, collected_answer)

                processing_time = time.time() - start_time
                self.logger.info(f"通用问题处理完成，耗时 {processing_time:.2f}秒")
                yield "", True
                return

            # 2. 法条查询 - 优先 BM25 精确检索（降低阈值）
            elif intent == "法条查询":
                self.logger.info("→ 路由：BM25 精确检索（法条查询）")
                answer, need_rag = self.bm25_search.search(query, threshold=3.0)

                if answer and not need_rag:
                    self.logger.info(f"BM25 命中法条")
                    if session_id:
                        self.update_session_history(session_id, query, answer)
                    processing_time = time.time() - start_time
                    self.logger.info(f"查询处理耗时 {processing_time:.2f}秒")
                    yield answer, True
                    return
                else:
                    self.logger.info("BM25 未命中，回退到 RAG")
                    force_rag = True

            # 3. 法律咨询 - 直接走 RAG 语义检索
            else:  # intent == "法律咨询"
                self.logger.info("→ 路由：RAG 语义检索（法律咨询）")
                force_rag = True

        # ========== 原有的 BM25 / RAG 逻辑 ==========
        # 默认先尝试MySQL精确查询；force_rag 时跳过（避免同一查询检索两次）
        if force_rag:
            answer, need_rag = None, True
        else:
            answer, need_rag = self.bm25_search.search(query, threshold=6.0)

        if answer and not force_rag:
            # MySQL找到精确答案，直接返回
            self.logger.info(f"MySQL答案: {answer}")
            if session_id:
                self.update_session_history(session_id, query, answer)  # 把BM25的QA更新到会话历史
            processing_time = time.time() - start_time
            self.logger.info(f"查询处理耗时 {processing_time:.2f}秒")
            # 对于MySQL答案，一次性返回
            yield answer, True  # 第二个参数表示这是完整答案
        elif need_rag and self.rag_available:
            # 需要使用RAG系统，支持流式输出
            self.logger.info("无可靠MySQL答案，回退到RAG")

            # 收集完整答案以便存储
            collected_answer = ""

            # 从RAG系统获取流式输出
            for token in self.rag_system.generate_answer(query, source_filter=source_filter, history=history):
                collected_answer += token
                yield token, False  # 第二个参数表示这是部分答案

            # 完整答案收集完毕，更新会话历史
            if session_id:
                self.update_session_history(session_id, query, collected_answer)  # 把RAG的QA更新到会话历史

            processing_time = time.time() - start_time
            self.logger.info(f"查询处理耗时 {processing_time:.2f}秒")
            # 标记结束
            yield "", True  # 空字符串表示流结束，True表示完成
        elif need_rag and not self.rag_available:
            # RAG 系统不可用
            self.logger.warning("RAG系统不可用，无法处理此查询")
            answer = "抱歉，向量检索系统当前不可用。本查询需要语义理解，建议：\n1. 尝试更精确的关键词\n2. 直接查询具体法条（如：民法典第509条）\n3. 联系管理员启动 Milvus 向量数据库"
            if session_id:
                self.update_session_history(session_id, query, answer)
            processing_time = time.time() - start_time
            self.logger.info(f"查询处理耗时 {processing_time:.2f}秒")
            yield answer, True
        else:
            # 未找到答案
            self.logger.info("未找到答案")
            processing_time = time.time() - start_time
            self.logger.info(f"查询处理耗时 {processing_time:.2f}秒")
            yield "未找到答案", True  # 一次性返回


def main():
    qa_system = IntegratedQASystem()
    session_id = str(uuid.uuid4())
    print("\n欢迎使用法律智能问答系统！")
    print(f"会话ID: {session_id}")
    print(f"支持的法律领域：{qa_system.config.VALID_SOURCES}")
    print("本系统提供民法典、劳动法、公司法等常用法律的信息参考，不构成法律意见。")
    print("输入查询进行问答，输入 'exit' 退出。")

    try:
        while True:
            query = input("\n输入查询: ").strip()
            if query.lower() == "exit":
                logger.info("退出系统")
                print("再见！")
                break
            source_filter = input(
                f"请输入学科类别 ({'/'.join(qa_system.config.VALID_SOURCES)}) (直接回车默认不过滤): ").strip()
            if source_filter and source_filter not in qa_system.config.VALID_SOURCES:
                logger.warning(f"无效的学科类别 '{source_filter}'，将不过滤")
                source_filter = None

            print("\n答案: ", end="", flush=True)  # 开始打印答案
            answer = ""  # 用于累积完整答案
            # 迭代 query 方法的生成器
            for token, is_complete in qa_system.query(query, source_filter=source_filter, session_id=session_id):
                if token:  # 仅当 token 非空时打印
                    print(token, end="", flush=True)  # 流式打印
                    answer += token  # 累积答案
                if is_complete:  # 如果是完整答案或流结束，换行并退出循环
                    print()  # 换行
                    break

            # 打印对话历史
            history = qa_system.get_session_history(session_id)
            print("\n最近对话历史:")
            for idx, entry in enumerate(history, 1):
                print(f"{idx}. 问: {entry['question']}\n   答: {entry['answer']}")
    except Exception as e:
        logger.error(f"系统错误: {e}")
        print(f"发生错误: {e}")
    finally:
        qa_system.mysql_client.close()


if __name__ == "__main__":
    main()
