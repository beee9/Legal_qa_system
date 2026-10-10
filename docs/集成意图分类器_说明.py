"""
集成法律意图分类器到现有系统

修改说明：
1. 在 IntegratedQASystem 初始化时加载分类器
2. 在 query 方法中添加意图判断逻辑
3. 根据意图选择不同的处理路径
"""

# ============ 修改 1: 在 new_main.py 顶部导入 ============
# 在第 14 行 import pymysql 后添加：

try:
    from rag_qa.core.legal_query_classifier import LegalQueryClassifier
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    print("警告: 法律意图分类器未安装，将使用传统模式")


# ============ 修改 2: 在 IntegratedQASystem.__init__ 中初始化分类器 ============
# 在第 49 行 self.init_conversation_table() 后添加：

        # 初始化法律意图分类器（可选）
        if CLASSIFIER_AVAILABLE:
            try:
                classifier_path = os.path.join(
                    os.path.dirname(__file__),
                    "rag_qa", "core", "legal_intent_classifier", "final_model"
                )
                self.query_classifier = LegalQueryClassifier(model_path=classifier_path)
                self.classifier_enabled = True
                self.logger.info("法律意图分类器已启动")
            except Exception as e:
                self.logger.warning(f"法律意图分类器加载失败: {e}")
                self.query_classifier = None
                self.classifier_enabled = False
        else:
            self.query_classifier = None
            self.classifier_enabled = False


# ============ 修改 3: 在 query 方法开头添加意图分类逻辑 ============
# 在第 167 行 history = ... 后添加：

        # 意图分类（如果启用）
        if self.classifier_enabled and self.query_classifier:
            intent = self.query_classifier.predict_category(query)
            self.logger.info(f"意图分类结果: {intent}")

            # 1. 通用问题 - 直连 LLM
            if intent == "通用问题":
                self.logger.info("检测到通用问题，直接调用 LLM")
                prompt = f"你是一个有用的助手。请回答以下问题：\n\n{query}"
                answer = ""
                for token in self.call_dashscope(prompt):
                    answer += token
                    yield token, False

                # 更新历史
                if session_id:
                    self.update_session_history(session_id, query, answer)

                processing_time = time.time() - start_time
                self.logger.info(f"通用问题处理完成，耗时 {processing_time:.2f}秒")
                yield "", True
                return

            # 2. 法条查询 - 优先 BM25 精确检索
            elif intent == "法条查询":
                self.logger.info("检测到法条查询，使用 BM25 精确检索")
                # 降低阈值，因为法条查询通常很精确
                answer, need_rag = self.bm25_search.search(query, threshold=3.0)

                if answer and not need_rag:
                    self.logger.info(f"BM25 找到精确答案")
                    if session_id:
                        self.update_session_history(session_id, query, answer)
                    processing_time = time.time() - start_time
                    self.logger.info(f"查询处理耗时 {processing_time:.2f}秒")
                    yield answer, True
                    return
                # 如果 BM25 没找到，继续走下面的 RAG 流程
                self.logger.info("BM25 未找到，回退到 RAG")

            # 3. 法律咨询 - 使用 RAG 语义检索
            else:  # intent == "法律咨询"
                self.logger.info("检测到法律咨询，使用 RAG 语义检索")
                # 跳过 BM25，直接走 RAG
                force_rag = True
        else:
            # 分类器未启用，使用原有逻辑
            force_rag = False


# ============ 修改 4: 调整原有的 BM25/RAG 逻辑 ============
# 将原来的第 172-175 行改为：

        # 如果未通过分类器强制 RAG，则执行 BM25 检索
        if not force_rag:
            answer, need_rag = self.bm25_search.search(query, threshold=6.0)
        else:
            answer, need_rag = None, True


# ============ 完整的修改后的 query 方法 ============
"""
完整代码见下方
"""
