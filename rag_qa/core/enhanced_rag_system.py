"""
增强版 RAG 系统 - Phase 2

整合多种检索策略：
1. 直接检索
2. 子查询检索
3. HyDE 检索
4. 回溯问题检索
"""

import time
from typing import List, Optional
from base import logger, Config
from .legal_rag_prompts import LegalRAGPrompts
from .retrieval_strategy_selector import RetrievalStrategySelector


class EnhancedRAGSystem:
    """增强版 RAG 系统"""

    def __init__(self, vector_store, llm_callable, strategy_selector=None):
        """
        初始化增强版 RAG 系统

        Args:
            vector_store: 向量存储对象（支持 hybrid_search_with_rerank）
            llm_callable: LLM 调用函数（生成器，用于流式输出）
            strategy_selector: 检索策略选择器（可选）
        """
        self.vector_store = vector_store
        self.llm = llm_callable
        self.config = Config()

        # 初始化 Prompt 模板
        self.prompts = LegalRAGPrompts()

        # 初始化策略选择器
        self.strategy_selector = strategy_selector or RetrievalStrategySelector()

        # 检索参数
        self.retrieval_k = 5  # 每次检索返回的文档数
        self.max_context_docs = 10  # 最终上下文的最大文档数

    def _call_llm_sync(self, prompt):
        """
        同步调用 LLM（用于策略内部的查询转换）

        Args:
            prompt: 提示词

        Returns:
            str: LLM 响应
        """
        try:
            # 将生成器转换为字符串
            response = ""
            for chunk in self.llm(prompt):
                response += chunk
            return response.strip()
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return ""

    def _retrieve_direct(self, query: str) -> List:
        """
        直接检索策略

        Args:
            query: 用户查询

        Returns:
            List: 检索到的文档列表
        """
        logger.info(f"[直接检索] 查询: '{query}'")
        try:
            docs = self.vector_store.hybrid_search_with_rerank(
                query,
                k=self.retrieval_k
            )
            logger.info(f"[直接检索] 检索到 {len(docs)} 个文档")
            return docs
        except Exception as e:
            logger.error(f"[直接检索] 失败: {e}")
            return []

    def _retrieve_subquery(self, query: str) -> List:
        """
        子查询检索策略

        将复杂查询分解为多个子查询，分别检索后合并去重

        Args:
            query: 用户查询

        Returns:
            List: 检索到的文档列表
        """
        logger.info(f"[子查询检索] 原始查询: '{query}'")
        try:
            # 1. 生成子查询
            subquery_prompt = self.prompts.subquery_prompt()
            subqueries_text = self._call_llm_sync(subquery_prompt.format(query=query))

            # 解析子查询（每行一个）
            subqueries = [sq.strip() for sq in subqueries_text.split('\n') if sq.strip()]
            logger.info(f"[子查询检索] 生成了 {len(subqueries)} 个子查询: {subqueries}")

            # 2. 对每个子查询进行检索
            all_docs = []
            for i, subquery in enumerate(subqueries):
                logger.info(f"[子查询检索] 处理子查询 {i+1}/{len(subqueries)}: '{subquery}'")
                docs = self.vector_store.hybrid_search_with_rerank(
                    subquery,
                    k=self.retrieval_k
                )
                all_docs.extend(docs)

            # 3. 去重（根据文档内容去重）
            unique_docs = []
            seen_contents = set()
            for doc in all_docs:
                content = doc.page_content
                if content not in seen_contents:
                    seen_contents.add(content)
                    unique_docs.append(doc)

            logger.info(f"[子查询检索] 去重后共 {len(unique_docs)} 个文档")
            return unique_docs

        except Exception as e:
            logger.error(f"[子查询检索] 失败: {e}")
            # 失败时回退到直接检索
            return self._retrieve_direct(query)

    def _retrieve_hyde(self, query: str) -> List:
        """
        HyDE（假设文档嵌入）检索策略

        先生成假设答案，再用假设答案进行检索

        Args:
            query: 用户查询

        Returns:
            List: 检索到的文档列表
        """
        logger.info(f"[HyDE 检索] 原始查询: '{query}'")
        try:
            # 1. 生成假设答案
            hyde_prompt = self.prompts.hyde_prompt()
            hypothetical_answer = self._call_llm_sync(hyde_prompt.format(query=query))
            logger.info(f"[HyDE 检索] 生成假设答案 ({len(hypothetical_answer)} 字符)")
            logger.debug(f"[HyDE 检索] 假设答案: {hypothetical_answer[:200]}...")

            # 2. 使用假设答案进行检索
            docs = self.vector_store.hybrid_search_with_rerank(
                hypothetical_answer,
                k=self.retrieval_k
            )

            logger.info(f"[HyDE 检索] 检索到 {len(docs)} 个文档")
            return docs

        except Exception as e:
            logger.error(f"[HyDE 检索] 失败: {e}")
            # 失败时回退到直接检索
            return self._retrieve_direct(query)

    def _retrieve_backtracking(self, query: str) -> List:
        """
        回溯问题检索策略

        将口语化、冗长的查询简化为核心问题

        Args:
            query: 用户查询

        Returns:
            List: 检索到的文档列表
        """
        logger.info(f"[回溯检索] 原始查询: '{query}'")
        try:
            # 1. 简化查询
            backtrack_prompt = self.prompts.backtracking_prompt()
            simplified_query = self._call_llm_sync(backtrack_prompt.format(query=query))
            logger.info(f"[回溯检索] 简化后: '{simplified_query}'")

            # 2. 使用简化查询进行检索
            docs = self.vector_store.hybrid_search_with_rerank(
                simplified_query,
                k=self.retrieval_k
            )

            logger.info(f"[回溯检索] 检索到 {len(docs)} 个文档")
            return docs

        except Exception as e:
            logger.error(f"[回溯检索] 失败: {e}")
            # 失败时回退到直接检索
            return self._retrieve_direct(query)

    def retrieve_documents(self, query: str, strategy: Optional[str] = None) -> List:
        """
        根据策略检索文档

        Args:
            query: 用户查询
            strategy: 检索策略（可选，不提供则自动选择）

        Returns:
            List: 检索到的文档列表
        """
        start_time = time.time()

        # 1. 选择策略
        if not strategy:
            strategy = self.strategy_selector.select_strategy(query)

        logger.info(f"[检索策略] 使用策略: {strategy}")

        # 2. 根据策略执行检索
        if strategy == "子查询检索":
            docs = self._retrieve_subquery(query)
        elif strategy == "假设问题检索":
            docs = self._retrieve_hyde(query)
        elif strategy == "回溯问题检索":
            docs = self._retrieve_backtracking(query)
        else:  # 默认：直接检索
            docs = self._retrieve_direct(query)

        # 3. 限制文档数量
        if len(docs) > self.max_context_docs:
            docs = docs[:self.max_context_docs]
            logger.info(f"[检索策略] 截断到 {self.max_context_docs} 个文档")

        elapsed = time.time() - start_time
        logger.info(f"[检索策略] 完成，耗时 {elapsed:.2f}s，返回 {len(docs)} 个文档")

        return docs

    def generate_answer(self, query: str, context_docs: List, stream: bool = True):
        """
        基于检索到的文档生成答案

        Args:
            query: 用户查询
            context_docs: 检索到的文档列表
            stream: 是否流式输出

        Returns:
            生成器（流式）或字符串（非流式）
        """
        # 1. 构建上下文
        if context_docs:
            context = "\n\n".join([
                f"【{doc.metadata.get('subject', '法律文档')}】\n{doc.page_content}"
                for doc in context_docs
            ])
            logger.info(f"[答案生成] 上下文包含 {len(context_docs)} 个文档块")
        else:
            context = "未检索到相关法律文档"
            logger.warning(f"[答案生成] 未检索到相关文档")

        # 2. 生成 Prompt
        rag_prompt = self.prompts.rag_prompt()
        full_prompt = rag_prompt.format(context=context, question=query)

        # 3. 调用 LLM 生成答案
        if stream:
            # 流式输出（生成器）
            return self.llm(full_prompt)
        else:
            # 非流式输出
            answer = self._call_llm_sync(full_prompt)
            return answer

    def query(self, query: str, strategy: Optional[str] = None, stream: bool = True):
        """
        完整的查询流程：检索 + 生成

        Args:
            query: 用户查询
            strategy: 检索策略（可选）
            stream: 是否流式输出

        Returns:
            生成器（流式）或字符串（非流式）
        """
        start_time = time.time()

        # 1. 检索文档
        docs = self.retrieve_documents(query, strategy=strategy)

        # 2. 生成答案
        answer = self.generate_answer(query, docs, stream=stream)

        elapsed = time.time() - start_time
        logger.info(f"[RAG 查询] 完成，总耗时 {elapsed:.2f}s")

        return answer


# 测试代码
if __name__ == "__main__":
    print("Enhanced RAG System - Phase 2")
    print("=" * 80)
    print("功能：")
    print("1. 直接检索 - 单一明确问题")
    print("2. 子查询检索 - 复杂多问题")
    print("3. HyDE 检索 - 概念性问题")
    print("4. 回溯检索 - 口语化问题")
    print("=" * 80)
